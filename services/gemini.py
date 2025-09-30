import os
import logging
import google.generativeai as genai
from services.sheets import get_menu_from_sheet  # ← ВИПРАВЛЕНО: без "s" на кінці!

logger = logging.getLogger('ferrik')

# Конфігурація
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

# Глобальні змінні
_model = None
_chat = None

def init_gemini_client():
    """Ініціалізує клієнт Gemini AI"""
    global _model, _chat
    
    try:
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY не знайдено в змінних середовища")
            return False
        
        # Конфігуруємо Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Створюємо модель
        _model = genai.GenerativeModel(GEMINI_MODEL)
        
        logger.info(f"✅ Gemini client initialized. Using model: {GEMINI_MODEL}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації Gemini: {e}", exc_info=True)
        return False


def is_gemini_connected():
    """Перевіряє, чи підключено Gemini"""
    return _model is not None


def get_ai_response(user_message: str, user_context: dict = None):
    """
    Отримує відповідь від Gemini AI на основі повідомлення користувача
    """
    if not _model:
        logger.warning("⚠️ Gemini не підключено")
        return "Вибачте, AI-асистент тимчасово недоступний. Спробуйте скористатися командами /menu або /help"
    
    try:
        # Отримуємо меню для контексту
        menu = get_menu_from_sheet()
        
        # Формуємо prompt з контекстом
        system_prompt = f"""
Ти - дружній асистент ресторану FerrikFoot. Твоя задача - допомогти клієнту з замовленням їжі.

ПРАВИЛА:
1. Завжди відповідай українською мовою
2. Будь ввічливим та дружнім
3. Допомагай вибрати страви з меню
4. Якщо користувач питає про страву, якої немає в меню - запропонуй альтернативи
5. Можеш порадити страви на основі побажань клієнта
6. Не вигадуй інформацію про страви - використовуй лише дані з меню

ДОСТУПНЕ МЕНЮ:
"""
        
        if menu:
            for item in menu[:20]:  # Обмежуємо до 20 позицій для оптимізації
                system_prompt += f"\n- {item.get('Страви')}: {item.get('Опис', '')} ({item.get('Ціна')} грн, категорія: {item.get('Категорія', 'Інше')})"
        else:
            system_prompt += "\nМеню тимчасово недоступне. Вибач за незручності."
        
        # Додаємо контекст користувача якщо є
        if user_context:
            system_prompt += f"\n\nІНФОРМАЦІЯ ПРО КОРИСТУВАЧА:\n"
            system_prompt += f"Ім'я: {user_context.get('first_name', 'Клієнт')}\n"
            if user_context.get('username'):
                system_prompt += f"Username: @{user_context.get('username')}\n"
        
        # Повний prompt
        full_prompt = f"{system_prompt}\n\nПОВІДОМЛЕННЯ КОРИСТУВАЧА: {user_message}\n\nТВОЯ ВІДПОВІДЬ:"
        
        # Генеруємо відповідь
        response = _model.generate_content(full_prompt)
        
        logger.info(f"✅ AI відповідь згенеровано для повідомлення: '{user_message[:50]}...'")
        return response.text
        
    except Exception as e:
        logger.error(f"❌ Помилка при генерації AI відповіді: {e}", exc_info=True)
        return "Вибачте, виникла помилка при обробці вашого запиту. Спробуйте ще раз або скористайтеся командою /menu"


def generate_order_summary(items: list):
    """Генерує резюме замовлення за допомогою AI"""
    if not _model:
        return None
    
    try:
        prompt = f"""
Створи коротке та зрозуміле резюме замовлення українською мовою.

ЗАМОВЛЕНІ СТРАВИ:
{items}

Напиши резюме у форматі:
"Ваше замовлення: [список страв]. Загальна вартість: [сума] грн. Приблизний час приготування: [час] хв."

Будь лаконічним та дружнім.
"""
        
        response = _model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"❌ Помилка генерації резюме замовлення: {e}", exc_info=True)
        return None


def suggest_dishes(preferences: str):
    """
    Пропонує страви на основі побажань користувача
    """
    if not _model:
        return []
    
    try:
        menu = get_menu_from_sheet()
        
        if not menu:
            return []
        
        # Формуємо список страв для AI
        menu_text = "\n".join([
            f"- {item.get('Страви')}: {item.get('Опис', '')} ({item.get('Ціна')} грн)"
            for item in menu[:30]
        ])
        
        prompt = f"""
На основі побажань користувача "{preferences}", обери 3-5 найкращих страв з меню.

МЕНЮ:
{menu_text}

Відповідь надай у форматі JSON array з назвами страв, наприклад:
["Піца Маргарита", "Салат Цезар", "Coca-Cola"]

Тільки JSON, без пояснень.
"""
        
        response = _model.generate_content(prompt)
        
        # Парсимо відповідь
        import json
        suggestions = json.loads(response.text.strip())
        
        logger.info(f"✅ AI запропонував {len(suggestions)} страв для запиту: '{preferences}'")
        return suggestions
        
    except Exception as e:
        logger.error(f"❌ Помилка при генерації пропозицій: {e}", exc_info=True)
        return []


def analyze_order_text(text: str):
    """
    Аналізує текст замовлення та витягує список страв
    """
    if not _model:
        return []
    
    try:
        menu = get_menu_from_sheet()
        
        if not menu:
            return []
        
        # Список доступних страв
        available_dishes = [item.get('Страви') for item in menu]
        
        prompt = f"""
Проаналізуй текст замовлення та визнач, які страви хоче замовити користувач.

ТЕКСТ ЗАМОВЛЕННЯ:
"{text}"

ДОСТУПНІ СТРАВИ:
{', '.join(available_dishes)}

Відповідь надай у форматі JSON array з об'єктами, наприклад:
[
  {{"name": "Піца Маргарита", "quantity": 1}},
  {{"name": "Салат Цезар", "quantity": 2}}
]

Якщо страви немає в доступному списку - не додавай її.
Тільки JSON, без пояснень.
"""
        
        response = _model.generate_content(prompt)
        
        # Парсимо відповідь
        import json
        import re
        
        # Витягуємо JSON з відповіді
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            orders = json.loads(json_match.group())
            logger.info(f"✅ AI розпізнав {len(orders)} позицій у замовленні")
            return orders
        
        return []
        
    except Exception as e:
        logger.error(f"❌ Помилка при аналізі тексту замовлення: {e}", exc_info=True)
        return []


def get_gemini_recommendation(prompt):
    """
    Загальна функція для отримання рекомендацій від Gemini
    Використовується для зворотної сумісності зі старим кодом
    """
    if not _model:
        logger.warning("⚠️ Gemini не підключено")
        return "AI-асистент тимчасово недоступний"
    
    try:
        response = _model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"❌ Помилка Gemini: {e}")
        return "Виникла помилка при обробці запиту"