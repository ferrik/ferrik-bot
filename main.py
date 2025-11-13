#!/usr/bin/env python3
"""
FerrikBot v3.2 - Fixed gevent + asyncio compatibility
"""

import os
import logging
import asyncio
import time
from threading import Thread
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.request import HTTPXRequest

# CRITICAL: Gevent monkey patch FIRST
from gevent import monkey
monkey.patch_all()

# CRITICAL: Fix sniffio for gevent compatibility
import sniffio
_original_current_async_library = sniffio.current_async_library

def patched_current_async_library():
    """Patched sniffio to work with gevent"""
    try:
        return _original_current_async_library()
    except sniffio.AsyncLibraryNotFoundError:
        # Return 'asyncio' when in gevent context
        return 'asyncio'

sniffio.current_async_library = patched_current_async_library

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not found in environment")

# Flask app
app = Flask(__name__)

# Global state
bot_application = None
bot_loop = None
bot_ready = False


def create_application():
    """Create and configure bot application"""
    logger.info("📦 Importing handlers...")
    
    try:
        from app.handlers.commands import start, menu, cart, order, help_command
        logger.info("✅ Commands imported")
        
        from app.handlers.callbacks import button_callback
        logger.info("✅ Callbacks imported")
        
        from app.handlers.messages import handle_text_message
        logger.info("✅ Messages imported")
        
    except ImportError as e:
        logger.error(f"❌ Failed to import handlers: {e}", exc_info=True)
        raise
    
    # Configure request with connection pool
    request = HTTPXRequest(
        connection_pool_size=16,
        pool_timeout=30.0,
        connect_timeout=20.0,
        read_timeout=20.0
    )
    
    # Build application
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request)
        .build()
    )
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("cart", cart))
    application.add_handler(CommandHandler("order", order))
    application.add_handler(CommandHandler("help", help_command))
    
    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Register message handler (must be last)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )
    
    logger.info("✅ All handlers registered")
    return application


def run_bot_async():
    """Run bot in dedicated thread with event loop"""
    global bot_loop, bot_ready
    
    try:
        # Create new event loop for this thread
        bot_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(bot_loop)
        
        logger.info("🔄 Initializing bot application...")
        
        # Initialize application
        bot_loop.run_until_complete(bot_application.initialize())
        
        bot_ready = True
        logger.info("✅ Bot initialized successfully")
        
        # Keep loop running
        bot_loop.run_forever()
        
    except Exception as e:
        logger.error(f"❌ Bot loop error: {e}", exc_info=True)
        bot_ready = False
    finally:
        if bot_loop and not bot_loop.is_closed():
            bot_loop.close()


def init_bot():
    """Initialize bot in background thread"""
    global bot_application
    
    logger.info("=" * 70)
    logger.info("🍕 FERRIKBOT v3.2 STARTING")
    logger.info("=" * 70)
    
    # Create application
    logger.info("🔧 Creating bot application...")
    bot_application = create_application()
    
    # Start bot loop in separate thread
    logger.info("🚀 Starting bot event loop...")
    bot_thread = Thread(target=run_bot_async, daemon=True, name="BotEventLoop")
    bot_thread.start()
    
    # Wait for bot to be ready
    timeout = 10
    start_time = time.time()
    while not bot_ready and (time.time() - start_time) < timeout:
        time.sleep(0.5)
    
    if not bot_ready:
        logger.error("❌ Bot initialization timeout")
        raise RuntimeError("Bot failed to initialize within timeout")
    
    logger.info("=" * 70)
    logger.info("✅ BOT READY!")
    logger.info(f"📍 Webhook URL: {WEBHOOK_URL}/webhook")
    logger.info("=" * 70)


# Flask routes

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'bot': 'FerrikBot v3.2',
        'webhook': f"{WEBHOOK_URL}/webhook",
        'ready': bot_ready
    })


@app.route('/health')
def health():
    """Detailed health check"""
    return jsonify({
        'status': 'healthy' if bot_ready else 'initializing',
        'bot_ready': bot_ready,
        'event_loop_running': bot_loop is not None and bot_loop.is_running() if bot_loop else False,
        'version': '3.2'
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    """Process Telegram webhook updates"""
    if not bot_ready:
        logger.warning("⚠️ Webhook called but bot not ready")
        return jsonify({'ok': False, 'error': 'Bot initializing'}), 503
    
    try:
        # Get update data
        data = request.get_json()
        
        if not data:
            logger.warning("⚠️ Empty webhook data received")
            return jsonify({'ok': False, 'error': 'No data'}), 400
        
        # Parse Telegram update
        update = Update.de_json(data, bot_application.bot)
        
        # Log update info
        if update.message:
            user = update.message.from_user
            text = update.message.text or '[media]'
            logger.info(f"📨 Message from {user.username or user.first_name}: {text[:50]}")
        elif update.callback_query:
            user = update.callback_query.from_user
            data = update.callback_query.data
            logger.info(f"🔘 Callback from {user.username or user.first_name}: {data}")
        
        # Process update in bot's event loop (thread-safe)
        future = asyncio.run_coroutine_threadsafe(
            bot_application.process_update(update),
            bot_loop
        )
        
        # Wait max 5 seconds for processing
        try:
            future.result(timeout=5.0)
            return jsonify({'ok': True}), 200
            
        except asyncio.TimeoutError:
            logger.warning("⚠️ Update processing timeout (>5s)")
            # Return 200 anyway to avoid Telegram retries
            return jsonify({'ok': True}), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        # Return 200 to prevent Telegram from retrying
        return jsonify({'ok': True}), 200


@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    """Set Telegram webhook"""
    if not bot_ready:
        return jsonify({'ok': False, 'error': 'Bot not ready'}), 503
    
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        
        logger.info(f"🔧 Setting webhook to: {webhook_url}")
        
        # Set webhook using thread-safe approach
        future = asyncio.run_coroutine_threadsafe(
            bot_application.bot.set_webhook(
                url=webhook_url,
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True
            ),
            bot_loop
        )
        
        result = future.result(timeout=10.0)
        
        if result:
            logger.info(f"✅ Webhook set successfully: {webhook_url}")
            return jsonify({
                'ok': True,
                'webhook_url': webhook_url,
                'message': 'Webhook set successfully'
            })
        else:
            logger.error("❌ Failed to set webhook")
            return jsonify({'ok': False, 'error': 'Set webhook failed'}), 500
    
    except Exception as e:
        logger.error(f"❌ Set webhook error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/delete_webhook', methods=['GET', 'POST'])
def delete_webhook():
    """Delete Telegram webhook"""
    if not bot_ready:
        return jsonify({'ok': False, 'error': 'Bot not ready'}), 503
    
    try:
        logger.info("🗑️ Deleting webhook...")
        
        future = asyncio.run_coroutine_threadsafe(
            bot_application.bot.delete_webhook(drop_pending_updates=True),
            bot_loop
        )
        
        result = future.result(timeout=10.0)
        
        if result:
            logger.info("✅ Webhook deleted")
            return jsonify({'ok': True, 'message': 'Webhook deleted'})
        else:
            return jsonify({'ok': False, 'error': 'Delete failed'}), 500
    
    except Exception as e:
        logger.error(f"❌ Delete webhook error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/webhook_info')
def webhook_info():
    """Get current webhook information"""
    if not bot_ready:
        return jsonify({'ok': False, 'error': 'Bot not ready'}), 503
    
    try:
        future = asyncio.run_coroutine_threadsafe(
            bot_application.bot.get_webhook_info(),
            bot_loop
        )
        
        info = future.result(timeout=10.0)
        
        return jsonify({
            'ok': True,
            'url': info.url,
            'has_custom_certificate': info.has_custom_certificate,
            'pending_update_count': info.pending_update_count,
            'last_error_date': info.last_error_date.isoformat() if info.last_error_date else None,
            'last_error_message': info.last_error_message,
            'max_connections': info.max_connections,
            'allowed_updates': info.allowed_updates
        })
    
    except Exception as e:
        logger.error(f"❌ Webhook info error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


# Error handlers

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


# Initialize bot on module load
logger.info("🔧 Patching sniffio for gevent compatibility...")

try:
    init_bot()
except Exception as e:
    logger.error(f"❌ Fatal error during bot initialization: {e}", exc_info=True)
    raise


# Main entry point for local development
if __name__ == '__main__':
    logger.info("🏠 Running in development mode")
    app.run(host='0.0.0.0', port=5000, debug=False)
