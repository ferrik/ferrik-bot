"""
🍕 FerrikBot v3.3 - Main ASGI Entry Point
Pure ASGI без Flask/Gunicorn
"""
import os
import logging
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import json

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# КОНФІГУРАЦІЯ
# ============================================================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set!")

# ============================================================================
# ІМПОРТ HANDLERS
# ============================================================================
logger.info("=" * 70)
logger.info("🍕 FERRIKBOT v3.3 STARTING (V1 + V2)")
logger.info("=" * 70)
logger.info("📦 Importing handlers...")

# V1 Handlers (окремі функції)
from app.handlers.commands import (
    start,
    menu,
    cart,
    order,
    profile,
    help_command
)
from app.handlers.callbacks import button_callback
from app.handlers.messages import handle_text_message

# V2 Handlers (імпорт функцій реєстрації)
from app.handlers.start_v2_wow import register_start_v2_wow_handlers
from app.handlers.cart_v2 import register_cart_v2_handlers
from app.handlers.checkout_v2 import register_checkout_v2_handlers
from app.handlers.messages_v2 import register_messages_v2_handlers

# Додаткові V2 handlers (якщо є)
try:
    from app.handlers.restaurant_selector import register_restaurant_selector_handlers
    has_restaurant_selector = True
except ImportError:
    has_restaurant_selector = False
    logger.warning("⚠️ restaurant_selector not found, skipping")

try:
    from app.handlers.menu_v2 import register_menu_v2_handlers
    has_menu_v2 = True
except ImportError:
    has_menu_v2 = False
    logger.warning("⚠️ menu_v2 not found, skipping")

logger.info("✅ Handlers imported")

# ============================================================================
# TELEGRAM BOT ІНІЦІАЛІЗАЦІЯ
# ============================================================================
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# ============================================================================
# РЕЄСТРАЦІЯ V1 HANDLERS (вручну через CommandHandler)
# ============================================================================

# Commands
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu))
application.add_handler(CommandHandler("cart", cart))
application.add_handler(CommandHandler("order", order))
application.add_handler(CommandHandler("profile", profile))
application.add_handler(CommandHandler("help", help_command))

# Callbacks
application.add_handler(CallbackQueryHandler(button_callback))

# Text messages
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

logger.info("✅ V1 handlers registered")

# ============================================================================
# РЕЄСТРАЦІЯ V2 HANDLERS (через функції реєстрації)
# ============================================================================
register_start_v2_wow_handlers(application)
register_cart_v2_handlers(application)
register_checkout_v2_handlers(application)
register_messages_v2_handlers(application)

# Опціональні handlers
if has_restaurant_selector:
    register_restaurant_selector_handlers(application)

if has_menu_v2:
    register_menu_v2_handlers(application)

logger.info("✅ V2 handlers registered")
logger.info("✅ All handlers registered (v1 + v2)")

# ВАЖЛИВО: НЕ викликаємо application.initialize() тут!
# У Pure ASGI mode ініціалізація відбувається автоматично при старті Uvicorn

logger.info("=" * 70)
logger.info("✅ BOT READY!")
logger.info("=" * 70)

# ============================================================================
# ASGI APPLICATION
# ============================================================================

# Keepalive для стабільності
import asyncio
_keepalive_task = None

async def keepalive():
    """Keepalive task щоб тримати бота живим"""
    while True:
        await asyncio.sleep(30)
        logger.debug("💓 Keepalive ping")

async def startup():
    """ASGI startup event"""
    global _keepalive_task
    _keepalive_task = asyncio.create_task(keepalive())
    logger.info("🚀 ASGI startup complete")

async def shutdown():
    """ASGI shutdown event"""
    global _keepalive_task
    if _keepalive_task:
        _keepalive_task.cancel()
    logger.info("🛑 ASGI shutdown complete")

async def app(scope, receive, send):
    """
    Pure ASGI application
    Підтримує GET, HEAD, POST
    """
    
    # Startup on first request
    if not hasattr(app, '_started'):
        app._started = True
        await startup()
    
    path = scope['path']
    method = scope['method']
    
    # ========================================================================
    # HEALTH CHECK ENDPOINT (GET + HEAD)
    # ========================================================================
    if path == '/' and method in ['GET', 'HEAD']:
        response_data = {
            "status": "alive",
            "version": "3.3.0",
            "timestamp": datetime.now().isoformat(),
            "bot": "FerrikBot",
            "mode": "production"
        }
        
        response_body = json.dumps(response_data).encode('utf-8')
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'application/json'],
                [b'content-length', str(len(response_body)).encode()],
            ],
        })
        
        # HEAD запит не повертає body
        if method == 'GET':
            await send({
                'type': 'http.response.body',
                'body': response_body,
            })
        else:
            await send({
                'type': 'http.response.body',
                'body': b'',
            })
        return
    
    # ========================================================================
    # WEBHOOK ENDPOINT (POST)
    # ========================================================================
    elif path == '/webhook' and method == 'POST':
        try:
            # Читання body
            body = b''
            while True:
                message = await receive()
                if message['type'] == 'http.request':
                    body += message.get('body', b'')
                    if not message.get('more_body'):
                        break
            
            # Парсинг JSON
            update_data = json.loads(body.decode('utf-8'))
            logger.info(f"📨 Webhook received: {update_data.get('update_id')}")
            
            # Обробка через Telegram Bot
            try:
                update = Update.de_json(update_data, application.bot)
                await application.process_update(update)
                logger.info(f"✅ Update {update_data.get('update_id')} processed")
            except Exception as process_error:
                logger.error(f"❌ Error processing update: {process_error}", exc_info=True)
                # ВСЕ ОДНО повертаємо 200, щоб Telegram не повторював
            
            # Відповідь OK (завжди 200, навіть якщо була помилка)
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': b'{"ok": true}',
            })
            
        except Exception as e:
            logger.error(f"❌ Webhook fatal error: {e}", exc_info=True)
            # Повертаємо 200 замість 500, щоб не блокувати webhook
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': b'{"ok": true}',
            })
        return
    
    # ========================================================================
    # SET WEBHOOK (GET)
    # ========================================================================
    elif path == '/set_webhook' and method == 'GET':
        try:
            webhook_url = f"{WEBHOOK_URL}/webhook"
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            result = await bot.set_webhook(url=webhook_url)
            
            response = {
                "status": "ok" if result else "error",
                "webhook_url": webhook_url
            }
            
            response_body = json.dumps(response).encode('utf-8')
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [
                    [b'content-type', b'application/json'],
                    [b'content-length', str(len(response_body)).encode()],
                ],
            })
            await send({
                'type': 'http.response.body',
                'body': response_body,
            })
            
        except Exception as e:
            logger.error(f"❌ Set webhook error: {e}")
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': json.dumps({"error": str(e)}).encode(),
            })
        return
    
    # ========================================================================
    # WEBHOOK INFO (GET)
    # ========================================================================
    elif path == '/webhook_info' and method == 'GET':
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            info = await bot.get_webhook_info()
            
            response = {
                "ok": True,
                "result": {
                    "url": info.url,
                    "has_custom_certificate": info.has_custom_certificate,
                    "pending_update_count": info.pending_update_count,
                    "last_error_date": info.last_error_date,
                    "last_error_message": info.last_error_message,
                }
            }
            
            response_body = json.dumps(response, default=str).encode('utf-8')
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [
                    [b'content-type', b'application/json'],
                    [b'content-length', str(len(response_body)).encode()],
                ],
            })
            await send({
                'type': 'http.response.body',
                'body': response_body,
            })
            
        except Exception as e:
            logger.error(f"❌ Webhook info error: {e}")
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': json.dumps({"error": str(e)}).encode(),
            })
        return
    
    # ========================================================================
    # DELETE WEBHOOK (GET)
    # ========================================================================
    elif path == '/delete_webhook' and method == 'GET':
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            result = await bot.delete_webhook()
            
            response = {
                "status": "ok" if result else "error",
                "message": "Webhook deleted"
            }
            
            response_body = json.dumps(response).encode('utf-8')
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [
                    [b'content-type', b'application/json'],
                    [b'content-length', str(len(response_body)).encode()],
                ],
            })
            await send({
                'type': 'http.response.body',
                'body': response_body,
            })
            
        except Exception as e:
            logger.error(f"❌ Delete webhook error: {e}")
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': json.dumps({"error": str(e)}).encode(),
            })
        return
    
    # ========================================================================
    # 404 NOT FOUND
    # ========================================================================
    else:
        await send({
            'type': 'http.response.start',
            'status': 404,
            'headers': [[b'content-type', b'application/json']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'{"error": "Not Found"}',
        })
        return
