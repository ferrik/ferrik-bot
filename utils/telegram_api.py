import requests
import json
import logging
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

def send_message(chat_id, text, keyboard=None, parse_mode="Markdown"):
    """
    Відправка повідомлення через Telegram Bot API
    
    Args:
        chat_id (int): ID чату
        text (str): Текст повідомлення
        keyboard (dict): Клавіатура (опціонально)
        parse_mode (str): Режим розбору тексту
        
    Returns:
        dict: Відповідь від API або None при помилці
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if keyboard:
            payload["reply_markup"] = json.dumps(keyboard)
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Message sent to {chat_id}")
            return response.json()
        else:
            logger.error(f"Failed to send message: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

def send_photo(chat_id, photo, caption=None, keyboard=None):
    """
    Відправка фото через Telegram Bot API
    
    Args:
        chat_id (int): ID чату
        photo (str): URL фото або file_id
        caption (str): Підпис до фото
        keyboard (dict): Клавіатура (опціонально)
        
    Returns:
        dict: Відповідь від API або None при помилці
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        
        payload = {
            "chat_id": chat_id,
            "photo": photo
        }
        
        if caption:
            payload["caption"] = caption
            
        if keyboard:
            payload["reply_markup"] = json.dumps(keyboard)
        
        response = requests.post(url, data=payload, timeout=15)
        
        if response.status_code == 200:
            logger.info(f"Photo sent to {chat_id}")
            return response.json()
        else:
            logger.error(f"Failed to send photo: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error sending photo: {e}")
        return None

def edit_message(chat_id, message_id, text, keyboard=None, parse_mode="Markdown"):
    """
    Редагування повідомлення через Telegram Bot API
    
    Args:
        chat_id (int): ID чату
        message_id (int): ID повідомлення для редагування
        text (str): Новий текст
        keyboard (dict): Клавіатура (опціонально)
        parse_mode (str): Режим розбору тексту
        
    Returns:
        dict: Відповідь від API або None при помилці
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if keyboard:
            payload["reply_markup"] = json.dumps(keyboard)
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Message edited in {chat_id}")
            return response.json()
        else:
            logger.error(f"Failed to edit message: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return None

def delete_message(chat_id, message_id):
    """
    Видалення повідомлення через Telegram Bot API
    
    Args:
        chat_id (int): ID чату
        message_id (int): ID повідомлення для видалення
        
    Returns:
        bool: True якщо успішно, False при помилці
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
        
        payload = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Message deleted from {chat_id}")
            return True
        else:
            logger.error(f"Failed to delete message: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        return False

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """
    Відповідь на callback query
    
    Args:
        callback_query_id (str): ID callback query
        text (str): Текст відповіді (опціонально)
        show_alert (bool): Показати як alert
        
    Returns:
        bool: True якщо успішно, False при помилці
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
        
        payload = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert
        }
        
        if text:
            payload["text"] = text
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("Callback query answered")
            return True
        else:
            logger.error(f"Failed to answer callback query: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error answering callback query: {e}")
        return False

def set_webhook(webhook_url):
    """
    Встановлення webhook для бота
    
    Args:
        webhook_url (str): URL для webhook
        
    Returns:
        bool: True якщо успішно, False при помилці
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        
        payload = {
            "url": webhook_url
        }
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                logger.info(f"Webhook set to: {webhook_url}")
                return True
            else:
                logger.error(f"Failed to set webhook: {result}")
                return False
        else:
            logger.error(f"Failed to set webhook: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return False

def get_me():
    """
    Отримання інформації про бота
    
    Returns:
        dict: Інформація про бота або None при помилці
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                logger.info("Bot info retrieved successfully")
                return result["result"]
            else:
                logger.error(f"Failed to get bot info: {result}")
                return None
        else:
            logger.error(f"Failed to get bot info: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        return None
