import requests
import json
import logging
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
        
    def send_message(self, chat_id, text, keyboard=None, parse_mode="Markdown"):
        """Відправка повідомлення"""
        try:
            url = f"{self.base_url}/sendMessage"
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

    def send_photo(self, chat_id, photo, caption=None, keyboard=None):
        """Відправка фото"""
        try:
            url = f"{self.base_url}/sendPhoto"
            payload = {"chat_id": chat_id, "photo": photo}
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


# Глобальний інстанс для зворотної сумісності
telegram_api = TelegramAPI()

# Функції для зворотної сумісності
def tg_send_message(chat_id, text, keyboard=None, parse_mode="Markdown"):
    return telegram_api.send_message(chat_id, text, keyboard, parse_mode)

def tg_send_photo(chat_id, photo, caption=None, keyboard=None):
    return telegram_api.send_photo(chat_id, photo, caption, keyboard)

def tg_answer_callback(callback_query_id, text="✅ Прийнято"):
    """Відповідає на callback query"""
    try:
        url = f"{telegram_api.base_url}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id, "text": text}
        response = requests.post(url, data=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Error answering callback: {e}")
        return None
