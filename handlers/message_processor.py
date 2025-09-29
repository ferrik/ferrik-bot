import logging
from services.telegram import tg_send_message
from services.gemini import get_gemini_recommendation

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def process_text_message(chat_id, user_id, user_name, text, menu_cache, gemini_client):
    """
    Обробляє текстові повідомлення, використовуючи Gemini для рекомендацій.
    """
    logger.info(f"Processing message from {user_id}: {text}")
    
    # Перевіряємо, чи текст відповідає категорії меню
    categories = set(item["category"] for item in menu_cache.values())
    text_lower = text.lower().strip()
    
    for category in categories:
        if category.lower() in text_lower:
            items = [item for item in menu_cache.values() if item["category"].lower() == category.lower()]
            response = f"Ось доступні страви в категорії **{category}**:\n"
            for item in items:
                response += f"- **{item['name']}** ({item['price']:.2f} грн): {item['description']}\n"
            tg_send_message(chat_id, response)
            return
    
    # Якщо категорія не знайдена, використовуємо Gemini
    if gemini_client:
        from models.user import get_chat_history
        chat_history = get_chat_history(user_id)
        response = get_gemini_recommendation(text, chat_history)
        tg_send_message(chat_id, response)
    else:
        tg_send_message(chat_id, "Вибачте, я можу допомогти лише з питаннями щодо нашого меню. Чим можу вас почастувати?")