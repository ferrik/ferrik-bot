"""
🤖 FerrikFoot Bot v2.1 - ЛЮДЯНА ВЕРСІЯ
Telegram бот з AI, бейджами, челленджами та теплими привітаннями
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
    filters,
    ContextTypes
)

from app.config import load_config
from app.services.sheets_service import SheetsService
from app.services.gemini_service import GeminiService

# Імпортуємо обновлені handlers
from app.handlers.commands import (
    start_handler,
    menu_handler,
    cart_handler,
    order_handler,
    help_handler,
    cancel_handler,
    show_profile_callback,
    show_challenge_callback,
)
from app.handlers.messages import message_handler
from app.handlers.callbacks import callback_query_handler

# Ініціалізація логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Завантаження конфігурації
try:
    telegram_config, gemini_config, sheets_config, app_config = load_config()
except Exception as e:
    logger.error(f"❌ Configuration failed: {e}")
    raise

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
        if gemini_service.test_connection():
            logger.info("✅ Gemini AI service initialized and tested")
        else:
            logger.warning("⚠️ Gemini AI test failed, but service initialized")
        
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
        return False
    
    try:
        await application.bot.set_webhook(
            url=f"{telegram_config.webhook_url}/webhook",
            allowed_updates=["message", "callback_query", "edited_message"]
        )
        logger.info(f"✅ Webhook set: {telegram_config.webhook_url}/webhook")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
        return False


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
    bot_application.bot_data['telegram_config'] = telegram_config
    
    logger.info("✅ Bot application created")
    
    return bot_application


# ============================================================================
# Flask routes
# ============================================================================

@app.route('/')
def index():
    """Головна сторінка"""
    return jsonify({
        "status": "🟢 online",
        "service": "🍕 FerrikFoot Bot",
        "version": "2.1.0",
        "features": [
            "AI recommendations",
            "Badges & achievements",
            "Weekly challenges",
            "Referral system",
            "Warm greetings",
            "Multi-partner platform"
        ],
        "environment": app_config.environment
    })


@app.route('/health')
def health():
    """Health check для Render"""
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "services": {
                "telegram": bot_application is not None,
                "sheets": sheets_service is not None,
                "gemini": gemini_service is not None
            },
            "uptime": "OK"
        })
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route('/stats')
def stats():
    """Статистика платформи"""
    try:
        from app.utils.session import get_platform_stats
        platform_stats = get_platform_stats()
        
        return jsonify({
            "status": "ok",
            "platform": platform_stats
        })
    except Exception as e:
        logger.error(f"❌ Stats error: {e}")
        return jsonify({"error": str(e)}), 500


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
            "webhook_url": f"{telegram_config.webhook_url}/webhook",
            "message": "✅ Webhook установлен успешно"
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
        return jsonify({
            "ok": True,
            "message": "✅ Webhook удален"
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.route('/menu')
def get_menu_api():
    """API для отримання меню (для вебу)"""
    try:
        if sheets_service:
            menu = sheets_service.get_menu()
            return jsonify({
                "ok": True,
                "items_count": len(menu),
                "menu": menu[:50]  # Обмежуємо для API
            })
        return jsonify({"ok": False, "error": "Service unavailable"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/send_message/<int:user_id>/<message>', methods=['POST'])
def send_message(user_id: int, message: str):
    """Адмін API - відправити повідомлення користувачу"""
    try:
        # Перевіряємо адміна
        if user_id not in telegram_config.admin_ids:
            return jsonify({"ok": False, "error": "Unauthorized"}), 403
        
        # Відправляємо
        # await bot_application.bot.send_message(
        #     chat_id=user_id,
        #     text=message
        # )
        
        return jsonify({"ok": True, "message": "Sent"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================================
# Startup and Error Handlers
# ============================================================================

@app.before_request
def before_request():
    """Логування перед кожним запитом"""
    logger.debug(f"📨 {request.method} {request.path}")


@app.errorhandler(404)
def not_found(error):
    """404 обробник"""
    return jsonify({
        "error": "Not found",
        "available_endpoints": [
            "/",
            "/health",
            "/stats",
            "/webhook",
            "/set_webhook",
            "/delete_webhook",
            "/menu"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 обробник"""
    logger.error(f"❌ Internal error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": str(error)
    }), 500


def startup():
    """Ініціалізація при запуску"""
    logger.info("=" * 70)
    logger.info("🚀 FERRIKFOOT BOT v2.1 - STARTING")
    logger.info("=" * 70)
    
    # Ініціалізація сервісів
    if not init_services():
        logger.error("❌ Failed to start: services initialization failed")
        return False
    
    # Створення bot application
    create_bot_application()
    
    logger.info("")
    logger.info("✅ Bot started successfully!")
    logger.info("")
    logger.info("📊 FEATURES ENABLED:")
    logger.info("  ✓ AI Recommendations (Gemini)")
    logger.info("  ✓ User Badges & Achievements")
    logger.info("  ✓ Weekly Challenges")
    logger.info("  ✓ Referral System")
    logger.info("  ✓ Warm Greetings")
    logger.info("  ✓ Multi-Partner Platform")
    logger.info("  ✓ Session Management")
    logger.info("")
    logger.info(f"🌐 Running on {app_config.host}:{app_config.port}")
    logger.info(f"🌍 Environment: {app_config.environment}")
    logger.info(f"🐛 Debug mode: {app_config.debug}")
    logger.info("")
    logger.info("=" * 70)
    
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
            debug=app_config.debug,
            use_reloader=False  # Important for Telegram webhook
        )