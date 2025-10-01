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
                    name = item.get("Назва Страви", "Без назви")
                    price = int(item.get("Ціна", 0))
                    text += f"• {name} – {price} грн\n"
                    total += price
                text += f"\n<b>Разом:</b> {total} грн\n\nЩоб оформити замовлення, натисніть /order"
                send_message(chat_id, text)
        
        elif cmd == '/order':
            cart = user_carts.get(chat_id, [])
            if not cart:
                send_message(chat_id, "🛒 Ваш кошик порожній")
            else:
                save_order_to_sheets(chat_id, cart)
                send_message(chat_id, "✅ Замовлення прийнято! Ми з вами зв'яжемось для підтвердження 📞")
                user_carts[chat_id] = []
        
        elif cmd == '/help':
            help_text = """
<b>📖 Довідка BonApp</b>

/start - Почати роботу
/menu - Переглянути меню
/cart - Переглянути кошик
/order - Оформити замовлення
/help - Ця довідка
"""
            send_message(chat_id, help_text)
        
        else:
            send_message(chat_id, f"Невідома команда: {cmd}\nВикористайте /help")
    except Exception as e:
        logger.error(f"❌ Error in handle_command: {str(e)}", exc_info=True)
        send_message(chat_id, "⚠️ Виникла помилка. Спробуйте ще раз. 😔")

def handle_text_message(chat_id, text, user):
    try:
        text_lower = text.lower()
        
        if text in ['🍕 Меню', 'меню']:
            show_menu(chat_id)
            return
        
        if text in ['📂 Категорії', 'категорії']:
            show_categories(chat_id)
            return
        
        if text in ['🛒 Кошик', 'кошик']:
            handle_command(chat_id, '/cart', user)
            return
        
        if text in ['ℹ️ Допомога', 'допомога']:
            handle_command(chat_id, '/help', user)
            return
        
        if any(kw in text_lower for kw in ['піца', 'салат', 'бургер', 'напій']):
            results = search_menu_items(text)
            if results:
                response = f"🔍 <b>Знайдено:</b>\n\n"
                for item in results[:5]:
                    name = item.get('Назва Страви', 'Без назви')
                    price = item.get('Ціна', '—')
                    description = item.get('Опис', '')
                    photo_url = item.get('Фото URL', '')
                    response += f"<b>{name}</b>\n💰 {price} грн\n{description}\n\n"
                    if photo_url:
                        send_photo(chat_id, photo_url, f"{name} – {price} грн\n{description}")
                send_message(chat_id, response)
                return
        
        if is_gemini_connected():
            user_context = {
                'first_name': user.get('first_name', ''),
                'username': user.get('username', '')
            }
            ai_response = get_ai_response(text, user_context)
            send_message(chat_id, f"🤖 {ai_response}")
        else:
            send_message(chat_id, "Використовуйте кнопки меню або команду /help")
    except Exception as e:
        logger.error(f"❌ Error in handle_text_message: {str(e)}", exc_info=True)
        send_message(chat_id, "⚠️ Виникла помилка. Спробуйте ще раз. 😔")

def show_menu(chat_id):
    try:
        if not is_sheets_connected():
            send_message(chat_id, "❌ Меню тимчасово недоступне 😔")
            return
        menu = get_menu_from_sheet()
        if not menu:
            send_message(chat_id, "⚠️ Меню порожнє")
            return
        buttons = []
        for idx, item in enumerate(menu[:10]):
            name = item.get("Назва Страви", "Без назви")
            price = item.get("Ціна", "—")
            buttons.append([{
                "text": f"{name} – {price} грн 🛒",
                "callback_data": f"add_{idx}"
            }])
        keyboard = {"inline_keyboard": buttons}
        send_message(chat_id, "📖 Оберіть страву:", keyboard)
    except Exception as e:
        logger.error(f"❌ Error in show_menu: {str(e)}", exc_info=True)
        send_message(chat_id, "Помилка показу меню 😔 Спробуйте ще раз.")

def show_categories(chat_id):
    try:
        if not is_sheets_connected():
            send_message(chat_id, "❌ Категорії тимчасово недоступні 😔")
            return
        menu = get_menu_from_sheet()
        categories = set(item.get("Категорія", "Без категорії") for item in menu if item.get("Активний", "Так").lower() == "так")
        if not categories:
            send_message(chat_id, "⚠️ Категорії відсутні. Спробуйте /menu")
            return
        buttons = [[{"text": cat, "callback_data": f"category_{cat}"}] for cat in sorted(categories)]
        keyboard = {"inline_keyboard": buttons}
        send_message(chat_id, "📂 Оберіть категорію:", keyboard)
    except Exception as e:
        logger.error(f"❌ Error in show_categories: {str(e)}", exc_info=True)
        send_message(chat_id, "Помилка показу категорій 😔 Спробуйте ще раз.")

def handle_callback_query(callback_query):
    try:
        chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
        callback_id = callback_query.get('id')
        data = callback_query.get('data', '')
        logger.info(f"🔘 Callback from {chat_id}: {data}")

        if data.startswith("add_"):
            index = int(data.split("_")[1])
            menu = get_menu_from_sheet()
            if 0 <= index < len(menu):
                item = menu[index]
                name = item.get("Назва Страви", "Без назви")
                price = item.get("Ціна", "—")
                photo_url = item.get("Фото URL", "")
                if chat_id not in user_carts:
                    user_carts[chat_id] = []
                user_carts[chat_id].append(item)
                if photo_url:
                    send_photo(chat_id, photo_url, f"🛒 Додано: {name} ({price} грн)\n\nПереглянути кошик: /cart")
                else:
                    send_message(chat_id, f"🛒 Додано: {name} ({price} грн)\n\nПереглянути кошик: /cart")
                answer_callback(callback_id, "✅ Додано до кошика")
        
        elif data.startswith("category_"):
            category = data.replace("category_", "")
            menu = get_menu_from_sheet()
            items = [item for item in menu if item.get("Категорія", "Без категорії") == category and item.get("Активний", "Так").lower() == "так"]
            if not items:
                send_message(chat_id, f"⚠️ У категорії {category} немає страв")
                return
            buttons = []
            for idx, item in enumerate(items[:10]):
                name = item.get("Назва Страви", "Без назви")
                price = item.get("Ціна", "—")
                buttons.append([{
                    "text": f"{name} – {price} грн 🛒",
                    "callback_data": f"add_{idx}"
                }])
            keyboard = {"inline_keyboard": buttons}
            send_message(chat_id, f"📖 Страви в категорії {category}:", keyboard)
            answer_callback(callback_id, f"Категорія {category}")

    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}", exc_info=True)
        send_message(chat_id, "⚠️ Виникла помилка. Спробуйте ще раз. 😔")

# Обробка помилок
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
