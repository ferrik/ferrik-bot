#!/usr/bin/env python3
"""
FerrikBot v3.2 - Pure async with uvicorn
Clean solution without gevent
"""

import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.request import HTTPXRequest

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
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not found")

# Global bot application
bot_application = None


async def create_application():
    """Create and configure bot application"""
    logger.info("📦 Importing handlers...")
    
    try:
        from app.handlers.commands import start, menu, cart, order, help_command
        from app.handlers.callbacks import button_callback
        from app.handlers.messages import handle_text_message
        logger.info("✅ Handlers imported")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}", exc_info=True)
        raise
    
    # Configure request
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
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("cart", cart))
    application.add_handler(CommandHandler("order", order))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )
    
    logger.info("✅ All handlers registered")
    
    # Initialize
    await application.initialize()
    logger.info("✅ Bot initialized")
    
    return application


# ASGI application
async def app(scope, receive, send):
    """ASGI application"""
    global bot_application
    
    # Initialize bot on first request
    if bot_application is None:
        logger.info("=" * 70)
        logger.info("🍕 FERRIKBOT v3.2 STARTING")
        logger.info("=" * 70)
        bot_application = await create_application()
        logger.info("=" * 70)
        logger.info("✅ BOT READY!")
        logger.info("=" * 70)
    
    # Only handle HTTP requests
    if scope['type'] != 'http':
        return
    
    path = scope['path']
    method = scope['method']
    
    # Route handling
    if path == '/' and method == 'GET':
        await handle_index(scope, receive, send)
    
    elif path == '/webhook' and method == 'POST':
        await handle_webhook(scope, receive, send)
    
    elif path == '/set_webhook' and method in ['GET', 'POST']:
        await handle_set_webhook(scope, receive, send)
    
    elif path == '/webhook_info' and method == 'GET':
        await handle_webhook_info(scope, receive, send)
    
    else:
        await send_response(send, 404, {'error': 'Not found'})


async def handle_index(scope, receive, send):
    """Health check endpoint"""
    await send_response(send, 200, {
        'status': 'ok',
        'bot': 'FerrikBot v3.2',
        'webhook': f"{WEBHOOK_URL}/webhook"
    })


async def handle_webhook(scope, receive, send):
    """Process Telegram webhook"""
    try:
        # Read request body
        body = b''
        while True:
            message = await receive()
            if message['type'] == 'http.request':
                body += message.get('body', b'')
                if not message.get('more_body'):
                    break
        
        # Parse JSON
        import json
        data = json.loads(body.decode('utf-8'))
        
        # Parse Telegram update
        update = Update.de_json(data, bot_application.bot)
        
        # Log
        if update.message:
            user = update.message.from_user
            text = update.message.text or '[media]'
            logger.info(f"📨 {user.username or user.first_name}: {text[:50]}")
        elif update.callback_query:
            user = update.callback_query.from_user
            logger.info(f"🔘 {user.username or user.first_name}: {update.callback_query.data}")
        
        # Process update
        await bot_application.process_update(update)
        
        await send_response(send, 200, {'ok': True})
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        await send_response(send, 200, {'ok': True})  # Return 200 anyway


async def handle_set_webhook(scope, receive, send):
    """Set webhook"""
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        
        result = await bot_application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=['message', 'callback_query'],
            drop_pending_updates=True
        )
        
        if result:
            logger.info(f"✅ Webhook set: {webhook_url}")
            await send_response(send, 200, {
                'ok': True,
                'url': webhook_url
            })
        else:
            await send_response(send, 500, {'ok': False})
            
    except Exception as e:
        logger.error(f"❌ Set webhook error: {e}")
        await send_response(send, 500, {
            'ok': False,
            'error': str(e)
        })


async def handle_webhook_info(scope, receive, send):
    """Get webhook info"""
    try:
        info = await bot_application.bot.get_webhook_info()
        
        await send_response(send, 200, {
            'ok': True,
            'url': info.url,
            'pending_updates': info.pending_update_count,
            'last_error': info.last_error_message
        })
        
    except Exception as e:
        logger.error(f"❌ Webhook info error: {e}")
        await send_response(send, 500, {
            'ok': False,
            'error': str(e)
        })


async def send_response(send, status, data):
    """Send JSON response"""
    import json
    
    body = json.dumps(data).encode('utf-8')
    
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': [
            [b'content-type', b'application/json'],
            [b'content-length', str(len(body)).encode()],
        ],
    })
    
    await send({
        'type': 'http.response.body',
        'body': body,
    })


# For local development
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
