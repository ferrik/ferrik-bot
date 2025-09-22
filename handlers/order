from models.user import get_cart, set_cart, set_state
from services.telegram import tg_send_message
from services.sheets import save_order_to_sheets

def start_checkout_process(chat_id):
    """
    Починає процес оформлення замовлення.
    Перевіряє, чи не порожній кошик і чи досягнута мінімальна сума замовлення,
    а потім запитує у користувача номер телефону.
    """
    # Отримуємо вміст кошика користувача
    cart = get_cart(chat_id)
    if not cart.get("items"):
        tg_send_message(chat_id, "🛒 Ваш кошик порожній. Додайте щось із меню! 🍽️")
        return

    # Розраховуємо загальну суму замовлення
    total = sum(float(it.get("price", 0.0)) * int(it.get("qty", 0)) for it in cart.get("items", []))
    MIN_ORDER_FOR_DELIVERY = 300.0
    if total < MIN_ORDER_FOR_DELIVERY:
        tg_send_message(chat_id, f"Мінімальна сума для доставки — {MIN_ORDER_FOR_DELIVERY:.2f} грн. Додайте ще на {MIN_ORDER_FOR_DELIVERY - total:.2f} грн! 😊")
        return

    # Якщо всі перевірки успішні, просимо номер телефону і змінюємо стан
    tg_send_message(chat_id, "Введіть ваш номер телефону у форматі +380XXXXXXXXX: 📱")
    set_state(chat_id, "awaiting_phone")
