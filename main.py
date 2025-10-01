import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import requests
import json
from concurrent.futures import ThreadPoolExecutor # Для асинхронних операцій

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ferrik')

# Ініціалізація Flask
app = Flask(__name__)

# --- ГЛОБАЛЬНІ СТАНОВІ ЗМІННІ (будуть ініціалізовані) ---
# Ці змінні зберігають підключення та кеші після успішної ініціалізації
# Вони мають бути імпортовані або визначені після успішного імпорту config, services
menu_cache = {}
sheets_client = None
telegram_api_url = ""
# Визначення конфігураційних змінних (будуть заповнені з config.py)
BOT_TOKEN = None
WEBHOOK_SECRET = None
WEBHOOK_URL = None


# ----------------------------------------------------------------------
# 1. СЕРВІСИ ТА УТИЛІТИ (Fallback функції та заглушки)
# ----------------------------------------------------------------------

# Fallback функція для відправки повідомлень (використовується до ініціалізації)
def fallback_send_message(chat_id, text, reply_markup=None):
    """Fallback функція для відправки повідомлень через Telegram API."""
    try:
        bot_token = os.environ.get('BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("❌ BOT_TOKEN not found for fallback.")
            return None
            
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Fallback send message error: {e}")
        return None

# Функція відповіді на callback query (для кнопок)
def answer_callback(callback_id, text=""):
    """Відповідає на callback query для приховування "loading" статусу."""
    try:
        bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
        
        payload = {
            "callback_query_id": callback_id,
            "text": text
        }
        
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"❌ Answer callback error: {e}")

# ----------------------------------------------------------------------
# 2. ІМПОРТ ТА ІНІЦІАЛІЗАЦІЯ СЕРВІСІВ
# ----------------------------------------------------------------------

# Ініціалізація сервісів
def init_services():
    """Ініціалізує всі сервіси бота (DB, Sheets, Gemini)."""
    global BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_URL
    global menu_cache, sheets_client, telegram_api_url
    
    logger.info("🛠️ Initializing services...")
    
    try:
        # Імпорт конфігурації
        from config import BOT_TOKEN as cfg_BOT_TOKEN, WEBHOOK_SECRET as cfg_WEBHOOK_SECRET, \
                           WEBHOOK_URL as cfg_WEBHOOK_URL, validate_config, log_config
        BOT_TOKEN = cfg_BOT_TOKEN
        WEBHOOK_SECRET = cfg_WEBHOOK_SECRET
        WEBHOOK_URL = cfg_WEBHOOK_URL
        telegram_api_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

        if not validate_config():
             logger.error("❌ Configuration validation failed. Bot may not work.")
        log_config()

        # Ініціалізація DB
        from models.user import init_user_db
        init_user_db()
        logger.info("✅ User DB initialized.")
        
        # Ініціалізація Google Sheets
        from services.sheets import init_gspread_client, get_menu_from_sheet
        sheets_client = init_gspread_client()
        if sheets_client:
            logger.info("✅ Google Sheets client initialized.")
            # Кешування меню
            global menu_cache
            menu_cache = get_menu_from_sheet(sheets_client, force=True)
            logger.info(f"✅ Menu cached: {len(menu_cache)} items.")
        else:
            logger.error("❌ Google Sheets client failed to initialize.")
        
        # Ініціалізація Gemini (AI)
        from services.gemini import init_gemini_client
        init_gemini_client()
        logger.info("✅ Gemini client initialized (if key present).")
        
        logger.info("🎉 FerrikFootBot initialization completed!")
        return True
    
    except Exception as e:
        logger.exception(f"❌ Critical startup error during service initialization: {e}")
        # Надіслати повідомлення про критичну помилку на заздалегідь відомий ID оператора
        fallback_send_message(os.environ.get('OPERATOR_CHAT_ID', ''), f"❌ Критична помилка при запуску бота: {e}")
        return False

# ----------------------------------------------------------------------
# 3. ОСНОВНА ЛОГІКА ОБРОБКИ
# ----------------------------------------------------------------------

def process_update(update):
    """Основна функція обробки оновлень від Telegram."""
    
    # Використовуємо функції з handlers/ та services/ (заглушки для прикладу)
    
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        
        if "text" in message:
            text = message["text"]
            
            if text == "/start":
                # Приклад: Відправка вітального повідомлення
                from prompts import GREETING
                fallback_send_message(chat_id, GREETING['ua'])
                
            elif text == "/menu":
                 # Приклад: Показати меню
                 menu_text = "📖 **Меню:**\n"
                 for item in menu_cache.values():
                     menu_text += f"**{item['Страви']}** - {item['Ціна']} грн\n"
                 fallback_send_message(chat_id, menu_text)
            
            else:
                 # Приклад: Обробка текстового запиту через Gemini
                 # from services.gemini import get_ai_response
                 # response = get_ai_response(text, menu_cache)
                 fallback_send_message(chat_id, f"Отримано: *{text}*. Працюю над відповіддю...")

        elif "location" in message:
            # Обробка геолокації (заглушка)
            fallback_send_message(chat_id, "Дякую за геолокацію! Перевіряю зону доставки...")

    elif "callback_query" in update:
        # Обробка натискань inline-кнопок
        callback_query = update["callback_query"]
        answer_callback(callback_query["id"], "Виконується...")
        
        # Приклад:
        # data = callback_query["data"]
        # process_callback_query(data)
        
    # Завжди повертаємо успіх для Telegram API
    return jsonify({"status": "ok"})


# ----------------------------------------------------------------------
# 4. РОУТИНГ FLASK
# ----------------------------------------------------------------------

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Обробляє вхідні оновлення від Telegram."""
    
    # 1. Перевірка секретного токена
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        logger.warning("❌ Webhook call with invalid secret token")
        return jsonify({"error": "Forbidden"}), 403

    # 2. Отримання даних
    try:
        update = request.get_json(force=True)
    except Exception as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        return jsonify({"error": "Invalid JSON"}), 400

    # 3. Асинхронна обробка
    # Використовуємо ThreadPoolExecutor, щоб швидко відповісти Telegram (HTTP 200 OK)
    # і продовжити обробку запиту у фоновому режимі.
    try:
        executor = ThreadPoolExecutor(max_workers=4)
        executor.submit(process_update, update)
    except Exception as e:
        logger.error(f"❌ Failed to submit job to executor: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
    # Швидка відповідь Telegram
    return jsonify({"status": "ok"}), 200

@app.route('/keep-alive', methods=['GET'])
def keep_alive():
    """Ендпоінт для запобігання 'засинанню' на Render."""
    return jsonify({"status": "alive"}), 200


# Обробка помилок Flask
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ----------------------------------------------------------------------
# 5. ЗАПУСК ДОДАТКУ
# ----------------------------------------------------------------------

with app.app_context():
    # Ініціалізація всіх сервісів при старті застосунку
    init_services()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    if debug_mode:
        # Режим розробки
        logger.info(f"Running in Debug mode on port {port}")
        app.run(host="0.0.0.0", port=port, debug=True)
    else:
        # Production (Render) - установка вебхука
        if WEBHOOK_URL and BOT_TOKEN and WEBHOOK_SECRET:
            try:
                # Встановлення вебхука при запуску в production
                response = requests.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                    params={
                        "url": WEBHOOK_URL,
                        "secret_token": WEBHOOK_SECRET
                    },
                    timeout=10
                )
                logger.info(f"✅ Webhook set response: {response.json()}")
            except Exception as e:
                logger.error(f"❌ Failed to set webhook: {e}")
        else:
            logger.error("❌ Cannot set webhook: Missing WEBHOOK_URL, BOT_TOKEN, or WEBHOOK_SECRET.")
        
        # Gunicorn запускає Flask:app, тому тут код не потрібен.
        # Запускаємо вручну лише для повного відтворення логіки
        # app.run(host="0.0.0.0", port=port)
