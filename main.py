import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import json
from werkzeug.exceptions import BadRequest

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ferrik')

# Ініціалізація Flask
app = Flask(__name__)

# ====================================================================
# Ініціалізація Конфігурації та Сервісів
# ====================================================================

logger.info("🚀 Starting FerrikFootBot...")

# 1. Спроба імпорту конфігурації
try:
    from config import BOT_TOKEN, WEBHOOK_SECRET, RENDER_URL
    from config import PORT, DEBUG # Імпортуємо DEBUG та PORT для запуску
    logger.info("✅ Config imported successfully")
except Exception as e:
    logger.error(f"❌ Config import error: {e}. Using fallback values. Check config.py for details.")
    # Fallback placeholders to prevent startup crash if config fails to import
    BOT_TOKEN = os.environ.get('BOT_TOKEN', 'fallback_token')
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'fallback_secret')
    RENDER_URL = os.environ.get('WEBHOOK_URL', 'https://fallback-url.com').replace('/webhook', '')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

# 2. Спроба імпорту Telegram сервісу
try:
    from services.telegram import tg_send_message, tg_answer_callback, tg_set_webhook
    logger.info("✅ Telegram service imported")
except Exception as e:
    logger.error(f"❌ Telegram service import error: {e}")
    # Fallback for core communication if import fails
    def tg_send_message(*args, **kwargs): logger.error("Telegram send fallback called."); return None
    def tg_answer_callback(*args, **kwargs): logger.error("Telegram answer fallback called.")
    def tg_set_webhook(*args, **kwargs): logger.error("Telegram set webhook fallback called."); return {"ok": False, "error": "Telegram service import failed"}


# ====================================================================
# Health Check and Keep-Alive Endpoints
# ====================================================================

@app.route("/health", methods=["GET"])
def health_check():
    """Стандартний health check endpoint. Відповідає 200 OK."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200

@app.route("/keep-alive", methods=["GET"])
def keep_alive():
    """Спеціальний endpoint для Render/GitHub Actions для пробудження сервісу. Відповідає 200 OK."""
    status = {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "config_loaded": BOT_TOKEN != 'fallback_token' # Проста перевірка конфігурації
    }
    return jsonify(status), 200

# ====================================================================
# Webhook Handling
# ====================================================================

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    """Головний ендпоінт для обробки оновлень від Telegram."""
    
    # 1. Валідація секретного токена
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        logger.warning("❌ Webhook call with invalid secret token")
        return jsonify({"ok": False, "error": "Invalid secret token"}), 403

    try:
        update = request.get_json(force=True)
        if not update:
            raise BadRequest("Invalid or empty request body")
        
        logger.info(f"Received update from chat: {update.get('message', {}).get('chat', {}).get('id', 'N/A')}")
        
        # --- Simplified Logic for demonstration/testing ---
        
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            # Заглушка: реальна логіка обробки повідомлень тут
            tg_send_message(chat_id, f"Отримано ваше повідомлення: <b>{user_text}</b>. Webhook працює!")
            
        elif "callback_query" in update:
            callback_query = update["callback_query"]
            data = callback_query["data"]
            # Заглушка: реальна логіка обробки callback-ів тут
            tg_answer_callback(callback_query["id"], f"Обрано: {data}")

        # --- End Simplified Logic ---

    except BadRequest as e:
        logger.error(f"❌ Bad request error: {e}")
        return jsonify({"ok": False, "error": "Bad Request"}), 400
    except Exception as e:
        logger.exception(f"❌ Unhandled error during webhook processing: {e}")
        return jsonify({"ok": False, "error": "Internal Server Error"}), 500

    return jsonify({"ok": True}), 200

# ====================================================================
# Webhook Setup Endpoint (for manual setup or testing)
# ====================================================================

@app.route("/set-webhook", methods=["GET"])
def set_webhook_route():
    """Встановлює вебхук для бота, використовуючи функцію з сервісу."""
    if not RENDER_URL:
        return jsonify({"ok": False, "error": "RENDER_URL is not set in config"}), 500
        
    logger.info(f"Attempting to set webhook to: {RENDER_URL}/{WEBHOOK_SECRET}")
    response_data = tg_set_webhook(RENDER_URL)
    return jsonify(response_data)


# ====================================================================
# Initialization and Startup Logic
# ====================================================================

def init_services():
    """Ініціалізує всі необхідні сервіси (DB, Sheets, Gemini)"""
    logger.info("Running service initialization...")
    
    # Тут має бути справжня логіка ініціалізації:
    # 1. База даних: init_user_db()
    # 2. Google Sheets: init_gspread_client()
    # 3. Gemini AI: init_gemini_client()
    
    logger.info("Services initialization finished.")
    return True


with app.app_context():
    try:
        from config import log_config
        log_config()
    except Exception:
        # У випадку, якщо навіть fallback config не спрацював
        logger.error("❌ Failed to run log_config function.")

    logger.info("Starting up FerrikFootBot...")
    
    # Виконуємо ініціалізацію
    if init_services():
        logger.info("🎉 FerrikFootBot ready to handle webhooks!")
    else:
        logger.error("❌ FerrikFootBot startup failed!")

if __name__ == "__main__":
    
    if DEBUG:
        app.run(host="0.0.0.0", port=PORT, debug=True)
    else:
        # Установка вебхука при запуску в production
        logger.info("Running in production mode. Relying on external webhook setup.")
