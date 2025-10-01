import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ferrik')

# Ініціалізація Flask
app = Flask(__name__)

# Імпорти з обробкою помилок
logger.info("🚀 Starting FerrikFootBot...")

try:
    from config import BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID, WEBHOOK_SECRET, WEBHOOK_URL
    logger.info("✅ Config imported successfully")
except Exception as e:
    logger.error(f"❌ Config import error: {e}")

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
    from models.user import init_user_db
    logger.info("✅ User model imported")
except Exception as e:
    logger.error(f"❌ User model import error: {e}")


# Ініціалізація сервісів
def init_services():
    """Ініціалізує всі сервіси: Sheets, Gemini, DB"""
    try:
        if is_sheets_connected() or init_gspread_client():
            menu_items = get_menu_from_sheet(force=True)
            logger.info(f"✅ Menu cached: {len(menu_items)} items")
            
        if is_gemini_connected() or init_gemini_client():
            logger.info("✅ Gemini client initialized")
            
        init_user_db()
        
    except Exception as e:
        logger.error(f"❌ Critical initialization error in init_services: {e}")


def send_message(chat_id, text, reply_markup=None):
    """Надсилає повідомлення через Telegram API"""
    import requests
    
    try:
        bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("❌ BOT_TOKEN not found for send_message")
            return None
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
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
    """Відповідає на callback query"""
    import requests
    
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


def process_telegram_update(update):
    """Основний обробник оновлень від Telegram"""
    
    # Видалення проблемного коду, що викликав SyntaxError
    # Рядок 211, де було:
    # name =
    # Початок блоку, де, ймовірно, мав бути оброблений update
    
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        user_name = message['from'].get('first_name', 'Користувач')
        text = message.get('text', '')

        if text == '/start':
            greeting = f"👋 Привіт, {user_name}! Я FoodBot, готовий приймати замовлення."
            send_message(chat_id, greeting)
        
        elif text == '/menu':
            send_message(chat_id, "📖 Наразі меню завантажується. Спробуйте пізніше або скористайтесь рекомендацією.")
            
        elif text == '/recommendation':
            # Приклад використання Gemini. Потрібна детальніша реалізація
            response_text = get_ai_response("Зроби коротку рекомендацію для обіду в обідній час.")
            send_message(chat_id, f"⭐ Рекомендація від AI:\n{response_text}")

        else:
            # Обробка текстового запиту через AI
            response_text = get_ai_response(f"Користувач {user_name} написав: '{text}'. Дай дружню відповідь, як помічник ресторану.")
            send_message(chat_id, response_text)

    elif 'callback_query' in update:
        callback_query = update['callback_query']
        callback_id = callback_query['id']
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']

        answer_callback(callback_id, f"Оброблено: {data}")
        send_message(chat_id, f"Ви натиснули кнопку з даними: `{data}`")


# ==========================================================
# FLASK ENDPOINTS
# ==========================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробник вебхука від Telegram"""
    
    # Перевірка секретного токена
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        logger.warning("❌ Webhook: Invalid Secret Token")
        return jsonify({'status': 'error', 'message': 'Invalid secret token'}), 403
    
    try:
        update = request.get_json()
        if update:
            process_telegram_update(update)
            return jsonify({'status': 'ok'}), 200
        else:
            return jsonify({'status': 'ok', 'message': 'No update'}), 200
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/set_webhook', methods=['POST'])
def set_webhook_route():
    """Ендпоінт для встановлення вебхука"""
    import requests
    
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            params={
                "url": WEBHOOK_URL,
                "secret_token": WEBHOOK_SECRET
            },
            timeout=10
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check для Render"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200


# Обробка помилок
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ==========================================================
# ІНІЦІАЛІЗАЦІЯ ДОДАТКУ
# ==========================================================
with app.app_context():
    logger.info("🚀 FerrikFootBot starting...")
    
    try:
        init_services()
        logger.info("🎉 FerrikFootBot initialization completed!")
        
    except Exception as e:
        logger.exception(f"❌ Critical startup error: {e}")


if __name__ == "__main__":
    # Локальний запуск для тестування (якщо FLASK_DEBUG=true)
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    if debug_mode:
        app.run(host="0.0.0.0", port=port, debug=True)
    else:
        # Установка вебхука при запуску в production
        if WEBHOOK_URL:
            import requests
            try:
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
                logger.error(f"Failed to set webhook: {e}")
