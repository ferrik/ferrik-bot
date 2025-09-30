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

# Імпорт конфігурації
try:
    from config import BOT_TOKEN, WEBHOOK_URL, OPERATOR_CHAT_ID
    logger.info("✅ Config imported successfully")
except Exception as e:
    logger.error(f"❌ Config import error: {e}")
    BOT_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com/webhook')
    OPERATOR_CHAT_ID = os.getenv('OPERATOR_CHAT_ID', '')

# Імпорт сервісів
try:
    from services.sheets import init_gspread_client, get_menu_from_sheet, is_sheets_connected
    logger.info("✅ Sheets service imported")
except Exception as e:
    logger.error(f"❌ Sheets import error: {e}")
    init_gspread_client = lambda: False
    get_menu_from_sheet = lambda: []
    is_sheets_connected = lambda: False

try:
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    logger.info("✅ Gemini service imported")
except Exception as e:
    logger.error(f"❌ Gemini import error: {e}")
    init_gemini_client = lambda: False
    get_ai_response = lambda x, y=None: "AI тимчасово недоступний"
    is_gemini_connected = lambda: False

# Імпорт функцій відправки повідомлень
try:
    from services.telegram import send_message as tg_send_message
    logger.info("✅ Telegram service imported")
except Exception as e:
    logger.error(f"❌ Telegram service import error: {e}")
    # Fallback функція
    import requests
    import json
    
    def tg_send_message(chat_id, text, keyboard=None, parse_mode="HTML"):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            if keyboard:
                payload["reply_markup"] = json.dumps(keyboard)
            
            response = requests.post(url, data=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"✅ Message sent to {chat_id}")
                return response.json()
            else:
                logger.error(f"❌ Failed to send: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Send message error: {e}")
            return None

# Глобальні змінні
menu_cache = []
services_initialized = False


def init_services():
    """Ініціалізація всіх сервісів"""
    global services_initialized, menu_cache
    
    logger.info("=" * 60)
    logger.info("🚀 FerrikFootBot starting initialization...")
    logger.info("=" * 60)
    
    try:
        # Google Sheets
        sheets_ok = init_gspread_client()
        if sheets_ok:
            logger.info("✅ Google Sheets підключено")
            # Завантажуємо меню
            try:
                menu_cache = get_menu_from_sheet()
                logger.info(f"✅ Меню завантажено: {len(menu_cache)} позицій")
            except Exception as e:
                logger.warning(f"⚠️ Не вдалося завантажити меню: {e}")
        else:
            logger.warning("⚠️ Google Sheets не підключено")
        
        # Gemini AI
        gemini_ok = init_gemini_client()
        if gemini_ok:
            logger.info("✅ Gemini AI підключено")
        else:
            logger.warning("⚠️ Gemini AI не підключено")
        
        services_initialized = True
        logger.info("=" * 60)
        logger.info("🎉 FerrikFootBot ініціалізовано!")
        logger.info(f"   - Sheets: {'✅' if sheets_ok else '❌'}")
        logger.info(f"   - Gemini: {'✅' if gemini_ok else '❌'}")
        logger.info(f"   - Меню: {len(menu_cache)} позицій")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації: {e}", exc_info=True)
        services_initialized = False


# Ініціалізація при старті
init_services()


# ============= ROUTES =============

@app.route('/')
def home():
    """Головна сторінка"""
    return jsonify({
        "status": "running",
        "bot": "FerrikFootBot",
        "version": "2.0",
        "services": {
            "google_sheets": is_sheets_connected(),
            "gemini_ai": is_gemini_connected(),
            "menu_items": len(menu_cache)
        },
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/health')
def health():
    """Health check"""
    sheets_ok = is_sheets_connected()
    gemini_ok = is_gemini_connected()
    
    return jsonify({
        "status": "healthy" if services_initialized else "degraded",
        "services": {
            "sheets": sheets_ok,
            "gemini": gemini_ok,
            "menu_cached": len(menu_cache) > 0
        }
    }), 200


@app.route('/keep-alive')
def keep_alive():
    """Keep-alive endpoint"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": "service is running"
    }), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook від Telegram"""
    try:
        update = request.get_json()
        
        if not update:
            logger.warning("⚠️ Порожній update")
            return jsonify({"ok": True}), 200
        
        logger.info(f"📨 Received update: {update.get('update_id', 'unknown')}")
        
        # Обробка повідомлень
        if 'message' in update:
            handle_message(update['message'])
        elif 'callback_query' in update:
            handle_callback_query(update['callback_query'])
        else:
            logger.warning(f"⚠️ Невідомий тип update: {list(update.keys())}")
        
        return jsonify({"ok": True}), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


# ============= MESSAGE HANDLERS =============

def handle_message(message):
    """Обробка вхідних повідомлень"""
    try:
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        user = message.get('from', {})
        username = user.get('first_name', 'Користувач')
        
        logger.info(f"👤 Message from {username} ({chat_id}): {text}")
        
        # Обробка команд
        if text.startswith('/'):
            handle_command(chat_id, text, user)
        else:
            # Звичайні повідомлення
            handle_text_message(chat_id, text, user)
            
    except Exception as e:
        logger.error(f"❌ Message handling error: {e}", exc_info=True)


def handle_command(chat_id, command, user):
    """Обробка команд"""
    try:
        cmd = command.split()[0].lower()
        username = user.get('first_name', 'Користувач')
        
        if cmd == '/start':
            welcome_text = f"""👋 <b>Вітаю, {username}!</b>

Я <b>FerrikFootBot</b> - ваш помічник у замовленні їжі! 🍕

<b>Що я вмію:</b>
🍔 Показати меню
📝 Прийняти замовлення
💬 Відповісти на ваші запитання
🤖 Допомогти з вибором страв через AI

<b>Доступні команди:</b>
/menu - Переглянути меню
/help - Допомога

Просто напишіть мені, що вас цікавить! 😊"""
            
            keyboard = {
                "keyboard": [
                    [{"text": "🍕 Меню"}, {"text": "📝 Замовити"}],
                    [{"text": "ℹ️ Допомога"}]
                ],
                "resize_keyboard": True
            }
            
            tg_send_message(chat_id, welcome_text, keyboard)
            
        elif cmd == '/help':
            help_text = """<b>📖 Довідка FerrikFootBot</b>

<b>Команди:</b>
/start - Почати роботу
/menu - Переглянути меню
/help - Ця довідка

<b>Як замовити:</b>
1️⃣ Натисніть /menu
2️⃣ Виберіть страву
3️⃣ Оформіть замовлення

<b>AI Асистент:</b>
Напишіть що хочете - я допоможу! 🤖"""
            
            tg_send_message(chat_id, help_text)
            
        elif cmd == '/menu':
            show_menu(chat_id)
            
        else:
            tg_send_message(chat_id, f"❓ Невідома команда: {cmd}\nВикористайте /help")
            
    except Exception as e:
        logger.error(f"❌ Command error: {e}", exc_info=True)
        tg_send_message(chat_id, "⚠️ Помилка обробки команди")


def handle_text_message(chat_id, text, user):
    """Обробка звичайних текстових повідомлень"""
    try:
        username = user.get('first_name', 'Користувач')
        
        # Обробка кнопок
        if text in ['🍕 Меню', 'Меню']:
            show_menu(chat_id)
            return
        
        if text in ['📝 Замовити', 'Замовити']:
            tg_send_message(chat_id, "Для замовлення перегляньте меню: /menu")
            return
        
        if text in ['ℹ️ Допомога', 'Допомога']:
            handle_command(chat_id, '/help', user)
            return
        
        # Пошук в меню
        if any(word in text.lower() for word in ['піца', 'паста', 'салат', 'напій']):
            search_in_menu(chat_id, text)
            return
        
        # Використовуємо AI
        if is_gemini_connected():
            user_context = {
                'first_name': username,
                'username': user.get('username', ''),
                'user_id': user.get('id', '')
            }
            
            response = get_ai_response(text, user_context)
            tg_send_message(chat_id, response)
        else:
            tg_send_message(chat_id, "Використовуйте кнопки меню або команду /help")
            
    except Exception as e:
        logger.error(f"❌ Text message error: {e}", exc_info=True)
        tg_send_message(chat_id, "⚠️ Виникла помилка")


def show_menu(chat_id):
    """Показує меню"""
    global menu_cache
    
    try:
        # Перезавантажуємо якщо пусто
        if not menu_cache:
            menu_cache = get_menu_from_sheet()
        
        if not menu_cache:
            tg_send_message(chat_id, "❌ Меню тимчасово недоступне")
            return
        
        # Групуємо по категоріях
        categories = {}
        for item in menu_cache:
            cat = item.get('Категорія', 'Інше')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        # Формуємо текст
        menu_text = "<b>🍽️ Наше меню:</b>\n\n"
        
        for category, items in categories.items():
            menu_text += f"<b>{category}:</b>\n"
            for item in items[:5]:  # Макс 5 на категорію
                menu_text += f"• {item.get('Страви')} - {item.get('Ціна')} грн\n"
                if item.get('Опис'):
                    menu_text += f"  <i>{item.get('Опис')[:50]}...</i>\n"
            menu_text += "\n"
        
        tg_send_message(chat_id, menu_text)
        
    except Exception as e:
        logger.error(f"❌ Show menu error: {e}", exc_info=True)
        tg_send_message(chat_id, "⚠️ Помилка завантаження меню")


def search_in_menu(chat_id, query):
    """Пошук в меню"""
    try:
        query_lower = query.lower()
        results = []
        
        for item in menu_cache:
            name = item.get('Страви', '').lower()
            desc = item.get('Опис', '').lower()
            
            if query_lower in name or query_lower in desc:
                results.append(item)
        
        if results:
            text = f"🔍 <b>Знайдено за запитом '{query}':</b>\n\n"
            for item in results[:5]:
                text += f"<b>{item.get('Страви')}</b>\n"
                text += f"💰 {item.get('Ціна')} грн\n"
                if item.get('Опис'):
                    text += f"📝 {item.get('Опис')}\n"
                text += "\n"
            
            tg_send_message(chat_id, text)
        else:
            tg_send_message(chat_id, f"❌ Нічого не знайдено за запитом '{query}'")
            
    except Exception as e:
        logger.error(f"❌ Search error: {e}")


def handle_callback_query(callback_query):
    """Обробка callback запитів"""
    try:
        chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
        data = callback_query.get('data')
        callback_id = callback_query.get('id')
        
        logger.info(f"🔘 Callback: {data}")
        
        # Тут буде логіка обробки кнопок
        
        # Відповідь на callback
        answer_callback(callback_id, "✅ Прийнято")
        
    except Exception as e:
        logger.error(f"❌ Callback error: {e}")


def answer_callback(callback_id, text):
    """Відповідає на callback query"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
        requests.post(url, json={"callback_query_id": callback_id, "text": text}, timeout=5)
    except Exception as e:
        logger.error(f"❌ Answer callback error: {e}")


# ============= ERROR HANDLERS =============

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ============= MAIN =============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting FerrikFootBot on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
