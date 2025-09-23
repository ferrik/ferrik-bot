import os
import logging
import json
import re
from flask import Flask, request, jsonify
import requests
from handlers.cart import show_cart, add_item_to_cart
from handlers.order import start_checkout_process
from handlers.geo import check_delivery_availability
from services.sheets import init_gspread_client, get_menu_from_sheet, get_item_by_id
from services.gemini import get_gemini_recommendation
from models.user import init_db, get_state, set_state, get_cart, set_cart
from datetime import datetime
from menu_logic import generate_menu_keyboard # Імпортуємо функцію для створення клавіатури меню

try:
    from zoneinfo import ZoneInfo
except ImportError:
    logging.warning("zoneinfo not found. Using naive datetime.")
    ZoneInfo = None

app = Flask(__name__)

# Налаштування логів
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)
logger = logging.getLogger("ferrik")

# Змінні середовища
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "Ferrik123").strip()
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "").strip()
OPERATOR_CHAT_ID = os.environ.get("OPERATOR_CHAT_ID", "").strip()
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Тернопіль").strip()
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_CX = os.environ.get("GOOGLE_SEARCH_CX")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TIMEZONE_NAME = "Europe/Kyiv"

menu_cache = []

# Функція для надсилання повідомлення в Telegram
def send_telegram_message(chat_id, text, reply_markup=None):
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
        'reply_markup': reply_markup,
    }
    try:
        requests.post(f"{API_URL}/sendMessage", json=payload)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

# Функція для надсилання дії в Telegram
def send_chat_action(chat_id, action):
    payload = {'chat_id': chat_id, 'action': action}
    try:
        requests.post(f"{API_URL}/sendChatAction", json=payload)
    except Exception as e:
        logger.error(f"Failed to send chat action: {e}")

# Функція для відповіді на callback-запит
def tg_answer_callback(callback_id, text=None):
    payload = {'callback_query_id': callback_id, 'text': text}
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json=payload)
    except Exception as e:
        logger.error(f"Failed to answer callback query: {e}")

def generate_personalized_greeting(user_name="Друже"):
    user_name = (user_name or '').strip() or 'Друже'
    current = datetime.now() if not ZoneInfo else datetime.now(ZoneInfo(TIMEZONE_NAME))
    hour = current.hour

    greeting = f"Доброго {'ранку' if 6 <= hour < 12 else 'дня' if 12 <= hour < 18 else 'вечора'}, {user_name}! 😊"
    status = "Ресторан відкритий! 🍽️ Готові прийняти ваше замовлення." if is_restaurant_open() else "Ресторан закритий. 😔 Працюємо з 9:00 до 22:00."
    return f"{greeting}\n\n{status}\n\nЯ ваш помічник для замовлення їжі! 🍔🍕"

def is_restaurant_open():
    current_hour = datetime.now().hour if not ZoneInfo else datetime.now(ZoneInfo(TIMEZONE_NAME)).hour
    return 9 <= current_hour < 22

# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

# Ініціалізація
with app.app_context():
    logger.info("Bot initialization started.")
    try:
        init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    try:
        global menu_cache
        menu_cache = get_menu_from_sheet(GOOGLE_SHEET_ID)
        if not menu_cache:
            raise ValueError("Menu is empty!")
        logger.info(f"Menu loaded: {len([item for item in menu_cache if item.get('Активний') == 'Так'])} active items from {len(menu_cache)} total")
    except Exception as e:
        logger.error(f"Failed to load menu from Google Sheet: {e}")
        menu_cache = []

# Webhook endpoint for Telegram updates
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        return jsonify({'status': 'invalid token'}), 403

    update = request.get_json()
    if not update:
        return jsonify({'status': 'no update data'}), 200

    logger.info(f"Received update: {update}")

    message = update.get('message')
    callback_query = update.get('callback_query')

    if callback_query:
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        # Обробка callback data
        if data.startswith('add_'):
            item_id = data.split('_')[1]
            add_item_to_cart(chat_id, item_id, menu_cache)
        elif data.startswith('remove_'):
            item_id = data.split('_')[1]
            # Assumes a remove_item_from_cart function exists
            pass
        elif data == 'show_cart':
            show_cart(chat_id, menu_cache)
        elif data == 'start_checkout':
            start_checkout_process(chat_id)
        
        tg_answer_callback(callback_query['id'])
        return '', 200

    if message:
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        user_name = message['from'].get('first_name', "Друже")
        text = message.get('text')

        if not text:
            return '', 200

        state = get_state(user_id) or 'start'
        
        if text == '/start':
            send_telegram_message(chat_id, generate_personalized_greeting(user_name))
            set_state(user_id, 'start')
            return '', 200
        
        elif text == '🍔 Замовити їжу':
            # Генеруємо клавіатуру меню за допомогою імпортованої функції
            reply_markup = generate_menu_keyboard(menu_cache)
            send_telegram_message(chat_id, "Оберіть, що бажаєте замовити:", reply_markup)
            return '', 200

    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
