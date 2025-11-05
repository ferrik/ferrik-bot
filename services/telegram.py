"""
Telegram API Service - Minimal Version
"""
import requests
import logging

logger = logging.getLogger(__name__)


class TelegramAPI:
    """Мінімальний Telegram API клієнт"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, chat_id: int, text: str, reply_markup: dict = None):
        """Відправити повідомлення"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None
    
    def answer_callback_query(self, callback_query_id: str, text: str = None):
        """Відповісти на callback query"""
        url = f"{self.base_url}/answerCallbackQuery"
        data = {'callback_query_id': callback_query_id}
        
        if text:
            data['text'] = text
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to answer callback: {e}")
            return None
    
    def set_webhook(self, webhook_url: str):
        """Встановити webhook"""
        url = f"{self.base_url}/setWebhook"
        data = {'url': webhook_url}
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            return None
    
    def get_webhook_info(self):
        """Отримати інформацію про webhook"""
        url = f"{self.base_url}/getWebhookInfo"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get webhook info: {e}")
            return None
