import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ferrik')

# Ініціалізація Flask
app = Flask(__name__)

# Імпорти з обробкою помилок
logger.info("🚀 Starting FerrikFootBot...")

try:
    # Припускаємо, що ці модулі та змінні існують
    from config import BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID, ENABLE_GOOGLE_SHEETS
    logger.info("✅ Config imported successfully")
except Exception as e:
    logger.error(f"❌ Config import error: {e}")

try:
    from services.sheets import init_gspread_client, get_menu_from_sheet, save_order_to_sheets, is_sheets_connected
    logger.info("✅ Sheets service imported")
except Exception as e:
    logger.error(f"❌ Sheets import error: {e}")

try:
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    logger.info("✅ Gemini service imported")
except Exception as e:
    logger.error(f"❌ Gemini import error: {e}")

try:
    from models.user import init_user_db
    logger.info("✅ User model imported")
except Exception as e:
    logger.error(f"❌ User model import error: {e}")


# Глобальні змінні
sheets_client = None
menu_cache = {}
user_db = False # Флаг стану
gemini_client = None


# Ініціалізація сервісів
def init_services():
    """Ініціалізує всі сервіси (DB, Sheets, Gemini)"""
    global sheets_client, menu_cache, user_db, gemini_client

    logger.info("🛠️ Initializing services...")
    
    # 1. Ініціалізація config та логування
    import config
    config.log_config()
    
    # 2. Ініціалізація бази даних користувачів
    try:
        if init_user_db():
            user_db = True  # Флаг для перевірки
            logger.info("✅ User DB initialized.")
        else:
            logger.error("❌ User DB initialization failed.")
    except Exception as e:
        logger.exception(f"❌ User DB startup error: {e}")

    # 3. Ініціалізація Google Sheets
    if ENABLE_GOOGLE_SHEETS:
        try:
            sheets_client = init_gspread_client()
            if is_sheets_connected():
                logger.info("✅ Google Sheets client initialized.")
                
                # --- ВИПРАВЛЕННЯ ПОМИЛКИ TypeError ---
                # Видалено 'force=True', оскільки це спричинило TypeError.
                # Тепер функція викликається лише з необхідним аргументом sheets_client.
                menu_data = get_menu_from_sheet(sheets_client)
                menu_cache = menu_data if menu_data is not None else {}
                logger.info(f"✅ Menu cached: {len(menu_cache)} items.")
            else:
                logger.warning("⚠️ Google Sheets client could not connect.")
        except Exception as e:
            # Логуємо помилку і продовжуємо, щоб бот не впав, але функціонал меню буде недоступний
            logger.exception(f"❌ Critical startup error during Google Sheets initialization: {e}")
    else:
        logger.info("⏭️ Google Sheets disabled by config.")
        
    # 4. Ініціалізація Gemini AI
    try:
        gemini_client = init_gemini_client()
        if is_gemini_connected():
            logger.info("✅ Gemini client initialized.")
        else:
            logger.warning("⚠️ Gemini client could not connect.")
    except Exception as e:
        logger.exception(f"❌ Gemini startup error: {e}")


# Декоратори для перевірки стану
def requires_db(func):
    def wrapper(*args, **kwargs):
        if not user_db:
            # Це функція send_message, яку потрібно визначити
            # Для простоти, припускаємо, що chat_id - перший аргумент
            chat_id = kwargs.get('chat_id') or args[0] if args else None
            send_message(chat_id, "❌ База даних користувачів недоступна. Спробуйте пізніше.")
            return None
        return func(*args, **kwargs)
    return wrapper

def requires_sheets(func):
    def wrapper(*args, **kwargs):
        if not menu_cache:
            chat_id = kwargs.get('chat_id') or args[0] if args else None
            send_message(chat_id, "❌ Меню тимчасово недоступне. Спробуйте пізніше.")
            return None
        return func(*args, **kwargs)
    return wrapper
    
# Функція відправки повідомлень (спрощена заглушка)
def send_message(chat_id, text, reply_markup=None):
    """Надсилає повідомлення через Telegram API."""
    import requests
    try:
        bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not found in send_message")
            return None
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            import json
            payload["reply_markup"] = json.dumps(reply_markup)
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Send message error: {e}")
        return None

# Решта функцій
# ... [handle_start, show_menu, show_contacts, show_recommendations, process_callback_query] ...

def handle_start(chat_id):
    """Обробка команди /start"""
    welcome_text = (
        "👋 Привіт!\n\n"
        "Я <b>FoodBot</b> – твій помічник для замовлення їжі.\n\n"
        "Обери дію в меню:"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📖 Меню", "callback_data": "menu"}],
            [{"text": "🛒 Корзина", "callback_data": "cart"}, {"text": "⭐ Рекомендація", "callback_data": "recommend"}]
        ]
    }
    
    send_message(chat_id, welcome_text, reply_markup=keyboard)


def show_menu(chat_id):
    """Показати меню"""
    if not menu_cache:
        send_message(chat_id, "Меню тимчасово недоступне.")
        return

    menu_text = "<b>📖 Наше Меню:</b>\n\n"
    
    # Спрощена логіка: виводимо перші 5 страв
    items = list(menu_cache.values())
    for item in items[:5]:
        menu_text += f"🍕 <b>{item.get('name', 'Без назви')}</b> - {item.get('price', '?')} грн\n"
    
    menu_text += "\n... та багато іншого! Використовуйте /full_menu для повного списку."
    send_message(chat_id, menu_text)


def show_contacts(chat_id):
    """Показати контакти"""
    contacts_text = """
📞 <b>Контакти</b>

📱 Телефон: +380XX XXX XX XX
📧 Email: info@ferrikfoot.com
📍 Адреса: м. Київ, вул. Прикладна, 1
"""
    send_message(chat_id, contacts_text)


def show_recommendations(chat_id):
    """Показати рекомендації"""
    # ... (реалізація з get_ai_response) ...
    send_message(chat_id, "🎯 <b>Рекомендації:</b>\n\nAI-рекомендації в розробці. Спробуйте пізніше!")


def process_callback_query(callback_query):
    """Обробка callback запитів"""
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        data = callback_query["data"]
        
        if data == "menu":
            show_menu(chat_id)
        elif data == "cart":
            send_message(chat_id, "🛒 Ваша корзина порожня.")
        elif data == "recommend":
            show_recommendations(chat_id)
        else:
            send_message(chat_id, f"Обрано: {data}")

    except Exception as e:
        logger.error(f"Callback error: {e}")


def process_message(message):
    """Обробка вхідного текстового повідомлення"""
    try:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        
        if text == "/start":
            handle_start(chat_id)
        elif text == "/menu" or text.lower() in ["меню", "показати меню"]:
            show_menu(chat_id)
        elif text == "/contacts" or text.lower() in ["контакти", "адреса"]:
            show_contacts(chat_id)
        else:
            send_message(chat_id, f"Я отримав ваше повідомлення: <b>{text}</b>. Спробуйте /start або /menu.")

    except Exception as e:
        logger.error(f"Message processing error: {e}")
        send_message(message["chat"]["id"], "Виникла помилка при обробці вашого запиту.")


@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробка вхідних вебхуків від Telegram"""
    if request.method == 'POST':
        update = request.get_json()
        if not update:
            logger.warning("Empty update received")
            return jsonify({'status': 'ok'})

        if 'message' in update:
            process_message(update['message'])
        elif 'callback_query' in update:
            process_callback_query(update['callback_query'])
            
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'method not allowed'}), 405


def answer_callback(callback_id, text):
    """Відповідає на callback query (заглушка)"""
    # Реалізація тут або імпорт з services.telegram
    pass


# Обробка помилок
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# Ініціалізація сервісів при запуску додатку
with app.app_context():
    init_services()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # У production-середовищі (Render) gunicorn запускає додаток, тому цей блок 
    # зазвичай не виконується. У development його можна використовувати.
    logger.warning("Running Flask in development mode (should be gunicorn in production)")
    app.run(host="0.0.0.0", port=port, debug=True)
