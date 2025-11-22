"""
🍕 FerrikBot v3.3 - Main ASGI Entry Point
Pure ASGI без Flask/Gunicorn
"""
import os
import logging
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, ContextTypes
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

# V1 Handlers
from app.handlers import commands, callbacks, messages

# V2 Handlers (WOW mode)
from app.handlers import (
    start_v2_wow,
    restaurant_selector,
    cart_v2,
    checkout_v2,
    messages_v2
)

logger.info("✅ Handlers imported")

# ============================================================================
# TELEGRAM BOT ІНІЦІАЛІЗАЦІЯ
# ============================================================================
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Реєстрація V1 handlers
commands.register_handlers(application)
callbacks.register_handlers(application)
messages.register_handlers(application)
logger.info("✅ V1 handlers registered")

# Реєстрація V2 handlers
start_v2_wow.register_handlers(application)
restaurant_selector.register_handlers(application)
cart_v2.register_handlers(application)
checkout_v2.register_handlers(application)
messages_v2.register_handlers(application)
logger.info("✅ V2 handlers registered")

logger.info("✅ All handlers registered (v1 + v2)")

# Ініціалізація бота
application.initialize()
logger.info("✅ Bot initialized")

logger.info("=" * 70)
logger.info("✅ BOT READY!")
logger.info("=" * 70)

# ============================================================================
# ASGI APPLICATION
# ============================================================================
async def app(scope, receive, send):
    """
    Pure ASGI application
    Підтримує GET, HEAD, POST
    """
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
            
            # Обробка через Telegram Bot
            update = Update.de_json(update_data, application.bot)
            await application.process_update(update)
            
            # Відповідь OK
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
            logger.error(f"❌ Webhook error: {e}", exc_info=True)
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
