import os
import requests
import logging
import json

logger = logging.getLogger("bonapp")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text, reply_markup=None):
    try:
        url = f"{API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Message sent to {chat_id}: {text[:50]}...")
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {str(e)}", exc_info=True)
        return None

def send_photo(chat_id, photo_url, caption, reply_markup=None):
    try:
        url = f"{API_URL}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Photo sent to {chat_id}: {caption[:50]}...")
        return response.json()
    except Exception as e:
        logger.error(f"Error sending photo to {chat_id}: {str(e)}", exc_info=True)
        return None

def answer_callback(callback_id, text=None):
    try:
        url = f"{API_URL}/answerCallbackQuery"
        payload = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Callback answered: {callback_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Error answering callback {callback_id}: {str(e)}", exc_info=True)
        return None
