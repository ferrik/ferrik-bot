"""
Message processor для обробки текстових повідомлень
"""

import logging
import json
from services.gemini import get_gemini_recommendation
from models.user import update_user_activity

logger = logging.getLogger(__name__)

def process_text_message(text, user_id, chat_id):
    """
    Обробка текстових повідомлень користувачів
    
    Args:
        text (str): Текст повідомлення
        user_id (int): ID користувача
        chat_id (int): ID чату
        
    Returns:
        str: Відповідь для користувача або None
    """
    try:
        # Оновлюємо активність користувача
        update_user_activity(user_id)
        
        # Логуємо повідомлення
        logger.info(f"Processing text from user {user_id}: {text}")
        
        # Обробка команд
        if text.startswith('/'):
            return process_command(text, user_id, chat_id)
        
        # Обробка ключових слів
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['меню', 'menu', 'їжа', 'food']):
            return "Для перегляду меню натисніть кнопку '🍔 Замовити їжу'"
        
        if any(word in text_lower for word in ['ціна', 'price', 'скільки', 'вартість']):
            return "Ціни на всі страви можна переглянути в нашому меню. Натисніть '🍔 Замовити їжу'"
        
        if any(word in text_lower for word in ['доставка', 'delivery', 'привезти']):
            return "🚚 Безкоштовна доставка від 300 грн. Час доставки: 30-45 хв"
        
        if any(word in text_lower for word in ['контакт', 'телефон', 'зв\'язок']):
            return "📞 Наші контакти доступні в розділі 'Контакти'"
        
        if any(word in text_lower for word in ['робота', 'час', 'відкрито']):
            return "🕒 Ми працюємо щодня з 10:00 до 22:00"
        
        # Якщо нічого не підійшло, використовуємо AI
        return process_with_ai(text, user_id)
        
    except Exception as e:
        logger.error(f"Error processing text message: {e}")
        return "Виникла помилка при обробці повідомлення"

def process_command(command, user_id, chat_id):
    """Обробка команд бота"""
    try:
        command_lower = command.lower().strip()
        
        if command_lower == '/start':
            return None  # Обробляється в main.py
        
        elif command_lower == '/help':
            return """
🤖 **Доступні команди:**

/start - Почати роботу з ботом
/help - Показати це меню
/menu - Переглянути меню
/contact - Контактна інформація
/info - Інформація про ресторан

Або використовуйте кнопки меню для навігації!
"""
        
        elif command_lower == '/menu':
            return "Для перегляду меню натисніть кнопку '🍔 Замовити їжу'"
        
        elif command_lower == '/contact':
            return """
📞 **Контактна інформація**

📱 Телефон: +380XX XXX XX XX
📧 Email: info@ferrikfoot.com
🌐 Сайт: www.ferrikfoot.com

📍 Адреса: м. Київ, вул. Прикладна, 1
"""
        
        elif command_lower == '/info':
            return """
ℹ️ **Про FerrikFoot**

🍔 Ми - команда ентузіастів, які створюють смачну їжу для вас!

🎯 Наша мета - швидка доставка якісної їжі за доступними цінами.

⭐ Що нас відрізняє:
• Свіжі інгредієнти
• Швидке приготування
• Дружній сервіс
"""
        
        else:
            return f"Команда {command} не розпізнана. Введіть /help для списку команд."
            
    except Exception as e:
        logger.error(f"Error processing command: {e}")
        return "Помилка при обробці команди"

def process_with_ai(text, user_id):
    """Обробка повідомлення через AI"""
    try:
        # Створюємо контекстний промт
        prompt = f"""
Ти - помічник ресторану FerrikFoot. Користувач написав: "{text}"

Контекст про ресторан:
- Назва: FerrikFoot
- Спеціалізація: швидке харчування, піца, бургери
- Час роботи: 10:00-22:00 щодня
- Безкоштовна доставка від 300 грн
- Час доставки: 30-45 хв
- Місто: Київ

Дай корисну та дружню відповідь українською мовою. Будь стислим (до 200 символів).
Якщо питання не стосується ресторану, ввічливо переспрямуй на наші послуги.
"""
        
        response = get_gemini_recommendation(prompt)
        
        if response and "недоступний" not in response.lower():
            return response
        else:
            return generate_fallback_response(text)
            
    except Exception as e:
        logger.error(f"Error processing with AI: {e}")
        return generate_fallback_response(text)

def generate_fallback_response(text):
    """Генерація запасної відповіді без AI"""
    text_lower = text.lower()
    
    # Привітання
    if any(word in text_lower for word in ['привіт', 'hello', 'вітаю', 'добрий']):
        return "Привіт! Я помічник ресторану FerrikFoot. Чим можу допомогти? 😊"
    
    # Подяка
    if any(word in text_lower for word in ['дякую', 'спасибі', 'thanks']):
        return "Будь ласка! Завжди радий допомогти! 🙂"
    
    # Питання про їжу
    if any(word in text_lower for word in ['смачно', 'голодний', 'поїсти', 'їсти']):
        return "У нас дуже смачна їжа! Подивіться наше меню 🍔"
    
    # Загальна відповідь
    return """
Не зовсім розумію ваше питання. 

Я можу допомогти з:
🍔 Замовленням їжі
📋 Інформацією про ресторан
📞 Контактами
🚚 Доставкою

Використовуйте кнопки меню!
"""

def is_spam_message(text, user_id):
    """Перевірка на спам"""
    try:
        # Базові перевірки на спам
        if len(text) > 1000:  # Занадто довге повідомлення
            return True
            
        # Занадто багато повторень символів
        if any(char * 5 in text for char in text):
            return True
            
        # Підозрілі слова
        spam_words = ['реклама', 'знижка', 'акція', 'купи', 'продам']
        if sum(word in text.lower() for word in spam_words) >= 2:
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error checking spam: {e}")
        return False

def log_user_interaction(user_id, text, response_type="text"):
    """Логування взаємодії з користувачем"""
    try:
        interaction_data = {
            'user_id': user_id,
            'message': text[:100],  # Перші 100 символів
            'response_type': response_type,
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                'interaction', logging.INFO, '', 0, '', (), None
            ))
        }
        
        logger.info(f"User interaction: {json.dumps(interaction_data, ensure_ascii=False)}")
        
    except Exception as e:
        logger.error(f"Error logging interaction: {e}")
