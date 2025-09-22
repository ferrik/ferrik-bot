import logging

logger = logging.getLogger("ferrik.cart")

def show_cart(update, context):
    """
    Показує вміст кошика користувача.
    Наразі це лише заглушка для запобігання помилці імпорту.
    """
    logger.info("Function show_cart was called.")
    # Тут буде логіка для відображення кошика
    # context.bot.send_message(chat_id=update.effective_chat.id, text="Ваш кошик порожній.")
    return None

def add_item_to_cart(update, context):
    """
    Додає вибраний елемент до кошика користувача.
    Наразі це лише заглушка.
    """
    logger.info("Function add_item_to_cart was called.")
    # Тут буде логіка для додавання елемента до кошика
    return None
