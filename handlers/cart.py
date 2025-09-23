import logging
from models.user import get_cart, set_cart
from services.sheets import get_item_by_id, get_min_delivery_amount
from services.telegram import tg_send_message, tg_send_photo, tg_answer_callback

logger = logging.getLogger("ferrik.cart")

def show_cart(chat_id):
    """Показує кошик користувача"""
    try:
        cart = get_cart(chat_id)
        items = cart.get("items", [])
        
        if not items:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🍽️ Переглянути меню", "callback_data": "show_menu"}]
                ]
            }
            tg_send_message(chat_id, "🛒 Ваш кошик порожній.\nДодайте щось смачненьке з нашого меню! 😋", reply_markup=keyboard)
            return

        # Розрахунок загальної суми
        total = sum(float(item.get("price", 0)) * int(item.get("qty", 0)) for item in items)
        
        # Формуємо текст кошика
        cart_text = "🛒 <b>Ваш кошик:</b>\n\n"
        
        # Додаємо кожну позицію
        inline_keyboard = []
        for idx, item in enumerate(items):
            item_price = float(item.get("price", 0))
            item_qty = int(item.get("qty", 0))
            item_subtotal = item_price * item_qty
            
            cart_text += f"<b>{item.get('name', 'N/A')}</b>\n"
            cart_text += f"💰 {item_price:.2f} грн × {item_qty} = {item_subtotal:.2f} грн\n\n"
            
            # Кнопки для кожної позиції
            inline_keyboard.append([
                {"text": "➖", "callback_data": f"qty_minus_{idx}"},
                {"text": f"{item_qty} шт", "callback_data": f"qty_info_{idx}"},
                {"text": "➕", "callback_data": f"qty_plus_{idx}"},
                {"text": "🗑️", "callback_data": f"remove_item_{idx}"}
            ])
        
        cart_text += f"💳 <b>Загальна сума: {total:.2f} грн</b>"
        
        # Перевіряємо мінімальну суму для замовлення
        min_amount = get_min_delivery_amount()
        
        if total >= min_amount:
            inline_keyboard.append([
                {"text": "✅ Оформити замовлення", "callback_data": "checkout"}
            ])
        else:
            needed = min_amount - total
            cart_text += f"\n\n⚠️ Мінімальна сума замовлення: {min_amount:.2f} грн"
            cart_text += f"\nДодайте ще на {needed:.2f} грн"
        
        # Додаткові кнопки
        inline_keyboard.extend([
            [{"text": "🍽️ Продовжити покупки", "callback_data": "show_menu"}],
            [{"text": "🗑️ Очистити кошик", "callback_data": "clear_cart"}]
        ])
        
        tg_send_message(chat_id, cart_text, reply_markup={"inline_keyboard": inline_keyboard})
        
    except Exception as e:
        logger.error(f"Error showing cart for {chat_id}: {e}")
        tg_send_message(chat_id, "Помилка при завантаженні кошика. Спробуйте ще раз. 😔")

def add_item_to_cart(chat_id, item_id, quantity=1):
    """Додає товар до кошика"""
    try:
        # Отримуємо інформацію про товар
        item_info = get_item_by_id(item_id)
        if not item_info:
            tg_send_message(chat_id, "Вибачте, цю позицію не знайдено в меню. 😔")
            return False
        
        # Перевіряємо чи товар активний
        if not item_info.get("active", True):
            tg_send_message(chat_id, "Вибачте, ця позиція зараз недоступна. 😔")
            return False
        
        # Отримуємо поточний кошик
        cart = get_cart(chat_id)
        cart_items = cart.get("items", [])
        
        # Шукаємо чи вже є такий товар в кошику
        item_found = False
        for cart_item in cart_items:
            if str(cart_item.get("id")) == str(item_id):
                # Товар уже є, збільшуємо кількість
                cart_item["qty"] = cart_item.get("qty", 0) + quantity
                item_found = True
                current_qty = cart_item["qty"]
                break
        
        if not item_found:
            # Додаємо новий товар до кошика
            new_item = {
                "id": item_info.get("ID"),
                "name": item_info.get("name"),  # ✅ Використовуємо правильну назву поля
                "price": float(item_info.get("price", 0)),
                "qty": quantity
            }
            cart_items.append(new_item)
            current_qty = quantity
        
        # Зберігаємо оновлений кошик
        cart["items"] = cart_items
        set_cart(chat_id, cart)
        
        # Формуємо повідомлення про успішне додавання
        caption = f"✅ <b>{item_info.get('name')}</b> додано до кошика!\n\n"
        caption += f"💰 Ціна: {item_info.get('price', 0):.2f} грн\n"
        caption += f"🛒 Кількість в кошику: {current_qty} шт"
        
        # Кнопки для швидких дій
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🛒 Переглянути кошик", "callback_data": "show_cart"},
                    {"text": "➕ Додати ще", "callback_data": f"add_item_{item_id}"}
                ],
                [{"text": "🍽️ Продовжити покупки", "callback_data": "show_menu"}]
            ]
        }
        
        # Відправляємо підтвердження з фото або без
        photo_url = item_info.get("photo", "").strip()
        if photo_url:
            tg_send_photo(chat_id, photo_url, caption, reply_markup=keyboard)
        else:
            tg_send_message(chat_id, caption, reply_markup=keyboard)
        
        logger.info(f"Added item {item_id} to cart for user {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error adding item {item_id} to cart for {chat_id}: {e}")
        tg_send_message(chat_id, "Помилка при додаванні товару до кошика. Спробуйте ще раз. 😔")
        return False

def handle_cart_quantity_change(chat_id, action, item_index, callback_id):
    """Обробляє зміну кількості товару в кошику"""
    try:
        cart = get_cart(chat_id)
        items = cart.get("items", [])
        
        if not (0 <= item_index < len(items)):
            tg_answer_callback(callback_id, "Помилка: товар не знайдено", show_alert=True)
            return
        
        item = items[item_index]
        current_qty = int(item.get("qty", 0))
        
        if action == "plus":
            new_qty = min(current_qty + 1, 99)  # Максимум 99 штук
        elif action == "minus":
            new_qty = max(current_qty - 1, 1)   # Мінімум 1 штука
        else:
            return
        
        # Оновлюємо кількість
        items[item_index]["qty"] = new_qty
        cart["items"] = items
        set_cart(chat_id, cart)
        
        tg_answer_callback(callback_id, f"Кількість оновлено: {new_qty} шт")
        
        # Оновлюємо відображення кошика
        show_cart(chat_id)
        
    except Exception as e:
        logger.error(f"Error changing quantity for user {chat_id}: {e}")
        tg_answer_callback(callback_id, "Помилка при оновленні кількості", show_alert=True)

def remove_item_from_cart(chat_id, item_index, callback_id):
    """Видаляє товар з кошика"""
    try:
        cart = get_cart(chat_id)
        items = cart.get("items", [])
        
        if not (0 <= item_index < len(items)):
            tg_answer_callback(callback_id, "Помилка: товар не знайдено", show_alert=True)
            return
        
        # Запам'ятовуємо назву для повідомлення
        item_name = items[item_index].get("name", "товар")
        
        # Видаляємо товар
        items.pop(item_index)
        cart["items"] = items
        set_cart(chat_id, cart)
        
        tg_answer_callback(callback_id, f"'{item_name}' видалено з кошика")
        
        # Оновлюємо відображення кошика
        show_cart(chat_id)
        
        logger.info(f"Removed item {item_index} from cart for user {chat_id}")
        
    except Exception as e:
        logger.error(f"Error removing item for user {chat_id}: {e}")
        tg_answer_callback(callback_id, "Помилка при видаленні товару", show_alert=True)

def clear_cart(chat_id, callback_id=None):
    """Очищує весь кошик"""
    try:
        from models.user import clear_cart as clear_user_cart
        
        if clear_user_cart(chat_id):
            message = "🗑️ Кошик очищено!\n\nМожете почати нові покупки з меню."
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🍽️ Переглянути меню", "callback_data": "show_menu"}]
                ]
            }
            tg_send_message(chat_id, message, reply_markup=keyboard)
            
            if callback_id:
                tg_answer_callback(callback_id, "Кошик очищено!")
                
            logger.info(f"Cart cleared for user {chat_id}")
        else:
            tg_send_message(chat_id, "Помилка при очищенні кошика.")
            
    except Exception as e:
        logger.error(f"Error clearing cart for user {chat_id}: {e}")
        if callback_id:
            tg_answer_callback(callback_id, "Помилка при очищенні кошика", show_alert=True)

def get_cart_total(chat_id):
    """Розраховує загальну суму кошика"""
    try:
        cart = get_cart(chat_id)
        items = cart.get("items", [])
        
        total = sum(float(item.get("price", 0)) * int(item.get("qty", 0)) for item in items)
        return total
        
    except Exception as e:
        logger.error(f"Error calculating cart total for {chat_id}: {e}")
        return 0.0

def get_cart_items_count(chat_id):
    """Підраховує кількість позицій в кошику"""
    try:
        cart = get_cart(chat_id)
        items = cart.get("items", [])
        
        return sum(int(item.get("qty", 0)) for item in items)
        
    except Exception as e:
        logger.error(f"Error counting cart items for {chat_id}: {e}")
        return 0
