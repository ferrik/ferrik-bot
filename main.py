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
STATE_AWAITING_OPERATOR_MESSAGE = "awaiting_operator_message"

# Функції Telegram API
def tg_send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        return None

def tg_send_photo(chat_id, photo_url, caption, reply_markup=None):
    payload = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(f"{API_URL}/sendPhoto", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send photo to {chat_id}: {e}")
        return None

def tg_edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(f"{API_URL}/editMessageText", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to edit message {message_id} in {chat_id}: {e}")
        return None

def tg_answer_callback(callback_id, text=""):
    try:
        response = requests.post(
            f"{API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": text},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to answer callback {callback_id}: {e}")
        return None

def main_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🍽️ Меню", "callback_data": "show_menu"}],
            [{"text": "🛒 Кошик", "callback_data": "show_cart"}],
            [{"text": "📞 Зв'язатися з оператором", "callback_data": "contact_operator"}],
            [{"text": "📝 Залишити відгук", "callback_data": "leave_feedback"}]
        ]
    }

def show_menu(chat_id):
    """Показує меню з категоріями"""
    try:
        menu_items = get_menu_from_sheet()
        if not menu_items:
            tg_send_message(chat_id, "Вибачте, меню тимчасово недоступне. 😔")
            return
            
        # Групуємо за категоріями
        categories = {}
        for item in menu_items:
            if item.get("active", True):
                cat = item.get("category", "Інше")
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)
        
        if not categories:
            tg_send_message(chat_id, "Меню порожнє. 😔")
            return
            
        # Створюємо кнопки категорій
        keyboard = {
            "inline_keyboard": [
                [{"text": f"{cat} ({len(items)})", "callback_data": f"category_{cat}"}] 
                for cat, items in categories.items()
            ]
        }
        tg_send_message(chat_id, "Оберіть категорію меню: 🍽️", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing menu: {e}")
        tg_send_message(chat_id, "Помилка при завантаженні меню. 😔")

def show_category_items(chat_id, category):
    """Показує страви з конкретної категорії"""
    try:
        menu_items = get_menu_from_sheet()
        category_items = [item for item in menu_items 
                         if item.get("category") == category and item.get("active", True)]
        
        if not category_items:
            tg_send_message(chat_id, f"У категорії '{category}' немає доступних страв. 😔")
            return
            
        for item in category_items:
            text = f"<b>{item['name']}</b>\n"
            text += f"💰 Ціна: {item['price']:.2f} грн\n"
            if item.get("description"):
                text += f"📝 {item['description']}\n"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "➕ Додати в кошик", "callback_data": f"add_item_{item['ID']}"}]
                ]
            }
            
            if item.get("photo"):
                tg_send_photo(chat_id, item["photo"], text, reply_markup=keyboard)
            else:
                tg_send_message(chat_id, text, reply_markup=keyboard)
                
        # Кнопка "Назад до категорій"
        back_keyboard = {
            "inline_keyboard": [
                [{"text": "⬅️ Назад до категорій", "callback_data": "show_menu"}]
            ]
        }
        tg_send_message(chat_id, "─────────────", reply_markup=back_keyboard)
        
    except Exception as e:
        logger.error(f"Error showing category {category}: {e}")
        tg_send_message(chat_id, "Помилка при завантаженні категорії. 😔")

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
            handle_phone_input(chat_id, text)
        elif user_state == STATE_AWAITING_ADDRESS:
            handle_address_input(chat_id, text)
        elif user_state == STATE_AWAITING_FEEDBACK:
            handle_feedback(chat_id, text)
        elif user_state == STATE_AWAITING_OPERATOR_MESSAGE:
            handle_operator_message(chat_id, text)
        else:
            # Використовуємо AI для відповіді
            try:
                ai_response = get_gemini_recommendation(text)
                tg_send_message(chat_id, ai_response)
            except:
                tg_send_message(chat_id, "Не зрозумів вас. Скористайтесь меню нижче: 👇", 
                              reply_markup=main_keyboard())

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
        elif data.startswith("category_"):
            category = data.replace("category_", "")
            show_category_items(chat_id, category)
            tg_answer_callback(callback_id)
        elif data.startswith("add_item_"):
            item_id = data.replace("add_item_", "")
            add_item_to_cart(chat_id, item_id)
            tg_answer_callback(callback_id, "Додано в кошик! 🛒")
        elif data == "checkout":
            start_checkout_process(chat_id)
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
            tg_edit_message(chat_id, message_id, "✅ Номер підтверджено!")
            set_state(chat_id, STATE_AWAITING_ADDRESS)
            tg_send_message(chat_id, "Тепер введіть вашу адресу доставки: 🏠")
        elif data == "change_phone":
            tg_answer_callback(callback_id, text="Введіть інший номер. 📱")
            tg_edit_message(chat_id, message_id, "Введіть інший номер телефону у форматі +380XXXXXXXXX:")
            set_state(chat_id, STATE_AWAITING_PHONE)
        # Обробка кошика
        elif data.startswith("qty_"):
            handle_cart_quantity(chat_id, data, callback_id)
        elif data.startswith("remove_item_"):
            handle_remove_item(chat_id, data, callback_id)
        else:
            tg_answer_callback(callback_id, "Невідома команда")

    return jsonify({"ok": True})

def handle_phone_input(chat_id, text):
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

def handle_address_input(chat_id, text):
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

def handle_feedback(chat_id, text):
    # Відправляємо відгук оператору
    if OPERATOR_CHAT_ID:
        operator_message = f"📝 Новий відгук від користувача {chat_id}:\n\n{text}"
        tg_send_message(OPERATOR_CHAT_ID, operator_message)
    
    tg_send_message(chat_id, "Дякуємо за ваш відгук! 😊 Ми цінуємо вашу думку.")
    set_state(chat_id, STATE_NORMAL)

def handle_operator_message(chat_id, text):
    # Відправляємо повідомлення оператору
    if OPERATOR_CHAT_ID:
        operator_message = f"📞 Повідомлення від користувача {chat_id}:\n\n{text}"
        tg_send_message(OPERATOR_CHAT_ID, operator_message)
        tg_send_message(chat_id, "Ваше повідомлення передано оператору! Очікуйте відповіді. 📞")
    else:
        tg_send_message(chat_id, "Вибачте, зараз оператор недоступний. 😔")
    
    set_state(chat_id, STATE_NORMAL)

def handle_cart_quantity(chat_id, data, callback_id):
    # Логіка для зміни кількості товару в кошику
    # Реалізація залежить від структури даних кошика
    tg_answer_callback(callback_id, "Кількість оновлено!")

def handle_remove_item(chat_id, data, callback_id):
    # Логіка для видалення товару з кошика
    # Реалізація залежить від структури даних кошика
    tg_answer_callback(callback_id, "Товар видалено з кошика!")

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
    
    if init_gspread_client():
        logger.info("Google Sheets connected successfully.")
    else:
        logger.error("Google Sheets initialization failed.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
