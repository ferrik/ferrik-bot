"""
🍕 FERRIKBOT v2.1 - MAIN APPLICATION (FINAL FIX)
Бот ініціалізується при старті Flask, не в if __name__ == '__main__'
"""

import os
import logging
import sys
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
    
    # App
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    PORT = int(os.getenv("PORT", 5000))
    
    @staticmethod
    def validate():
        """Перевірка необхідних конфігурацій"""
        if not Config.TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not set")
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
                "4️⃣ оформи замовлення",
                parse_mode='Markdown'
            )
        
        async def menu_command(update: Update, context):
            """Команда /menu"""
            logger.info(f"📋 /menu від користувача {update.effective_user.id}")
            await update.message.reply_text(
                "📋 *Меню:*\n\n"
                "🍕 Піца Маргарита — 180 грн\n"
                "🍔 Бургер Класик — 150 грн\n"
                "🌮 Тако Мексиканське — 120 грн",
                parse_mode='Markdown'
            )
        
        # Реєстрація команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("menu", menu_command))
        
        logger.info("✅ All handlers registered")
        return True
    
    except Exception as e:
        logger.error(f"❌ Handler registration error: {e}", exc_info=True)
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
        
        # Зберігання конфіга у bot_data
        bot_application.bot_data['config'] = config
        
        logger.info("✅ Bot application created successfully")
        return bot_application
    
    except Exception as e:
        logger.error(f"❌ Failed to create bot application: {e}", exc_info=True)
        return None


# ============================================================================
# STARTUP FUNCTION (ВИКЛИКАЄТЬСЯ ПРИ СТАРТІ FLASK)
# ============================================================================

def startup():
    """Ініціалізація при запуску Flask"""
    
    global bot_application
    
    logger.info("=" * 70)
    logger.info("🚀 FERRIKBOT v2.1 STARTING...")
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
    if not create_bot_application():
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
    logger.info(f"📍 Telegram Webhook: {config.WEBHOOK_URL}/webhook")
    logger.info("")
    logger.info("=" * 70)
    logger.info("")
    
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
        "version": "2.1.0",
        "bot_initialized": bot_application is not None,
        "environment": config.ENVIRONMENT,
        "debug": config.DEBUG
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    is_healthy = bot_application is not None
    return jsonify({
        "status": "healthy" if is_healthy else "initializing",
        "bot_initialized": is_healthy,
        "timestamp": __import__('datetime').datetime.now().isoformat(),
    }), 200 if is_healthy else 503


# ============================================================================
# 🔥 WEBHOOK ROUTES
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
    """Спільна обробка webhook запитів"""
    try:
        # Перевіри, чи бот ініціалізований
        if not bot_application:
            logger.error("❌ Bot application not initialized")
            return jsonify({"ok": False, "error": "Bot not initialized"}), 500
        
        # Отримай JSON від Telegram
        data = req.get_json()
        
        if not data:
            logger.error("❌ Webhook: порожні дані")
            return jsonify({"ok": False}), 400
        
        logger.info(f"📨 Update received: {data.get('update_id')}")
        
        # Розпарс Update від Telegram
        update = Update.de_json(data, bot_application.bot)
        
        if not update:
            logger.error("❌ Failed to parse update")
            return jsonify({"ok": False}), 400
        
        # Обробити месідж асинхронно
        import asyncio
        
        async def process():
            await bot_application.process_update(update)
        
        try:
            asyncio.run(process())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(process())
        
        logger.info("✅ Update processed")
        return jsonify({"ok": True}), 200
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """404 обробник"""
    return jsonify({
        "error": "Not found",
        "status": 404,
        "endpoints": ["/", "/health", "/webhook", "/webhook/webhook"]
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
# 🔥 FLASK BEFORE_FIRST_REQUEST (ЗАПУСКАЄТЬСЯ ПРИ ПЕРШОМУ ЗАПИТІ)
# ============================================================================

initialized = False

@app.before_request
def initialize_bot_on_first_request():
    """Ініціалізуй бот при першому запиті до Flask"""
    global initialized
    
    if not initialized:
        logger.info("🔔 First request detected, initializing bot...")
        startup()
        initialized = True


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    logger.info("🍕 Initializing FerrikBot...")
    logger.info("")
    
    # Запуск Flask
    app.run(
        host="0.0.0.0",
        port=config.PORT,
        debug=config.DEBUG,
        use_reloader=False
    )
