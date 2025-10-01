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
    from config import BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID
    logger.info("✅ Config imported successfully")
except Exception as e:
    logger.error(f"❌ Config import error: {e}")

try:
    from services.sheets import init_gspread_client, get_menu_from_sheet, save_order_to_sheets, is_sheets_connected, search_menu_items
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
    """Ініціалізує всі сервіси бота"""
    logger.info("🔧 Initializing services...")
    
    try:
        init_user_db()
        logger.info("✅ User database initialized")
    except Exception as e:
        logger.error(f"❌ User DB initialization failed: {e}")
    
    sheets_ok = False
    try:
        sheets_ok = init_gspread_client()
        if sheets_ok:
            logger.info("✅ Google Sheets connected")
        else:
            logger.warning("⚠️ Google Sheets connection failed")
    except Exception as e:
        logger.error(f"❌ Sheets initialization error: {e}")
    
    gemini_ok = False
    try:
        gemini_ok = init_gemini_client()
        if gemini_ok:
            logger.info("✅ Gemini AI connected")
        else:
            logger.warning("⚠️ Gemini AI connection failed")
    except Exception as e:
        logger.error(f"❌ Gemini initialization error: {e}")
    
    logger.info("🎉 FerrikFootBot initialization completed!")
    return sheets_ok, gemini_ok


# Ініціалізуємо при старті
init_services()

# 🛒 Сховище кошиків користувачів (chat_id -> список страв)
user_carts = {}


# ============= ROUTES =============

@app.route('/')
def home():
    """Головна сторінка - показує статус бота"""
    try:
        menu_count = len(get_menu_from_sheet()) if is_sheets_connected() else 0
    except:
        menu_count = 0
    
    return jsonify({
        "status": "running",
        "bot": "FerrikFootBot",
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
    try:
        update = request.get_json()
        if not update:
            logger.warning("⚠️ Empty update received")
            return jsonify({"ok": True}), 200
        
        logger.info(f"📨 Received update: {update.get('update_id', 'unknown')}")
        
        if 'message' in update:
            handle_message(update['message'])
        elif 'callback_query' in update:
            handle_callback_query(update['callback_query'])
        else:
            logger.warning(f"⚠️ Unknown update type: {list(update.keys())}")
        
        return jsonify({"ok": True}), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


# ============= HANDLERS =============

def handle_message(message):
    try:
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        user = message.get('from', {})
        
        if not chat_id:
            logger.error("No chat_id in message")
            return
        
        username = user.get('first_name', 'User')
        logger.info(f"👤 Message from {username} ({chat_id}): {text}")
        
        if text.startswith('/'):
            handle_command(chat_id, text, user)
        else:
            handle_text_message(chat_id, text, user)
            
    except Exception as e:
        logger.error(f"❌ Error in handle_message: {e}", exc_info=True)
        try:
            send_message(chat_id, "⚠️ Виникла помилка. Спробуйте ще раз.")
        except:
            pass


def handle_command(chat_id, command, user):
    try:
        cmd = command.split()[0].lower()
        username = user.get('first_name', 'друже')
        
        if cmd == '/start':
            welcome_text = f"""
👋 <b>Вітаю, {username}!</b>

Я <b>FerrikFootBot</b> - ваш помічник у замовленні їжі! 🍕

<b>Що я вмію:</b>
🍔 Показати меню
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
                    [{"text": "🍕 Меню"}, {"text": "🛒 Кошик"}],
                    [{"text": "ℹ️ Допомога"}]
                ],
                "resize_keyboard": True
            }
            send_message(chat_id, welcome_text, keyboard)
            
        elif cmd == '/menu':
            show_menu_with_cart_buttons(chat_id)
            
        elif cmd == '/cart':
            cart = user_carts.get(chat_id, [])
            if not cart:
                send_message(chat_id, "🛒 Ваш кошик порожній")
            else:
                text = "🛒 <b>Ваш кошик:</b>\n\n"
                total = 0
                for item in cart:
                    name = item.get("Страви", "Без назви")
                    price = int(item.get("Ціна", 0))
                    text += f"• {name} – {price} грн\n"
                    total += price
                text += f"\n<b>Разом:</b> {total} грн\n\n" \
                        f"Щоб оформити замовлення, натисніть /order"
                send_message(chat_id, text)
        
        elif cmd == '/help':
            help_text = """
<b>📖 Довідка FerrikFootBot</b>

/start - Почати роботу
/menu - Переглянути меню
/cart - Переглянути кошик
/order - Оформити замовлення
/help - Ця довідка
"""
            send_message(chat_id, help_text)
        
        elif cmd == '/order':
            cart = user_carts.get(chat_id, [])
            if not cart:
                send_message(chat_id, "🛒 Ваш кошик порожній")
            else:
                send_message(chat_id, "✅ Замовлення прийнято! Ми з вами зв'яжемось для підтвердження 📞")
                # TODO: тут можна додати save_order_to_sheets(cart)
                user_carts[chat_id] = []  # очищаємо кошик після замовлення
        
        else:
            send_message(chat_id, f"Невідома команда: {cmd}\nВикористайте /help")
    except Exception as e:
        logger.error(f"❌ Error in handle_command: {e}", exc_info=True)


def handle_text_message(chat_id, text, user):
    try:
        text_lower = text.lower()
        
        if text in ['🍕 меню', 'меню']:
            show_menu_with_cart_buttons(chat_id)
            return
        
        if text in ['🛒 кошик', 'кошик']:
            handle_command(chat_id, '/cart', user)
            return
        
        if text in ['ℹ️ допомога', 'допомога']:
            handle_command(chat_id, '/help', user)
            return
        
        if any(kw in text_lower for kw in ['піца', 'салат', 'бургер', 'напій']):
            try:
                results = search_menu_items(text)
                if results:
                    response = f"🔍 <b>Знайдено:</b>\n\n"
                    for item in results[:5]:
                        response += f"<b>{item.get('Страви')}</b>\n"
                        response += f"💰 {item.get('Ціна')} грн\n\n"
                    send_message(chat_id, response)
                    return
            except Exception as e:
                logger.error(f"Search error: {e}")
        
        if is_gemini_connected():
            try:
                user_context = {
                    'first_name': user.get('first_name', ''),
                    'username': user.get('username', '')
                }
                ai_response = get_ai_response(text, user_context)
                send_message(chat_id, ai_response)
            except Exception as e:
                logger.error(f"AI error: {e}")
                send_message(chat_id, "Не зовсім зрозумів. Спробуйте /menu або /help")
        else:
            send_message(chat_id, "Використовуйте кнопки меню або команду /help")
    except Exception as e:
        logger.error(f"❌ Error in handle_text_message: {e}", exc_info=True)


def show_menu_with_cart_buttons(chat_id):
    try:
        if not is_sheets_connected():
            send_message(chat_id, "❌ Меню тимчасово недоступне")
            return
        menu = get_menu_from_sheet()
        if not menu:
            send_message(chat_id, "⚠️ Меню порожнє")
            return
        buttons = []
        for idx, item in enumerate(menu[:10]):
            name = item.get("Страви", "Без назви")
            price = item.get("Ціна", "—")
            buttons.append([{
                "text": f"{name} – {price} грн 🛒",
                "callback_data": f"add_{idx}"
            }])
        keyboard = {"inline_keyboard": buttons}
        send_message(chat_id, "📖 Оберіть страву:", keyboard)
    except Exception as e:
        logger.error(f"❌ Error in show_menu_with_cart_buttons: {e}")
        send_message(chat_id, "Помилка показу меню")


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
                name = item.get("Страви", "Без назви")
                price = item.get("Ціна", "—")

                if chat_id not in user_carts:
                    user_carts[chat_id] = []
                user_carts[chat_id].append(item)

                send_message(chat_id, f"🛒 Додано: {name} ({price} грн)\n\n"
                                      f"Переглянути кошик: /cart")

        answer_callback(callback_id, "✅ Прийнято")
    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)


# ============= HELPERS =============

def send_message(chat_id, text, reply_markup=None):
    import requests
    try:
        bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("No BOT_TOKEN")
            return None
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
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
    import requests
    try:
        bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
        payload = {"callback_query_id": callback_id, "text": text}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"❌ Answer callback error: {e}")


# Обробка помилок
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# Запуск додатку
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
