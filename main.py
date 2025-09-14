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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Налаштування Telegram бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
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
    await update.message.reply_text("Вітаємо у @ferrikfoot_bot! 🍽️ Виберіть заклад або перегляньте меню через /menu.")

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
        keyboard.append([InlineKeyboardButton("📥 Переглянути кошик", callback_data="view_cart")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Меню {restaurant['name']}:", reply_markup=reply_markup)
        await query.answer()

    elif data.startswith("add_"):
        item_id = data.split("_")[1]
        rest_id = item_id.split("_")[0]
        item = next(i for i in RESTAURANTS[rest_id]["menu"] if i["id"] == item_id)
        if user_id not in CARTS:
            CARTS[user_id] = []
        CARTS[user_id].append(item)
        await query.answer(f"✅ Додано {item['name']} до кошика!")
        logger.info(f"User {user_id} added item {item['name']} to cart")

    elif data == "view_cart":
        if user_id not in CARTS or not CARTS[user_id]:
            await query.edit_message_text("Ваш кошик порожній! Додайте страви.")
        else:
            cart_items = "\n".join(f"• {item['name']} - {item['price']} грн" for item in CARTS[user_id])
            total = sum(item["price"] for item in CARTS[user_id])
            cart_text = f"Ваш кошик:\n{cart_items}\n\nЗагалом: {total} грн"
            keyboard = [
                [InlineKeyboardButton("📝 Оформити замовлення", callback_data="order")],
                [InlineKeyboardButton("🗑 Очистити кошик", callback_data="clear_cart")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(cart_text, reply_markup=reply_markup)
        await query.answer()

    elif data == "clear_cart":
        CARTS[user_id] = []
        await query.edit_message_text("🗑 Кошик очищено!")
        await query.answer()
        logger.info(f"User {user_id} cleared cart")

    elif data == "order":
        if user_id not in CARTS or not CARTS[user_id]:
            await query.edit_message_text("Кошик порожній!")
        else:
            cart_items = "\n".join(f"• {item['name']} - {item['price']} грн" for item in CARTS[user_id])
            total = sum(item["price"] for item in CARTS[user_id])
            order_text = f"✅ Замовлення оформлено!\n{cart_items}\n\nСума: {total} грн\n\nОчікуйте дзвінка для підтвердження."
            logger.info(f"ORDER from {user_id}: {cart_items}, Total: {total} грн")
            await query.edit_message_text(order_text)
            CARTS[user_id] = []
        await query.answer()

# Ендпоінти
@app.route('/')
def hello_world():
    logger.info("Hello World endpoint accessed")
    return "Hello, World! @ferrikfoot_bot is running."

@app.route('/health')
def health_check():
    logger.info("Health check endpoint accessed")
    return jsonify({"status": "healthy"})

@app.route('/webhook', methods=['POST'])
async def webhook():
    logger.info("Webhook received")
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if update:
            await application.process_update(update)
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
