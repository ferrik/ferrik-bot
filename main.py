"""
🤖 Ferrik Bot 2.0 - Головний файл (Simplified for Render)
"""
import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import json

# ============================================================================
# Конфігурація з .env
# ============================================================================
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'bot.db')
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')

# ============================================================================
# Logging
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Flask App
# ============================================================================
app = Flask(__name__)


# ============================================================================
# Простий імпорт модулів (якщо вони є)
# ============================================================================
try:
    from services.telegram import TelegramAPI
    from services.sheets import SheetsAPI
    from services.database import Database
    telegram = TelegramAPI(TELEGRAM_BOT_TOKEN)
    sheets = SheetsAPI()
    db = Database(DATABASE_PATH)
    logger.info("✅ Services loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Some services not available: {e}")
    telegram = None
    sheets = None
    db = None


# ============================================================================
# Health Check
# ============================================================================
@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'bot': 'Ferrik Bot 2.0',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/health')
def health():
    """Detailed health check"""
    health_status = {
        'status': 'healthy',
        'services': {
            'telegram': telegram is not None,
            'sheets': sheets is not None,
            'database': db is not None
        },
        'config': {
            'token_set': bool(TELEGRAM_BOT_TOKEN),
            'webhook_set': bool(TELEGRAM_WEBHOOK_URL),
            'sheets_id_set': bool(GOOGLE_SHEETS_SPREADSHEET_ID)
        }
    }
    return jsonify(health_status)


# ============================================================================
# Webhook
# ============================================================================
@app.route('/webhook', methods=['POST'])
def webhook():
    """Main webhook handler"""
    try:
        update = request.get_json()
        logger.info(f"📨 Received update: {update.get('update_id', 'unknown')}")
        
        # Обробка повідомлення
        if 'message' in update:
            handle_message(update['message'])
        elif 'callback_query' in update:
            handle_callback(update['callback_query'])
        
        return jsonify({'ok': True})
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


def handle_message(message: dict):
    """Handle incoming messages"""
    user_id = message['from']['id']
    text = message.get('text', '')
    
    logger.info(f"👤 User {user_id}: {text}")
    
    # Простий відповідь для тестування
    if text.startswith('/start'):
        if telegram:
            telegram.send_message(
                user_id,
                "🍴 Привіт! Я — Ferrik Bot 2.0!\n\n"
                "Бот успішно запущено на Render! 🚀\n\n"
                "Доступні команди:\n"
                "/menu - Меню\n"
                "/help - Допомога"
            )
    elif text.startswith('/help'):
        if telegram:
            telegram.send_message(
                user_id,
                "📋 Доступні команди:\n\n"
                "/start - Почати\n"
                "/menu - Переглянути меню\n"
                "/cart - Кошик\n"
                "/profile - Профіль\n"
                "/help - Ця довідка"
            )
    else:
        if telegram:
            telegram.send_message(
                user_id,
                "Використовуй /help для списку команд"
            )


def handle_callback(callback: dict):
    """Handle callback queries"""
    user_id = callback['from']['id']
    data = callback['data']
    
    logger.info(f"🔘 Callback from {user_id}: {data}")
    
    if telegram:
        telegram.answer_callback_query(callback['id'], text="Готово!")


# ============================================================================
# Запуск
# ============================================================================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 Starting Ferrik Bot on port {port}...")
    
    # Встановлення webhook при запуску (опціонально)
    if TELEGRAM_WEBHOOK_URL and telegram:
        try:
            result = telegram.set_webhook(TELEGRAM_WEBHOOK_URL + '/webhook')
            logger.info(f"✅ Webhook set: {result}")
        except Exception as e:
            logger.error(f"❌ Failed to set webhook: {e}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
