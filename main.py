import os
import logging
import json
import uuid
from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
import re
import sqlite3
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# Для Gemini
import google.generativeai as genai

# Для Google Sheets
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Геолокація
geolocator = Nominatim(user_agent="ferrikfoot_bot")
RESTAURANT_LOCATION = (49.553517, 25.594767)  # Центр Тернополя
DELIVERY_RADIUS_KM = 7

# Конфігурація
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "Ferrik123")  # Коректний токен
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1Uz8T1E3_8eq8yt4SMh6Fd_KvGpW9Fe0PFI-mtcqSDJI")
SERVICE_ACCOUNT_KEY_PATH = os.environ.get("SERVICE_ACCOUNT_KEY_PATH", "creds.json")
OPERATOR_CHAT_ID = os.environ.get("OPERATOR_CHAT_ID", None)
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Тернопіль").strip()
TIMEZONE_NAME = os.environ.get("TIMEZONE", "Europe/Kyiv").strip()
RESTAURANT_OPEN_HOUR = int(os.environ.get("RESTAURANT_OPEN_HOUR", "9"))
RESTAURANT_CLOSE_HOUR = int(os.environ.get("RESTAURANT_CLOSE_HOUR", "22"))
DELIVERY_FEE = float(os.environ.get("DELIVERY_FEE", "50.0"))
MIN_ORDER_FOR_DELIVERY = float(os.environ.get("MIN_ORDER_FOR_DELIVERY", "300.0"))
RESTAURANT_ADDRESS = os.environ.get("RESTAURANT_ADDRESS", f"вул. Головна, 123, м. {DEFAULT_CITY}").strip()
CACHE_TIMEOUT_SECONDS = int(os.environ.get("CACHE_TIMEOUT_SECONDS", "900"))  # 15 хвилин

API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Логи
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger("ferrik")

# Flask app
app = Flask(__name__)

# SQLite Database Setup
DATABASE_PATH = "bot_data.db"

def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                chat_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_carts (
                chat_id INTEGER PRIMARY KEY,
                cart_data TEXT NOT NULL
            )
        """)
        conn.commit()
    logger.info("SQLite database initialized successfully.")

init_db()  # Ініціалізуємо базу при старті

# Стани
STATE_NORMAL = "normal"
STATE_AWAITING_PHONE = "awaiting_phone"
STATE_AWAITING_PHONE_CONFIRM = "awaiting_phone_confirm"
STATE_AWAITING_ADDRESS = "awaiting_address"
STATE_AWAITING_PAYMENT_METHOD_CHOICE = "awaiting_payment_method_choice"
STATE_AWAITING_DELIVERY_TYPE_CHOICE = "awaiting_delivery_type_choice"
STATE_AWAITING_DELIVERY_TIME_CHOICE = "awaiting_delivery_time_choice"
STATE_AWAITING_FINAL_CONFIRMATION = "awaiting_final_confirmation"
STATE_AWAITING_OPERATOR_MESSAGE = "awaiting_operator_message"
STATE_AWAITING_SEARCH_QUERY = "awaiting_search_query"
STATE_AWAITING_FEEDBACK = "awaiting_feedback"

# Функції для стану та кошика
def get_state(chat_id):
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT state FROM user_states WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            return result[0] if result else STATE_NORMAL
    except sqlite3.Error as e:
        logger.error(f"Error getting state for chat_id {chat_id}: {e}")
        return STATE_NORMAL

def set_state(chat_id, state):
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO user_states (chat_id, state) VALUES (?, ?)", (chat_id, state))
            conn.commit()
        logger.debug(f"State for chat_id {chat_id} set to {state}")
    except sqlite3.Error as e:
        logger.error(f"Error setting state for chat_id {chat_id}: {e}")

def get_cart(chat_id):
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cart_data FROM user_carts WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            default_cart = {"items": [], "address": "", "phone": "", "payment_method": "", "delivery_type": "", "delivery_time": ""}
            return json.loads(result[0]) if result else default_cart
    except sqlite3.Error as e:
        logger.error(f"Error getting cart for chat_id {chat_id}: {e}")
        return {"items": [], "address": "", "phone": "", "payment_method": "", "delivery_type": "", "delivery_time": ""}

def set_cart(chat_id, cart_data):
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO user_carts (chat_id, cart_data) VALUES (?, ?)", (chat_id, json.dumps(cart_data, ensure_ascii=False)))
            conn.commit()
        logger.debug(f"Cart for chat_id {chat_id} updated.")
    except sqlite3.Error as e:
        logger.error(f"Error setting cart for chat_id {chat_id}: {e}")

def delete_cart(chat_id):
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_carts WHERE chat_id = ?", (chat_id,))
            conn.commit()
        logger.debug(f"Cart for chat_id {chat_id} deleted.")
    except sqlite3.Error as e:
        logger.error(f"Error deleting cart for chat_id {chat_id}: {e}")

# Функції для меню (з кешуванням)
menu_cache = []
last_menu_cache_time = None

def update_menu_cache(force=False):
    global menu_cache, last_menu_cache_time
    try:
        if not spreadsheet and not init_gspread_client():
            logger.warning("update_menu_cache: Google Sheets client not available.")
            return

        if not force and last_menu_cache_time and (datetime.now() - last_menu_cache_time).total_seconds < CACHE_TIMEOUT_SECONDS:
            logger.debug("update_menu_cache: using cached menu.")
            return
        
        logger.info("update_menu_cache: updating menu cache from Google Sheet...")
        ws = spreadsheet.worksheet("Меню")
        records = ws.get_all_records()
        processed = []
        for rec in records:
            item = {k: v for k, v in rec.items() if k} # Filter empty keys
            
            item['Назва Страви'] = str(item.get('Назва Страви') or item.get('Назва', '')).strip()
            
            if not item['Назва Страви']:
                logger.warning(f"update_menu_cache: skipped item without a name: {rec}")
                continue

            item['Активний'] = str(item.get('Активний', 'Так')).strip()
            item['ID'] = str(item.get('ID')) if item.get('ID') is not None else None

            if item['ID'] is None:
                logger.warning(f"update_menu_cache: skipped item '{item['Назва Страви']}' without an ID.")
                continue

            try:
                price_str = str(item.get('Ціна', '0')).strip().replace(',', '.')
                item['Ціна'] = float(price_str) if price_str else 0.0
            except (ValueError, TypeError):
                logger.warning(f"update_menu_cache: invalid price '{item.get('Ціна')}' for '{item['Назва Страви']}'. Setting to 0.0.")
                item['Ціна'] = 0.0
            
            item.setdefault('Опис', '').strip()
            item.setdefault('Категорія', 'Без категорії').strip()
            item.setdefault('Фото URL', '').strip()
            processed.append(item)
        
        menu_cache = processed
        last_menu_cache_time = datetime.now()
        logger.info(f"update_menu_cache: cached {len(menu_cache)} menu items.")
    except gspread.exceptions.WorksheetNotFound:
        logger.error("update_menu_cache: worksheet 'Меню' not found in Google Sheet.")
        menu_cache = []
    except Exception as e:
        logger.exception(f"update_menu_cache error: {e}")
        menu_cache = []

def get_item_by_id(item_id):
    update_menu_cache()
    item_id_str = str(item_id)
    for item in menu_cache:
        if str(item.get('ID')) == item_id_str:
            return item
    logger.warning(f"get_item_by_id: item with ID '{item_id_str}' not found in menu.")
    return None

# Функції для кошика
def show_cart(chat_id):
    cart = get_cart(chat_id)
    items = cart.get("items", [])
    if not items:
        tg_send_message(chat_id, "🛒 Ваш кошик порожній.")
        return

    total = sum(float(it.get("price", 0.0)) * int(it.get("qty", 0)) for it in items)
    cart_summary_text = "<b>Ваш кошик:</b>\n\n"
    inline_keyboard = []

    for idx, item_in_cart in enumerate(items):
        item_price = float(item_in_cart.get("price", 0.0))
        item_qty = int(item_in_cart.get("qty", 0))
        item_subtotal = item_price * item_qty
        cart_summary_text += f"{item_in_cart.get('name')} — {item_qty} × {item_price:.2f} = {item_subtotal:.2f} грн\n"
        inline_keyboard.append([
            {"text": "➖", "callback_data": f"qty_minus_{idx}"},
            {"text": f"{item_qty}", "callback_data": f"qty_info_{idx}"},
            {"text": "➕", "callback_data": f"qty_plus_{idx}"},
            {"text": "🗑️", "callback_data": f"remove_item_{idx}"}
        ])

    cart_summary_text += f"\n<b>Всього: {total:.2f} грн</b>"
    inline_keyboard.append([{"text": "✅ Оформити замовлення", "callback_data": "checkout"}])
    inline_keyboard.append([{"text": "🗑️ Очистити кошик", "callback_data": "clear_all_cart"}])
    tg_send_message(chat_id, cart_summary_text, reply_markup={"inline_keyboard": inline_keyboard})

def add_item_to_cart(chat_id, item_id, quantity=1):
    selected_item_info = get_item_by_id(item_id)
    if not selected_item_info:
        tg_send_message(chat_id, "Вибачте, цю позицію не знайдено в меню.")
        return

    user_cart = get_cart(chat_id)
    found_in_cart = False
    for item_in_cart in user_cart["items"]:
        if str(item_in_cart.get("id")) == str(selected_item_info.get("ID")):
            item_in_cart["qty"] = item_in_cart.get("qty", 0) + quantity
            found_in_cart = True
            break
    
    if not found_in_cart:
        user_cart["items"].append({
            "id": selected_item_info.get("ID"),
            "name": selected_item_info.get("Назва Страви", "N/A"),
            "price": selected_item_info.get("Ціна", 0.0),
            "qty": quantity
        })

    set_cart(chat_id, user_cart)
    tg_send_message(chat_id, f"'{selected_item_info.get('Назва Страви', 'N/A')} ' додано до кошика. Кількість: {user_cart['items'][-1]['qty'] if not found_in_cart else item_in_cart['qty']}.")

# Інші функції кошика (handle_cart_quantity_change, handle_remove_item_from_cart, clear_all_user_cart) з твоєї попередньої розробки

# Функції для оформлення замовлення
def start_checkout_process(chat_id):
    cart = get_cart(chat_id)
    if not cart.get('items'):
        tg_send_message(chat_id, "Ваш кошик порожній.", reply_markup=main_keyboard())
        return

    total_cart_value = sum(float(it.get("price", 0.0)) * int(it.get("qty", 0)) for it in cart["items"])
    if total_cart_value < MIN_ORDER_FOR_DELIVERY:
        tg_send_message(chat_id, f"Мінімальна сума замовлення для доставки становить {format_currency(MIN_ORDER_FOR_DELIVERY)}. Додайте ще... 😊", reply_markup=get_back_to_menu_keyboard())
        return
    
    # Запит телефону
    tg_send_message(chat_id, "Будь ласка, введіть ваш номер телефону для доставки (формат +380XXXXXXXXX):")
    set_state(chat_id, STATE_AWAITING_PHONE)

# Оновлений webhook з логікою телефону
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_SECRET and header_secret and header_secret != WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret header: %s", header_secret)
        return jsonify({"ok": False, "error": "invalid secret"}), 403

    update = request.get_json(force=True)
    logger.info("Update received: %s", json.dumps(update)[:1000])

    # message (text)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        user_state = get_state(chat_id)

        if user_state == STATE_AWAITING_PHONE:
            phone_number = re.sub(r'[^\d+]', '', text)
            if re.match(r'^\+?3?8?0\d{9}$', phone_number):
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "✅ Вірний номер", "callback_data": "confirm_phone"}],
                        [{"text": "✏️ Ввести інший", "callback_data": "change_phone"}]
                    ]
                }
                tg_send_message(chat_id, f"Ви ввели номер: {phone_number}. Чи вірний він? 😊", reply_markup=keyboard)
                set_state(chat_id, STATE_AWAITING_PHONE_CONFIRM)
            else:
                tg_send_message(chat_id, "Будь ласка, введіть коректний номер телефону у форматі +380XXXXXXXXX. 📱")
            
        # Інша логіка з твоєї попередньої розробки (меню, кошик, тощо)

    # callback_query (inline button pressed)
    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data", "")
        callback_id = cq.get("id")
        message = cq.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        if data == "confirm_phone":
            cart = get_cart(chat_id)
            cart["phone"] = phone_number  # Збереження номера
            set_cart(chat_id, cart)
            tg_answer_callback(callback_id, text="Номер підтверджено! ✅")
            tg_edit_message(chat_id, message_id, "✅ Номер підтверджено!", reply_markup=None)
            set_state(chat_id, STATE_NORMAL)
            # Продовжуємо до адреси
            tg_send_message(chat_id, "Тепер введіть вашу адресу доставки: 🏠")

        elif data == "change_phone":
            tg_answer_callback(callback_id, text="Введіть інший номер. 📱")
            tg_edit_message(chat_id, message_id, "Введіть інший номер телефону у форматі +380XXXXXXXXX:", reply_markup=None)
            set_state(chat_id, STATE_AWAITING_PHONE)

        # Інша логіка callback з твоєї попередньої розробки

    return jsonify({"ok": True})

# ---- health check ----
@app.route("/health", methods=["GET"])
def health():
    logger.info("Health check endpoint accessed")
    return jsonify({"status": "ok"})

# ---- Run (for local testing) ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting local Flask server on port %s", port)
    app.run(host="0.0.0.0", port=port)
