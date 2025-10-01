import os
import requests
import logging
import json
from config import BOT_TOKEN, WEBHOOK_SECRET, RENDER_URL

logger = logging.getLogger('telegram_service')

def tg_send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """Відправляє повідомлення в Telegram"""
    try:
        # BOT_TOKEN імпортується з config.py, де є обробка fallback
        if not BOT_TOKEN or BOT_TOKEN == 'fallback_token':
            logger.error("❌ BOT_TOKEN is not set or is a fallback.")
            return None
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ Telegram HTTP error: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"❌ Send message error: {e}")
        return None

def tg_answer_callback(callback_id, text, show_alert=False):
    """Відповідає на callback query (показує спливаюче повідомлення)."""
    try:
        if not BOT_TOKEN or BOT_TOKEN == 'fallback_token':
            logger.error("❌ BOT_TOKEN is not set or is a fallback.")
            return None
            
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
        
        payload = {
            "callback_query_id": callback_id,
            "text": text,
            "show_alert": show_alert
        }
        
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"❌ Answer callback error: {e}")

def tg_set_webhook(url):
    """Встановлює вебхук для бота."""
    try:
        if not BOT_TOKEN or BOT_TOKEN == 'fallback_token':
             logger.error("❌ BOT_TOKEN not set for webhook setup.")
             return {"ok": False, "error": "BOT_TOKEN not set"}
        
        webhook_url_full = f"{url}/{WEBHOOK_SECRET}" 
        
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            params={
                "url": webhook_url_full,
                "secret_token": WEBHOOK_SECRET
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ Telegram HTTP error on setWebhook: {e.response.text}")
        return {"ok": False, "error": f"HTTP Error: {e.response.text}"}
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
        return {"ok": False, "error": str(e)}
