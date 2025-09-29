import logging
from datetime import datetime
import uuid
from services.sheets import save_order
from services.telegram import tg_send_message
from models.user import get_cart, clear_cart

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def start_checkout_process(chat_id: str, user_id: str):
    """
    Починає процес оформлення замовлення.
    Зберігає замовлення в Google Sheets та очищає корзину.
    """
    logger.info(f"Starting checkout for user {user_id}")
    
    cart = get_cart(user_id)
    if not cart or not cart["items"]:
        tg_send_message(chat_id, "Ваш кошик порожній. Додайте товари за допомогою /menu!")
        return
    
    try:
        # Генеруємо унікальний ID замовлення
        order_id = str(uuid.uuid4())
        order_time = datetime.now().isoformat()
        
        # Формуємо дані замовлення
        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "order_time": order_time,
            "items": cart["items"],
            "total_amount": cart["total"],
            "address": "",  # Потрібно реалізувати отримання адреси
            "phone": "",    # Потрібно реалізувати отримання телефону
            "payment_method": "Очікується вибір",
            "status": "Нове",
            "channel": "Telegram",
            "delivery_cost": 0.0,  # Потрібно реалізувати логіку доставки
            "total_with_delivery": cart["total"],
            "delivery_type": "Доставка",  # Або "Самовивіз"
            "delivery_time": "",  # Потрібно реалізувати
            "operator": "",  # Призначиться оператором
            "notes": ""
        }
        
        # Зберігаємо замовлення в Google Sheets
        if save_order(order_data):
            tg_send_message(chat_id, f"Замовлення #{order_id} створено! Сума: {cart['total']:.2f} грн. Очікуйте підтвердження.")
            # Очищаємо корзину
            clear_cart(user_id)
        else:
            tg_send_message(chat_id, "Помилка при створенні замовлення. Спробуйте ще раз.")
        
    except Exception as e:
        logger.error(f"Error in checkout process for user {user_id}: {e}")
        tg_send_message(chat_id, "Виникла помилка при оформленні замовлення. Спробуйте пізніше.")