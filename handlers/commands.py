import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger('ferrik')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def send_message(chat_id, text, reply_markup=None):
    """Відправляє повідомлення в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"✅ Повідомлення відправлено в чат {chat_id}")
        return response.json()
    except Exception as e:
        logger.error(f"❌ Помилка відправки повідомлення: {e}")
        return None


def handle_start(chat_id, user):
    """Обробник команди /start"""
    username = user.get('first_name', 'друже')
    
    welcome_text = f"""
👋 <b>Вітаю, {username}!</b>

Я <b>FerrikFootBot</b> - ваш помічник у замовленні їжі! 🍕

<b>Що я вмію:</b>
🍔 Показати меню
📝 Прийняти замовлення
💬 Відповісти на ваші запитання
🤖 Допомогти з вибором страв через AI

<b>Доступні команди:</b>
/menu - Переглянути меню
/order - Зробити замовлення
/help - Допомога

Просто напишіть мені, що вас цікавить! 😊
"""
    
    # Клавіатура з швидкими командами
    keyboard = {
        "keyboard": [
            [{"text": "🍕 Меню"}, {"text": "📝 Замовити"}],
            [{"text": "ℹ️ Допомога"}]
        ],
        "resize_keyboard": True
    }
    
    send_message(chat_id, welcome_text, keyboard)


def handle_help(chat_id, user):
    """Обробник команди /help"""
    help_text = """
<b>📖 Довідка FerrikFootBot</b>

<b>Основні команди:</b>
/start - Почати роботу з ботом
/menu - Переглянути меню ресторану
/order - Зробити замовлення
/help - Показати цю довідку

<b>Як зробити замовлення:</b>
1️⃣ Натисніть /menu щоб побачити доступні страви
2️⃣ Напишіть назву страви або опишіть, що хочете
3️⃣ Я допоможу оформити замовлення

<b>Розумний асистент:</b>
Просто напишіть мені звичайним текстом:
• "Що у вас є з морепродуктами?"
• "Порадь щось смачне"
• "Хочу піцу з грибами"

Я використовую AI, щоб зрозуміти ваші побажання! 🤖

<b>Підтримка:</b>
Якщо виникли питання - пишіть @ferrik
"""
    
    send_message(chat_id, help_text)


def handle_menu(chat_id, user):
    """Обробник команди /menu"""
    try:
        from services.sheets import get_menu, is_sheets_connected
        
        if not is_sheets_connected():
            menu_text = """
<b>🍽 Наше меню:</b>

<b>🍕 Піца:</b>
• Маргарита - 150 грн
• Пепероні - 180 грн
• Чотири сира - 200 грн

<b>🍝 Паста:</b>
• Карбонара - 140 грн
• Болоньєзе - 130 грн

<b>🥗 Салати:</b>
• Цезар - 120 грн
• Грецький - 110 грн

<b>🥤 Напої:</b>
• Coca-Cola - 40 грн
• Сік - 35 грн

<i>⚠️ Меню статичне (Google Sheets не підключено)</i>
"""
            send_message(chat_id, menu_text)
            return
        
        # Отримуємо меню з Google Sheets
        menu_data = get_menu()
        
        if not menu_data:
            send_message(chat_id, "⚠️ Не вдалося завантажити меню. Спробуйте пізніше.")
            return
        
        # Формуємо текст меню
        menu_text = "<b>🍽 Наше меню:</b>\n\n"
        
        current_category = None
        for item in menu_data:
            category = item.get('Категорія', '')
            name = item.get('Назва', '')
            price = item.get('Ціна', '')
            
            if category != current_category:
                menu_text += f"\n<b>{category}:</b>\n"
                current_category = category
            
            menu_text += f"• {name} - {price} грн\n"
        
        # Кнопка для замовлення
        keyboard = {
            "inline_keyboard": [
                [{"text": "📝 Зробити замовлення", "callback_data": "make_order"}]
            ]
        }
        
        send_message(chat_id, menu_text, keyboard)
        
    except Exception as e:
        logger.error(f"❌ Помилка показу меню: {e}", exc_info=True)
        send_message(chat_id, "⚠️ Виникла помилка при завантаженні меню")


def handle_order(chat_id, user):
    """Обробник команди /order"""
    order_text = """
<b>📝 Оформлення замовлення</b>

Щоб зробити замовлення, просто напишіть мені:
• Назви страв з меню
• Або опишіть, що хочете, і я допоможу вибрати

<b>Приклад:</b>
"Піцу Маргарита, салат Цезар і Колу"

Або використайте наш AI-асистент:
"Хочу щось легке на обід" 🤖

Чекаю на ваше замовлення! 😊
"""
    
    send_message(chat_id, order_text)