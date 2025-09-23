import logging
from datetime import datetime, timedelta
from models.user import get_cart, set_cart, set_state, clear_cart
from services.telegram import tg_send_message, format_order_confirmation, notify_operator
from services.sheets import save_order_to_sheets, get_min_delivery_amount

logger = logging.getLogger("ferrik.order")

def start_checkout_process(chat_id):
    """Починає процес оформлення замовлення"""
    try:
        cart = get_cart(chat_id)
        items = cart.get("items", [])
        
        if not items:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🍽️ Переглянути меню", "callback_data": "show_menu"}]
                ]
            }
            tg_send_message(chat_id, "🛒 Ваш кошик порожній. Додайте щось із меню! 🍽️", reply_markup=keyboard)
            return False
        
        # Перевіряємо мінімальну суму замовлення
        total = sum(float(item.get("price", 0)) * int(item.get("qty", 0)) for item in items)
        min_amount = get_min_delivery_amount()
        
        if total < min_amount:
            needed = min_amount - total
            message = f"⚠️ Мінімальна сума замовлення — {min_amount:.2f} грн.\n"
            message += f"Додайте ще товарів на {needed:.2f} грн! 😊"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🍽️ Додати ще товарів", "callback_data": "show_menu"}],
                    [{"text": "🛒 Переглянути кошик", "callback_data": "show_cart"}]
                ]
            }
            tg_send_message(chat_id, message, reply_markup=keyboard)
            return False
        
        # Перевіряємо чи вже є номер телефону
        phone = cart.get("phone")
        if phone:
            # Переходимо до вибору типу доставки
            ask_delivery_type(chat_id)
        else:
            # Просимо ввести номер телефону
            message = "📱 Для оформлення замовлення введіть ваш номер телефону у форматі:\n"
            message += "<code>+380XXXXXXXXX</code> або <code>0XXXXXXXXX</code>"
            
            tg_send_message(chat_id, message)
            set_state(chat_id, "awaiting_phone")
        
        return True
        
    except Exception as e:
        logger.error(f"Error starting checkout for {chat_id}: {e}")
        tg_send_message(chat_id, "Помилка при оформленні замовлення. Спробуйте ще раз. 😔")
        return False

def ask_delivery_type(chat_id):
    """Запитує тип доставки"""
    try:
        message = "🚚 Оберіть спосіб отримання замовлення:"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🚚 Доставка", "callback_data": "delivery_type_delivery"}],
                [{"text": "🏃‍♂️ Самовивіз", "callback_data": "delivery_type_pickup"}]
            ]
        }
        
        tg_send_message(chat_id, message, reply_markup=keyboard)
        set_state(chat_id, "awaiting_delivery_type")
        
    except Exception as e:
        logger.error(f"Error asking delivery type for {chat_id}: {e}")
        tg_send_message(chat_id, "Помилка при виборі доставки. 😔")

def handle_delivery_type(chat_id, delivery_type, callback_id):
    """Обробляє вибір типу доставки"""
    try:
        cart = get_cart(chat_id)
        
        from services.telegram import tg_answer_callback
        
        if delivery_type == "delivery":
            cart["delivery_type"] = "Доставка"
            set_cart(chat_id, cart)
            
            tg_answer_callback(callback_id, "Доставка обрана! 🚚")
            
            message = "🏠 Введіть адресу доставки:\n\n"
            message += "Наприклад: <i>вул. Хрещатик, 1, кв. 10, м. Тернопіль</i>\n\n"
            message += "💡 Чим детальніше адреса, тим швидше ми доставимо!"
            
            tg_send_message(chat_id, message)
            set_state(chat_id, "awaiting_address")
            
        elif delivery_type == "pickup":
            cart["delivery_type"] = "Самовивіз"
            cart["address"] = "Самовивіз"
            cart["delivery_cost"] = 0
            set_cart(chat_id, cart)
            
            tg_answer_callback(callback_id, "Самовивіз обраний! 🏃‍♂️")
            
            # Показуємо адресу для самовивозу
            message = "🏃‍♂️ <b>Самовивіз</b>\n\n"
            message += "📍 <b>Адреса:</b> вул. Руська, 12, Тернопіль\n"
            message += "🕐 <b>Час роботи:</b> 10:00 - 22:00\n\n"
            message += "Оберіть спосіб оплати:"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💳 Картою онлайн", "callback_data": "payment_card"}],
                    [{"text": "💵 Готівка при отриманні", "callback_data": "payment_cash"}]
                ]
            }
            
            tg_send_message(chat_id, message, reply_markup=keyboard)
            set_state(chat_id, "awaiting_payment_method")
        
    except Exception as e:
        logger.error(f"Error handling delivery type for {chat_id}: {e}")
        from services.telegram import tg_answer_callback
        tg_answer_callback(callback_id, "Помилка при виборі доставки", show_alert=True)

def handle_address_input(chat_id, address):
    """Обробляє введення адреси"""
    try:
        from handlers.geo import check_delivery_availability
        
        # Перевіряємо можливість доставки
        coords = check_delivery_availability(address)
        
        if coords:
            cart = get_cart(chat_id)
            cart["address"] = address.strip()
            cart["coords"] = coords
            cart["delivery_cost"] = 50  # Стандартна вартість доставки
            set_cart(chat_id, cart)
            
            message = f"✅ Адреса прийнята!\n\n"
            message += f"📍 <b>Доставка:</b> {address}\n"
            message += f"💰 <b>Вартість доставки:</b> 50 грн\n\n"
            message += "Оберіть спосіб оплати:"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💳 Картою онлайн", "callback_data": "payment_card"}],
                    [{"text": "💵 Готівка при доставці", "callback_data": "payment_cash"}]
                ]
            }
            
            tg_send_message(chat_id, message, reply_markup=keyboard)
            set_state(chat_id, "awaiting_payment_method")
            
        else:
            message = "😔 Вибачте, доставка за цією адресою неможлива.\n\n"
            message += "🚚 Зона доставки: м. Тернопіль та околиці (до 7 км)\n\n"
            message += "Спробуйте ввести іншу адресу або оберіть самовивіз:"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🏃‍♂️ Самовивіз", "callback_data": "delivery_type_pickup"}],
                    [{"text": "📝 Ввести іншу адресу", "callback_data": "retry_address"}]
                ]
            }
            
            tg_send_message(chat_id, message, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error handling address for {chat_id}: {e}")
        tg_send_message(chat_id, "Помилка при обробці адреси. Спробуйте ще раз. 😔")

def handle_payment_method(chat_id, payment_method, callback_id):
    """Обробляє вибір способу оплати"""
    try:
        cart = get_cart(chat_id)
        
        from services.telegram import tg_answer_callback
        
        if payment_method == "card":
            cart["payment_method"] = "Картою онлайн"
            tg_answer_callback(callback_id, "Онлайн оплата обрана! 💳")
            
        elif payment_method == "cash":
            delivery_type = cart.get("delivery_type", "Доставка")
            if delivery_type == "Самовивіз":
                cart["payment_method"] = "Готівка при самовивозі"
                tg_answer_callback(callback_id, "Готівка при самовивозі! 💵")
            else:
                cart["payment_method"] = "Готівка при доставці"
                tg_answer_callback(callback_id, "Готівка при доставці! 💵")
        
        set_cart(chat_id, cart)
        
        # Переходимо до вибору часу
        ask_delivery_time(chat_id)
        
    except Exception as e:
        logger.error(f"Error handling payment method for {chat_id}: {e}")
        from services.telegram import tg_answer_callback
        tg_answer_callback(callback_id, "Помилка при виборі оплати", show_alert=True)

def ask_delivery_time(chat_id):
    """Запитує час доставки/самовивозу"""
    try:
        cart = get_cart(chat_id)
        delivery_type = cart.get("delivery_type", "Доставка")
        
        now = datetime.now()
        
        # Створюємо варіанти часу
        time_options = []
        
        # Найближчий можливий час (через 30-60 хв)
        earliest = now + timedelta(minutes=45)
        time_options.append(earliest.strftime("%H:%M"))
        
        # Додаємо ще кілька варіантів
        for i in range(1, 4):
            option_time = earliest + timedelta(minutes=30 * i)
            if option_time.hour < 22:  # До 22:00
                time_options.append(option_time.strftime("%H:%M"))
        
        message = f"⏰ Коли вам зручно {'отримати доставку' if delivery_type == 'Доставка' else 'забрати замовлення'}?\n\n"
        message += "Оберіть час або напишіть свій варіант:"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": f"🕒 {time}", "callback_data": f"delivery_time_{time}"} for time in time_options[:2]],
                [{"text": f"🕒 {time}", "callback_data": f"delivery_time_{time}"} for time in time_options[2:4]],
                [{"text": "📝 Вказати свій час", "callback_data": "custom_delivery_time"}]
            ]
        }
        
        tg_send_message(chat_id, message, reply_markup=keyboard)
        set_state(chat_id, "awaiting_delivery_time")
        
    except Exception as e:
        logger.error(f"Error asking delivery time for {chat_id}: {e}")
        tg_send_message(chat_id, "Помилка при виборі часу. 😔")

def handle_delivery_time(chat_id, delivery_time, callback_id=None):
    """Обробляє вибір часу доставки"""
    try:
        cart = get_cart(chat_id)
        cart["delivery_time"] = delivery_time
        set_cart(chat_id, cart)
        
        if callback_id:
            from services.telegram import tg_answer_callback
            tg_answer_callback(callback_id, f"Час обрано: {delivery_time} ✅")
        
        # Показуємо підсумок замовлення
        show_order_confirmation(chat_id)
        
    except Exception as e:
        logger.error(f"Error handling delivery time for {chat_id}: {e}")
        if callback_id:
            from services.telegram import tg_answer_callback
            tg_answer_callback(callback_id, "Помилка при виборі часу", show_alert=True)

def show_order_confirmation(chat_id):
    """Показує підтвердження замовлення"""
    try:
        cart = get_cart(chat_id)
        items = cart.get("items", [])
        
        if not items:
            tg_send_message(chat_id, "Помилка: кошик порожній. 😔")
            return
        
        # Розраховуємо суми
        subtotal = sum(float(item.get("price", 0)) * int(item.get("qty", 0)) for item in items)
        delivery_cost = float(cart.get("delivery_cost", 0))
        total = subtotal + delivery_cost
        
        # Формуємо текст підтвердження
        message = "📋 <b>Підтвердження замовлення</b>\n\n"
        
        # Список товарів
        message += "🛒 <b>Ваше замовлення:</b>\n"
        for item in items:
            price = float(item.get("price", 0))
            qty = int(item.get("qty", 0))
            subtotal_item = price * qty
            message += f"• {item.get('name')} × {qty} = {subtotal_item:.2f} грн\n"
        
        message += f"\n💰 <b>Вартість товарів:</b> {subtotal:.2f} грн"
        
        if delivery_cost > 0:
            message += f"\n🚚 <b>Доставка:</b> {delivery_cost:.2f} грн"
        
        message += f"\n💳 <b>До сплати:</b> {total:.2f} грн"
        
        # Деталі замовлення
        message += f"\n\n📞 <b>Телефон:</b> {cart.get('phone', 'N/A')}"
        message += f"\n🏠 <b>Адреса:</b> {cart.get('address', 'N/A')}"
        message += f"\n💸 <b>Оплата:</b> {cart.get('payment_method', 'N/A')}"
        message += f"\n⏰ <b>Час:</b> {cart.get('delivery_time', 'N/A')}"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ Підтвердити замовлення", "callback_data": "confirm_order"}],
                [{"text": "✏️ Змінити дані", "callback_data": "edit_order"}],
                [{"text": "❌ Відмінити", "callback_data": "cancel_order"}]
            ]
        }
        
        tg_send_message(chat_id, message, reply_markup=keyboard)
        set_state(chat_id, "awaiting_confirmation")
        
    except Exception as e:
        logger.error(f"Error showing order confirmation for {chat_id}: {e}")
        tg_send_message(chat_id, "Помилка при підтвердженні замовлення. 😔")

def confirm_order(chat_id, callback_id):
    """Підтверджує та зберігає замовлення"""
    try:
        cart = get_cart(chat_id)
        items = cart.get("items", [])
        
        if not items:
            from services.telegram import tg_answer_callback
            tg_answer_callback(callback_id, "Помилка: кошик порожній", show_alert=True)
            return
        
        # Підготовка даних для збереження
        subtotal = sum(float(item.get("price", 0)) * int(item.get("qty", 0)) for item in items)
        delivery_cost = float(cart.get("delivery_cost", 0))
        total = subtotal + delivery_cost
        
        order_data = {
            "chat_id": chat_id,
            "items": items,
            "total": subtotal,
            "delivery_cost": delivery_cost,
            "total_with_delivery": total,
            "phone": cart.get("phone"),
            "address": cart.get("address"),
            "coords": cart.get("coords"),
            "payment_method": cart.get("payment_method"),
            "delivery_type": cart.get("delivery_type"),
            "delivery_time": cart.get("delivery_time"),
            "notes": cart.get("notes", "")
        }
        
        # Зберігаємо в Google Sheets
        order_id = save_order_to_sheets(order_data)
        
        if order_id:
            from services.telegram import tg_answer_callback
            tg_answer_callback(callback_id, "Замовлення прийняте! ✅")
            
            # Повідомлення клієнту
            message = f"✅ <b>Замовлення #{order_id} прийняте!</b>\n\n"
            message += f"💳 <b>Сума:</b> {total:.2f} грн\n"
            message += f"⏰ <b>Час:</b> {cart.get('delivery_time')}\n\n"
            message += "📞 Наш оператор зв'яжеться з вами найближчим часом для підтвердження.\n\n"
            message += "Дякуємо за ваше замовлення! 😊"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🍽️ Нове замовлення", "callback_data": "show_menu"}],
                    [{"text": "📞 Зв'язатися з нами", "callback_data": "contact_operator"}]
                ]
            }
            
            tg_send_message(chat_id, message, reply_markup=keyboard)
            
            # Повідомлення оператору
            operator_message = f"🔔 <b>Нове замовлення #{order_id}</b>\n\n"
            operator_message += f"👤 <b>Клієнт:</b> {chat_id}\n"
            operator_message += f"📞 <b>Телефон:</b> {cart.get('phone')}\n"
            operator_message += f"🏠 <b>Адреса:</b> {cart.get('address')}\n"
            operator_message += f"💰 <b>Сума:</b> {total:.2f} грн\n"
            operator_message += f"💸 <b>Оплата:</b> {cart.get('payment_method')}\n"
            operator_message += f"⏰ <b>Час:</b> {cart.get('delivery_time')}\n\n"
            
            # Список товарів для оператора
            operator_message += "<b>Товари:</b>\n"
            for item in items:
                qty = int(item.get("qty", 0))
                operator_message += f"• {item.get('name')} × {qty}\n"
            
            notify_operator(operator_message, chat_id)
            
            # Очищуємо кошик та скидаємо стан
            clear_cart(chat_id)
            set_state(chat_id, "normal")
            
            logger.info(f"Order {order_id} confirmed for user {chat_id}")
            
        else:
            from services.telegram import tg_answer_callback
            tg_answer_callback(callback_id, "Помилка збереження замовлення", show_alert=True)
            tg_send_message(chat_id, "Помилка при збереженні замовлення. Спробуйте ще раз або зв'яжіться з оператором. 😔")
        
    except Exception as e:
        logger.error(f"Error confirming order for {chat_id}: {e}")
        from services.telegram import tg_answer_callback
        tg_answer_callback(callback_id, "Помилка підтвердження замовлення", show_alert=True)

def cancel_order(chat_id, callback_id):
    """Скасовує поточне замовлення"""
    try:
        from services.telegram import tg_answer_callback
        tg_answer_callback(callback_id, "Замовлення скасовано")
        
        message = "❌ Замовлення скасовано.\n\nВаш кошик збережено. Можете продовжити покупки! 😊"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🛒 Переглянути кошик", "callback_data": "show_cart"}],
                [{"text": "🍽️ Продовжити покупки", "callback_data": "show_menu"}]
            ]
        }
        
        tg_send_message(chat_id, message, reply_markup=keyboard)
        set_state(chat_id, "normal")
        
        logger.info(f"Order cancelled for user {chat_id}")
        
    except Exception as e:
        logger.error(f"Error cancelling order for {chat_id}: {e}")
        from services.telegram import tg_answer_callback
        tg_answer_callback(callback_id, "Помилка скасування", show_alert=True)
