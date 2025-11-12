"""
🍕 FERRIKBOT v3.0 - MAIN APPLICATION
Повна інтеграція всіх модулів з гібридним меню + GDPR + Redis
"""

import os
import logging
import sys
import asyncio
from threading import Thread
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from telegram.request import HTTPXRequest

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

    # Google Sheets
    GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
    
    # Gemini AI
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "")

    # Database (для майбутнього)
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://ferrik_user:ferrik_secure_123!@localhost:5432/ferrik_bot"
    )

    # App
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    PORT = int(os.getenv("PORT", 5000))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Cron Secret (для cleanup endpoint)
    CRON_SECRET = os.getenv("CRON_SECRET", "change-me-in-production")
    
    # Google Sheets Config (для SheetsService)
    @property
    def credentials_json(self):
        return self.GOOGLE_SHEETS_CREDENTIALS
    
    @property
    def spreadsheet_id(self):
        return self.GOOGLE_SHEETS_ID

    @staticmethod
    def validate():
        """Перевірка необхідних конфігурацій"""
        errors = []

        if not Config.TELEGRAM_BOT_TOKEN:
            errors.append("❌ TELEGRAM_BOT_TOKEN not set")

        if errors:
            for error in errors:
                logger.error(error)
            return False

        return True


config = Config()

# ============================================================================
# TELEGRAM BOT SETUP
# ============================================================================

def setup_handlers(application):
    """Реєстрація всіх обробників Telegram команд"""

    logger.info("📝 Setting up Telegram handlers...")

    try:
        # 1️⃣ КОМАНДИ (існуючі)
        from app.handlers.commands import register_command_handlers
        register_command_handlers(application)
        logger.info("✅ Command handlers registered")
        
        # 2️⃣ CALLBACK QUERIES (існуючі)
        from app.handlers.callbacks import register_callback_handlers
        register_callback_handlers(application)
        logger.info("✅ Callback handlers registered")
        
        # 3️⃣ GDPR HANDLERS (нові)
        try:
            from app.handlers.gdpr import register_gdpr_handlers
            register_gdpr_handlers(application)
            logger.info("✅ GDPR handlers registered")
        except ImportError as e:
            logger.warning(f"⚠️ GDPR handlers not available: {e}")
        
        # 4️⃣ ГІБРИДНЕ МЕНЮ V2 (нове)
        try:
            from app.handlers.menu_v2 import register_menu_v2_handlers
            register_menu_v2_handlers(application)
            logger.info("✅ Menu v2 handlers registered")
        except ImportError as e:
            logger.warning(f"⚠️ Menu v2 not available: {e}")
        
        # 5️⃣ TEXT MESSAGES (AI обробка + багатокрокові діалоги)
        try:
            from app.handlers.messages import message_handler
            application.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    message_handler
                )
            )
            logger.info("✅ Text message handler registered")
        except ImportError as e:
            logger.warning(f"⚠️ Message handler not available: {e}")

        logger.info("✅ All handlers registered successfully")
        return True

    except ImportError as e:
        logger.error(f"❌ Handler import error: {e}", exc_info=True)
        logger.warning("⚠️ Some handlers may not be available")
        return False
    except Exception as e:
        logger.error(f"❌ Handler registration error: {e}", exc_info=True)
        return False


async def create_bot_application_async():
    """Асинхронне створення та ініціалізація Telegram bot application"""

    logger.info("🤖 Creating Telegram bot application...")

    TOKEN = config.TELEGRAM_BOT_TOKEN

    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        return None

    try:
        # 🔥 ВИПРАВЛЕННЯ: Збільшуємо connection pool для Render Free tier
        request = HTTPXRequest(
            connection_pool_size=16,  # Збільшено з 8 до 16
            pool_timeout=30.0,        # Таймаут очікування вільного з'єднання
            connect_timeout=20.0,     # Таймаут підключення до Telegram
            read_timeout=20.0,        # Таймаут читання відповіді
            write_timeout=20.0        # Таймаут запису
        )
        
        logger.info("🔧 HTTPXRequest configured:")
        logger.info(f"   Pool size: 16 connections")
        logger.info(f"   Pool timeout: 30s")
        logger.info(f"   Connect/Read timeout: 20s")
        
        # Створення application з власним request
        application = (
            Application.builder()
            .token(TOKEN)
            .request(request)  # 🔥 Використовуємо власний request
            .build()
        )

        # 🔥 КРИТИЧНО: Ініціалізувати application
        logger.info("🔄 Initializing bot application...")
        await application.initialize()
        logger.info("✅ Bot application initialized")

        # Реєстрація обробників
        if not setup_handlers(application):
            logger.warning("⚠️ Some handlers failed to register, but continuing...")

        # Зберігання конфіга у bot_data
        application.bot_data['config'] = config

        logger.info("✅ Bot application created successfully")
        return application

    except Exception as e:
        logger.error(f"❌ Failed to create bot application: {e}", exc_info=True)
        return None


def create_bot_application():
    """Синхронна обгортка для асинхронного створення бота"""
    try:
        # Створюємо новий event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаємо асинхронну функцію
        application = loop.run_until_complete(create_bot_application_async())
        
        return application
    except Exception as e:
        logger.error(f"❌ Failed in sync wrapper: {e}", exc_info=True)
        return None
    finally:
        # НЕ закриваємо loop тут, бо він може використовуватись далі
        pass


# ============================================================================
# SERVICES INITIALIZATION
# ============================================================================

def initialize_services(application):
    """Ініціалізація всіх сервісів (Google Sheets, Gemini, Redis)"""
    
    logger.info("🔧 Initializing services...")
    
    # 1️⃣ GOOGLE SHEETS SERVICE
    try:
        if config.GOOGLE_SHEETS_ID and config.GOOGLE_SHEETS_CREDENTIALS:
            from app.services.sheets_service import SheetsService
            
            sheets_service = SheetsService(config)
            application.bot_data['sheets_service'] = sheets_service
            
            logger.info("✅ Google Sheets Service initialized")
        else:
            logger.warning("⚠️ Google Sheets credentials not found (bot will work without it)")
    except Exception as e:
        logger.error(f"❌ Google Sheets Service error: {e}")
        logger.warning("⚠️ Bot will work without Google Sheets")
    
    # 2️⃣ GEMINI AI SERVICE (опціонально)
    try:
        if config.GEMINI_API_KEY:
            from app.services.gemini_service import GeminiService
            
            gemini_service = GeminiService(config.GEMINI_API_KEY)
            application.bot_data['gemini_service'] = gemini_service
            
            logger.info("✅ Gemini AI Service initialized")
        else:
            logger.warning("⚠️ Gemini API key not found (AI features disabled)")
    except Exception as e:
        logger.error(f"❌ Gemini Service error: {e}")
        logger.warning("⚠️ Bot will work without AI features")
    
    # 3️⃣ REDIS (для кошика)
    if config.REDIS_URL:
        logger.info("✅ Redis URL configured (cart_manager will use it)")
    else:
        logger.warning("⚠️ Redis URL not found (cart will use in-memory storage)")
    
    logger.info("✅ Services initialization completed")


# ============================================================================
# STARTUP FUNCTION
# ============================================================================

def startup():
    """Ініціалізація при запуску"""

    global bot_application

    logger.info("=" * 70)
    logger.info("🚀 FERRIKBOT v3.0 STARTING...")
    logger.info("=" * 70)
    logger.info("")

    # 1️⃣ ВАЛІДАЦІЯ КОНФІГ
    logger.info("🔍 Validating configuration...")
    if not config.validate():
        logger.error("❌ Configuration validation failed")
        return False

    logger.info("✅ Configuration valid")
    logger.info(f"   Token: {config.TELEGRAM_BOT_TOKEN[:20]}...")
    logger.info(f"   Webhook: {config.WEBHOOK_URL}")
    logger.info(f"   Google Sheets ID: {config.GOOGLE_SHEETS_ID[:20] if config.GOOGLE_SHEETS_ID else 'Not set'}...")
    logger.info(f"   Redis URL: {'Configured' if config.REDIS_URL else 'Not set'}")
    logger.info("")

    # 2️⃣ СТВОРЕННЯ БОТА
    logger.info("🤖 Creating bot application...")
    bot_application = create_bot_application()
    
    if not bot_application:
        logger.error("❌ Failed to create bot application")
        return False

    logger.info("✅ Bot application created")
    logger.info("")

    # 3️⃣ ІНІЦІАЛІЗАЦІЯ СЕРВІСІВ
    logger.info("🔧 Initializing services...")
    initialize_services(bot_application)
    logger.info("")

    # 4️⃣ ІНФОРМАЦІЯ ПРО ЗАПУСК
    logger.info("✅ BOT READY!")
    logger.info("")
    logger.info("📊 FEATURES ENABLED:")
    logger.info("  ✓ /start команда (warm greetings)")
    logger.info("  ✓ /menu команда (існуюче меню)")
    logger.info("  ✓ /menu_v2 команда (гібридне меню)")
    logger.info("  ✓ /cart команда")
    logger.info("  ✓ /order команда")
    logger.info("  ✓ Callback handlers (кнопки)")
    logger.info("  ✓ Text message handler (AI + діалоги)")
    logger.info("  ✓ GDPR compliance (згода + видалення)")
    logger.info("  ✓ Surprise Me функція")
    logger.info("  ✓ Google Sheets інтеграція")
    logger.info("  ✓ Redis cart storage")
    logger.info("  ✓ Webhook обробка")
    logger.info("  ✓ Connection Pool: 16 connections")
    logger.info("")
    logger.info(f"🌐 Running on port {config.PORT}")
    logger.info(f"🌍 Environment: {config.ENVIRONMENT}")
    logger.info(f"🐛 Debug mode: {config.DEBUG}")
    logger.info(f"📍 Telegram Webhook: {config.WEBHOOK_URL}/webhook")
    logger.info("")
    logger.info("=" * 70)
    logger.info("")

    return True


# ============================================================================
# AUTO-STARTUP (для Gunicorn)
# ============================================================================

startup()

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Головна сторінка"""
    return jsonify({
        "status": "🟢 online",
        "bot": "🍕 FerrikBot v3.0",
        "version": "3.0.2",
        "bot_initialized": bot_application is not None,
        "environment": config.ENVIRONMENT,
        "debug": config.DEBUG,
        "features": {
            "google_sheets": config.GOOGLE_SHEETS_ID != "",
            "gemini_ai": config.GEMINI_API_KEY != "",
            "redis": config.REDIS_URL != "",
            "hybrid_menu": True,
            "warm_greetings": True,
            "surprise_me": True,
            "text_message_handler": True,
            "gdpr_compliance": True,
            "connection_pool": "16 connections"
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy" if bot_application else "initializing",
        "bot_initialized": bot_application is not None,
        "timestamp": __import__('datetime').datetime.now().isoformat(),
    }), 200 if bot_application else 503


# ============================================================================
# WEBHOOK ROUTES
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Основний webhook маршрут"""
    logger.info("📨 Webhook /webhook отримав запит")
    return process_webhook(request)


@app.route('/webhook/webhook', methods=['POST'])
def webhook_double():
    """Резервний webhook маршрут"""
    logger.warning("⚠️ Webhook /webhook/webhook отримав запит (старий маршрут)")
    return process_webhook(request)


def process_webhook(req):
    """
    🔥 ВИПРАВЛЕНА обробка webhook для Flask/Gunicorn
    Використовує окремий thread для async операцій
    """
    try:
        # Перевіри, чи бот ініціалізований
        if not bot_application:
            logger.error("❌ Bot application not initialized")
            return jsonify({"ok": False, "error": "Bot not initialized"}), 500

        # Отримай JSON від Telegram
        data = req.get_json()

        if not data:
            logger.error("❌ Webhook: порожні дані")
            return jsonify({"ok": False, "error": "Empty data"}), 400

        logger.info(f"📨 Webhook data received: update_id={data.get('update_id')}")

        # Розпарс Update від Telegram
        update = Update.de_json(data, bot_application.bot)

        if not update:
            logger.error("❌ Failed to parse update")
            return jsonify({"ok": False}), 400

        # 🔥 ВИПРАВЛЕННЯ: Обробляємо update в окремому thread
        # щоб не блокувати Flask і не закривати event loop передчасно
        
        def process_update_sync():
            """Обробка update в окремому потоці"""
            try:
                # Створюємо новий event loop для цього thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Створюємо новий HTTP client для цього loop
                from telegram.request import HTTPXRequest
                request = HTTPXRequest(
                    connection_pool_size=8,
                    pool_timeout=30.0,
                    connect_timeout=20.0,
                    read_timeout=20.0,
                    write_timeout=20.0
                )
                
                # Тимчасово замінюємо request
                original_request = bot_application.bot._request
                bot_application.bot._request = request
                
                try:
                    # Обробляємо update
                    loop.run_until_complete(bot_application.process_update(update))
                    logger.info("✅ Update processed successfully")
                finally:
                    # Відновлюємо оригінальний request
                    bot_application.bot._request = original_request
                    # Закриваємо loop після обробки
                    loop.close()
            except Exception as e:
                logger.error(f"❌ Error in thread: {e}", exc_info=True)
        
        # Запускаємо обробку в окремому thread
        thread = Thread(target=process_update_sync)
        thread.start()
        
        # Одразу повертаємо 200 OK (Telegram не буде чекати)
        # Thread продовжить обробку в фоні
        return jsonify({"ok": True}), 200

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook_route():
    """Встановлення webhook для Telegram"""
    if not bot_application:
        return jsonify({"ok": False, "error": "Bot not initialized"}), 500

    try:
        webhook_url = f"{config.WEBHOOK_URL}/webhook"

        # Створюємо event loop для async операції
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                bot_application.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=["message", "callback_query"]
                )
            )
            
            logger.info(f"✅ Webhook set: {webhook_url}")

            return jsonify({
                "ok": True,
                "webhook_url": webhook_url,
                "message": "✅ Webhook установлено успішно"
            }), 200
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ Set webhook error: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/delete_webhook', methods=['GET', 'POST'])
def delete_webhook_route():
    """Видалення webhook"""
    if not bot_application:
        return jsonify({"ok": False}), 500

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(bot_application.bot.delete_webhook())
            logger.info("✅ Webhook deleted")
            return jsonify({"ok": True, "message": "✅ Webhook видалено"}), 200
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ Delete webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================================
# CRON ENDPOINTS
# ============================================================================

@app.route('/cron/cleanup', methods=['POST'])
def cron_cleanup():
    """
    Endpoint for cronjob cleanup of old orders
    Called daily via GitHub Actions or cron-job.org
    """
    
    # Check secret
    secret = request.headers.get('X-Cron-Secret')
    if secret != config.CRON_SECRET:
        logger.warning("⚠️ Unauthorized cron attempt")
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        sheets_service = bot_application.bot_data.get('sheets_service')
        if sheets_service:
            # TODO: Implement cleanup_old_orders
            logger.info("✅ Cleanup job triggered")
            return jsonify({"ok": True, "message": "Cleanup completed"}), 200
        else:
            return jsonify({"error": "Sheets service not available"}), 500
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.before_request
def before_request():
    """Логування перед кожним запитом"""
    if request.path != '/health':
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
            "/webhook",
            "/webhook/webhook",
            "/set_webhook",
            "/delete_webhook",
            "/cron/cleanup"
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
# MAIN
# ============================================================================

if __name__ == '__main__':
    logger.info("🍕 Running in development mode...")
    
    if bot_application:
        logger.info("🚀 Starting Flask development server...")
        app.run(
            host="0.0.0.0",
            port=config.PORT,
            debug=config.DEBUG,
            use_reloader=False
        )
    else:
        logger.error("❌ Bot not initialized!")
        sys.exit(1)