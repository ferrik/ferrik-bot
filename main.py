import os
import logging
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
import json
from datetime import datetime

# Імпорти з вашої існуючої структури
from config import BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID
from services.telegram import send_message as tg_send_message
from services.sheets import init_sheets, get_menu_from_sheets
from services.gemini import get_gemini_recommendation
from models.user import create_user, get_user
from handlers.message_processor import process_text_message

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ініціалізація Flask
app = Flask(__name__)

# Глобальні змінні
menu_cache = {}
sheets_client = None

def initialize_bot():
    """Ініціалізація всіх компонентів бота"""
    global menu_cache, sheets_client
    
    logger.info("🚀 FerrikFootBot starting initialization...")
    
    try:
        # 1. Ініціалізація Google Sheets
        sheets_client = init_sheets()
        logger.info("✅ Google Sheets connected")
        
        # 2. Завантаження меню
        try:
            menu_cache = get_menu_from_sheets()
            logger.info(f"✅ Menu cached: {len(menu_cache)} items")
        except Exception as e:
            logger.warning(f"Menu loading failed: {e}")
            menu_cache = {}
        
        logger.info("🎉 FerrikFootBot initialization completed!")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        # Не викидаємо помилку, щоб сервіс продовжував працювати

# Ініціалізація при запуску
initialize_bot()

@app.route('/', methods=['GET'])
def health_check():
    """Перевірка здоров'я сервісу для запобігання засипанню"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "FerrikFootBot",
        "menu_items": len(menu_cache)
    })

@app.route('/keep-alive', methods=['GET'])
def keep_alive():
    """Endpoint для підтримки активності сервісу"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": "service is running",
        "cache_status": "active" if menu_cache else "empty"
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробник вебхука від Telegram"""
    try:
        data = request.get_json()
        
        if not data:
            raise BadRequest("No JSON data received")
        
        logger.info(f"Received update: {data}")
        
        # Обробка повідомлення
        if "message" in data:
            process_message(data["message"])
        elif "callback_query" in data:
            process_callback_query(data["callback_query"])
            
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_message(message):
    """Обробка текстових повідомлень"""
    try:
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        username = message["from"].get("first_name", "User")
        text = message.get("text", "")
        
        logger.info(f"Processing message from {username} ({user_id}): {text}")
        
        # Створення користувача, якщо не існує
        try:
            user = get_user(user_id)
            if not user:
                create_user(user_id, username)
                logger.info(f"Created new user: {user_id}")
        except Exception as e:
            logger.error(f"Error with user management: {e}")
        
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
            
            tg_send_message(chat_id, greeting_text, keyboard=keyboard)
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
            # Спробуємо використати існуючий message_processor
            try:
                from handlers.message_processor import process_text_message
                response = process_text_message(text, user_id, chat_id)
                if response:
                    tg_send_message(chat_id, response)
                else:
                    handle_unknown_message(chat_id, text)
            except Exception as e:
                logger.error(f"Message processor error: {e}")
                handle_unknown_message(chat_id, text)
        
    except Exception as e:
        logger.error(f"Error in process_message for chat_id {chat_id}: {e}")
        try:
            tg_send_message(chat_id, "Виникла помилка. Спробуйте пізніше.")
        except:
            logger.error("Failed to send error message to user")

def handle_unknown_message(chat_id, text):
    """Обробка невідомих повідомлень через AI"""
    try:
        if GEMINI_API_KEY:
            prompt = f"""
Користувач написав: "{text}"
Меню ресторану: {json.dumps(menu_cache, ensure_ascii=False)}
Дай корисну відповідь українською мовою про наш ресторан або їжу.
"""
            response_text = get_gemini_recommendation(prompt)
            tg_send_message(chat_id, response_text)
        else:
            tg_send_message(chat_id, "Не розумію. Виберіть опцію з меню.")
    except Exception as e:
        logger.error(f"AI processing error: {e}")
        tg_send_message(chat_id, "Не розумію. Виберіть опцію з меню.")

def show_menu(chat_id):
    """Показати меню"""
    try:
        if not menu_cache:
            # Спробуємо перезавантажити меню
            global menu_cache
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
    """Показати замовлення користувача"""
    tg_send_message(chat_id, "📋 Ваші замовлення:\n\nПоки що замовлень немає.")

def show_info(chat_id):
    """Показати інформацію"""
    info_text = """
ℹ️ **Інформація про FerrikFoot**

🕒 **Час роботи:**
Пн-Нд: 10:00 - 22:00

🚚 **Доставка:**
Безкоштовна доставка від 300 грн
Час доставки: 30-45 хв

💳 **Оплата:**
• Готівка при отриманні
• Карткою при отриманні
• Онлайн оплата

🎯 **Наші переваги:**
• Свіжі продукти
• Швидка доставка
• Доступні ціни
• Якісне обслуговування
"""
    tg_send_message(chat_id, info_text)

def show_contacts(chat_id):
    """Показати контакти"""
    contacts_text = """
📞 **Контактна інформація**

📱 Телефон: +380XX XXX XX XX
📧 Email: info@ferrikfoot.com
🌐 Сайт: www.ferrikfoot.com

📍 **Адреса:**
м. Київ, вул. Прикладна, 1

🕒 **Час роботи:**
Щодня з 10:00 до 22:00

📱 **Соціальні мережі:**
Instagram: @ferrikfoot
Facebook: FerrikFoot
"""
    tg_send_message(chat_id, contacts_text)

def show_recommendations(chat_id):
    """Показати рекомендації"""
    try:
        if GEMINI_API_KEY and menu_cache:
            # Створюємо промт для AI
            menu_items = []
            for item in menu_cache.values():
                if item.get('active', True):
                    menu_items.append(f"{item['name']} - {item['price']} грн")
            
            prompt = f"""
З нашого меню: {', '.join(menu_items[:5])}
Порекомендуй 2-3 найпопулярніші страви для замовлення. 
Відповідь українською мовою, коротко та переконливо.
"""
            
            recommendation = get_gemini_recommendation(prompt)
            tg_send_message(chat_id, f"🎯 **Наші рекомендації:**\n\n{recommendation}")
        else:
            tg_send_message(chat_id, "🍕 Рекомендуємо спробувати нашу фірмову піцу!")
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        tg_send_message(chat_id, "🍕 Рекомендуємо спробувати нашу фірмову піцу!")

def process_callback_query(callback_query):
    """Обробка callback запитів"""
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        data = callback_query["data"]
        
        # Тут можна додати логіку обробки inline кнопок
        tg_send_message(chat_id, f"Обрано: {data}")
        
    except Exception as e:
        logger.error(f"Error processing callback query: {e}")

if __name__ == '__main__':
    # Для локального тестування
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
