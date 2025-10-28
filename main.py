"""
🤖 FerrikFoot Bot - головний файл
Telegram бот для замовлення їжі з AI та Google Sheets
"""
import os
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from app.config import load_config
from app.handlers import (
    start_handler,
    menu_handler,
    cart_handler,
    order_handler,
    help_handler,
    message_handler,
    callback_query_handler,
    cancel_handler
)
from app.services.sheets_service import SheetsService
from app.services.gemini_service import GeminiService

# Ініціалізація логування
logger = logging.getLogger(__name__)

# Завантаження конфігурації
telegram_config, gemini_config, sheets_config, app_config = load_config()

# Flask app
app = Flask(__name__)

# Telegram bot application
bot_application = None

# Сервіси
sheets_service = None
gemini_service = None


def init_services():
    """Ініціалізація сервісів"""
    global sheets_service, gemini_service
    
    try:
        # Google Sheets
        sheets_service = SheetsService(sheets_config)
        logger.info("✅ Google Sheets service initialized")
        
        # Gemini AI
        gemini_service = GeminiService(gemini_config)
        logger.info("✅ Gemini AI service initialized")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        return False


def setup_handlers(application: Application):
    """Налаштування обробників команд"""
    
    # Команди
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("menu", menu_handler))
    application.add_handler(CommandHandler("cart", cart_handler))
    application.add_handler(CommandHandler("order", order_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("cancel", cancel_handler))
    
    # Callback queries (inline кнопки)
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Текстові повідомлення (AI обробка)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        message_handler
    ))
    
    logger.info("✅ Handlers registered")


async def setup_webhook(application: Application):
    """Налаштування webhook для Render"""
    if not telegram_config.webhook_url:
        logger.warning("⚠️ WEBHOOK_URL not set, skipping webhook setup")
        return
    
    try:
        await application.bot.set_webhook(
            url=f"{telegram_config.webhook_url}/webhook",
            allowed_updates=["message", "callback_query"]
        )
        logger.info(f"✅ Webhook set: {telegram_config.webhook_url}/webhook")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")


def create_bot_application():
    """Створення Telegram bot application"""
    global bot_application
    
    # Створюємо application
    bot_application = (
        Application.builder()
        .token(telegram_config.bot_token)
        .build()
    )
    
    # Налаштовуємо обробники
    setup_handlers(bot_application)
    
    # Зберігаємо сервіси в bot_data для доступу з handlers
    bot_application.bot_data['sheets_service'] = sheets_service
    bot_application.bot_data['gemini_service'] = gemini_service
    bot_application.bot_data['app_config'] = app_config
    
    logger.info("✅ Bot application created")
    
    return bot_application


# ============================================================================
# Flask routes
# ============================================================================

@app.route('/')
def index():
    """Головна сторінка"""
    return jsonify({
        "status": "online",
        "service": "FerrikFoot Bot",
        "version": "2.0",
        "environment": app_config.environment
    })


@app.route('/health')
def health():
    """Health check для Render"""
    return jsonify({
        "status": "healthy",
        "services": {
            "telegram": bot_application is not None,
            "sheets": sheets_service is not None,
            "gemini": gemini_service is not None
        }
    })


@app.route('/webhook', methods=['POST'])
async def webhook():
    """Webhook endpoint для Telegram"""
    try:
        # Отримуємо update від Telegram
        update = Update.de_json(request.get_json(), bot_application.bot)
        
        # Обробляємо update
        await bot_application.process_update(update)
        
        return jsonify({"ok": True})
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/set_webhook', methods=['GET', 'POST'])
async def set_webhook_route():
    """Ручне встановлення webhook"""
    if not telegram_config.webhook_url:
        return jsonify({
            "ok": False,
            "error": "WEBHOOK_URL not configured"
        }), 400
    
    try:
        await setup_webhook(bot_application)
        return jsonify({
            "ok": True,
            "webhook_url": f"{telegram_config.webhook_url}/webhook"
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.route('/delete_webhook', methods=['GET', 'POST'])
async def delete_webhook_route():
    """Видалення webhook"""
    try:
        await bot_application.bot.delete_webhook()
        return jsonify({"ok": True, "message": "Webhook deleted"})
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# ============================================================================
# Startup
# ============================================================================

def startup():
    """Ініціалізація при запуску"""
    logger.info("=" * 60)
    logger.info("🚀 Starting FerrikFoot Bot")
    logger.info("=" * 60)
    
    # Ініціалізація сервісів
    if not init_services():
        logger.error("❌ Failed to start: services initialization failed")
        return False
    
    # Створення bot application
    create_bot_application()
    
    # Встановлення webhook (асинхронно при першому запиті)
    logger.info("✅ Bot started successfully")
    logger.info(f"🌐 Running on {app_config.host}:{app_config.port}")
    logger.info("=" * 60)
    
    return True


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    # Запуск
    if startup():
        # Flask server
        app.run(
            host=app_config.host,
            port=app_config.port,
            debug=app_config.debug
        )
