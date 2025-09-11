from flask import Flask, request, jsonify
import logging
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__)

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Налаштування Telegram бота
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Замініть на ваш токен
bot = telegram.Bot(token=TELEGRAM_TOKEN)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text("Вітаємо у боті доставки їжі! 🍽️ Виберіть заклад або перегляньте меню через /menu.")

# Реєстрація обробників
application.add_handler(CommandHandler("start", start))

@app.route('/')
def hello_world():
    logger.info("Hello World endpoint accessed")
    return "Hello, World! Food Delivery Bot is running."

@app.route('/health')
def health_check():
    logger.info("Health check endpoint accessed")
    return jsonify({"status": "healthy"})

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    await application.process_update(update)
    return jsonify({"status": "ok"})

def set_webhook():
    webhook_url = "YOUR_RENDER_URL/webhook"  # Замініть на ваш URL від Render.com
    bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

if __name__ == '__main__':
    set_webhook()
    app.run(host='0.0.0.0', port=8000)
