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
    from services.sheets import init_gspread_client, get_menu_from_sheet, is_sheets_connected
    logger.info("✅ Sheets service imported")
except Exception as e:
    logger.error(f"❌ Sheets import error: {e}")

try:
    from services.gemini import init_gemini_client, is_gemini_connected
    logger.info("✅ Gemini service imported")
except Exception as e:
    logger.error(f"❌ Gemini import error: {e}")

try:
    from models.user import init_user_db, create_user, update_user_activity
    logger.info("✅ User model imported")
except Exception as e:
    logger.error(f"❌ User model import error: {e}")

try:
    from handlers.menu import show_menu_with_cart_buttons, show_categories
    from handlers.callbacks import handle_callback_query
    from handlers.cart import show_cart
    logger.info("✅ Handlers imported")
except Exception as e:
    logger.error(f"❌ Handlers import error: {e}")


# Ініціалізація сервісів
def init_services():
    """Ініціалізує всі сервіси бота"""
    logger.info("🔧 Initializing services...")
    
    # База даних
    try:
        init_user_db()
        logger.info("✅ User database initialized")
    except Exception as e:
        logger.error(f"❌ User DB error: {e}")
    
    # Google Sheets
    sheets_ok = False
    try:
        sheets_ok = init_gspread_client()
        if sheets_ok:
            logger.info("✅ Google Sheets connected")
        else:
            logger.warning("⚠️ Google Sheets connection failed")
    except Exception as e:
        logger.error(f"❌ Sheets error: {e}")
    
    # Gemini AI
    gemini_ok = False
    try:
        gemini_ok = init_gemini_client()
        if gemini_ok:
            logger.info("✅ Gemini AI connected")
        else:
            logger.warning("⚠️ Gemini AI connection failed")
    except Exception as e:
        logger.error(f"❌ Gemini error: {e}")
    
    logger.info("🎉 FerrikFootBot initialization completed!")
    return sheets_ok, gemini_ok


# Ініціалізуємо при старті
init_services()


# ============= ROUTES =============

@app.route('/')
def home():
    """Головна сторінка"""
    try:
        menu_count = len(get_menu_from_sheet()) if is_sheets_connected() else 0
    except:
        menu_count = 0
    
    return jsonify({
        "status": "running",
        "bot": "FerrikFootBot",
        "version": "2.1",
        "features": ["menu", "cart", "ai_recommendations", "quick_order"],
        "services": {
            "google_sheets": is_sheets_connected(),
            "gemini_ai": is_gemini_connected()
        },
        "menu_items": menu_count,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/health')
def health():
    """Health check"""
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
    """Keep-alive endpoint"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробник webhook від Telegram"""
    try:
        update = request.get_json()
        
        if not update:
            logger.warning("⚠️ Empty update")
            return jsonify({"ok": True}), 200
        
        logger.info(f"📨 Update {update.get('update_id', 'unknown')}")
        
        # Обробка повідомлень
        if 'message' in update:
            handle_message(update['message'])
        
        # Обробка callback'ів
        elif 'callback_query' in update:
            handle_callback_query(update)
        
        else:
            logger.warning(f"⚠️ Unknown update type")
        
        return jsonify({"ok": True}), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


def handle_message(message):
    """Обробляє вхідне повідомлення"""
    try:
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        user = message.get('from', {})
        
        if not chat_id:
            return
        
        user_id = user.get('id')
        username = user.get('first_name', 'User')
        
        logger.info(f"👤 {username} ({chat_id}): {text}")
        
        # Оновлюємо активність
        try:
            create_user(user_id, user.get('username'), username)
            update_user_activity(user_id)
        except:
            pass
        
        # Обробка команд
        if text.startswith('/'):
            handle_command(chat_id, text, user)
        
        # Обробка кнопок
        elif text in ['📖 Меню', '🍕 Меню', 'Меню']:
            show_menu_with_cart_buttons(chat_id)
        
        elif text in ['📂 Категорії', 'Категорії']:
            show_categories(chat_id)
        
        elif text in ['🛒 Корзина', '🛒 Кошик', 'Корзина', 'Кошик']:
            show_cart(chat_id)
        
        # Інші повідомлення
        else:
            handle_text_message(chat_id, text, user)
            
    except Exception as e:
        logger.error(f"❌ Message error: {e}", exc_info=True)


def handle_command(chat_id, command, user):
    """Обробляє команди"""
    try:
        cmd = command.split()[0].lower()
        username = user.get('first_name', 'друже')
        
        if cmd == '/start':
            welcome = f"""👋 <b>Вітаю, {username}!</b>

Я <b>FerrikFootBot</b> - ваш помічник для замовлення їжі в Тернополі!

<b>Що я вмію:</b>
🍕 Показати меню з фото
🛒 Швидке додавання в кошик
💬 AI-рекомендації страв
📦 Оформлення замовлення

Натисніть кнопку нижче щоб почати! 👇"""
            
            keyboard = {
                "keyboard": [
                    [{"text": "📖 Меню"}, {"text": "📂 Категорії"}],
                    [{"text": "🛒 Кошик"}, {"text": "ℹ️ Допомога"}]
                ],
                "resize_keyboard": True
            }
            
            send_message(chat_id, welcome, keyboard)
            
        elif cmd == '/menu':
            show_menu_with_cart_buttons(chat_id)
            
        elif cmd == '/help':
            help_text = """<b>📖 Довідка FerrikFootBot</b>

<b>Команди:</b>
/start - Почати роботу
/menu - Переглянути меню
/help - Ця довідка

<b>Як замовити:</b>
1️⃣ Натисніть "📖 Меню"
2️⃣ Оберіть страву
3️⃣ Натисніть "➕ Додати в кошик"
4️⃣ Оформіть замовлення

<b>Швидке додавання:</b>
• Кнопка "➕" - додає 1 шт
• Кнопка "➖ 1 ➕" - вибір кількості
• В кошику можна змінити кількість

Питання? Пишіть нам! 😊"""
            send_message(chat_id, help_text)
            
        else:
            send_message(chat_id, f"Невідома команда. Використайте /help")
            
    except Exception as e:
        logger.error(f"❌ Command error: {e}", exc_info=True)


def handle_text_message(chat_id, text, user):
    """Обробляє текстові повідомлення"""
    try:
        from services.sheets import search_menu_items
        
        # Пошук страв
        results = search_menu_items(text)
        
        if results:
            send_message(chat_id, f"🔍 Знайдено {len(results)} страв. Показую меню...")
            
            # Показуємо знайдені страви
            from handlers.menu import send_menu_item_with_button
            for item in results[:5]:
                send_menu_item_with_button(chat_id, item)
        else:
            # AI відповідь якщо нічого не знайдено
            if is_gemini_connected():
                try:
                    from services.gemini import get_ai_response
                    menu = get_menu_from_sheet()
                    
                    context = "Доступні страви: " + ", ".join([
                        item.get('Страви', '') for item in menu[:10]
                    ])
                    
                    prompt = f"{context}\n\nКористувач: {text}\n\nДай коротку відповідь українською."
                    
                    response = get_ai_response(prompt, {
                        'first_name': user.get('first_name', '')
                    })
                    
                    send_message(chat_id, response)
                except Exception as e:
                    logger.error(f"AI error: {e}")
                    send_message(chat_id, "Використовуйте кнопки меню для навігації")
            else:
                send_message(chat_id, "Нічого не знайдено. Спробуйте /menu")
            
    except Exception as e:
        logger.error(f"❌ Text message error: {e}", exc_info=True)


def send_message(chat_id, text, reply_markup=None):
    """Відправляє повідомлення"""
    import requests
    
    try:
        bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
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
        logger.error(f"❌ Send error: {e}")
        return None


# Обробка помилок
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# Запуск
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
