import os
import requests
import logging
from config import BOT_TOKEN, WEBHOOK_SECRET, RENDER_URL

logger = logging.getLogger('telegram_service')

def tg_send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """Відправка повідомлення"""
    try:
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN not set")
            return None
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        error_text = e.response.text if hasattr(e, 'response') else str(e)
        logger.error(f"❌ HTTP error: {error_text}")
        return None
    except Exception as e:
        logger.error(f"❌ Send error: {e}")
        return None

def tg_answer_callback(callback_id, text, show_alert=False):
    """Відповідь на callback"""
    try:
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN not set")
            return None
            
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
        
        payload = {
            "callback_query_id": callback_id,
            "text": text,
            "show_alert": show_alert
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"❌ Answer callback error: {e}")
        return None

def tg_set_webhook(url):
    """Встановлення webhook"""
    try:
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN not set")
            return {"ok": False, "error": "BOT_TOKEN not set"}
        
        webhook_url_full = f"{url}/webhook"
        
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={
                "url": webhook_url_full,
                "secret_token": WEBHOOK_SECRET
            },
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"✅ Webhook set: {webhook_url_full}")
        else:
            logger.error(f"❌ Webhook failed: {result}")
            
        return result
        
    except requests.exceptions.HTTPError as e:
        error_text = e.response.text if hasattr(e, 'response') else str(e)
        logger.error(f"❌ HTTP error: {error_text}")
        return {"ok": False, "error": error_text}
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return {"ok": False, "error": str(e)}
