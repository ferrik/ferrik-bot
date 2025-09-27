import os
import logging
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
import json
from datetime import datetime
import time

# Імпорти для бота
from utils.telegram_api import send_message as tg_send_message, send_photo, edit_message  # Додано імпорт
from database.db_manager import init_db, create_user, get_user
from handlers.message_processor import process_text_message
from utils.google_sheets import init_sheets, add_user_data, get_menu_from_sheets
from config import BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID
from utils.gemini_api import get_gemini_recommendation

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
        # 1. Ініціалізація бази даних
        init_db()
        logger.info("✅ Database initialized")
        
        # 2. Ініціалізація Google Sheets
        sheets_client = init_sheets()
        logger.info("✅ Google Sheets connected")
        
        # 3. Завантаження меню
        menu_cache = get_menu_from_sheets()
        logger.info(f"✅ Menu cached: {len(menu_cache)} items")
        
        # 4. Створення структури панелі адміністратора
        create_dashboard_structure()
        logger.info("✅ Dashboard structure created")
        
        logger.info("🎉 FerrikFootBot initialization completed!")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        raise

def create_dashboard_structure():
    """Створює структуру панелі адміністратора"""
    try:
        if sheets_client:
            # Спробуємо створити воркшіт для статистики, якщо його немає
            try:
                stats_sheet = sheets_client.worksheet("Statistics")
            except:
                try:
                    stats_sheet = sheets_client.add_worksheet("Statistics", 1000, 10)
                    # Додаємо заголовки
                    stats_sheet.append_row([
                        "Date", "User ID", "Username", "Action", 
                        "Order Details", "Total Amount", "Status"
                    ])
                except Exception as e:
                    logger.error(f"Error creating Statistics worksheet: {e}")
    except Exception as e:
        logger.error(f"Error creating dashboard: {e}")

# Ініціалізація при запуску
initialize_bot()

@app.route('/', methods=['GET'])
def health_check():
    """Перевірка здоров'я сервісу для запобігання засипанню"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "FerrikFootBot"
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробник вебхука від Telegram"""
    try:
        data = request.get_json()
        
        if not data:
            raise BadRequest("No JSON data received")
        
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
        user = get_user(user_id)
        if not user:
            create_user(user_id, username)
            logger.info(f"Created new user: {user_id}")
            
            # Додавання в Google Sheets
            try:
                add_user_data(user_id, username, "New user registered")
            except Exception as e:
                logger.error(f"Error adding user data: {e}")
        
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
            # Обробка через AI
            try:
                prompt = f"""
Користувач написав: "{text}"
Меню ресторану: {json.dumps(menu_cache, ensure_ascii=False)}
Дай корисну відповідь українською мовою.
"""
                # Виправлення: передаємо тільки prompt
                response_text = get_gemini_recommendation(prompt)
                tg_send_message(chat_id, response_text)
            except Exception as e:
                logger.error(f"AI processing error: {e}")
                tg_send_message(chat_id, "Вибачте, виникла помилка при обробці запиту.")
        
    except Exception as e:
        logger.error(f"Error in process_message for chat_id {chat_id}: {e}")
        try:
            tg_send_message(chat_id, f"Виникла помилка: {e}")
        except:
            logger.error("Failed to send error message to user")

def show_menu(chat_id):
    """Показати меню"""
    if not menu_cache:
        tg_send_message(chat_id, "❌ Меню тимчасово недоступне")
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
    if not menu_cache:
        tg_send_message(chat_id, "❌ Рекомендації тимчасово недоступні")
        return
    
    try:
        # Створюємо промт для AI
        menu_items = []
        for item in menu_cache.values():
            if item.get('active', True):
                menu_items.append(f"{item['name']} - {item['price']} грн")
        
        prompt = f"""
З нашого меню: {', '.join(menu_items)}
Порекомендуй 2-3 найпопулярніші страви для замовлення. 
Відповідь українською мовою, коротко та переконливо.
"""
        
        # Виправлення: передаємо тільки prompt
        recommendation = get_gemini_recommendation(prompt)
        tg_send_message(chat_id, f"🎯 **Наші рекомендації:**\n\n{recommendation}")
        
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

# Функція для підтримки активності сервісу
@app.route('/keep-alive', methods=['GET'])
def keep_alive():
    """Endpoint для підтримки активності сервісу"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": "service is running"
    })

if __name__ == '__main__':
    # Для локального тестування
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))