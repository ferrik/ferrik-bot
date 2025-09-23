import os
import logging
import requests
import json
from typing import Optional, Dict, List, Any

logger = logging.getLogger("ferrik.telegram")

# Змінні середовища
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
OPERATOR_CHAT_ID = os.environ.get("OPERATOR_CHAT_ID", "").strip()

def tg_send_message(chat_id: int, text: str, reply_markup: Optional[Dict] = None, parse_mode: str = "HTML") -> Optional[Dict]:
    """Відправляє текстове повідомлення"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending message to {chat_id}: {e}")
        return None

def tg_send_photo(chat_id: int, photo_url: str, caption: str = "", reply_markup: Optional[Dict] = None, parse_mode: str = "HTML") -> Optional[Dict]:
    """Відправляє фото з підписом"""
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": parse_mode
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(f"{API_URL}/sendPhoto", json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send photo to {chat_id}: {e}")
        # Fallback - відправляємо як текстове повідомлення
        fallback_text = f"{caption}\n\n📷 Фото: {photo_url}"
        return tg_send_message(chat_id, fallback_text, reply_markup, parse_mode)
    except Exception as e:
        logger.error(f"Unexpected error sending photo to {chat_id}: {e}")
        return None

def tg_edit_message(chat_id: int, message_id: int, text: str, reply_markup: Optional[Dict] = None, parse_mode: str = "HTML") -> Optional[Dict]:
    """Редагує існуюче повідомлення"""
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(f"{API_URL}/editMessageText", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to edit message {message_id} in {chat_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error editing message {message_id} in {chat_id}: {e}")
        return None

def tg_edit_message_reply_markup(chat_id: int, message_id: int, reply_markup: Optional[Dict] = None) -> Optional[Dict]:
    """Редагує тільки клавіатуру повідомлення"""
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": reply_markup
    }
    
    try:
        response = requests.post(f"{API_URL}/editMessageReplyMarkup", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to edit message markup {message_id} in {chat_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error editing message markup {message_id} in {chat_id}: {e}")
        return None

def tg_answer_callback(callback_id: str, text: str = "", show_alert: bool = False) -> Optional[Dict]:
    """Відповідає на callback query"""
    payload = {
        "callback_query_id": callback_id,
        "text": text,
        "show_alert": show_alert
    }
    
    try:
        response = requests.post(f"{API_URL}/answerCallbackQuery", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to answer callback {callback_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error answering callback {callback_id}: {e}")
        return None

def tg_delete_message(chat_id: int, message_id: int) -> bool:
    """Видаляє повідомлення"""
    payload = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    
    try:
        response = requests.post(f"{API_URL}/deleteMessage", json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to delete message {message_id} in {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting message {message_id} in {chat_id}: {e}")
        return False

def tg_send_location(chat_id: int, latitude: float, longitude: float, title: str = "", address: str = "") -> Optional[Dict]:
    """Відправляє геолокацію"""
    payload = {
        "chat_id": chat_id,
        "latitude": latitude,
        "longitude": longitude
    }
    
    try:
        response = requests.post(f"{API_URL}/sendLocation", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send location to {chat_id}: {e}")
        return None

def tg_send_contact(chat_id: int, phone_number: str, first_name: str, last_name: str = "") -> Optional[Dict]:
    """Відправляє контакт"""
    payload = {
        "chat_id": chat_id,
        "phone_number": phone_number,
        "first_name": first_name
    }
    
    if last_name:
        payload["last_name"] = last_name
    
    try:
        response = requests.post(f"{API_URL}/sendContact", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send contact to {chat_id}: {e}")
        return None

def tg_get_chat_member(chat_id: int, user_id: int) -> Optional[Dict]:
    """Отримує інформацію про учасника чату"""
    payload = {
        "chat_id": chat_id,
        "user_id": user_id
    }
    
    try:
        response = requests.post(f"{API_URL}/getChatMember", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get chat member {user_id} in {chat_id}: {e}")
        return None

def notify_operator(message: str, chat_id: int = None, user_info: Dict = None) -> bool:
    """Надсилає повідомлення оператору"""
    if not OPERATOR_CHAT_ID:
        logger.warning("OPERATOR_CHAT_ID not set, cannot notify operator")
        return False
    
    try:
        # Формуємо повідомлення для оператора
        operator_message = f"🔔 <b>Повідомлення від користувача</b>\n\n"
        
        if chat_id:
            operator_message += f"👤 <b>Chat ID:</b> {chat_id}\n"
        
        if user_info:
            if user_info.get("first_name"):
                operator_message += f"📝 <b>Ім'я:</b> {user_info['first_name']}"
                if user_info.get("last_name"):
                    operator_message += f" {user_info['last_name']}"
                operator_message += "\n"
            
            if user_info.get("username"):
                operator_message += f"🏷️ <b>Username:</b> @{user_info['username']}\n"
        
        operator_message += f"\n💬 <b>Повідомлення:</b>\n{message}"
        
        # Створюємо кнопку для швидкої відповіді
        reply_markup = None
        if chat_id:
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "📞 Відповісти користувачу", "callback_data": f"reply_to_{chat_id}"}]
                ]
            }
        
        result = tg_send_message(OPERATOR_CHAT_ID, operator_message, reply_markup)
        return result is not None
        
    except Exception as e:
        logger.error(f"Failed to notify operator: {e}")
        return False

def send_to_user_from_operator(chat_id: int, message: str, operator_name: str = "Оператор") -> bool:
    """Відправляє повідомлення користувачу від оператора"""
    try:
        operator_message = f"👨‍💼 <b>Повідомлення від {operator_name}:</b>\n\n{message}"
        result = tg_send_message(chat_id, operator_message)
        return result is not None
    except Exception as e:
        logger.error(f"Failed to send message to user {chat_id} from operator: {e}")
        return False

def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> Dict:
    """Створює inline клавіатуру"""
    return {"inline_keyboard": buttons}

def create_reply_keyboard(buttons: List[List[str]], resize_keyboard: bool = True, one_time_keyboard: bool = False) -> Dict:
    """Створює reply клавіатуру"""
    keyboard = []
    for row in buttons:
        keyboard.append([{"text": button} for button in row])
    
    return {
        "keyboard": keyboard,
        "resize_keyboard": resize_keyboard,
        "one_time_keyboard": one_time_keyboard
    }

def remove_reply_keyboard() -> Dict:
    """Видаляє reply клавіатуру"""
    return {"remove_keyboard": True}

def format_menu_item_message(item: Dict) -> str:
    """Форматує повідомлення для позиції меню"""
    message = f"<b>{item.get('name', 'Назва відсутня')}</b>\n\n"
    
    if item.get('description'):
        message += f"📝 {item['description']}\n\n"
    
    message += f"💰 <b>Ціна:</b> {item.get('price', 0):.2f} грн"
    
    if item.get('restaurant'):
        message += f"\n🏪 <b>Ресторан:</b> {item['restaurant']}"
    
    if item.get('cooking_time'):
        message += f"\n⏰ <b>Час приготування:</b> {item['cooking_time']} хв"
    
    if item.get('allergens'):
        message += f"\n⚠️ <b>Алергени:</b> {item['allergens']}"
    
    if item.get('rating'):
        try:
            rating = float(item['rating'])
            stars = '⭐' * int(rating)
            message += f"\n{stars} <b>Рейтинг:</b> {rating}/5"
        except (ValueError, TypeError):
            pass
    
    return message

def format_cart_summary(cart: Dict) -> str:
    """Форматує підсумок кошика"""
    items = cart.get("items", [])
    if not items:
        return "🛒 <b>Ваш кошик порожній</b>"
    
    message = "🛒 <b>Ваш кошик:</b>\n\n"
    total = 0
    
    for item in items:
        price = float(item.get("price", 0))
        qty = int(item.get("qty", 0))
        subtotal = price * qty
        total += subtotal
        
        message += f"• {item.get('name', 'N/A')} × {qty}\n"
        message += f"  {price:.2f} грн × {qty} = {subtotal:.2f} грн\n\n"
    
    message += f"💰 <b>Всього: {total:.2f} грн</b>"
    
    return message

def format_order_confirmation(order_data: Dict) -> str:
    """Форматує підтвердження замовлення"""
    message = "✅ <b>Підтвердження замовлення</b>\n\n"
    
    # Товари
    message += "📦 <b>Замовлені товари:</b>\n"
    total = 0
    for item in order_data.get("items", []):
        price = float(item.get("price", 0))
        qty = int(item.get("qty", 0))
        subtotal = price * qty
        total += subtotal
        message += f"• {item.get('name')} × {qty} = {subtotal:.2f} грн\n"
    
    message += f"\n💰 <b>Сума товарів:</b> {total:.2f} грн"
    
    # Доставка
    delivery_cost = float(order_data.get("delivery_cost", 0))
    if delivery_cost > 0:
        message += f"\n🚚 <b>Доставка:</b> {delivery_cost:.2f} грн"
        message += f"\n💳 <b>До сплати:</b> {total + delivery_cost:.2f} грн"
    else:
        message += f"\n🏃‍♂️ <b>Самовивіз</b>"
        message += f"\n💳 <b>До сплати:</b> {total:.2f} грн"
    
    # Контакти та адреса
    if order_data.get("phone"):
        message += f"\n\n📞 <b>Телефон:</b> {order_data['phone']}"
    
    if order_data.get("address"):
        message += f"\n🏠 <b>Адреса:</b> {order_data['address']}"
    
    # Спосіб оплати
    if order_data.get("payment_method"):
        message += f"\n💸 <b>Оплата:</b> {order_data['payment_method']}"
    
    # Час доставки
    if order_data.get("delivery_time"):
        message += f"\n⏰ <b>Час доставки:</b> {order_data['delivery_time']}"
    
    if order_data.get("notes"):
        message += f"\n📝 <b>Примітки:</b> {order_data['notes']}"
    
    return message

def validate_phone_number(phone: str) -> bool:
    """Валідує номер телефону"""
    import re
    # Приводимо до стандартного формату
    cleaned_phone = re.sub(r'[^\d+]', '', phone)
    
    # Перевіряємо українські номери
    patterns = [
        r'^\+380\d{9}$',      # +380XXXXXXXXX
        r'^380\d{9}$',        # 380XXXXXXXXX
        r'^0\d{9}$',          # 0XXXXXXXXX
    ]
    
    for pattern in patterns:
        if re.match(pattern, cleaned_phone):
            return True
    
    return False

def normalize_phone_number(phone: str) -> str:
    """Нормалізує номер телефону до формату +380XXXXXXXXX"""
    import re
    cleaned_phone = re.sub(r'[^\d+]', '', phone)
    
    if cleaned_phone.startswith('+380') and len(cleaned_phone) == 13:
        return cleaned_phone
    elif cleaned_phone.startswith('380') and len(cleaned_phone) == 12:
        return '+' + cleaned_phone
    elif cleaned_phone.startswith('0') and len(cleaned_phone) == 10:
        return '+38' + cleaned_phone
    elif len(cleaned_phone) == 9:
        return '+380' + cleaned_phone
    
    return phone  # Повертаємо оригінал якщо не вдалося нормалізувати

def log_telegram_error(error: Exception, action: str, chat_id: int = None) -> None:
    """Логує помилки Telegram API"""
    error_msg = f"Telegram API error during {action}"
    if chat_id:
        error_msg += f" for chat {chat_id}"
    error_msg += f": {error}"
    
    logger.error(error_msg)
    
    # Можна додати додатковий моніторинг або алерти тут
