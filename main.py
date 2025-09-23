import os
import logging
import json
import re
from flask import Flask, request, jsonify
import requests
from handlers.cart import show_cart, add_item_to_cart, handle_cart_quantity_change, remove_item_from_cart, clear_cart
from handlers.order import start_checkout_process, handle_delivery_type, handle_address_input, handle_payment_method, handle_delivery_time, show_order_confirmation, confirm_order, cancel_order
from handlers.geo import check_delivery_availability
from services.sheets import init_gspread_client, get_menu_from_sheet, get_item_by_id, get_categories, get_items_by_category
from services.telegram import tg_send_message, tg_send_photo, tg_answer_callback, tg_edit_message, notify_operator
from services.gemini import get_gemini_recommendation
from models.user import init_db, get_state, set_state, get_cart, set_cart, get_or_create_user, add_chat_history
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

def main_keyboard():
    """Головне меню бота"""
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
        categories = get_categories()
        if not categories:
            tg_send_message(chat_id, "Вибачте, меню тимчасово недоступне. 😔")
            return
            
        keyboard = {
            "inline_keyboard": [
                [{"text": f"🍽️ {cat}", "callback_data": f"category_{cat}"}] 
                for cat in categories
            ]
        }
        tg_send_message(chat_id, "Оберіть категорію меню: 🍽️", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing menu: {e}")
        tg_send_message(chat_id, "Помилка при завантаженні меню. 😔")

def show_category_items(chat_id, category):
    """Показує страви з конкретної категорії"""
    try:
        items = get_items_by_category(category)
        
        if not items:
            tg_send_message(chat_id, f"У категорії '{category}' немає доступних страв. 😔")
            return
            
        for item in items:
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

def handle_phone_input(chat_id, text):
    """Обробляє введення номера телефону"""
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

def handle_feedback(chat_id, text):
    """Обробляє відгук користувача"""
    if OPERATOR_CHAT_ID:
        user_info = {"first_name": "Користувач"}  # Можна отримати з бази
        notify_operator(f"📝 Новий відгук:\n\n{text}", chat_id, user_info)
    
    tg_send_message(chat_id, "Дякуємо за ваш відгук! 😊 Ми цінуємо вашу думку.")
    set_state(chat_id, STATE_NORMAL)

def handle_operator_message(chat_id, text):
    """Обробляє повідомлення для оператора"""
    if OPERATOR_CHAT_ID:
        user_info = {"first_name": "Користувач"}
        notify_operator(f"📞 Повідомлення від користувача:\n\n{text}", chat_id, user_info)
        tg_send_message(chat_id, "Ваше повідомлення передано оператору! Очікуйте відповіді. 📞")
    else:
        tg_send_message(chat_id, "Вибачте, зараз оператор недоступний. 😔")
    
    set_state(chat_id, STATE_NORMAL)

def generate_personalized_greeting(user_name="Друже"):
    """Генерує персоналізоване вітання"""
    user_name = (user_name or '').strip() or 'Друже'
    current = datetime.now() if not ZoneInfo else datetime.now(ZoneInfo(TIMEZONE_NAME))
    hour = current.hour

    greeting = f"Доброго {'ранку' if 6 <= hour < 12 else 'дня' if 12 <= hour < 18 else 'вечора'}, {user_name}! 😊"
    status = "Ресторан відкритий! 🍽️ Готові прийняти ваше замовлення." if is_restaurant_open() else "Ресторан закритий. 😔 Працюємо з 9:00 до 22:00."
    return f"{greeting}\n\n{status}\n\nЯ ваш помічник для замовлення їжі! 🍔🍕"

def is_restaurant_open():
    """Перевіряє чи відкритий ресторан"""
    current_hour = datetime.now().hour if not ZoneInfo else datetime.now(ZoneInfo(TIMEZONE_NAME)).hour
    return 9 <= current_hour < 22

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробляє оновлення від Telegram"""
    header_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if WEBHOOK_SECRET and header_secret != WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret header: %s", header_secret)
        return jsonify({"ok": False, "error": "invalid secret"}), 403

    update = request.get_json(silent=True)
    if not update:
        logger.warning("Webhook received empty data.")
        return jsonify({"status": "empty"}), 200

    logger.info(f"Update received: {update}")

    # Обробка повідомлень
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_info = msg.get("from", {})
        text = msg.get("text", "").strip()
        user_state = get_state(chat_id)

        # Створюємо або оновлюємо користувача
        get_or_create_user(
            chat_id, 
            user_info.get("username"),
            user_info.get("first_name"),
            user_info.get("last_name")
        )

        # Зберігаємо в історію чату
        if text:
            add_chat_history(chat_id, text, is_user=True)

        if text == "/start":
            greeting = generate_personalized_greeting(user_info.get("first_name", "Друже"))
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
        elif user_state == STATE_AWAITING_DELIVERY_TIME:
            handle_delivery_time(chat_id, text)
        else:
            # Використовуємо AI для відповіді або показуємо головне меню
            try:
                if text and len(text) > 5:  # Якщо це справді запит
                    ai_response = get_gemini_recommendation(text)
                    tg_send_message(chat_id, ai_response)
                    add_chat_history(chat_id, ai_response, is_user=False)
                else:
                    tg_send_message(chat_id, "Не зрозумів вас. Скористайтеся меню: 👇", 
                                  reply_markup=main_keyboard())
            except Exception as e:
                logger.error(f"AI response error: {e}")
                tg_send_message(chat_id, "Не зрозумів вас. Скористайтеся меню: 👇", 
                              reply_markup=main_keyboard())

    # Обробка callback queries
    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data", "")
        callback_id = cq.get("id")
        message = cq.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        user_info = cq.get("from", {})

        # Створюємо або оновлюємо користувача
        get_or_create_user(
            chat_id, 
            user_info.get("username"),
            user_info.get("first_name"), 
            user_info.get("last_name")
        )

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
            
            # Переходимо до вибору типу доставки
            from handlers.order import ask_delivery_type
            ask_delivery_type(chat_id)
        elif data == "change_phone":
            tg_answer_callback(callback_id, text="Введіть інший номер. 📱")
            tg_edit_message(chat_id, message_id, "Введіть інший номер телефону у форматі +380XXXXXXXXX:")
            set_state(chat_id, STATE_AWAITING_PHONE)
        # Обробка типів доставки
        elif data.startswith("delivery_type_"):
            delivery_type = data.replace("delivery_type_", "")
            handle_delivery_type(chat_id, delivery_type, callback_id)
        # Обробка способів оплати
        elif data.startswith("payment_"):
            payment_method = data.replace("payment_", "")
            handle_payment_method(chat_id, payment_method, callback_id)
        # Обробка часу доставки
        elif data.startswith("delivery_time_"):
            delivery_time = data.replace("delivery_time_", "")
            handle_delivery_time(chat_id, delivery_time, callback_id)
        elif data == "custom_delivery_time":
            tg_answer_callback(callback_id)
            tg_send_message(chat_id, "Введіть бажаний час доставки у форматі ГГ:ХХ (наприклад, 14:30):")
            set_state(chat_id, STATE_AWAITING_DELIVERY_TIME)
        # Обробка підтвердження замовлення
        elif data == "confirm_order":
            confirm_order(chat_id, callback_id)
        elif data == "cancel_order":
            cancel_order(chat_id, callback_id)
        elif data == "edit_order":
            tg_answer_callback(callback_id)
            tg_send_message(chat_id, "Функція редагування поки що недоступна. Скасуйте замовлення та почніть заново.")
        # Обробка кошика
        elif data.startswith("qty_minus_"):
            idx = int(data.replace("qty_minus_", ""))
            handle_cart_quantity_change(chat_id, "minus", idx, callback_id)
        elif data.startswith("qty_plus_"):
            idx = int(data.replace("qty_plus_", ""))
            handle_cart_quantity_change(chat_id, "plus", idx, callback_id)
        elif data.startswith("remove_item_"):
            idx = int(data.replace("remove_item_", ""))
            remove_item_from_cart(chat_id, idx, callback_id)
        elif data == "clear_cart":
            clear_cart(chat_id, callback_id)
        else:
            tg_answer_callback(callback_id, "Невідома команда")

    return jsonify({"ok": True})

# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """Health check для Render"""
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

# Root endpoint
@app.route("/", methods=["GET"])
def root():
    """Корінний endpoint"""
    return jsonify({
        "message": "FerrikFootBot API",
        "status": "running",
        "endpoints": ["/webhook", "/health"]
    })

# Ініціалізація
with app.app_context():
    logger.info("Bot initialization started.")
    
    # Ініціалізуємо базу даних
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Підключаємося до Google Sheets
    if init_gspread_client():
        logger.info("Google Sheets connected successfully.")
        # Завантажуємо меню для кешування
        try:
            menu_items = get_menu_from_sheet(force=True)
            logger.info(f"Menu cached: {len(menu_items)} items")
        except Exception as e:
            logger.error(f"Failed to cache menu: {e}")
    else:
        logger.error("Google Sheets initialization failed.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
