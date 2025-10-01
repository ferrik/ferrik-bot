import os
import logging
import json
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    logging.warning("zoneinfo not found. Using naive datetime.")
    ZoneInfo = None

# Імпорти сервісів
try:
    from services.sheets import init_gspread_client, get_menu_from_sheet, save_order_to_sheets, is_sheets_connected, search_menu_items
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    from services.telegram import send_message, answer_callback, send_photo
    from models.user import init_user_db
except Exception as e:
    logging.error(f"❌ Import error: {str(e)}", exc_info=True)

# Налаштування логів
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bonapp.log')]
)
logger = logging.getLogger("bonapp")

# Ініціалізація Flask
app = Flask(__name__)
CORS(app)
limiter = Limiter(app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

# Змінні середовища
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "BonApp123!").strip()
SPREADSHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "").strip()
OPERATOR_CHAT_ID = os.environ.get("OPERATOR_CHAT_ID", "").strip()
TIMEZONE_NAME = os.environ.get("TIMEZONE", "Europe/Kyiv").strip()

# Сховище кошиків
user_carts = {}

# Ініціалізація сервісів
def init_services():
    logger.info("🔧 Initializing BonApp services...")
    try:
        init_user_db()
        logger.info("✅ User database initialized")
    except Exception as e:
        logger.error(f"❌ User DB initialization failed: {str(e)}", exc_info=True)
    
    sheets_ok = False
    try:
        sheets_ok = init_gspread_client()
        if sheets_ok:
            logger.info("✅ Google Sheets connected")
        else:
            logger.warning("⚠️ Google Sheets connection failed")
    except Exception as e:
        logger.error(f"❌ Sheets initialization error: {str(e)}", exc_info=True)
    
    gemini_ok = False
    try:
        gemini_ok = init_gemini_client()
        if gemini_ok:
            logger.info("✅ Gemini AI connected")
        else:
            logger.warning("⚠️ Gemini AI connection failed")
    except Exception as e:
        logger.error(f"❌ Gemini initialization error: {str(e)}", exc_info=True)
    
    logger.info("🎉 BonApp initialization completed!")
    return sheets_ok, gemini_ok

init_services()

# ============= ROUTES =============

@app.route('/')
def home():
    try:
        menu_count = len(get_menu_from_sheet()) if is_sheets_connected() else 0
    except:
        menu_count = 0
    return jsonify({
        "status": "running",
        "bot": "BonApp",
        "version": "2.1",
        "services": {
            "google_sheets": is_sheets_connected(),
            "gemini_ai": is_gemini_connected()
        },
        "menu_items": menu_count,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
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

@app.route('/keep-alive')
def keep_alive():
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running"
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_SECRET and header_secret != WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret: %s", header_secret)
        return jsonify({"ok": False, "error": "invalid secret"}), 403

    update = request.get_json(silent=True)
    if not update:
        logger.warning("⚠️ Empty update received")
        return jsonify({"ok": True}), 200
    
    try:
        logger.info(f"📨 Update {update.get('update_id', 'unknown')}")
        if 'message' in update:
            handle_message(update['message'])
        elif 'callback_query' in update:
            handle_callback_query(update['callback_query'])
        else:
            logger.warning(f"⚠️ Unknown update type: {list(update.keys())}")
        return jsonify({"ok": True}), 200
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500

# ============= HANDLERS =============

def handle_message(message):
    try:
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '').strip()
        user = message.get('from', {})
        if not chat_id:
            logger.error("No chat_id in message")
            return
        username = user.get('first_name', 'Друже')
        logger.info(f"👤 {username} ({chat_id}): {text}")
        
        if text.startswith('/'):
            handle_command(chat_id, text, user)
        else:
            handle_text_message(chat_id, text, user)
    except Exception as e:
        logger.error(f"❌ Error in handle_message: {str(e)}", exc_info=True)
        send_message(chat_id, "⚠️ Виникла помилка. Спробуйте ще раз. 😔")

def handle_command(chat_id, command, user):
    try:
        cmd = command.split()[0].lower()
        username = user.get('first_name', 'Друже')
        
        if cmd == '/start':
            welcome_text = f"""
👋 <b>Вітаю, {username}!</b>

Я <b>BonApp</b> - ваш помічник у замовленні їжі! 🍕

<b>Що я вмію:</b>
🍔 Показати меню
📂 Показати категорії
🛒 Додати страви у кошик
📝 Оформити замовлення
🤖 Допомогти з вибором через AI

<b>Доступні команди:</b>
/menu - Переглянути меню
/cart - Переглянути кошик
/help - Допомога
"""
            keyboard = {
                "keyboard": [
                    [{"text": "🍕 Меню"}, {"text": "📂 Категорії"}],
                    [{"text": "🛒 Кошик"}, {"text": "ℹ️ Допомога"}]
                ],
                "resize_keyboard": True
            }
            send_message(chat_id, welcome_text, keyboard)
        
        elif cmd == '/menu':
            show_menu(chat_id)
        
        elif cmd == '/cart':
            cart = user_carts.get(chat_id, [])
            if not cart:
                send_message(chat_id, "🛒 Ваш кошик порожній")
            else:
                text = "🛒 <b>Ваш кошик:</b>\n\n"
                total = 0
                for item in cart:
                    name =
