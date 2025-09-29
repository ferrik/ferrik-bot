import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Ініціалізація логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ferrik')

# Ініціалізація Flask
app = Flask(__name__)

# Імпорт сервісів та обробників
try:
    from services.sheets import init_gspread_client, is_sheets_connected
    from services.gemini import init_gemini_client, is_gemini_connected
    from handlers.commands import handle_start, handle_help, handle_menu, handle_order
    from handlers.messages import handle_text_message
except ImportError as e:
    logger.error(f"❌ Помилка імпорту модулів: {e}")
    raise

# Конфігурація
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com')

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не знайдено!")
    raise ValueError("TELEGRAM_BOT_TOKEN is required")


# Ініціалізація сервісів при запуску
def init_services():
    """Ініціалізує всі сервіси"""
    logger.info("🚀 Ініціалізація FerrikFootBot...")
    
    # Google Sheets
    sheets_ok = init_gspread_client()
    if sheets_ok:
        logger.info("✅ Google Sheets підключено")
    else:
        logger.warning("⚠️ Google Sheets не підключено. Деякі функції будуть недоступні.")
    
    # Gemini AI
    gemini_ok = init_gemini_client()
    if gemini_ok:
        logger.info("✅ Gemini AI підключено")
    else:
        logger.warning("⚠️ Gemini AI не підключено")
    
    logger.info("🎉 FerrikFootBot готовий до роботи!")
    return sheets_ok, gemini_ok


# Ініціалізуємо сервіси
init_services()


# ============= ROUTES =============

@app.route('/')
def home():
    """Головна сторінка - показує статус бота"""
    return jsonify({
        "status": "running",
        "bot": "FerrikFootBot",
        "version": "1.0",
        "services": {
            "google_sheets": is_sheets_connected(),
            "gemini_ai": is_gemini_connected()
        },
        "timestamp": datetime.now().isoformat()
    })


@app.route('/health')
def health():
    """Health check для Render"""
    sheets_status = is_sheets_connected()
    gemini_status = is_gemini_connected()
    
    status_code = 200 if (sheets_status or gemini_status) else 503
    
    return jsonify({
        "status": "healthy" if status_code == 200 else "degraded",
        "services": {
            "google_sheets": sheets_status,
            "gemini_ai": gemini_status
        }
    }), status_code


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Обробник webhook від Telegram
    """
    try:
        update = request.get_json()
        
        if not update:
            logger.warning("⚠️ Отримано порожній update")
            return jsonify({"ok": True}), 200
        
        logger.info(f"📨 Received update: {update.keys()}")
        
        # Обробка різних типів оновлень
        if 'message' in update:
            handle_message(update['message'])
        elif 'callback_query' in update:
            handle_callback_query(update['callback_query'])
        else:
            logger.warning(f"⚠️ Невідомий тип update: {update.keys()}")
        
        return jsonify({"ok": True}), 200
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки webhook: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


def handle_message(message):
    """Обробляє вхідне повідомлення"""
    try:
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        user = message.get('from', {})
        
        logger.info(f"👤 Message from {user.get('username', 'unknown')}: {text}")
        
        # Обробка команд
        if text.startswith('/'):
            handle_command(chat_id, text, user)
        else:
            # Обробка звичайних повідомлень (через AI)
            handle_text_message(chat_id, text, user)
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки повідомлення: {e}", exc_info=True)


def handle_command(chat_id, command, user):
    """Розподіляє команди по обробникам"""
    try:
        cmd = command.split()[0].lower()
        
        handlers = {
            '/start': handle_start,
            '/help': handle_help,
            '/menu': handle_menu,
            '/order': handle_order
        }
        
        handler = handlers.get(cmd)
        if handler:
            handler(chat_id, user)
        else:
            send_message(chat_id, f"❓ Невідома команда: {cmd}\nВикористайте /help")
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки команди: {e}", exc_info=True)
        send_message(chat_id, "⚠️ Виникла помилка при обробці команди")


def handle_callback_query(callback_query):
    """Обробляє callback від inline кнопок"""
    try:
        callback_id = callback_query.get('id')
        chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
        data = callback_query.get('data')
        
        logger.info(f"🔘 Callback: {data}")
        
        # Тут додайте логіку обробки callback
        # Наприклад, вибір страв з меню
        
        # Відповідь на callback
        answer_callback_query(callback_id, "✅ Прийнято!")
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки callback: {e}", exc_info=True)


def send_message(chat_id, text, reply_markup=None):
    """Відправляє повідомлення в Telegram"""
    import requests
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Помилка відправки повідомлення: {e}")
        return None


def answer_callback_query(callback_id, text):
    """Відповідає на callback query"""
    import requests
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_id,
        "text": text
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"❌ Помилка відповіді на callback: {e}")


# Запуск додатку
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)