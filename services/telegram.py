"""
Telegram API Wrapper
Обгортка для роботи з Telegram Bot API
"""
import logging
import requests
from typing import Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

# Base URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{config.BOT_TOKEN}"


def tg_send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: Optional[Dict] = None,
    disable_web_page_preview: bool = True
) -> bool:
    """
    Відправити повідомлення в Telegram
    
    Args:
        chat_id: ID чату
        text: Текст повідомлення
        parse_mode: HTML або Markdown
        reply_markup: Клавіатура (keyboard або inline_keyboard)
        disable_web_page_preview: Вимкнути превью посилань
    
    Returns:
        bool: True якщо успішно
    """
    url = f"{TELEGRAM_API_URL}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            logger.info(f"✅ Message sent to {chat_id}")
            return True
        else:
            logger.error(f"❌ Telegram API error: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return False


def tg_send_photo(
    chat_id: int,
    photo_url: str,
    caption: str = "",
    reply_markup: Optional[Dict] = None
) -> bool:
    """
    Відправити фото в Telegram
    
    Args:
        chat_id: ID чату
        photo_url: URL фото
        caption: Підпис до фото
        reply_markup: Клавіатура
    
    Returns:
        bool: True якщо успішно
    """
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            logger.info(f"✅ Photo sent to {chat_id}")
            return True
        else:
            logger.error(f"❌ Telegram API error: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return False


def tg_answer_callback(
    callback_query_id: str,
    text: str = "",
    show_alert: bool = False
) -> bool:
    """
    Відповісти на callback query
    
    Args:
        callback_query_id: ID callback query
        text: Текст відповіді
        show_alert: Показати як alert
    
    Returns:
        bool: True якщо успішно
    """
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        return result.get("ok", False)
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Answer callback failed: {e}")
        return False


def tg_set_webhook(webhook_url: str, secret_token: str) -> bool:
    """
    Встановити webhook
    
    Args:
        webhook_url: URL webhook
        secret_token: Секретний токен
    
    Returns:
        bool: True якщо успішно
    """
    url = f"{TELEGRAM_API_URL}/setWebhook"
    
    payload = {
        "url": webhook_url,
        "secret_token": secret_token,
        "allowed_updates": ["message", "callback_query"]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            logger.info(f"✅ Webhook set: {webhook_url}")
            return True
        else:
            logger.error(f"❌ Set webhook failed: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return False


def tg_get_webhook_info() -> Dict[str, Any]:
    """
    Отримати інформацію про webhook
    
    Returns:
        dict: Інформація про webhook
    """
    url = f"{TELEGRAM_API_URL}/getWebhookInfo"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            return result.get("result", {})
        else:
            logger.error(f"❌ Get webhook info failed: {result.get('description')}")
            return {}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return {}


def setup_webhook_safe() -> bool:
    """
    Безпечно налаштувати webhook
    
    Returns:
        bool: True якщо успішно
    """
    if not config.WEBHOOK_URL:
        logger.warning("⚠️ WEBHOOK_URL not set")
        return False
    
    if not config.WEBHOOK_SECRET:
        logger.warning("⚠️ WEBHOOK_SECRET not set")
        return False
    
    webhook_url = f"{config.WEBHOOK_URL}/webhook"
    
    # Перевірка поточного webhook
    info = tg_get_webhook_info()
    current_url = info.get("url", "")
    
    if current_url == webhook_url:
        logger.info(f"✅ Webhook already set: {webhook_url}")
        return True
    
    # Встановлення нового webhook
    return tg_set_webhook(webhook_url, config.WEBHOOK_SECRET)


def test_telegram_connection() -> bool:
    """
    Тест з'єднання з Telegram API
    
    Returns:
        bool: True якщо успішно
    """
    url = f"{TELEGRAM_API_URL}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            bot_info = result.get("result", {})
            logger.info(f"✅ Bot connected: @{bot_info.get('username')}")
            return True
        else:
            logger.error(f"❌ Telegram API error: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False


# Тестування при імпорті
if __name__ == "__main__":
    print("🧪 Testing Telegram service...")
    if test_telegram_connection():
        print("✅ Telegram connection OK")
    else:
        print("❌ Telegram connection FAILED")
