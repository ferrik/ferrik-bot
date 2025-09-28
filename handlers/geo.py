import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def check_delivery_availability(chat_id, user_id, address):
    """
    Перевіряє доступність доставки за адресою.
    Це заглушка — реалізуйте логіку за вашим сценарієм.
    """
    logger.info(f"Checking delivery availability for user {user_id} at {address}")
    from services.telegram import tg_send_message
    tg_send_message(chat_id, "Перевірка доставки ще в розробці. Спробуйте пізніше!")
    return False