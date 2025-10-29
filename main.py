"""
🍕 FERRIKBOT v2.1 - WORKING VERSION
Всі проблеми з async та Application ініціалізацією виправлені
"""

import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler
import threading

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
initialization_lock = threading.Lock()

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Конфігурація додатку"""
    
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5000")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    PORT = int(os.getenv("PORT", 5000))
    
    @staticmethod
    def validate():
        """Перевірка конфігурації"""
        if not Config.TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not set")
            return False
        return True


config = Config()

# ============================================================================
# TELEGRAM BOT CREATION (БЕЗ PROCESS_UPDATE - ТІЛЬКИ ОБРОБНИКИ)
# ============================================================================

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
        
        # ✅ ВАЖЛИВО: Ініціалізуємо Application
        # Без цього процес_update впаде з помилкою
        import asyncio
        
        async def init_app():
            await bot_application.initialize()
        
        # Запусти ініціалізацію
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_app())
        
        logger.info("✅ Application initialized")
        
        # Реєстрація обробників
        setup_handlers(bot_application)
        
        logger.info("✅ Bot application created successfully")
        return bot_application
    
    except Exception as e:
        logger.error(f"❌ Failed to create bot application: {e}", exc_info=True)
        return None


def setup_handlers(application):
    """Реєстрація обробників"""
    
    logger.info("📝 Setting up handlers...")
    
    try:
        async def start_command(update: Update, context):
            """Команда /start"""
            logger.info(f"✅ /start від {update.effective_user.id}")
            await update.message.reply_text(
                "🍴 Привіт! Я — Ferrik, твій персональний помічник зі смаку 🤖✨\n\n"
                "Команди:\n"
                "• /menu — меню\n"
                "• /help — допомога"
            )
        
        async def help_command(update: Update, context):
            """Команда /help"""
            await update.message.reply_text(
                "📚 Як користуватися:\n\n"
                "/menu — переглянути меню\n"
                "/start — почнемо знову"
            )
        
        async def menu_command(update: Update, context):
            """Команда /menu"""
            await update.message.reply_text(
                "📋 Меню:\n\n"
                "🍕 Піца — 180 грн\n"
                "🍔 Бургер — 150 грн"
            )
        
        # Реєстрація
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("menu", menu_command))
        
        logger.info("✅ Handlers registered")
        return True
    
    except Exception as e:
        logger.error(f"❌ Handler error: {e}", exc_info=True)
        return False


def startup():
    """Ініціалізація при першому запиті"""
    
    global bot_application
    
    logger.info("=" * 70)
    logger.info("🚀 FERRIKBOT v2.1 STARTING...")
    logger.info("=" * 70)
    
    # Валідація конфігу
    if not config.validate():
        logger.error("❌ Configuration validation failed")
        return False
    
    logger.info("✅ Configuration valid")
    logger.info(f"   Token: {config.TELEGRAM_BOT_TOKEN[:20]}...")
    logger.info(f"   Webhook: {config.WEBHOOK_URL}")
    
    # Створення бота
    if not create_bot_application():
        logger.error("❌ Failed to create bot")
        return False
    
    logger.info("✅ BOT READY!")
    logger.info(f"   Port: {config.PORT}")
    logger.info(f"   Webhook: {config.WEBHOOK_URL}/webhook")
    logger.info("=" * 70)
    
    return True


# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Головна сторінка"""
    return jsonify({
        "status": "🟢 online",
        "bot": "🍕 FerrikBot v2.1",
        "bot_initialized": bot_application is not None,
        "environment": config.ENVIRONMENT
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    is_healthy = bot_application is not None
    return jsonify({
        "status": "healthy" if is_healthy else "initializing",
        "bot_initialized": is_healthy,
    }), 200 if is_healthy else 503


# ============================================================================
# 🔥 WEBHOOK МАРШРУТИ
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Основний webhook"""
    logger.info("📨 /webhook запит отримано")
    return process_webhook(request)


@app.route('/webhook/webhook', methods=['POST'])
def webhook_double():
    """Резервний webhook"""
    logger.warning("⚠️ /webhook/webhook запит (старий маршрут)")
    return process_webhook(request)


def process_webhook(req):
    """
    Обробка webhook запитів від Telegram
    ✅ БЕЗ loop.close() - дозволяємо бібліотеці управляти
    """
    try:
        # Перевіри бот
        if not bot_application:
            logger.error("❌ Bot not initialized")
            return jsonify({"ok": False}), 500
        
        # Отримай дані
        data = req.get_json()
        if not data:
            return jsonify({"ok": False}), 400
        
        logger.info(f"📨 Update ID: {data.get('update_id')}")
        
        # Розпарс Update
        update = Update.de_json(data, bot_application.bot)
        if not update:
            return jsonify({"ok": False}), 400
        
        # ✅ ПРАВИЛЬНА ОБРОБКА: async без loop.close()
        import asyncio
        
        async def process():
            """Обробка Update асинхронно"""
            try:
                await bot_application.process_update(update)
                logger.info("✅ Update processed")
            except Exception as e:
                logger.error(f"❌ Error processing update: {e}", exc_info=True)
        
        # НЕ ЗАКРИВАЙ LOOP - дозволь asyncio управляти
        try:
            # Намагайся запустити в існуючому loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            # НЕ запускай як .run_until_complete() - це блокує
            # Замість цього, просто вернемо 200 і дозволимо обробці відбуватися
            import threading
            threading.Thread(target=lambda: asyncio.run(process())).start()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            import threading
            threading.Thread(target=lambda: asyncio.run(process())).start()
        
        return jsonify({"ok": True}), 200
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False}), 500


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ ПРИ ПЕРВОМ ЗАПРОСЕ
# ============================================================================

initialized = False

@app.before_request
def initialize_on_first_request():
    """Ініціалізуй бот при першому запиті"""
    global initialized
    
    if not initialized:
        with initialization_lock:
            if not initialized:  # Double-check
                logger.info("🔔 First request - initializing bot...")
                startup()
                globals()['initialized'] = True


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not found",
        "endpoints": ["/", "/health", "/webhook"]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ 500 error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    logger.info("🍕 Starting Ferrik Bot...")
    app.run(
        host="0.0.0.0",
        port=config.PORT,
        debug=config.DEBUG,
        use_reloader=False
    )
