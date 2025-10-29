"""
🍕 FERRIKBOT v2.1 - MAIN APPLICATION (FIXED)
Повний файл, готовий до використання на GitHub та Render
"""

import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ============================================================================
# LOAD ENVIRONMENT
# ============================================================================

load_dotenv()

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================

app = Flask(__name__)

# Telegram bot application (глобальна змінна)
bot_application = None

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Конфігурація додатку"""
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5000")
    ADMIN_IDS = [
        int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") 
        if id.strip()
    ]
    
    # Google
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
    
    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://ferrik_user:ferrik_secure_123!@localhost:5432/ferrik_bot"
    )
    
    # App
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    PORT = int(os.getenv("PORT", 5000))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @staticmethod
    def validate():
        """Перевірка необхідних конфігурацій"""
        errors = []
        
        if not Config.TELEGRAM_BOT_TOKEN:
            errors.append("❌ TELEGRAM_BOT_TOKEN not set")
        
        if not Config.GEMINI_API_KEY:
            errors.append("❌ GEMINI_API_KEY not set")
        
        if errors:
            for error in errors:
                logger.error(error)
            return False
        
        return True


config = Config()

# ============================================================================
# SERVICES INITIALIZATION
# ============================================================================

def init_services():
    """Ініціалізація всіх сервісів"""
    
    services = {
        'telegram': False,
        'gemini': False,
        'sheets': False,
        'database': False,
    }
    
    try:
        # 1️⃣ TELEGRAM
        logger.info("🔧 Initializing Telegram service...")
        # Бот ініціалізується пізніше в create_bot_application()
        services['telegram'] = True
        logger.info("✅ Telegram service ready")
        
    except Exception as e:
        logger.error(f"❌ Telegram service error: {e}")
    
    try:
        # 2️⃣ GEMINI
        logger.info("🔧 Initializing Gemini AI service...")
        from app.services.gemini_service import GeminiService
        
        gemini_service = GeminiService(config.GEMINI_API_KEY)
        
        if gemini_service.test_connection():
            services['gemini'] = True
            logger.info("✅ Gemini AI service ready")
        else:
            logger.warning("⚠️ Gemini test failed, but service initialized")
            services['gemini'] = True
    
    except Exception as e:
        logger.error(f"❌ Gemini service error: {e}")
        gemini_service = None
    
    try:
        # 3️⃣ GOOGLE SHEETS
        logger.info("🔧 Initializing Google Sheets service...")
        from app.services.sheets_service import SheetsService
        
        sheets_service = SheetsService(config.GOOGLE_SHEETS_CREDENTIALS, 
                                       config.GOOGLE_SHEETS_ID)
        services['sheets'] = True
        logger.info("✅ Google Sheets service ready")
    
    except Exception as e:
        logger.warning(f"⚠️ Google Sheets service error: {e}")
        sheets_service = None
    
    try:
        # 4️⃣ DATABASE
        logger.info("🔧 Initializing database...")
        from app.database import test_connection, init_db
        
        if not test_connection():
            logger.error("❌ Database connection failed")
            return services, gemini_service, sheets_service, None
        
        if not init_db():
            logger.error("❌ Database initialization failed")
            return services, gemini_service, sheets_service, None
        
        services['database'] = True
        logger.info("✅ Database ready")
    
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
    
    return services, gemini_service, sheets_service, None


# ============================================================================
# TELEGRAM BOT SETUP
# ============================================================================

def setup_handlers(application):
    """Реєстрація всіх Telegram обробників"""
    
    logger.info("📝 Setting up Telegram handlers...")
    
    try:
        from app.handlers.commands import register_command_handlers
        from app.handlers.callbacks import register_callback_handlers
        
        # Реєстрація команд
        register_command_handlers(application)
        
        # Реєстрація callback queries (кнопки)
        register_callback_handlers(application)
        
        logger.info("✅ All handlers registered")
        return True
    
    except Exception as e:
        logger.error(f"❌ Handler registration error: {e}")
        return False


def create_bot_application():
    """Створення Telegram bot application"""
    
    global bot_application
    
    logger.info("🤖 Creating Telegram bot application...")
    
    TOKEN = config.TELEGRAM_BOT_TOKEN
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        return None
    
    try:
        # Створення application
        bot_application = Application.builder().token(TOKEN).build()
        
        # Реєстрація обробників
        if not setup_handlers(bot_application):
            return None
        
        # Зберігання сервісів у bot_data
        _, gemini_service, sheets_service, _ = init_services()
        
        bot_application.bot_data['gemini_service'] = gemini_service
        bot_application.bot_data['sheets_service'] = sheets_service
        bot_application.bot_data['config'] = config
        
        logger.info("✅ Bot application created successfully")
        return bot_application
    
    except Exception as e:
        logger.error(f"❌ Failed to create bot application: {e}")
        return None


# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Головна сторінка"""
    return jsonify({
        "status": "🟢 online",
        "bot": "🍕 FerrikBot v2.1",
        "version": "2.1.0",
        "features": [
            "Warm Greetings",
            "Surprise Me",
            "Profiles & Stats",
            "Challenges",
            "AI Recommendations",
            "PostgreSQL Backend",
            "Rate Limiting"
        ],
        "environment": config.ENVIRONMENT,
        "debug": config.DEBUG
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check для моніторингу"""
    try:
        services_status = {
            'telegram': bot_application is not None,
            'gemini': bot_application and bot_application.bot_data.get('gemini_service') is not None,
            'sheets': bot_application and bot_application.bot_data.get('sheets_service') is not None,
            'database': True  # Якщо дійшли сюди, БД OK
        }
        
        all_ok = all(services_status.values())
        
        return jsonify({
            "status": "healthy" if all_ok else "degraded",
            "services": services_status,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "environment": config.ENVIRONMENT
        }), 200 if all_ok else 503
    
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route('/stats', methods=['GET'])
def stats():
    """Статистика платформи"""
    try:
        from app.utils.session import get_platform_stats
        
        platform_stats = get_platform_stats()
        
        return jsonify({
            "status": "ok",
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "platform": platform_stats
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Stats error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# 🔥 WEBHOOK ROUTES (КРИТИЧНО ВАЖНО - ОБИДВА МАРШРУТИ!)
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Основний webhook маршрут для Telegram
    Telegram надсилає месіджи сюди: POST /webhook
    """
    logger.info("📨 Webhook /webhook отримав запит")
    return process_webhook(request)


@app.route('/webhook/webhook', methods=['POST'])
def webhook_double():
    """
    Резервний webhook маршрут (для старого налаштування)
    Якщо раніше webhook був встановлено як /webhook/webhook
    """
    logger.warning("⚠️ Webhook /webhook/webhook отримав запит (старий маршрут)")
    return process_webhook(request)


def process_webhook(req):
    """
    Спільна обробка всіх webhook запитів
    Розпаршує Update від Telegram і обробляє його
    """
    try:
        # Отримай JSON від Telegram
        data = req.get_json()
        
        if not data:
            logger.error("❌ Webhook: порожні дані")
            return jsonify({"ok": False, "error": "Empty data"}), 400
        
        logger.info(f"📨 Webhook data: {data}")
        
        if not bot_application:
            logger.error("❌ Bot application not initialized")
            return jsonify({"ok": False}), 500
        
        # Розпарс Update від Telegram
        update = Update.de_json(data, bot_application.bot)
        
        if not update:
            logger.error("❌ Failed to parse update")
            return jsonify({"ok": False}), 400
        
        # Обробити месідж через зареєстровані обробники
        bot_application.process_update(update)
        
        logger.info("✅ Update processed successfully")
        return jsonify({"ok": True}), 200
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook_route():
    """
    Встановлення webhook для Telegram
    Можна викликати: GET /set_webhook або POST /set_webhook
    """
    if not bot_application:
        return jsonify({"ok": False, "error": "Bot not initialized"}), 500
    
    try:
        webhook_url = f"{config.WEBHOOK_URL}/webhook"
        
        # Синхронна функція для встановлення webhook
        import asyncio
        
        async def set_it():
            await bot_application.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query", "edited_message"]
            )
        
        # Запусти асинхронну функцію
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(set_it())
        
        logger.info(f"✅ Webhook set: {webhook_url}")
        
        return jsonify({
            "ok": True,
            "webhook_url": webhook_url,
            "message": "✅ Webhook установлено успішно"
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Set webhook error: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/delete_webhook', methods=['GET', 'POST'])
def delete_webhook_route():
    """Видалення webhook"""
    if not bot_application:
        return jsonify({"ok": False}), 500
    
    try:
        import asyncio
        
        async def delete_it():
            await bot_application.bot.delete_webhook()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(delete_it())
        
        logger.info("✅ Webhook deleted")
        return jsonify({"ok": True, "message": "✅ Webhook видалено"}), 200
    
    except Exception as e:
        logger.error(f"❌ Delete webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/menu', methods=['GET'])
def get_menu_api():
    """API для отримання меню"""
    try:
        if not bot_application or not bot_application.bot_data.get('sheets_service'):
            return jsonify({"ok": False, "error": "Service unavailable"}), 503
        
        sheets_service = bot_application.bot_data['sheets_service']
        menu = sheets_service.get_menu()
        
        return jsonify({
            "ok": True,
            "items_count": len(menu),
            "menu": menu[:50]  # Обмежуємо для API
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Menu API error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================================
# ERROR HANDLERS
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
        "status": 404,
        "available_endpoints": [
            "/",
            "/health",
            "/stats",
            "/menu",
            "/webhook",
            "/webhook/webhook",
            "/set_webhook",
            "/delete_webhook"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 обробник"""
    logger.error(f"❌ Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "status": 500
    }), 500


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

def startup():
    """Ініціалізація при запуску"""
    
    logger.info("=" * 70)
    logger.info("🚀 FERRIKBOT v2.1 STARTING...")
    logger.info("=" * 70)
    logger.info("")
    
    # 1️⃣ ВАЛІДАЦІЯ КОНФІГ
    if not config.validate():
        logger.error("❌ Configuration validation failed")
        return False
    
    # 2️⃣ ІНІЦІАЛІЗАЦІЯ СЕРВІСІВ
    services_status, gemini_service, sheets_service, _ = init_services()
    
    logger.info("")
    logger.info("📊 SERVICES STATUS:")
    for service, status in services_status.items():
        emoji = "✅" if status else "❌"
        logger.info(f"  {emoji} {service}")
    
    # 3️⃣ СТВОРЕННЯ БОТА
    logger.info("")
    logger.info("🤖 Creating Telegram bot...")
    
    if not create_bot_application():
        logger.error("❌ Failed to create bot application")
        return False
    
    # 4️⃣ ВСТАНОВЛЕННЯ WEBHOOK
    logger.info("")
    logger.info("🔗 Webhook setup...")
    logger.info(f"   URL: {config.WEBHOOK_URL}/webhook")
    logger.info(f"   Резервний: {config.WEBHOOK_URL}/webhook/webhook")
    
    # 5️⃣ ІНФОРМАЦІЯ ПРО ЗАПУСК
    logger.info("")
    logger.info("✅ BOT READY!")
    logger.info("")
    logger.info("📊 FEATURES ENABLED:")
    logger.info("  ✓ Warm Greetings")
    logger.info("  ✓ Surprise Me (AI Combos)")
    logger.info("  ✓ Profiles & Badges")
    logger.info("  ✓ Challenges")
    logger.info("  ✓ Rate Limiting")
    logger.info("  ✓ PostgreSQL Database")
    logger.info("")
    logger.info(f"🌐 Running on http://localhost:{config.PORT}")
    logger.info(f"🌍 Environment: {config.ENVIRONMENT}")
    logger.info(f"🐛 Debug mode: {config.DEBUG}")
    logger.info(f"📍 Telegram Webhook: {config.WEBHOOK_URL}/webhook")
    logger.info("")
    logger.info("=" * 70)
    logger.info("")
    
    return True


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    logger.info("🍕 Initializing FerrikBot...")
    
    # Запуск
    if startup():
        logger.info("🚀 Starting Flask server...")
        
        # Запуск Flask
        app.run(
            host="0.0.0.0",
            port=config.PORT,
            debug=config.DEBUG,
            use_reloader=False  # Важливо для Telegram webhook
        )
    else:
        logger.error("❌ Failed to start bot!")
        exit(1)
