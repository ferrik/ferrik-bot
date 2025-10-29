"""
🍕 FERRIKBOT v2.1 - MAIN APPLICATION (FULLY FIXED)
Готовий до використання на GitHub та Render
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
# STARTUP FUNCTION (КРИТИЧНО!)
# ============================================================================

def startup():
    """Ініціалізація при запуску (ВИКЛИКАЄТЬСЯ ОДИН РАЗ)"""
    
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
    logger.info(f"🐛 Debug mode: {config.DEBUG}")
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
    return jsonify({
        "status": "healthy" if bot_application else "initializing",
        "bot_initialized": bot_application is not None,
        "timestamp": __import__('datetime').datetime.now().isoformat(),
    }), 200 if bot_application else 503


# ============================================================================
# 🔥 WEBHOOK ROUTES (КРИТИЧНО!)
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Основний webhook маршрут для Telegram
    POST /webhook
    """
    logger.info("📨 Webhook /webhook отримав запит")
    return process_webhook(request)


@app.route('/webhook/webhook', methods=['POST'])
def webhook_double():
    """
    Резервний webhook маршрут (для старого налаштування)
    POST /webhook/webhook
    """
    logger.warning("⚠️ Webhook /webhook/webhook отримав запит (старий маршрут)")
    return process_webhook(request)


def process_webhook(req):
    """
    Спільна обробка всіх webhook запитів
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
        
        # Обробити месідж через зареєстровані обробники
        # ВАЖЛИВО: це синхронна функція, запускаємо обробку асинхронно
        import asyncio
        
        async def process():
            await bot_application.process_update(update)
        
        # Запусти асинхронну обробку
        try:
            asyncio.run(process())
        except RuntimeError:
            # Якщо вже є event loop
            loop = asyncio.get_event_loop()
            loop.run_until_complete(process())
        
        logger.info("✅ Update processed successfully")
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
        
        import asyncio
        
        async def set_it():
            await bot_application.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query"]
            )
        
        try:
            asyncio.run(set_it())
        except RuntimeError:
            loop = asyncio.get_event_loop()
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
        
        try:
            asyncio.run(delete_it())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(delete_it())
        
        logger.info("✅ Webhook deleted")
        return jsonify({"ok": True, "message": "✅ Webhook видалено"}), 200
    
    except Exception as e:
        logger.error(f"❌ Delete webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.before_request
def before_request():
    """Логування перед кожним запитом"""
    if request.path != '/health':  # Не логуй health checks
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
    logger.info("🍕 Initializing FerrikBot...")
    logger.info("")
    
    # ВИКЛИКАЙ STARTUP - ЦЕ КРИТИЧНО!
    if startup():
        logger.info("🚀 Starting Flask server...")
        logger.info("")
        
        # Запуск Flask
        app.run(
            host="0.0.0.0",
            port=config.PORT,
            debug=config.DEBUG,
            use_reloader=False  # Важливо для Telegram webhook
        )
    else:
        logger.error("❌ Failed to start bot!")
        sys.exit(1)
