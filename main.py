import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Логування
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен з Render (ENV VAR)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Меню з емодзі
main_menu = [
    ["🍔 Меню", "📦 Замовлення"],
    ["ℹ️ Інформація", "☎️ Контакти"]
]

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Привіт! Я бот FerrikFoot 🚀\n"
        "Вибери дію з меню нижче ⬇️",
        reply_markup=reply_markup
    )

# Тексти для кнопок
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🍔 Меню":
        await update.message.reply_text("Наше меню 🍕🍟🍹\n(тут можна додати страви з БД або API)")
    elif text == "📦 Замовлення":
        await update.message.reply_text("Твої замовлення 🛒 ще пусті.")
    elif text == "ℹ️ Інформація":
        await update.message.reply_text("ℹ️ Ми працюємо щодня з 10:00 до 22:00")
    elif text == "☎️ Контакти":
        await update.message.reply_text("📞 Телефон: +380123456789\n📍 Адреса: м. Тернопіль")
    else:
        await update.message.reply_text("❓ Я тебе не зрозумів, вибери опцію з меню ⬇️")

# Запуск
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    port = int(os.environ.get("PORT", 8080))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
