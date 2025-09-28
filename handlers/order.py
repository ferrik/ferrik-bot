import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def start_checkout_process(chat_id, user_id):
    """
    Починає процес оформлення замовлення.
    Це заглушка — реалізуйте логіку за вашим сценарієм.
    """
    logger.info(f"Starting checkout for user {user_id}")
    from services.telegram import tg_send_message
    tg_send_message(chat_id, "Оформлення замовлення ще в розробці. Спробуйте /cart!")