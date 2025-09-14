from flask import Flask, request, jsonify
import logging
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os

app = Flask(__name__)

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Налаштування Telegram бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не знайдено! Додайте його до змінних оточення.")
    raise ValueError("TELEGRAM_TOKEN is not set!")

bot = telegram.Bot(token=TELEGRAM_TOKEN)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Приклад бази даних закладів
RESTAURANTS = {
    "1": {"name": "Піцерія Наполі", "menu": [
        {"id": "1_1", "name": "Піца Маргарита", "price": 150},
        {"id": "1_2", "name": "Піца Пепероні", "price": 180}
    ]},
    "2": {"name": "Суші Майстер", "menu": [
        {"id": "2_1", "name": "Каліфорнія рол", "price": 200},
        {"id": "2_2", "name": "Філадельфія", "price": 250}
    ]}
}

# Зберігання кошика
CARTS = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started the bot")
    await update.message.reply_text("Вітаємо у @ferrikfoot_bot! 🍽️ Виберіть заклад через /menu.")

# Команда /menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} accessed menu")
    keyboard = [
        [InlineKeyboardButton(restaurant["name"], callback_data=f"rest_{id}")]
        for id, restaurant in RESTAURANTS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Виберіть заклад у Тернополі:", reply_markup=reply_markup)

# Обробка кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    logger.info(f"User {user_id} clicked button: {data}")

    if data.startswith("rest_"):
        rest_id = data.split("_")[1]
        restaurant = RESTAURANTS[rest_id]
        keyboard = [
            [InlineKeyboardButton(f"{item['name']} ({item['price']} грн)", callback_data=f"add_{item['id']}")]
            for item in restaurant["menu"]
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Назад до закладів", callback_data="back_to_menu")])
        keyboard.append([InlineKeyboardButton("📥 Переглянути кошик", callback_data="view_cart")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Меню {restaurant['name']}:", reply_markup=reply_markup)

    elif data.startswith("add_"):
        item_id_parts = data.split("_")
        rest_id = item_id_parts[1]
        item_full_id = f"{item_id_parts[1]}_{item_id_parts[2]}"
        item = next((i for i in RESTAURANTS[rest_id]["menu"] if i["id"] == item_full_id), None)
        if item:
            if user_id not in CARTS:
                CARTS[user_id] = []
            CARTS[user_id].append(item)
            await context.bot.send_message(chat_id=user_id, text=f"✅ Додано '{item['name']}' до кошика!")
            logger.info(f"User {user_id} added item {item['name']} to cart")
        else:
            await context.bot.send_message(chat_id=user_id, text="Помилка: страву не знайдено.")

    elif data == "view_cart":
        if user_id not in CARTS or not CARTS[user_id]:
            cart_text = "Ваш кошик порожній! 🛒"
            keyboard = [[InlineKeyboardButton("⬅️ Повернутись до меню", callback_data="back_to_menu")]]
        else:
            cart_items = "\n".join(f"• {item['name']} - {item['price']} грн" for item in CARTS[user_id])
            total = sum(item["price"] for item in CARTS[user_id])
            cart_text = f"🛒 Ваш кошик:\n{cart_items}\n\n*Загалом: {total} грн*"
            keyboard = [
                [InlineKeyboardButton("📝 Оформити замовлення", callback_data="order")],
                [InlineKeyboardButton("🗑 Очистити кошик", callback_data="clear_cart")],
                [InlineKeyboardButton("⬅️ Продовжити вибір", callback_data="back_to_menu")]
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(cart_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == "clear_cart":
        CARTS[user_id] = []
        logger.info(f"User {user_id} cleared cart")
        await query.edit_message_text("🗑 Кошик очищено!")

    elif data == "order":
        if user_id not in CARTS or not CARTS[user_id]:
            await query.edit_message_text("Кошик порожній! Неможливо оформити замовлення.")
        else:
            cart_items = "\n".join(f"• {item['name']}" for item in CARTS[user_id])
            total = sum(item["price"] for item in CARTS[user_id])
            order_text = f"✅ Замовлення оформлено!\n\nСклад:\n{cart_items}\n\n*Сума: {total} грн*\n\nОчікуйте на дзвінок оператора для підтвердження."
            logger.info(f"ORDER from {user_id}: {cart_items}, Total: {total} грн")
            await query.edit_message_text(order_text, parse_mode='Markdown')
            CARTS[user_id] = []

    elif data == "back_to_menu":
        await menu(query, context)

# Ендпоінти
@app.route('/')
def index():
    logger.info("Index endpoint accessed")
    return "Hello, World! @ferrikfoot_bot is running."

@app.route('/health')
def health_check():
    logger.info("Health check endpoint accessed")
    return jsonify({"status": "healthy"})

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("Webhook received")
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if update:
            application.run_polling(update=update)  # Синхронна обробка
            logger.info("Webhook processed successfully")
        else:
            logger.error("No update received in webhook")
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Реєстрація обробників
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu))
application.add_handler(CallbackQueryHandler(button_callback))

if __name__ == '__main__':
    logger.info("Starting @ferrikfoot_bot")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
