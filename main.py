import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('hubsy')

# Ініціалізація Flask
app = Flask(__name__)

# Імпорти
logger.info("🚀 Starting Hubsy Bot...")

try:
    from config import (
        BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID, 
        WEBHOOK_SECRET, validate_config, log_config
    )
    logger.info("✅ Config imported successfully")
except Exception as e:
    logger.error(f"❌ Config import error: {e}")
    BOT_TOKEN = None
    WEBHOOK_SECRET = "Ferrik123"

try:
    from services.sheets import (
        init_gspread_client, get_menu_from_sheet, 
        save_order_to_sheets, is_sheets_connected, search_menu_items
    )
    logger.info("✅ Sheets service imported")
except Exception as e:
    logger.error(f"❌ Sheets import error: {e}")

try:
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    logger.info("✅ Gemini service imported")
except Exception as e:
    logger.error(f"❌ Gemini import error: {e}")

try:
    from services.telegram import tg_send_message, tg_answer_callback, tg_set_webhook
    logger.info("✅ Telegram service imported")
except Exception as e:
    logger.error(f"❌ Telegram service import error: {e}")

# Глобальні змінні
menu_cache = []
user_carts = defaultdict(list)  # {chat_id: [items]}
user_states = {}  # {chat_id: 'state'}

# Ініціалізація сервісів
def init_services():
    global menu_cache
    logger.info("🛠️ Initializing Hubsy services...")
    
    try:
        log_config()
        validate_config()
    except: pass
    
    # Завантаження меню
    try:
        menu_cache = get_menu_from_sheet()
        logger.info(f"✅ Menu cached: {len(menu_cache)} items")
    except Exception as e:
        logger.error(f"❌ Menu loading error: {e}")
    
    # Ініціалізація AI
    try:
        init_gemini_client()
        logger.info("✅ Gemini initialized")
    except Exception as e:
        logger.error(f"❌ Gemini error: {e}")
    
    # Встановлення webhook
    try:
        from config import RENDER_URL
        result = tg_set_webhook(RENDER_URL)
        if result and result.get('ok'):
            logger.info("✅ Webhook set successfully")
    except Exception as e:
        logger.error(f"❌ Webhook setup error: {e}")

# Функція відправки
def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    try:
        return tg_send_message(chat_id, text, reply_markup, parse_mode)
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def answer_callback(callback_id, text="", show_alert=False):
    try:
        return tg_answer_callback(callback_id, text, show_alert)
    except Exception as e:
        logger.error(f"Callback answer error: {e}")

# Утиліти для меню
def get_categories():
    """Отримати унікальні категорії з меню"""
    categories = set()
    for item in menu_cache:
        cat = item.get("Категорія", "Інше")
        if cat:
            categories.add(cat)
    return sorted(list(categories))

def get_items_by_category(category):
    """Отримати страви за категорією"""
    return [item for item in menu_cache if item.get("Категорія") == category]

def format_item(item, show_full=False):
    """Форматування страви"""
    name = item.get("Назва Страви", "Без назви")
    price = item.get("Ціна", "?")
    
    if show_full:
        desc = item.get("Опис", "")
        weight = item.get("Вага", "")
        text = f"<b>{name}</b>\n"
        if desc:
            text += f"{desc}\n"
        if weight:
            text += f"⚖️ {weight}\n"
        text += f"💰 <b>{price} грн</b>"
        return text
    else:
        return f"{name} - {price} грн"

# Обробники команд
def handle_start(chat_id):
    """Головне меню"""
    text = (
        "👋 Вітаємо в <b>Hubsy</b>!\n\n"
        "🍕 Ваш помічник для швидкого замовлення смачної їжі.\n\n"
        "Оберіть дію:"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📖 Меню", "callback_data": "show_categories"}],
            [
                {"text": "🔍 Пошук", "callback_data": "search_mode"},
                {"text": "🛒 Корзина", "callback_data": "show_cart"}
            ],
            [
                {"text": "✨ AI-Порада", "callback_data": "ai_recommend"},
                {"text": "📞 Контакти", "callback_data": "contacts"}
            ]
        ]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def show_categories(chat_id):
    """Показати категорії меню"""
    categories = get_categories()
    
    if not categories:
        send_message(chat_id, "❌ Меню тимчасово недоступне")
        return
    
    text = "📖 <b>Оберіть категорію:</b>"
    
    keyboard = {"inline_keyboard": []}
    
    # Емодзі для категорій
    category_emoji = {
        "Піца": "🍕",
        "Бургери": "🍔",
        "Суші": "🍣",
        "Салати": "🥗",
        "Напої": "🥤",
        "Десерти": "🍰"
    }
    
    for cat in categories:
        emoji = category_emoji.get(cat, "🍽️")
        keyboard["inline_keyboard"].append([
            {"text": f"{emoji} {cat}", "callback_data": f"cat_{cat}"}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔙 Назад", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)

def show_category_items(chat_id, category):
    """Показати страви категорії"""
    items = get_items_by_category(category)
    
    if not items:
        send_message(chat_id, f"В категорії <b>{category}</b> поки немає страв")
        return
    
    text = f"📋 <b>{category}</b>\n\n"
    
    keyboard = {"inline_keyboard": []}
    
    for i, item in enumerate(items[:10]):  # Максимум 10 страв
        item_text = format_item(item)
        text += f"{i+1}. {item_text}\n"
        
        item_id = item.get("ID") or item.get("Назва Страви", "")
        keyboard["inline_keyboard"].append([
            {"text": f"➕ {item.get('Назва Страви', '')[:20]}", "callback_data": f"add_{item_id}"}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔙 Категорії", "callback_data": "show_categories"},
        {"text": "🏠 Головна", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)

def add_to_cart(chat_id, item_id):
    """Додати страву в корзину"""
    # Знайти страву
    item = None
    for menu_item in menu_cache:
        if str(menu_item.get("ID", "")) == str(item_id) or menu_item.get("Назва Страви") == item_id:
            item = menu_item
            break
    
    if not item:
        return "❌ Страву не знайдено"
    
    user_carts[chat_id].append(item)
    name = item.get("Назва Страви", "Страва")
    return f"✅ <b>{name}</b> додано в корзину!"

def show_cart(chat_id):
    """Показати корзину"""
    cart = user_carts.get(chat_id, [])
    
    if not cart:
        text = "🛒 Ваша корзина порожня\n\nПерегляньте меню та додайте страви!"
        keyboard = {
            "inline_keyboard": [[
                {"text": "📖 Меню", "callback_data": "show_categories"}
            ]]
        }
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    # Підрахунок
    total = 0
    items_count = defaultdict(int)
    
    for item in cart:
        name = item.get("Назва Страви", "")
        items_count[name] += 1
        try:
            price = float(str(item.get("Ціна", 0)).replace(",", "."))
            total += price
        except:
            pass
    
    text = "🛒 <b>Ваше замовлення:</b>\n\n"
    
    for name, count in items_count.items():
        text += f"• {name} x{count}\n"
    
    text += f"\n💰 <b>Сума: {total:.2f} грн</b>"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Оформити замовлення", "callback_data": "checkout"}],
            [{"text": "🗑️ Очистити корзину", "callback_data": "clear_cart"}],
            [{"text": "➕ Додати ще", "callback_data": "show_categories"}],
            [{"text": "🔙 Назад", "callback_data": "start"}]
        ]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def clear_cart(chat_id):
    """Очистити корзину"""
    user_carts[chat_id] = []
    return "🗑️ Корзину очищено"

def checkout(chat_id):
    """Оформлення замовлення"""
    cart = user_carts.get(chat_id, [])
    
    if not cart:
        return "❌ Корзина порожня"
    
    try:
        # Зберігаємо замовлення
        save_order_to_sheets(chat_id, cart)
        
        # Очищаємо корзину
        user_carts[chat_id] = []
        
        text = (
            "✅ <b>Замовлення прийнято!</b>\n\n"
            "📞 Наш менеджер зв'яжеться з вами найближчим часом.\n\n"
            "Дякуємо що обрали Hubsy! 💙"
        )
        
        keyboard = {
            "inline_keyboard": [[
                {"text": "🏠 Головна", "callback_data": "start"}
            ]]
        }
        
        send_message(chat_id, text, reply_markup=keyboard)
        return None
        
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        return "❌ Помилка оформлення. Спробуйте пізніше."

def ai_recommend(chat_id):
    """AI рекомендації"""
    if not is_gemini_connected():
        text = "❌ AI-помічник тимчасово недоступний"
        keyboard = {
            "inline_keyboard": [[
                {"text": "🔙 Назад", "callback_data": "start"}
            ]]
        }
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    try:
        # Формуємо контекст для AI
        categories = get_categories()
        prompt = f"""Ти - помічник ресторану Hubsy. Порекомендуй 2-3 страви користувачу.

Доступні категорії: {', '.join(categories)}

Дай коротку (2-3 речення) персональну рекомендацію в дружньому стилі."""

        recommendation = get_ai_response(prompt)
        
        text = f"✨ <b>AI-Рекомендація:</b>\n\n{recommendation}"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📖 Переглянути меню", "callback_data": "show_categories"}],
                [{"text": "🔄 Інша порада", "callback_data": "ai_recommend"}],
                [{"text": "🔙 Назад", "callback_data": "start"}]
            ]
        }
        
        send_message(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"AI recommend error: {e}")
        send_message(chat_id, "❌ Помилка AI. Спробуйте пізніше.")

def show_contacts(chat_id):
    """Контакти"""
    text = """
📞 <b>Контакти Hubsy</b>

📱 Телефон: +380 XX XXX XX XX
📧 Email: hello@hubsy.com
📍 Адреса: м. Київ, вул. Смачна, 1

🕐 Працюємо: щодня 9:00-23:00

🚗 Доставка: 30-40 хвилин
💳 Оплата: готівка, картка
"""
    
    keyboard = {
        "inline_keyboard": [[
            {"text": "🔙 Назад", "callback_data": "start"}
        ]]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def search_mode(chat_id):
    """Режим пошуку"""
    user_states[chat_id] = 'searching'
    text = "🔍 <b>Пошук страв</b>\n\nНапишіть назву або частину назви страви:"
    
    keyboard = {
        "inline_keyboard": [[
            {"text": "❌ Скасувати", "callback_data": "start"}
        ]]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def process_search(chat_id, query):
    """Обробка пошуку"""
    results = search_menu_items(query)
    
    if not results:
        text = f"❌ Нічого не знайдено за запитом '<b>{query}</b>'\n\nСпробуйте інший запит:"
        keyboard = {
            "inline_keyboard": [[
                {"text": "📖 Переглянути все меню", "callback_data": "show_categories"}
            ]]
        }
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    text = f"🔍 Результати пошуку '<b>{query}</b>':\n\n"
    keyboard = {"inline_keyboard": []}
    
    for item in results[:10]:
        item_text = format_item(item)
        text += f"• {item_text}\n"
        
        item_id = item.get("ID") or item.get("Назва Страви", "")
        keyboard["inline_keyboard"].append([
            {"text": f"➕ {item.get('Назва Страви', '')[:25]}", "callback_data": f"add_{item_id}"}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔍 Новий пошук", "callback_data": "search_mode"},
        {"text": "🏠 Головна", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)
    user_states[chat_id] = None

# Обробка callback
def process_callback_query(callback_query):
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        callback_id = callback_query["id"]
        data = callback_query["data"]
        
        answer_callback(callback_id, "⏳")
        
        if data == "start":
            handle_start(chat_id)
        elif data == "show_categories":
            show_categories(chat_id)
        elif data.startswith("cat_"):
            category = data[4:]
            show_category_items(chat_id, category)
        elif data.startswith("add_"):
            item_id = data[4:]
            msg = add_to_cart(chat_id, item_id)
            answer_callback(callback_id, msg, show_alert=True)
        elif data == "show_cart":
            show_cart(chat_id)
        elif data == "clear_cart":
            msg = clear_cart(chat_id)
            answer_callback(callback_id, msg, show_alert=True)
            show_cart(chat_id)
        elif data == "checkout":
            msg = checkout(chat_id)
            if msg:
                answer_callback(callback_id, msg, show_alert=True)
        elif data == "ai_recommend":
            ai_recommend(chat_id)
        elif data == "contacts":
            show_contacts(chat_id)
        elif data == "search_mode":
            search_mode(chat_id)
        else:
            send_message(chat_id, f"Обрано: {data}")
            
    except Exception as e:
        logger.error(f"Callback error: {e}")

# Обробка повідомлень
def process_message(message):
    try:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        
        # Перевірка режиму пошуку
        if user_states.get(chat_id) == 'searching':
            process_search(chat_id, text)
            return
        
        # Команди
        if text == "/start":
            handle_start(chat_id)
        elif text == "/menu":
            show_categories(chat_id)
        elif text == "/cart":
            show_cart(chat_id)
        elif text == "/help":
            handle_start(chat_id)
        else:
            # AI-відповідь на текст
            if is_gemini_connected():
                try:
                    prompt = f"Користувач написав: {text}\n\nДай коротку дружню відповідь від імені ресторану Hubsy."
                    response = get_ai_response(prompt)
                    send_message(chat_id, response)
                except:
                    send_message(chat_id, "Спробуйте /start для перегляду меню")
            else:
                send_message(chat_id, "Спробуйте /start для перегляду меню")
                
    except Exception as e:
        logger.error(f"Message error: {e}")

# Flask routes
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'status': 'ok',
        'bot': 'Hubsy',
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/test-menu', methods=['GET'])
def test_menu():
    """Тестовий endpoint для перевірки меню"""
    try:
        # Перевірка підключення
        is_connected = is_sheets_connected()
        
        # Спроба завантажити меню
        menu = get_menu_from_sheet()
        
        return jsonify({
            'sheets_connected': is_connected,
            'menu_items_count': len(menu),
            'menu_cached': len(menu_cache),
            'sample_items': menu[:3] if menu else [],
            'spreadsheet_id': os.environ.get('GOOGLE_SHEET_ID') or os.environ.get('SPREADSHEET_ID'),
            'has_credentials': bool(os.environ.get('GOOGLE_CREDENTIALS_JSON'))
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/<path:secret>', methods=['POST'])
def webhook(secret):
    if secret != WEBHOOK_SECRET:
        logger.warning(f"Invalid webhook path: {secret}")
        return jsonify({'status': 'unauthorized'}), 401
    
    try:
        update = request.get_json()
        if not update:
            return jsonify({'status': 'ok'})

        logger.info(f"Update: {update.get('update_id', 'unknown')}")

        if 'message' in update:
            process_message(update['message'])
        elif 'callback_query' in update:
            process_callback_query(update['callback_query'])
            
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        return jsonify({'status': 'error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# Ініціалізація
with app.app_context():
    init_services()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)