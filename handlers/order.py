from models.user import get_cart, set_cart, set_state
from services.telegram import tg_send_message
from services.sheets import save_order_to_sheets
import time

def start_checkout_process(chat_id):
    cart = get_cart(chat_id)
    if not cart.get("items"):
        tg_send_message(chat_id, "🛒 Ваш кошик порожній. Додайте щось із меню! 🍽️")
        return

    total = sum(float(it.get("price", 0.0)) * int(it.get("qty", 0)) for it in cart.get("items", []))
    if total < 300.0:  # MIN_ORDER_FOR_DELIVERY
        tg_send_message(chat_id, f"Мінімальна сума для доставки — 300 грн. Додайте ще на {300.0 - total:.2f} грн! 😊")
        return

    loading_message = tg_send_message(chat_id, "⏳ Оформлюємо ваше замовлення...")
    time.sleep(2)  # Імітація завантаження
    tg_send_message(chat_id, "✅ Замовлення оформлено! Дякуємо! 🎉\nОчікуйте підтвердження від оператора. 📞")
    save_order_to_sheets(chat_id, cart)
    set_cart(chat_id, {"items": [], "address": "", "phone": "", "payment_method": "", "delivery_type": "", "delivery_time": ""})
    set_state(chat_id, STATE_NORMAL)
