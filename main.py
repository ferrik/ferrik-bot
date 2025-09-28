import os
import logging
import json
import re
from flask import Flask, request, jsonify
import requests
from handlers.cart import show_cart, add_item_to_cart
from handlers.order import start_checkout_process
from handlers.geo import check_delivery_availability
from services.sheets import init_gspread_client, get_menu_from_sheet, get_item_by_id
from services.gemini import get_gemini_recommendation
from models.user import init_db, get_state, set_state, get_cart, set_cart, get_or_create_user, add_chat_history
from datetime import datetime
from werkzeug.exceptions import BadRequest

try:
    from zoneinfo import ZoneInfo
except ImportError:
    logging.warning("zoneinfo not found. Using naive datetime.")
    ZoneInfo = None

app = Flask(__name__)

# Налаштування логів
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)
logger = logging.getLogger("ferrik")

# Змінні середовища
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "Ferrik123").strip()
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "").strip()
OPERATOR_CHAT_ID = os.environ.get("OPERATOR_CHAT_ID", "").strip()
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Kyiv").strip()
TIMEZONE_NAME = os.environ.get("TIMEZONE_NAME", "Europe/Kiev").strip()

# Глобальні об'єкти
MENU_CACHE = {} 
GSPREAD_CLIENT = None
GEMINI_CLIENT = None

def tg_send_message(chat_id, text, keyboard=None, parse_mode="Markdown"):
    """Надсилає повідомлення через Telegram API."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set. Cannot send message.")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
        
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending message to {chat_id}: {e}")
        return None

def tg_answer_callback(callback_id, text, show_alert=False):
    """Надсилає відповідь на callback запит."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set. Cannot answer callback.")
        return
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_id,
        "text": text,
        "show_alert": show_alert
    }
    try:
        response = requests.post(url, data=payload, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error answering callback {callback_id}: {e}")
        return None

def generate_personalized_greeting(user_name="Друже"):
    user_name = (user_name or '').strip() or 'Друже'
    current = datetime.now() if not ZoneInfo else datetime.now(ZoneInfo(TIMEZONE_NAME))
    hour = current.hour

    greeting = f"Доброго {'ранку' if 6 <= hour < 12 else 'дня' if 12 <= hour < 18 else 'вечора'}, {user_name}! 😊"
    status = "Ресторан відкритий! 🍽️ Готові прийняти ваше замовлення." if is_restaurant_open() else "Ресторан закритий. 😔 Працюємо з 9:00 до 22:00."
    return f"{greeting}\n\n{status}\n\nЯ ваш помічник для замовлення їжі! 🍔🍕"

def is_restaurant_open():
    current_hour = datetime.now().hour if not ZoneInfo else datetime.now(ZoneInfo(TIMEZONE_NAME)).hour
    return 9 <= current_hour < 22
    
# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """Перевірка стану програми та зовнішніх сервісів."""
    status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "db_status": "ok" if init_db() else "error", 
        "sheets_status": "ok" if GSPREAD_CLIENT else "error",
        "menu_cached_items": len(MENU_CACHE),
        "bot_token_present": bool(BOT_TOKEN)
    }
    return jsonify(status)

# Ініціалізація додатку
with app.app_context():
    logger.info("🚀 FerrikFootBot starting initialization...")
    
    try:
        # Ініціалізація бази даних
        from models.user import init_db
        if init_db():
            logger.info("✅ Database initialized")
        else:
            logger.error("❌ Database initialization failed")
        
        # Підключення до Google Sheets
        GSPREAD_CLIENT = init_gspread_client()
        if GSPREAD_CLIENT:
            logger.info("✅ Google Sheets connected")
            
            # Завантажуємо меню для кешування
            MENU_CACHE = get_menu_from_sheet(force=True)
            logger.info(f"✅ Menu cached: {len(MENU_CACHE)} items")
        else:
            logger.error("❌ Google Sheets connection failed")
            
        # Ініціалізація Gemini
        from services.gemini import init_gemini_client
        GEMINI_CLIENT = init_gemini_client() 
        if not GEMINI_CLIENT:
            logger.warning("⚠️ Gemini client not initialized. AI recommendations will be unavailable.")
        else:
            logger.info("✅ Gemini client initialized.")

        logger.info("🎉 FerrikFootBot initialization completed!")
        
    except Exception as e:
        logger.exception(f"❌ Critical startup error: {e}")

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """Основний обробник для Telegram вебхуків."""
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return jsonify({"status": "error", "message": "Invalid secret token"}), 403

    try:
        update = request.get_json(force=True)
        if not update:
            return jsonify({"status": "ok"})

        logger.info(f"Received update: {update.keys()}")

        if "message" in update:
            # Обробка текстових повідомлень та команд
            chat_id = update["message"]["chat"]["id"]
            user_id = update["message"]["from"]["id"]
            user_name = update["message"]["from"].get("first_name", "")
            
            from models.user import get_or_create_user, add_chat_history
            user = get_or_create_user(user_id, chat_id, user_name)
            if 'text' in update['message']:
                add_chat_history(user_id, 'user', update['message']['text'])
                
            text = update["message"]["text"]
            
            # Обробка команд
            if text == "/start":
                greeting = generate_personalized_greeting(user_name)
                tg_send_message(chat_id, greeting) 
            elif text == "/menu":
                tg_send_message(chat_id, "Ось наше **Меню**! Виберіть категорію.")
            elif text == "/cart":
                from handlers.cart import show_cart
                show_cart(chat_id, user_id)
            elif text == "/checkout":
                from handlers.order import start_checkout_process
                start_checkout_process(chat_id, user_id)
            elif text == "/contacts":
                contacts_text = """
📞 **Контакти**

📱 Телефон: +380XX XXX XX XX
📧 Email: info@ferrikfoot.com
📍 Адреса: м. Київ, вул. Прикладна, 1
"""
                tg_send_message(chat_id, contacts_text)
            else:
                from handlers.message_processor import process_text_message
                # Використовуємо глобальні змінні
                process_text_message(chat_id, user_id, user_name, text, MENU_CACHE, GEMINI_CLIENT)

        elif "callback_query" in update:
            # Обробка натискань inline кнопок
            callback_query = update["callback_query"]
            chat_id = callback_query["message"]["chat"]["id"]
            user_id = callback_query["from"]["id"]
            data = callback_query["data"]
            callback_id = callback_query["id"]

            # Обробка кнопок
            if data.startswith("add_"):
                item_id = data.split("_")[1]
                from handlers.cart import add_item_to_cart
                add_item_to_cart(chat_id, user_id, item_id)
                tg_answer_callback(callback_id, "Товар додано до кошика!")
            elif data == "checkout":
                from handlers.order import start_checkout_process
                start_checkout_process(chat_id, user_id)
                tg_answer_callback(callback_id, "Починаємо оформлення замовлення")
            else:
                tg_answer_callback(callback_id, "Невідома дія.")
        
        return jsonify({"status": "ok"})

    except BadRequest as e:
        logger.error(f"Invalid JSON request: {e}")
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
    except Exception as e:
        logger.exception(f"Unhandled error in webhook: {e}")
        return jsonify({"status": "error", "message": "Internal error"}), 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    """Встановлення Telegram вебхука."""
    try:
        webhook_url = os.environ.get("WEBHOOK_URL")
        if not webhook_url:
            return jsonify({"ok": False, "error": "WEBHOOK_URL environment variable is missing"}), 500

        # Використовуємо BOT_TOKEN
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", 
            params={
                "url": webhook_url,
                "secret_token": WEBHOOK_SECRET
            },
            timeout=10
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    if debug_mode:
        app.run(host="0.0.0.0", port=port, debug=True)
    else:
        # Установка вебхука при запуску в production
        webhook_url = os.environ.get("WEBHOOK_URL", "")
        if webhook_url:
            try:
                response = requests.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                    params={
                        "url": webhook_url,
                        "secret_token": WEBHOOK_SECRET
                    },
                    timeout=10
                )
                logger.info(f"Webhook set response: {response.json()}")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}")