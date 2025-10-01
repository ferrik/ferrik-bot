"""
Централізований роутер для обробки всіх callback запитів
"""

import logging
from services.telegram import tg_answer_callback
from handlers.menu import (
    show_menu_with_cart_buttons,
    show_categories,
    handle_add_to_cart_callback,
    handle_quick_quantity_selector,
    handle_add_quantity_callback,
    show_item_details
)
from handlers.cart import (
    show_cart,
    handle_cart_quantity_change,
    remove_item_from_cart,
    clear_cart
)
from handlers.order import (
    start_checkout_process,
    handle_delivery_type,
    handle_payment_method,
    handle_delivery_time,
    confirm_order,
    cancel_order
)

logger = logging.getLogger('ferrik')


def route_callback(chat_id, callback_data, callback_id, message_id=None):
    """
    Головний роутер для обробки callback запитів
    
    Args:
        chat_id: ID чату
        callback_data: Дані callback
        callback_id: ID callback для відповіді
        message_id: ID повідомлення (опціонально)
    """
    try:
        logger.info(f"Routing callback: {callback_data} from chat {chat_id}")
        
        # ============= МЕНЮ =============
        
        # Показати категорії
        if callback_data == "show_categories":
            show_categories(chat_id)
            tg_answer_callback(callback_id)
            
        # Показати меню за категорією
        elif callback_data.startswith("category_"):
            category = callback_data.replace("category_", "")
            show_menu_with_cart_buttons(chat_id, category=category, page=1)
            tg_answer_callback(callback_id)
            
        # Пагінація меню
        elif callback_data.startswith("menu_page_"):
            parts = callback_data.split("_")
            category = parts[2] if parts[2] != "all" else None
            page = int(parts[3])
            show_menu_with_cart_buttons(chat_id, category=category, page=page)
            tg_answer_callback(callback_id)
            
        # Додати в кошик
        elif callback_data.startswith("add_to_cart_"):
            handle_add_to_cart_callback(chat_id, callback_data, callback_id)
            
        # Швидкий вибір кількості
        elif callback_data.startswith("quick_qty_"):
            handle_quick_quantity_selector(chat_id, callback_data, callback_id)
            
        # Додати з вказаною кількістю
        elif callback_data.startswith("add_qty_"):
            handle_add_quantity_callback(chat_id, callback_data, callback_id)
            
        # Детальна інформація про страву
        elif callback_data.startswith("item_details_"):
            item_id = callback_data.replace("item_details_", "")
            show_item_details(chat_id, item_id, callback_id)
            
        # ============= КОШИК =============
        
        # Показати кошик
        elif callback_data == "show_cart":
            show_cart(chat_id)
            tg_answer_callback(callback_id)
            
        # Змінити кількість товару
        elif callback_data.startswith("qty_plus_"):
            item_index = int(callback_data.replace("qty_plus_", ""))
            handle_cart_quantity_change(chat_id, "plus", item_index, callback_id)
            
        elif callback_data.startswith("qty_minus_"):
            item_index = int(callback_data.replace("qty_minus_", ""))
            handle_cart_quantity_change(chat_id, "minus", item_index, callback_id)
            
        # Видалити товар з кошика
        elif callback_data.startswith("remove_item_"):
            item_index = int(callback_data.replace("remove_item_", ""))
            remove_item_from_cart(chat_id, item_index, callback_id)
            
        # Очистити кошик
        elif callback_data == "clear_cart":
            clear_cart(chat_id, callback_id)
            
        # Продовжити покупки
        elif callback_data == "continue_shopping":
            show_menu_with_cart_buttons(chat_id, page=1)
            tg_answer_callback(callback_id, "Продовжуємо покупки! 🛍")
            
        # ============= ЗАМОВЛЕННЯ =============
        
        # Оформити замовлення
        elif callback_data == "checkout":
            start_checkout_process(chat_id)
            tg_answer_callback(callback_id)
            
        # Тип доставки
        elif callback_data.startswith("delivery_type_"):
            delivery_type = callback_data.replace("delivery_type_", "")
            handle_delivery_type(chat_id, delivery_type, callback_id)
            
        # Спосіб оплати
        elif callback_data.startswith("payment_"):
            payment_method = callback_data.replace("payment_", "")
            handle_payment_method(chat_id, payment_method, callback_id)
            
        # Час доставки
        elif callback_data.startswith("delivery_time_"):
            time = callback_data.replace("delivery_time_", "")
            handle_delivery_time(chat_id, time, callback_id)
            
        # Підтвердити замовлення
        elif callback_data == "confirm_order":
            confirm_order(chat_id, callback_id)
            
        # Скасувати замовлення
        elif callback_data == "cancel_order":
            cancel_order(chat_id, callback_id)
            
        # Змінити дані замовлення
        elif callback_data == "edit_order":
            tg_answer_callback(callback_id, "Функція редагування в розробці")
            # TODO: Implement order editing
            
        # ============= ІНШЕ =============
        
        # No-op (для кнопок-індикаторів)
        elif callback_data == "noop":
            tg_answer_callback(callback_id)
            
        # Скасувати дію
        elif callback_data.startswith("cancel_"):
            tg_answer_callback(callback_id, "Скасовано")
            
        # Невідомий callback
        else:
            logger.warning(f"Unknown callback_data: {callback_data}")
            tg_answer_callback(callback_id, "⚠️ Невідома дія")
        
    except Exception as e:
        logger.error(f"Error routing callback {callback_data}: {e}", exc_info=True)
        try:
            tg_answer_callback(callback_id, "❌ Помилка обробки", show_alert=True)
        except:
            pass


def handle_callback_query(update):
    """
    Обробляє callback_query з update
    
    Args:
        update: Dict з даними update від Telegram
    """
    try:
        callback_query = update.get('callback_query', {})
        
        chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
        callback_id = callback_query.get('id')
        callback_data = callback_query.get('data')
        message_id = callback_query.get('message', {}).get('message_id')
        
        if not all([chat_id, callback_id, callback_data]):
            logger.error("Missing required callback data")
            return
        
        # Роутимо callback
        route_callback(chat_id, callback_data, callback_id, message_id)
        
    except Exception as e:
        logger.error(f"Error handling callback query: {e}", exc_info=True)
