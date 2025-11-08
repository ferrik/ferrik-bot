"""
🍕 FERRIKBOT v2.3 - MAIN APPLICATION (PRODUCTION READY)
✅ Повністю працюючий з Gunicorn + async handlers
"""

import os
import logging
import sys
import asyncio
from threading import Thread
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler

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
    """Реєстрація обробників Telegram команд"""

    logger.info("📝 Setting up Telegram handlers...")

    try:
        # Базові обробники команд
        async def start_command(update: Update, context):
            """Команда /start"""
            logger.info(f"✅ /start від користувача {update.effective_user.id}")
            await update.message.reply_text(
                "🍴 Привіт! Я — Ferrik, твій персональний помічник зі смаку 🤖✨\n\n"
                "Що я можу робити:\n"
                "• 🔍 Шукати — просто напиши, що хочеш\n"
                "• 📋 Показати меню\n"
                "• 🎁 Дати тобі бонус на першу закупку\n"
                "• 💬 Порадити на основі твоїх смаків\n\n"
                "Готовий почати? 👇"
            )

        async def help_command(update: Update, context):
            """Команда /help"""
            logger.info(f"📚 /help від користувача {update.effective_user.id}")
            await update.message.reply_text(
                "📚 *Як працює Ferrik?*\n\n"
                "1️⃣ /menu — переглянути меню\n"
                "2️⃣ натисни товар — додати в кошик\n"
                "3️⃣ /cart — переглянути кошик\n"
                "4️⃣ оформи замовлення\n\n"
                "Потреби допомога? Напиши /support",
                parse_mode='Markdown'
            )

        async def menu_command(update: Update, context):
            """Команда /menu"""
            logger.info(f"📋 /menu від користувача {update.effective_user.id}")
            await update.message.reply_text(
                "📋 *Меню:*\n\n"
                "🍕 Піца Маргарита — 180 грн\n"
                "🍔 Бургер Класик — 150 грн\n"
                "🌮 Тако Мексиканське — 120 грн\n\n"
                "_Скоро будуть більш деталі!_",
                parse_mode='Markdown'
            )

        # Реєстрація команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("menu", menu_command))

        logger.info("✅ All handlers registered")
        return True

    except Exception as e:
        logger.error(f"❌ Handler registration error: {e}")
        return False


async def create_bot_application_async():
    """Асинхронне створення та ініціалізація Telegram bot application"""

    logger.info("🤖 Creating Telegram bot application...")

    TOKEN = config.TELEGRAM_BOT_TOKEN

    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        return None

    try:
        # Створення application
        application = Application.builder().token(TOKEN).build()

        # 🔥 КРИТИЧНО: Ініціалізувати application
        logger.info("🔄 Initializing bot application...")
        await application.initialize()
        logger.info("✅ Bot application initialized")

        # Реєстрація обробників
        if not setup_handlers(application):
            return None

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


# ============================================================================
# STARTUP FUNCTION
# ============================================================================

def startup():
    """Ініціалізація при запуску"""

    global bot_application

    logger.info("=" * 70)
    logger.info("🚀 FERRIKBOT v2.3 STARTING...")
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
    logger.info("")

    # 2️⃣ СТВОРЕННЯ БОТА
    logger.info("🤖 Creating bot application...")
    bot_application = create_bot_application()
    
    if not bot_application:
        logger.error("❌ Failed to create bot application")
        return False

    logger.info("✅ Bot application created")
    logger.info("")

    # 3️⃣ ІНФОРМАЦІЯ ПРО ЗАПУСК
    logger.info("✅ BOT READY!")
    logger.info("")
    logger.info("📊 FEATURES ENABLED:")
    logger.info("  ✓ /start команда")
    logger.info("  ✓ /help команда")
    logger.info("  ✓ /menu команда")
    logger.info("  ✓ Webhook обробка")
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
        "bot": "🍕 FerrikBot v2.3",
        "version": "2.3.0",
        "bot_initialized": bot_application is not None,
        "environment": config.ENVIRONMENT,
        "debug": config.DEBUG
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
                
                try:
                    # Обробляємо update
                    loop.run_until_complete(bot_application.process_update(update))
                    logger.info("✅ Update processed successfully")
                finally:
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