import logging
from services.telegram import tg_send_message

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def process_text_message(chat_id, user_id, user_name, text, menu_cache, gemini_client):
    """
    Обробляє текстові повідомлення, використовуючи Gemini для рекомендацій.
    Це заглушка — реалізуйте логіку за вашим сценарієм.
    """
    logger.info(f"Processing message from {user_id}: {text}")
    response = "Вибачте, обробка текстових повідомлень ще в розробці. Спробуйте /menu або /cart!"
    tg_send_message(chat_id, response)