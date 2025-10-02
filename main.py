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
    from config import (
        BOT_TOKEN, 
        GEMINI_API_KEY, 
        SPREADSHEET_ID, 
        WEBHOOK_SECRET,
        validate_config,
        log_config
    )
    # Перевірка чи існує ENABLE_GOOGLE_SHEETS
    try:
        from config import ENABLE_GOOGLE_SHEETS
    except ImportError:
        ENABLE_GOOGLE_SHEETS = bool(SPREADSHEET_ID)  # Якщо є SPREADSHEET_ID, то ввімкнено
        logger.warning("⚠️ ENABLE_GOOGLE_SHEETS not in config, using automatic detection")
    
    logger.info("✅ Config imported successfully")
except Exception as e:
    logger.error(f"❌ Config import error: {e}")
    # Fallback значення
    BOT_TOKEN = None
    GEMINI_API_KEY = None
    SPREADSHEET_ID = None
    ENABLE_GOOGLE_SHEETS = False
    WEBHOOK_SECRET = "Ferrik123"

try:
    from services.sheets import init_gspread_client, get_menu_from_sheet, save_order_to_sheets, is_sheets_connected
    logger.info("✅ Sheets service imported")
except Exception as e:
    logger.error(f"❌ Sheets import error: {e}")
    # Заглушки
    def init_gspread_client(): return None
    def get_menu_from_sheet(client): return {}
    def save_order_to_sheets(*args, **kwargs): return False
    def is_sheets_connected(): return False

try:
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    logger.info("✅ Gemini service imported")
except Exception as e:
    logger.error(f"❌ Gemini import error: {e}")
    # Заглушки
    def init_gemini_client(): return None
    def get_ai_response(*args, **kwargs): return "AI недоступний"
    def is_gemini_connected(): return False

try:
    from models.user import init_user_db
    logger.info("✅ User model imported")
except Exception as e:
    logger.error(f"❌ User model import error: {e}")
    def init_user_db(): return False

try:
    from services.telegram import tg_send_message, tg_answer_callback, tg_set_webhook
    logger.info("✅ Telegram service imported")
except Exception as e:
    logger.error(f"❌ Telegram service import error: {e}")
    # Заглушка буде визначена нижче

# Глобальні змінні
sheets_client = None
menu_cache = {}
user_db = False
gemini_client = None


# Ініціалізація сервісів
def init_services():
    """Ініціалізує всі сервіси (DB, Sheets, Gemini)"""
    global sheets_client, menu_cache, user_db, gemini_client

    logger.info("🛠️ Initializing services...")
    
    # 1. Логування конфігурації
    try:
        log_config()
        validate_config()
    except Exception as e:
        logger.error(f"Config validation error: {e}")
    
    # 2. Ініціалізація бази даних користувачів
    try:
        if init_user_db():
            user_db = True
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
                
                # ВИПРАВЛЕННЯ: викликаємо без аргументів
                menu_data = get_menu_from_sheet()
                menu_cache = menu_data if menu_data is not None else {}
                logger.info(f"✅ Menu cached: {len(menu_cache)} items.")
            else:
                logger.warning("⚠️ Google Sheets client could not connect.")
        except TypeError as e:
            logger.error(f"❌ TypeError in get_menu_from_sheet: {e}")
            logger.info("💡 Check if get_menu_from_sheet accepts correct parameters")
        except Exception as e:
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
    
    # 5. Встановлення webhook
    try:
        from config import RENDER_URL
        result = tg_set_webhook(RENDER_URL)
        if result and result.get('ok'):
            logger.info("✅ Webhook set successfully")
        else:
            logger.error(f"❌ Failed to set webhook: {result}")
    except Exception as e:
        logger.error(f"❌ Webhook setup error: {e}")


# Функція відправки повідомлень
def send_message(chat_id, text, reply_markup=None):
    """Надсилає повідомлення через Telegram API."""
    try:
        # Спроба використати імпортовану функцію
        return tg_send_message(chat_id, text, reply_markup)
    except NameError:
        # Fallback якщо імпорт не вдався
        import requests
        try:
            bot_token = BOT_TOKEN or os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
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
                payload["reply_markup"] = reply_markup  # requests.post с json= сам сериализует
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Send message error: {e}")
            return None


def answer_callback(callback_id, text, show_alert=False):
    """Відповідає на callback query"""
    try:
        return tg_answer_callback(callback_id, text, show_alert)
    except NameError:
        logger.warning("tg_answer_callback not available")
        return None


# Обробники команд
def handle_start(chat_id):
    """Обробка команди /start"""
    welcome_text = (
        "👋 Привіт!\n\n"
        "Я <b>FerrikFootBot</b> – твій помічник для замовлення їжі.\n\n"
        "Обери дію в меню:"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📖 Меню", "callback_data": "menu"}],
            [{"text": "🛒 Корзина", "callback_data": "cart"}, {"text": "⭐ Рекомендація", "callback_data": "recommend"}],
            [{"text": "📞 Контакти", "callback_data": "contacts"}]
        ]
    }
    
    send_message(chat_id, welcome_text, reply_markup=keyboard)


def show_menu(chat_id):
    """Показати меню"""
    if not menu_cache:
        send_message(chat_id, "❌ Меню тимчасово недоступне. Спробуйте пізніше.")
        return

    menu_text = "<b>📖 Наше Меню:</b>\n\n"
    
    items = list(menu_cache.values())[:10]  # Перші 10 страв
    for item in items:
        name = item.get('name', 'Без назви')
        price = item.get('price', '?')
        menu_text += f"🍕 <b>{name}</b> - {price} грн\n"
    
    if len(menu_cache) > 10:
        menu_text += f"\n... та ще {len(menu_cache) - 10} страв!"
    
    send_message(chat_id, menu_text)


def show_contacts(chat_id):
    """Показати контакти"""
    contacts_text = """
📞 <b>Контакти</b>

📱 Телефон: +380XX XXX XX XX
📧 Email: info@ferrikfoot.com
📍 Адреса: м. Київ, вул. Прикладна, 1

🕐 Працюємо: Пн-Нд 9:00-22:00
"""
    send_message(chat_id, contacts_text)


def show_recommendations(chat_id):
    """Показати AI рекомендації"""
    if not is_gemini_connected():
        send_message(chat_id, "❌ AI-рекомендації тимчасово недоступні.")
        return
    
    try:
        recommendation = get_ai_response("Порекомендуй популярну страву з меню")
        send_message(chat_id, f"🎯 <b>Рекомендація:</b>\n\n{recommendation}")
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        send_message(chat_id, "❌ Не вдалося отримати рекомендацію.")


def process_callback_query(callback_query):
    """Обробка callback запитів"""
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        callback_id = callback_query["id"]
        data = callback_query["data"]
        
        # Відповідаємо на callback (прибираємо годинник завантаження)
        answer_callback(callback_id, "Обробляю...")
        
        if data == "menu":
            show_menu(chat_id)
        elif data == "cart":
            send_message(chat_id, "🛒 Ваша корзина порожня.")
        elif data == "recommend":
            show_recommendations(chat_id)
        elif data == "contacts":
            show_contacts(chat_id)
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
            # Можна додати AI-обробку тексту
            send_message(chat_id, f"Я отримав: <b>{text}</b>\n\nСпробуйте /start або /menu")

    except Exception as e:
        logger.error(f"Message processing error: {e}")
        try:
            send_message(message["chat"]["id"], "❌ Виникла помилка при обробці запиту.")
        except:
            pass


# Flask routes
@app.route('/', methods=['GET'])
def index():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'bot': 'FerrikFootBot',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/<path:secret>', methods=['POST'])
def webhook(secret):
    """Обробка вхідних вебхуків від Telegram"""
    # Перевірка secret token через URL path
    if secret != WEBHOOK_SECRET:
        logger.warning(f"Invalid webhook path: {secret}")
        return jsonify({'status': 'unauthorized'}), 401
    
    if request.method != 'POST':
        return jsonify({'status': 'method not allowed'}), 405
    
    try:
        update = request.get_json()
        if not update:
            logger.warning("Empty update received")
            return jsonify({'status': 'ok'})

        logger.info(f"Received update: {update.get('update_id', 'unknown')}")

        if 'message' in update:
            process_message(update['message'])
        elif 'callback_query' in update:
            process_callback_query(update['callback_query'])
        else:
            logger.warning(f"Unknown update type: {update.keys()}")
            
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.exception(f"Webhook processing error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


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
    logger.warning("⚠️ Running Flask in development mode (should use gunicorn in production)")
    app.run(host="0.0.0.0", port=port, debug=False)  # debug=False для production