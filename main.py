import os
import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.request import HTTPXRequest

# ----------------------------------------------------------------------------
# 🔧 Logging
# ----------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("ferrik-bot")

# ----------------------------------------------------------------------------
# ⚙️ Flask app
# ----------------------------------------------------------------------------
app = Flask(__name__)

# ----------------------------------------------------------------------------
# 🔐 Environment variables
# ----------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

bot_app = None  # Глобальна змінна для Application


# ----------------------------------------------------------------------------
# 🧠 Handlers
# ----------------------------------------------------------------------------
async def start_command(update: Update, context):
    await update.message.reply_text("👋 Привіт! Ferrik Bot на зв’язку.")

async def handle_message(update: Update, context):
    user_message = update.message.text
    await update.message.reply_text(f"Ви написали: {user_message}")

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer("✅ Callback отримано!")
    await query.edit_message_text("Відповідь на callback!")


# ----------------------------------------------------------------------------
# 🧩 Webhook routes (подвійна сумісність)
# ----------------------------------------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook_handler():
    """Telegram webhook endpoint (основний)"""
    return handle_telegram_webhook()

@app.route("/webhook/webhook", methods=["POST"])
def webhook_handler_double():
    """Telegram webhook endpoint (подвійний шлях для Render)"""
    return handle_telegram_webhook()


def handle_telegram_webhook():
    """Спільна логіка обробки webhook"""
    try:
        global bot_app

        if bot_app is None:
            logger.error("❌ Bot application not initialized")
            return jsonify({"status": "error", "message": "Bot not ready"}), 503

        data = request.get_json(force=True)
        logger.info(f"📥 Received webhook update: {data.get('update_id', 'unknown')}")

        update = Update.de_json(data, bot_app.bot)

        # ✅ Асинхронна обробка без повторної ініціалізації
        asyncio.run(bot_app.process_update(update))

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


# ----------------------------------------------------------------------------
# 🤖 BOT INITIALIZATION
# ----------------------------------------------------------------------------
def setup_bot():
    """Налаштувати Telegram бота з розширеним пулом"""
    global bot_app

    try:
        # Розширений пул підключень (вирішує PoolTimeoutError)
        request = HTTPXRequest(
            connection_pool_size=50,  # стандарт був 10
            connect_timeout=10.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=10.0,
        )

        bot_app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .request(request)
            .build()
        )

        # Додавання хендлерів
        bot_app.add_handler(CommandHandler("start", start_command))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        bot_app.add_handler(CallbackQueryHandler(handle_callback))

        logger.info("✅ Bot initialized successfully")

    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}", exc_info=True)
        bot_app = None


# ----------------------------------------------------------------------------
# 🚀 FLASK STARTUP
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("🚀 Starting Ferrik Bot...")

    setup_bot()

    # Налаштування webhook
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        webhook_url = f"{WEBHOOK_URL}/webhook"
        bot.delete_webhook()
        bot.set_webhook(url=webhook_url)
        logger.info(f"🌐 Webhook set to: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}", exc_info=True)

    # Запуск Flask сервера
    app.run(host="0.0.0.0", port=PORT)
