"""
🤖 FerrikBot v3.4 - Main Entry Point
Pure ASGI + FastAPI + Telegram Bot + Mini App API
"""
import os
import json
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENVIRONMENT
# ============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://ferrik-bot-zvev.onrender.com")
PORT = int(os.getenv("PORT", 8000))

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не встановлено!")

# ============================================================================
# TELEGRAM BOT SETUP
# ============================================================================
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# V1 Handlers
from app.handlers.commands import start, menu, cart, order, profile, help_command
from app.handlers.callbacks import button_callback
from app.handlers.messages import handle_text_message

# V2 Handlers
from app.handlers.start_v2_wow import register_start_v2_wow_handlers
from app.handlers.cart_v2 import register_cart_v2_handlers
from app.handlers.checkout_v2 import register_checkout_v2_handlers
from app.handlers.menu_v2 import register_menu_v2_handlers
from app.handlers.messages_v2 import register_messages_v2_handlers

# Реєстрація handlers (ПОРЯДОК ВАЖЛИВИЙ!)
# 1. V1 Commands
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu))
application.add_handler(CommandHandler("cart", cart))
application.add_handler(CommandHandler("order", order))
application.add_handler(CommandHandler("profile", profile))
application.add_handler(CommandHandler("help", help_command))

# 2. V2 Handlers (ПЕРЕД V1 callbacks!)
register_start_v2_wow_handlers(application)
register_cart_v2_handlers(application)
register_checkout_v2_handlers(application)
register_menu_v2_handlers(application)
register_messages_v2_handlers(application)

# 3. V1 Callbacks (fallback)
application.add_handler(CallbackQueryHandler(button_callback))

# 4. V1 Text handlers
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

# ============================================================================
# FASTAPI SETUP
# ============================================================================
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

fastapi_app = FastAPI(
    title="FerrikBot API",
    version="3.4.0",
    description="API для Telegram Mini App"
)

# CORS для Mini App
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшені обмежити до конкретних доменів
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Додати Mini App API роутер
from app.api.miniapp_api import router as miniapp_router
fastapi_app.include_router(miniapp_router)

# FastAPI root
@fastapi_app.get("/")
async def root():
    return {
        "status": "alive",
        "bot": "FerrikBot v3.4",
        "api": "Mini App API",
        "endpoints": {
            "menu": "/api/v1/menu",
            "mood": "/api/v1/menu/mood/{tag}",
            "restaurants": "/api/v1/restaurants",
            "order": "/api/v1/order (POST)",
            "health": "/api/v1/health"
        }
    }

# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================
async def startup():
    """Ініціалізація при запуску"""
    try:
        await application.initialize()
        await application.start()
        logger.info("✅ Telegram Application initialized")
        
        # Встановити webhook
        webhook_url = f"{WEBHOOK_URL}/webhook"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook set to: {webhook_url}")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

async def shutdown():
    """Очищення при зупинці"""
    try:
        await application.stop()
        await application.shutdown()
        logger.info("✅ Application stopped")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")

# ============================================================================
# PURE ASGI APPLICATION
# ============================================================================
async def app(scope, receive, send):
    """
    Pure ASGI application
    Роутинг:
    - /api/* → FastAPI
    - /webhook → Telegram webhook
    - / → Health check
    """
    
    # Startup on first request
    if not hasattr(app, '_started'):
        app._started = True
        await startup()
    
    request_type = scope['type']
    
    if request_type != 'http':
        return
    
    path = scope.get('path', '/')
    method = scope.get('method', 'GET')
    
    # ========================================================================
    # API ROUTES → FastAPI
    # ========================================================================
    if path.startswith('/api/'):
        await fastapi_app(scope, receive, send)
        return
    
    # ========================================================================
    # TELEGRAM WEBHOOK
    # ========================================================================
    if path == '/webhook' and method == 'POST':
        try:
            # Отримати body
            body = b''
            while True:
                message = await receive()
                if message['type'] == 'http.request':
                    body += message.get('body', b'')
                    if not message.get('more_body', False):
                        break
            
            # Парсити JSON
            update_data = json.loads(body.decode('utf-8'))
            update = Update.de_json(update_data, application.bot)
            
            # Обробити update
            await application.process_update(update)
            
            # Відповідь
            response_body = json.dumps({"ok": True}).encode()
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'application/json']],
            })
            
            await send({
                'type': 'http.response.body',
                'body': response_body,
            })
            
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
            
            error_body = json.dumps({"ok": False, "error": str(e)}).encode()
            
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [[b'content-type', b'application/json']],
            })
            
            await send({
                'type': 'http.response.body',
                'body': error_body,
            })
        
        return
    
    # ========================================================================
    # HEALTH CHECK & WEBHOOK INFO
    # ========================================================================
    if path == '/' and method in ['GET', 'HEAD']:
        response_body = json.dumps({
            "status": "alive",
            "bot": "FerrikBot v3.4",
            "webhook": f"{WEBHOOK_URL}/webhook",
            "api": "Mini App API available at /api/v1"
        }).encode()
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'application/json']],
        })
        
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
    
    if path == '/webhook_info' and method == 'GET':
        try:
            webhook_info = await application.bot.get_webhook_info()
            
            response_body = json.dumps({
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count,
                "last_error_date": webhook_info.last_error_date,
                "last_error_message": webhook_info.last_error_message,
                "max_connections": webhook_info.max_connections,
                "allowed_updates": webhook_info.allowed_updates,
            }, default=str).encode()
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'application/json']],
            })
            
            await send({
                'type': 'http.response.body',
                'body': response_body,
            })
            
        except Exception as e:
            logger.error(f"❌ Error getting webhook info: {e}")
            error_body = json.dumps({"error": str(e)}).encode()
            
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [[b'content-type', b'application/json']],
            })
            
            await send({
                'type': 'http.response.body',
                'body': error_body,
            })
        
        return
    
    if path == '/set_webhook' and method == 'GET':
        try:
            webhook_url = f"{WEBHOOK_URL}/webhook"
            await application.bot.set_webhook(webhook_url)
            
            response_body = json.dumps({
                "ok": True,
                "message": f"Webhook set to {webhook_url}"
            }).encode()
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'application/json']],
            })
            
            await send({
                'type': 'http.response.body',
                'body': response_body,
            })
            
        except Exception as e:
            logger.error(f"❌ Error setting webhook: {e}")
            error_body = json.dumps({"ok": False, "error": str(e)}).encode()
            
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [[b'content-type', b'application/json']],
            })
            
            await send({
                'type': 'http.response.body',
                'body': error_body,
            })
        
        return
    
    if path == '/delete_webhook' and method == 'GET':
        try:
            await application.bot.delete_webhook()
            
            response_body = json.dumps({
                "ok": True,
                "message": "Webhook deleted"
            }).encode()
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'application/json']],
            })
            
            await send({
                'type': 'http.response.body',
                'body': response_body,
            })
            
        except Exception as e:
            logger.error(f"❌ Error deleting webhook: {e}")
            error_body = json.dumps({"ok": False, "error": str(e)}).encode()
            
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [[b'content-type', b'application/json']],
            })
            
            await send({
                'type': 'http.response.body',
                'body': error_body,
            })
        
        return
    
    # ========================================================================
    # 404 NOT FOUND
    # ========================================================================
    response_body = json.dumps({
        "error": "Not Found",
        "path": path
    }).encode()
    
    await send({
        'type': 'http.response.start',
        'status': 404,
        'headers': [[b'content-type', b'application/json']],
    })
    
    await send({
        'type': 'http.response.body',
        'body': response_body,
    })

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting FerrikBot v3.4...")
    logger.info(f"📍 Webhook URL: {WEBHOOK_URL}/webhook")
    logger.info(f"📍 API URL: {WEBHOOK_URL}/api/v1")
    logger.info(f"🔧 Port: {PORT}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
