import os
import requests
import logging
import json
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
            payload["reply_markup"] =
