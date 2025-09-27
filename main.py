import os
import logging
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
import json
from datetime import datetime
import requests

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ініціалізація Flask
app = Flask(__name__)

# Глобальні змінні - декларуються на початку
menu_cache = {}
sheets_client = None
tg_send_message = None
get_gemini_recommendation = None
init_sheets = None
get_menu_from_sheets = None
create_user = None
get_user = None

def create_fallback_send_message():
    """Створює fallback функцію для відправки повідомлень"""
    def fallback_send(chat_id, text, keyboard=None, parse_mode="Markdown"):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            if not bot_token:
                logger.error("BOT_TOKEN not found")
                return None
                
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            if keyboard:
                payload["reply_markup"] = json.dumps(keyboard)
            
            response = requests.post(url, data=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Fallback message sent to {chat_id}")
                return response.json()
            else:
                logger.error(f"Fallback send failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Fallback send error: {e}")
            return None
    
    return fallback_send

def safe_import():
    """Безпечний імпорт модулів з обробкою помилок"""
    global tg_send_message, get_gemini_recommendation, init_sheets, get_menu_from_sheets, create_user, get_user
    
    try:
        # Імпорти з config
        from config import BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID
        logger.info("Config imported successfully")
    except Exception as e:
        logger.error(f"Config import error: {e}")
        # Fallback to environment variables - вони і так використовуються
    
    try:
        from services.telegram import send_message as tg_send_message
        logger.info("Telegram service imported")
    except Exception as e:
        logger.error(f"Telegram import error: {e}")
        # Fallback function
        tg_send_message = create_fallback_send_message()
    
    try:
        from services.gemini import get_gemini_recommendation
        logger.info("Gemini service imported")
    except Exception as e:
        logger.error(f"Gemini import error: {e}")
        get_gemini_recommendation = lambda x: "AI тимчасово недоступний"
    
    try:
        from services.sheets import init_sheets, get_menu_from_sheets
        logger.info("Sheets service imported")
    except Exception as e:
        logger.error(f"Sheets import error: {e}")
        init_sheets = lambda: None
        get_menu_from_sheets = lambda: {}
    
    try:
        from models.user import create_user, get_user
        logger.info("User model imported")
    except Exception as e:
        logger.error(f"User model import error: {e}")
        create_user = lambda x, y: True
        get_user = lambda x: None

def initialize_bot():
    """Ініціалізація всіх компонентів бота"""
    global menu_cache, sheets_client
    
    logger.info("🚀 FerrikFootBot starting initialization...")
    
    try:
        # Безпечний імпорт
        safe_import()
        
        # Ініціалізація Google Sheets
        try:
            sheets_client = init_sheets()
            logger.info("✅ Google Sheets connected")
        except Exception as e:
            logger.warning(f"Sheets connection failed: {e}")
            sheets_client = None
        
        # Завантаження меню
        try:
            menu_cache = get_menu_from_sheets()
            logger.info(f"✅ Menu cached: {len(menu_cache)} items")
        except Exception as e:
            logger.warning(f"Menu loading failed: {e}")
            menu_cache = {}
        
        logger.info("🎉 FerrikFootBot initialization completed!")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")

# Ініціалізація при запуску
initialize_bot()

@app.route('/', methods=['GET'])
def health_check():
    """Перевірка здоров'я сервісу"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "FerrikFootBot",
        "menu_items": len(menu_cache) if menu_cache else 0
    }), 200

@app.route('/keep-alive', methods=['GET'])
def keep_alive():
    """Endpoint для підтримки активності сервісу"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": "service is running",
        "cache_status": "active" if menu_cache else "empty"
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробник вебхука від Telegram"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
        
        logger.info(f"Received update: {data.get('update_id', 'unknown')}")
        
        # Обробка повідомлення
        if "message" in data:
            process_message(data["message"])
        elif "callback_query" in data:
            process_callback_query(data["callback_query"])
            
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": "Internal error"}), 500

def process_message(message):
    """Обробка текстових повідомлень"""
    chat_id = None
    try:
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        username = message["from"].get("first_name", "User")
        text = message.get("text", "")
        
        logger.info(f"Processing message from {username} ({user_id}): {text}")
        
        # Створення користувача
        try:
            user = get_user(user_id)
            if not user:
                create_user(user_id, username)
                logger.info(f"Created new user: {user_id}")
        except Exception as e:
            logger.error(f"User management error: {e}")
        
        # Обробка команди /start
        if text == "/start":
            greeting_text = f"""
🍔 Вітаємо в FerrikFoot! 

Привіт, {username}! 👋

Я ваш особистий помічник для замовлення смачної їжі. 
Що бажаєте зробити?
"""
            
            keyboard = {
                "keyboard": [
                    [{"text": "🍔 Замовити їжу"}],
                    [{"text": "📋 Мої замовлення"}, {"text": "ℹ️ Інформація"}],
                    [{"text": "📞 Контакти"}, {"text": "🎯 Рекомендації"}]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            
            try:
                tg_send_message(chat_id, greeting_text, keyboard=keyboard)
            except Exception as e:
                logger.error(f"Error sending greeting: {e}")
            return
        
        # Обробка інших повідомлень
        if text == "🍔 Замовити їжу":
            show_menu(chat_id)
        elif text == "📋 Мої замовлення":
            show_orders(chat_id)
        elif text == "ℹ️ Інформація":
            show_info(chat_id)
        elif text == "📞 Контакти":
            show_contacts(chat_id)
        elif text == "🎯 Рекомендації":
            show_recommendations(chat_id)
        else:
            handle_unknown_message(chat_id, text)
        
    except Exception as e:
        logger.error(f"Error in process_message: {e}")
        if chat_id:
            try:
                tg_send_message(chat_id, "Виникла помилка. Спробуйте пізніше.")
            except:
                logger.error("Failed to send error message")

def handle_unknown_message(chat_id, text):
    """Обробка невідомих повідомлень"""
    try:
        # Спробуємо AI
        prompt = f"""
Користувач написав: "{text}"
Ти помічник ресторану FerrikFoot. Дай коротку корисну відповідь українською.
"""
        response = get_gemini_recommendation(prompt)
        
        if response and "недоступний" not in response:
            tg_send_message(chat_id, response)
        else:
            tg_send_message(chat_id, "Не розумію. Виберіть опцію з меню або напишіть /help")
            
    except Exception as e:
        logger.error(f"Error handling unknown message: {e}")
        tg_send_message(chat_id, "Використовуйте кнопки меню для навігації")

def show_menu(chat_id):
    """Показати меню"""
    global menu_cache
    
    try:
        if not menu_cache:
            # Спробуємо перезавантажити
            menu_cache = get_menu_from_sheets()
    except:
        pass
    
    if not menu_cache:
        tg_send_message(chat_id, "❌ Меню тимчасово недоступне. Спробуйте пізніше.")
        return
    
    menu_text = "🍽️ **Наше меню:**\n\n"
    for item_id, item in menu_cache.items():
        if item.get('active', True):
            menu_text += f"🍕 **{item['name']}**\n"
            menu_text += f"💰 Ціна: {item['price']} грн\n"
            if item.get('description'):
                menu_text += f"📝 {item['description']}\n"
            menu_text += "\n"
    
    tg_send_message(chat_id, menu_text)

def show_orders(chat_id):
    """Показати замовлення"""
    tg_send_message(chat_id, "📋 **Ваші замовлення:**\n\nПоки що замовлень немає.")

def show_info(chat_id):
    """Показати інформацію"""
    info_text = """
ℹ️ **Інформація про FerrikFoot**

🕒 **Час роботи:** Пн-Нд: 10:00 - 22:00
🚚 **Доставка:** Безкоштовна від 300 грн (30-45 хв)
💳 **Оплата:** Готівка або картка
🎯 **Переваги:** Свіжі продукти, швидка доставка
"""
    tg_send_message(chat_id, info_text)

def show_contacts(chat_id):
    """Показати контакти"""
    contacts_text = """
📞 **Контакти**

📱 Телефон: +380XX XXX XX XX
📧 Email: info@ferrikfoot.com
📍 Адреса: м. Київ, вул. Прикладна, 1
"""
    tg_send_message(chat_id, contacts_text)

def show_recommendations(chat_id):
    """Показати рекомендації"""
    try:
        if menu_cache:
            menu_items = [f"{item['name']} - {item['price']} грн" 
                         for item in menu_cache.values() if item.get('active', True)][:5]
            
            prompt = f"Порекомендуй страви з меню: {', '.join(menu_items)}. Коротко українською."
            recommendation = get_gemini_recommendation(prompt)
            
            tg_send_message(chat_id, f"🎯 **Рекомендації:**\n\n{recommendation}")
        else:
            tg_send_message(chat_id, "🍕 Рекомендуємо нашу фірмову піцу!")
    except:
        tg_send_message(chat_id, "🍕 Рекомендуємо нашу фірмову піцу!")

def process_callback_query(callback_query):
    """Обробка callback запитів"""
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        data = callback_query["data"]
        tg_send_message(chat_id, f"Обрано: {data}")
    except Exception as e:
        logger.error(f"Callback error: {e}")

# Обробка помилок Flask
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
