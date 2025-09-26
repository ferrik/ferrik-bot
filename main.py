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
from models.user import init_db, get_state, set_state, get_cart, set_cart, get_or_create_user, add_chat_history
from datetime import datetime

# Додані імпорти для оператора та адмін-панелі
from handlers.operator import handle_operator_command, handle_admin_callback
from services.admin_panel import track_user_activity, admin_panel

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
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Ternopil").strip()
TIMEZONE_NAME = os.environ.get("TIMEZONE_NAME", "Europe/Kyiv").strip()

# Кеш меню
MENU_CACHE = {}

# Обробка вхідних вебхуків
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Перевірка секретного токену
        if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
            logger.warning("Invalid webhook secret token received.")
            return jsonify({"status": "error", "message": "Invalid token"}), 403

        if "message" in data:
            process_message(data["message"])
        elif "callback_query" in data:
            process_callback_query(data["callback_query"])

        return jsonify({"status": "ok"})
    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_message(msg):
    """Обробляє текстові повідомлення"""
    try:
        chat_id = msg["chat"]["id"]
        user_info = msg.get("from", {})
        text = msg.get("text", "").strip()
        
        # Створюємо/оновлюємо користувача
        get_or_create_user(
            chat_id,
            user_info.get("username"),
            user_info.get("first_name"),
            user_info.get("last_name")
        )
        
        # Додаємо відстеження активності користувача для адмін-панелі
        track_user_activity(chat_id, user_info)
        
        if not text:
            return
            
        # Перевіряємо чи це команда для оператора
        if OPERATOR_CHAT_ID and handle_operator_command(chat_id, text, OPERATOR_CHAT_ID):
            return
            
        state = get_state(chat_id)
        
        # Обробка команд
        if text == "/start":
            user_name = user_info.get("first_name", "Друже")
            greeting_text = generate_personalized_greeting(user_name)
            
            keyboard = [[
                {"text": "Подивитися меню"},
                {"text": "Кошик"}
            ]]
            
            tg_send_message(chat_id, greeting_text, keyboard=keyboard)
        
        elif text == "/menu" or text == "Подивитися меню":
            show_main_menu(chat_id)

        elif text == "/cart" or text == "Кошик":
            show_cart(chat_id)

        elif text == "/contact":
            tg_send_message(chat_id, f"Зв'язатися з оператором: {OPERATOR_CHAT_ID}")
            
        elif text == "/help":
            help_text = "Я можу допомогти вам з наступними речами:\n" \
                        "/menu - показати меню\n" \
                        "/cart - показати кошик\n" \
                        "/contact - зв'язатися з оператором\n" \
                        "Також, ви можете просто написати мені, що ви хочете, і я допоможу з вибором!"
            tg_send_message(chat_id, help_text)

        elif text == "/status":
            tg_send_message(chat_id, "Бот працює справно!")

        # Перевіряємо, чи це не команда і не є станом очікування введення
        elif state in ["start_checkout", "ask_phone", "ask_city", "ask_street", "ask_house", "ask_flat", "ask_payment", "ask_delivery_time"]:
            handle_order_input(chat_id, text)
        
        else:
            # Обробка вільного тексту з Gemini
            handle_gemini_message(chat_id, text)

    except Exception as e:
        logger.exception(f"Error in process_message for chat_id {chat_id}: {e}")
        tg_send_message(chat_id, f"Виникла помилка: {e}")

def process_callback_query(cq):
    """Обробляє callback queries"""
    try:
        callback_id = cq.get("id")
        data = cq.get("data", "")
        message = cq.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        user_info = cq.get("from", {})
        
        # Перевіряємо чи це callback для адміністратора
        if OPERATOR_CHAT_ID and handle_admin_callback(chat_id, data, callback_id, OPERATOR_CHAT_ID):
            return
            
        parts = data.split("_")
        action = parts[0]
        
        if action == "category":
            show_items_by_category(chat_id, parts[1])

        elif action == "item":
            show_item_details(chat_id, parts[1])

        elif action == "add":
            item_id = parts[1]
            add_item_to_cart(chat_id, item_id)
            tg_answer_callback(callback_id, "Товар додано до кошика!")

        elif action == "cart":
            show_cart(chat_id)

        elif action == "checkout":
            start_checkout_process(chat_id, message_id)
            tg_answer_callback(callback_id, "Переходимо до оформлення!")

        elif action == "remove":
            item_id = parts[1]
            remove_item_from_cart(chat_id, item_id)
            tg_answer_callback(callback_id, "Товар видалено з кошика!")

        elif action == "clear_cart":
            set_cart(chat_id, {})
            show_cart(chat_id)
            tg_answer_callback(callback_id, "Кошик очищено.")

        elif action == "confirm_order":
            confirm_order(chat_id)
            tg_answer_callback(callback_id, "Замовлення підтверджено!")
        
        elif action == "cancel_order":
            cancel_order(chat_id)
            tg_answer_callback(callback_id, "Замовлення скасовано.")

        elif action == "delivery":
            handle_delivery_type(chat_id, data)
        
        elif action == "payment":
            handle_payment_method(chat_id, data)

        elif action == "time":
            handle_delivery_time(chat_id, data)

        else:
            tg_answer_callback(callback_id, "Невідома дія.")

    except Exception as e:
        logger.exception(f"Error in process_callback_query for chat_id {chat_id}: {e}")
        tg_answer_callback(callback_id, f"Виникла помилка: {e}")

def handle_order_input(chat_id, text):
    """Обробляє введення користувача на етапах оформлення замовлення"""
    state = get_state(chat_id)
    if state == "ask_phone":
        # ... (існуючий код)
        pass
    elif state == "ask_city":
        # ... (існуючий код)
        pass
    elif state == "ask_street":
        # ... (існуючий код)
        pass
    elif state == "ask_house":
        # ... (існуючий код)
        pass
    elif state == "ask_flat":
        # ... (існуючий код)
        pass

def handle_gemini_message(chat_id, text):
    """Обробляє повідомлення за допомогою Gemini"""
    add_chat_history(chat_id, "user", text)
    recommendation = get_gemini_recommendation(chat_id, text, get_menu_from_sheet())
    add_chat_history(chat_id, "assistant", recommendation)
    tg_send_message(chat_id, recommendation)

def show_main_menu(chat_id):
    """Відображає головне меню з категоріями"""
    categories = list(set(item['Категорія'] for item in get_menu_from_sheet()))
    keyboard = []
    for cat in categories:
        keyboard.append([{"text": cat, "callback_data": f"category_{cat}"}])
    
    tg_send_message(chat_id, "Ось наше меню, оберіть категорію:", keyboard=keyboard)

def show_items_by_category(chat_id, category):
    """Відображає товари в обраній категорії"""
    items = [item for item in get_menu_from_sheet() if item['Категорія'] == category]
    keyboard = []
    for item in items:
        keyboard.append([{"text": f"{item['Страви']} - {item['Ціна']} грн", "callback_data": f"item_{item['ID']}"}])
    
    keyboard.append([{"text": "⬅️ Назад до меню", "callback_data": "menu"}])
    
    tg_send_message(chat_id, f"Ось що ми маємо в категорії '{category}':", keyboard=keyboard)

def show_item_details(chat_id, item_id):
    """Відображає деталі конкретного товару"""
    item = get_item_by_id(item_id)
    if not item:
        tg_send_message(chat_id, "Вибачте, цей товар не знайдено.")
        return
        
    message_text = f"**{item['Страви']}**\n\n" \
                   f"{item['Опис']}\n\n" \
                   f"💰 **Ціна**: {item['Ціна']} грн"
    
    keyboard = [[{"text": f"🛒 Додати в кошик", "callback_data": f"add_{item['ID']}"}]]
    tg_send_message(chat_id, message_text, keyboard=keyboard)

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

# Доданий endpoint для ручного створення дашборду
@app.route("/setup_dashboard", methods=["GET"])
def setup_dashboard():
    """Створює початкову структуру дашборду в Google Sheets"""
    try:
        success = admin_panel.create_dashboard_formulas()
        if success:
            return jsonify({
                "status": "ok", 
                "message": "Dashboard created successfully",
                "sheets_url": f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to create dashboard"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Доданий endpoint для отримання статистики через API
@app.route("/api/stats", methods=["GET"])
def api_stats():
    """API endpoint для отримання статистики"""
    try:
        date_param = request.args.get('date')
        if date_param:
            from datetime import datetime
            date = datetime.strptime(date_param, '%Y-%m-%d').date()
        else:
            date = None
            
        stats = admin_panel.get_daily_stats(date)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ініціалізація
with app.app_context():
    logger.info("🚀 FerrikFootBot starting initialization...")
    
    try:
        # Ініціалізація бази даних
        if init_db():
            logger.info("✅ Database initialized")
        else:
            logger.error("❌ Database initialization failed")
        
        # Підключення до Google Sheets
        if init_gspread_client():
            logger.info("✅ Google Sheets connected")
            
            # Завантажуємо меню для кешування
            menu_items = get_menu_from_sheet(force=True)
            logger.info(f"✅ Menu cached: {len(menu_items)} items")
        else:
            logger.error("❌ Google Sheets connection failed")

        # Ініціалізуємо адмін-панель
        if admin_panel.init_connection():
            logger.info("✅ Admin panel connected successfully")
            
            # Створюємо структуру дашборду якщо потрібно
            try:
                admin_panel.create_dashboard_formulas()
                logger.info("✅ Dashboard structure created")
            except Exception as e:
                logger.warning(f"⚠️ Dashboard setup warning: {e}")
        else:
            logger.error("❌ Admin panel connection failed")
        
        logger.info("🎉 FerrikFootBot initialization completed!")
        
    except Exception as e:
        logger.exception(f"❌ Critical startup error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    if debug_mode:
        app.run(host="0.0.0.0", port=port, debug=True)
    else:
        # Установка вебхука при запуску в production
        webhook_url = os.environ.get("WEBHOOK_URL", "")
        if webhook_url:
            try:
                response = requests.get(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                    params={
                        "url": webhook_url,
                        "secret_token": WEBHOOK_SECRET
                    },
                    timeout=10
                )
                logger.info(f"Webhook set response: {response.json()}")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}")
