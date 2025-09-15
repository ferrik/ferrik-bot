import os
import logging
import json
from flask import Flask, request, jsonify
import requests
from handlers.cart import show_cart, add_item_to_cart
from handlers.order import start_checkout_process
from handlers.geo import check_delivery_availability
from services.sheets import init_gspread_client, update_menu_cache, get_item_by_id
from services.gemini import get_gemini_recommendation
from models.user import init_db, get_state, set_state, get_cart, set_cart
from datetime import datetime
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
TIMEZONE_NAME = os.environ.get("TIMEZONE", "Europe/Kyiv").strip()

# Стани користувача
STATE_NORMAL = "normal"
STATE_AWAITING_PHONE = "awaiting_phone"
STATE_AWAITING_PHONE_CONFIRM = "awaiting_phone_confirm"
STATE_AWAITING_ADDRESS = "awaiting_address"
STATE_AWAITING_PAYMENT_METHOD = "awaiting_payment_method"
STATE_AWAITING_DELIVERY_TYPE = "awaiting_delivery_type"
STATE_AWAITING_DELIVERY_TIME = "awaiting_delivery_time"
STATE_AWAITING_CONFIRMATION = "awaiting_confirmation"
STATE_AWAITING_FEEDBACK = "awaiting_feedback"

# Функції Telegram API
def tg_send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")

def tg_send_photo(chat_id, photo_url, caption, reply_markup=None):
    payload = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(f"{API_URL}/sendPhoto", json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send photo to {chat_id}: {e}")

def tg_answer_callback(callback_id, text=""):
    try:
        response = requests.post(
            f"{API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": text},
            timeout=10
        )
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to answer callback {callback_id}: {e}")

def main_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🍽️ Меню", "callback_data": "show_menu"}],
            [{"text": "🛒 Кошик", "callback_data": "show_cart"}],
            [{"text": "📞 Зв’язатися з оператором", "callback_data": "contact_operator"}],
            [{"text": "📝 Залишити відгук", "callback_data": "leave_feedback"}]
        ]
    }

# Webhook
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_SECRET and header_secret != WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret header: %s", header_secret)
        return jsonify({"ok": False, "error": "invalid secret"}), 403

    update = request.get_json(silent=True)
    if not update:
        logger.warning("Webhook received empty data.")
        return jsonify({"status": "empty"}), 200

    # Обробка повідомлень
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        user_state = get_state(chat_id)

        if text == "/start":
            greeting = generate_personalized_greeting(msg.get("from", {}).get("first_name", "Друже"))
            tg_send_message(chat_id, greeting, reply_markup=main_keyboard())
            set_state(chat_id, STATE_NORMAL)
        elif text == "/cart":
            show_cart(chat_id)
        elif text.startswith("/add_"):
            item_id = text.replace("/add_", "")
            add_item_to_cart(chat_id, item_id)
        elif user_state == STATE_AWAITING_PHONE:
            phone_number = re.sub(r'[^\d+]', '', text)
            if re.match(r'^\+?3?8?0\d{9}$', phone_number):
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "✅ Вірний номер", "callback_data": f"confirm_phone_{phone_number}"}],
                        [{"text": "✏️ Ввести інший", "callback_data": "change_phone"}]
                    ]
                }
                tg_send_message(chat_id, f"Ви ввели номер: {phone_number}. Чи вірний він? 😊", reply_markup=keyboard)
                set_state(chat_id, STATE_AWAITING_PHONE_CONFIRM)
            else:
                tg_send_message(chat_id, "Будь ласка, введіть коректний номер телефону у форматі +380XXXXXXXXX. 📱")
        elif user_state == STATE_AWAITING_ADDRESS:
            address = text.strip()
            coords = check_delivery_availability(address)
            if coords:
                cart = get_cart(chat_id)
                cart["address"] = address
                cart["coords"] = coords
                set_cart(chat_id, cart)
                tg_send_message(chat_id, "Адреса прийнята! 🏠 Оберіть спосіб оплати:", reply_markup={
                    "inline_keyboard": [
                        [{"text": "💳 Карта", "callback_data": "payment_card"}],
                        [{"text": "💵 Готівка", "callback_data": "payment_cash"}]
                    ]
                })
                set_state(chat_id, STATE_AWAITING_PAYMENT_METHOD)
            else:
                tg_send_message(chat_id, "Вибачте, доставка за цією адресою неможлива. 😔 Спробуйте іншу адресу.")

    # Обробка callback
    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data", "")
        callback_id = cq.get("id")
        message = cq.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        if data == "show_menu":
            show_menu(chat_id)
            tg_answer_callback(callback_id)
        elif data == "show_cart":
            show_cart(chat_id)
            tg_answer_callback(callback_id)
        elif data == "contact_operator":
            tg_send_message(chat_id, "Напишіть ваше повідомлення для оператора: 📞")
            set_state(chat_id, STATE_AWAITING_OPERATOR_MESSAGE)
            tg_answer_callback(callback_id)
        elif data == "leave_feedback":
            tg_send_message(chat_id, "Будь ласка, напишіть ваш відгук: 📝")
            set_state(chat_id, STATE_AWAITING_FEEDBACK)
            tg_answer_callback(callback_id)
        elif data.startswith("confirm_phone_"):
            phone_number = data.replace("confirm_phone_", "")
            cart = get_cart(chat_id)
            cart["phone"] = phone_number
            set_cart(chat_id, cart)
            tg_answer_callback(callback_id, text="Номер підтверджено! ✅")
            tg_edit_message(chat_id, message_id, "✅ Номер підтверджено!", reply_markup=None)
            set_state(chat_id, STATE_AWAITING_ADDRESS)
            tg_send_message(chat_id, "Тепер введіть вашу адресу доставки: 🏠")
        elif data == "change_phone":
            tg_answer_callback(callback_id, text="Введіть інший номер. 📱")
            tg_edit_message(chat_id, message_id, "Введіть інший номер телефону у форматі +380XXXXXXXXX:", reply_markup=None)
            set_state(chat_id, STATE_AWAITING_PHONE)

    return jsonify({"ok": True})

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

def show_menu(chat_id):
    update_menu_cache()
    categories = set(item["Категорія"] for item in menu_cache if item.get("Активний", "Так").lower() == "так")
    keyboard = {
        "inline_keyboard": [[{"text": cat, "callback_data": f"category_{cat}"}] for cat in sorted(categories)]
    }
    tg_send_message(chat_id, "Оберіть категорію меню: 🍽️", reply_markup=keyboard)

# Ініціалізація
with app.app_context():
    logger.info("Bot initialization started.")
    init_db()
    init_gspread_client()
    update_menu_cache(force=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
