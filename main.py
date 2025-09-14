import os
import logging
import asyncio
from flask import Flask, request, jsonify
from dotenv import load_dotenv

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Завантаження .env для локальної розробки
load_dotenv()

# --- Налаштування ---
app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()] # На Render краще логувати в консоль
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не знайдено! Додайте його до змінних оточення.")
    raise ValueError("TELEGRAM_TOKEN is not set!")

application = Application.builder().token(TELEGRAM_TOKEN).build()

# --- База даних (тимчасова, в пам'яті) ---
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
CARTS = {} # ПОПЕРЕДЖЕННЯ: Дані будуть втрачатись при перезапуску!

# --- Обробники команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started the bot")
    await update.message.reply_text("Вітаємо у @ferrikfoot_bot! 🍽️ Виберіть заклад через /menu.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} accessed menu")
    keyboard = [
        [InlineKeyboardButton(restaurant["name"], callback_data=f"rest_{id}")]
        for id, restaurant in RESTAURANTS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Виберіть заклад у Тернополі:", reply_markup=reply_markup)

# --- Обробник кнопок ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Важливо відповісти на запит одразу
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
            CARTS[user_id] = [] # Очищуємо кошик після замовлення

    elif data == "back_to_menu":
        # Імітуємо виклик команди /menu
        await menu(query, context)


# --- Реєстрація обробників ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu))
application.add_handler(CallbackQueryHandler(button_callback))

# --- Веб-сервер Flask ---
@app.route('/')
def index():
    return "Hello, World! @ferrikfoot_bot is running."

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

# Цей ендпоінт обробляє запити від Telegram
@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
async def webhook():
    json_data = request.get_json()
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return "OK", 200

# Цей ендпоінт потрібен для одноразового налаштування вебхука
@app.route('/set_webhook')
def set_webhook():
    render_url = os.getenv('RENDER_EXTERNAL_URL')
    if not render_url:
        return "Помилка: змінна RENDER_EXTERNAL_URL не встановлена.", 500
    
    webhook_url = f'{render_url}/{TELEGRAM_TOKEN}'
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(application.bot.set_webhook(webhook_url))
        logger.info(f"Webhook set to {webhook_url}")
        return f"Webhook успішно встановлено на {webhook_url}", 200
    except Exception as e:
        logger.error(f"Помилка встановлення вебхука: {e}")
        return f"Помилка встановлення вебхука: {e}", 500

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', 8000)))

