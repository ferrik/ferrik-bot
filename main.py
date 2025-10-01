import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import requests # Використовується для встановлення вебхука та відправки повідомлень

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ferrik')

# Ініціалізація Flask
app = Flask(__name__)

# Змінні для заглушок, якщо конфігурація не завантажилася
WEBHOOK_SECRET = ""
BOT_TOKEN = ""
WEBHOOK_URL = ""

# Імпорти з обробкою помилок
logger.info("🚀 Starting FerrikFootBot...")

try:
    # ВИПРАВЛЕННЯ: Додаємо WEBHOOK_SECRET, WEBHOOK_URL, та OPERATOR_CHAT_ID до імпорту
    from config import (
        BOT_TOKEN, WEBHOOK_SECRET, GEMINI_API_KEY, SPREADSHEET_ID,
        OPERATOR_CHAT_ID, WEBHOOK_URL
    )
    logger.info("✅ Config imported successfully")
except Exception as e:
    logger.error(f"❌ Config import error: {e}")
    # Присвоєння порожніх значень, якщо config.py не зміг імпортувати
    logger.warning("Using empty strings for critical configs due to import failure.")
    
try:
    from services.sheets import init_gspread_client, get_menu_from_sheet, save_order_to_sheets, is_sheets_connected
    logger.info("✅ Sheets service imported")
except Exception as e:
    logger.error(f"❌ Sheets import error: {e}")
    
try:
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    logger.info("✅ Gemini service imported")
except Exception as e:
    logger.error(f"❌ Gemini import error: {e}")

try:
    from models.user import init_user_db, get_user, create_user
    logger.info("✅ User model imported")
except Exception as e:
    logger.error(f"❌ User model import error: {e}")


# ========== Telegram API Helpers (Використовують BOT_TOKEN) ==========

def send_message(chat_id, text, reply_markup=None):
    """Відправляє повідомлення через Telegram API."""
    try:
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not found in send_message")
            return None
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            import json
            payload["reply_markup"] = json.dumps(reply_markup)
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Send message error: {e}")
        return None

def answer_callback(callback_id, text):
    """Відповідає на callback query."""
    try:
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not found in answer_callback")
            return
            
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
        
        payload = {
            "callback_query_id": callback_id,
            "text": text
        }
        
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"❌ Answer callback error: {e}")


# ========== Webhook та Роути Flask ==========

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Render/uptime monitoring."""
    # Перевірки наявності функцій, оскільки імпорт може бути невдалим
    status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "sheets_connected": is_sheets_connected() if 'is_sheets_connected' in locals() else False,
        "gemini_connected": is_gemini_connected() if 'is_gemini_connected' in locals() else False,
    }
    return jsonify(status)

@app.route("/keep-alive", methods=["GET"])
def keep_alive():
    """Endpoint для підтримки активності бота (Render free plan)"""
    return jsonify({"status": "i'm alive", "time": datetime.now().isoformat()})

# Основний Webhook для Telegram
@app.route("/webhook", methods=["POST"])
def webhook():
    """Обробляє вхідні оновлення від Telegram"""
    
    # 1. Перевірка секретного токену (Захист від сторонніх запитів)
    # ВИПРАВЛЕНО: WEBHOOK_SECRET тепер імпортується і доступний тут.
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        logger.warning("❌ Webhook call with invalid secret token")
        return jsonify({"status": "Invalid secret token"}), 403

    # 2. Обробка оновлення
    try:
        data = request.get_json(force=True)
        if not data:
            raise ValueError("Empty or invalid JSON data")
        
        # Виклик функції-обробника
        process_update(data)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        return jsonify({"status": "Internal Error"}), 500

def process_update(update):
    """Головний обробник оновлень Telegram (заглушка)"""
    # Це спрощена логіка. Тут має бути виклик реальних хендлерів.
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text')
        user_name = message.get('from', {}).get('first_name', 'Друже')
        
        logger.info(f"➡️ Message from {chat_id} ({user_name}): {text}")

        # ... (Логіка обробки повідомлень, що використовує send_message)
        send_message(chat_id, f"Отримано: **{text}**")
            
    elif 'callback_query' in update:
        callback_query = update['callback_query']
        callback_id = callback_query['id']
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        
        logger.info(f"➡️ Callback from {chat_id}: {data}")
        
        answer_callback(callback_id, f"Вибрано: {data}")
        send_message(chat_id, f"Вибрано: **{data}**")

# ========== Обробка помилок Flask ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ========== Запуск і Ініціалізація ==========

# Ініціалізація сервісів (заглушка)
def init_services():
    """Ініціалізує всі сервіси"""
    logger.info("Running service initialization...")
    # Тут мають бути реальні виклики ініціалізації БД, Sheets, Gemini
    logger.info("Services initialization finished.")


with app.app_context():
    try:
        init_services() 
        logger.info("✅ Services initialization completed.")

        # Установка вебхука при запуску в production
        if WEBHOOK_URL and BOT_TOKEN and WEBHOOK_SECRET:
            response = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                params={
                    "url": WEBHOOK_URL,
                    "secret_token": WEBHOOK_SECRET
                },
                timeout=10
            )
            logger.info(f"Webhook set response: {response.json()}")
        
    except Exception as e:
        logger.exception(f"❌ Critical startup error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    if debug_mode:
        app.run(host="0.0.0.0", port=port, debug=True)
