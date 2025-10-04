import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape as html_escape
from threading import RLock

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread-safe locks
carts_lock = RLock()
states_lock = RLock()

# Імпорти
logger.info("Starting Hubsy Bot...")

try:
    from config import (
        BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID, 
        WEBHOOK_SECRET, validate_config, log_config
    )
    
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN not set")
        raise RuntimeError("BOT_TOKEN is required")
    
    if not WEBHOOK_SECRET:
        logger.critical("WEBHOOK_SECRET not set")
        raise RuntimeError("WEBHOOK_SECRET must be set")
    
    logger.info("Config imported successfully")
    
except Exception as e:
    logger.exception("Config error")
    raise

try:
    from services.sheets import get_menu_from_sheet, save_order_to_sheets, search_menu_items
    logger.info("Sheets service imported")
except Exception as e:
    logger.exception("Sheets import error")
    raise

try:
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    logger.info("Gemini service imported")
except Exception as e:
    logger.exception("Gemini import error")
    raise

try:
    from services.telegram import tg_send_message, tg_answer_callback, tg_set_webhook
    logger.info("Telegram service imported")
except Exception as e:
    logger.exception("Telegram service import error")
    raise

# Глобальні змінні
menu_cache = []
user_carts = defaultdict(list)
user_states = {}

# Константи (адаптовані під вашу таблицю)
KEY_NAME = "Назва Страви"  # В sheets.py конвертується з "Страви"
KEY_PRICE = "Ціна"
KEY_CATEGORY = "Категорія"
KEY_DESCRIPTION = "Опис"
KEY_WEIGHT = "Вага"
KEY_ID = "ID"
KEY_RESTAURANT = "Ресторан"
KEY_RATING = "Рейтинг"

MAX_CALLBACK_LENGTH = 64

def safe_callback_data(prefix: str, value: str) -> str:
    """Безпечний callback_data"""
    safe_value = "".join(c for c in str(value) if c.isalnum() or c in "-_")
    callback = f"{prefix}_{safe_value}"
    return callback[:MAX_CALLBACK_LENGTH]

def parse_price(price_str) -> Decimal:
    """Парсинг ціни в Decimal"""
    try:
        clean_price = str(price_str).replace(",", ".").strip()
        return Decimal(clean_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as e:
        logger.warning(f"Failed to parse price '{price_str}': {e}")
        return Decimal('0.00')

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """Відправка повідомлення"""
    try:
        safe_text = text.replace("&", "&amp;")
        safe_text = safe_text.replace("<", "&lt;").replace(">", "&gt;")
        safe_text = safe_text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
        safe_text = safe_text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        
        result = tg_send_message(chat_id, safe_text, reply_markup, parse_mode)
        
        if not result or not result.get('ok'):
            logger.error(f"Send failed: {result}")
            raise RuntimeError("Failed to send message")
        
        return result
        
    except Exception as e:
        logger.exception(f"Send error for chat {chat_id}")
        raise

def answer_callback(callback_id, text="", show_alert=False):
    """Відповідь на callback"""
    try:
        return tg_answer_callback(callback_id, text, show_alert)
    except Exception as e:
        logger.exception(f"Callback answer error")
        return None

def init_services():
    """Ініціалізація сервісів"""
    global menu_cache
    
    logger.info("Initializing services...")
    
    try:
        log_config()
        validate_config()
    except Exception as e:
        logger.exception(f"Config error: {e}")
    
    try:
        menu_cache = get_menu_from_sheet()
        if menu_cache:
            logger.info(f"Menu cached: {len(menu_cache)} items")
        else:
            logger.warning("Menu is empty")
    except Exception as e:
        logger.exception(f"Menu loading error: {e}")
        menu_cache = []
    
    try:
        init_gemini_client()
        if is_gemini_connected():
            logger.info("Gemini initialized")
    except Exception as e:
        logger.exception(f"Gemini error: {e}")
    
    try:
        from config import RENDER_URL
        result = tg_set_webhook(RENDER_URL)
        if result and result.get('ok'):
            logger.info("Webhook set successfully")
        else:
            logger.error(f"Webhook failed: {result}")
    except Exception as e:
        logger.exception(f"Webhook error: {e}")

def get_categories():
    """Унікальні категорії"""
    categories = set()
    for item in menu_cache:
        cat = item.get(KEY_CATEGORY, "")
        if cat:
            categories.add(cat)
    return sorted(list(categories))

def get_items_by_category(category):
    """Страви за категорією"""
    return [item for item in menu_cache if item.get(KEY_CATEGORY) == category]

def format_item(item, show_full=False):
    """Форматування страви"""
    name = html_escape(item.get(KEY_NAME, "Без назви"))
    price = item.get(KEY_PRICE, "?")
    
    if show_full:
        desc = html_escape(item.get(KEY_DESCRIPTION, ""))
        restaurant = html_escape(item.get(KEY_RESTAURANT, ""))
        rating = item.get(KEY_RATING, "")
        
        text = f"<b>{name}</b>\n"
        if desc:
            text += f"{desc}\n"
        if restaurant:
            text += f"🏪 {restaurant}\n"
        if rating:
            text += f"⭐ {rating}\n"
        text += f"💰 <b>{price} грн</b>"
        return text
    else:
        return f"{name} - {price} грн"

def handle_start(chat_id):
    """Головне меню"""
    text = (
        "👋 Вітаємо в <b>Hubsy</b>!\n\n"
        "🍕 Ваш помічник для замовлення їжі.\n\n"
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
    """Показати категорії"""
    categories = get_categories()
    
    if not categories:
        send_message(chat_id, "❌ Меню тимчасово недоступне")
        return
    
    text = "📖 <b>Оберіть категорію:</b>"
    keyboard = {"inline_keyboard": []}
    
    category_emoji = {
        "Піца": "🍕", "Бургери": "🍔", "Суші": "🍣",
        "Салати": "🥗", "Напої": "🥤", "Десерти": "🍰"
    }
    
    for cat in categories:
        emoji = category_emoji.get(cat, "🍽️")
        safe_cat = safe_callback_data("cat", cat)
        keyboard["inline_keyboard"].append([
            {"text": f"{emoji} {cat}", "callback_data": safe_cat}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔙 Назад", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)

def show_category_items(chat_id, category):
    """Показати страви"""
    items = get_items_by_category(category)
    
    if not items:
        send_message(chat_id, f"В категорії <b>{html_escape(category)}</b> немає страв")
        return
    
    text = f"📋 <b>{html_escape(category)}</b>\n\n"
    keyboard = {"inline_keyboard": []}
    
    for i, item in enumerate(items[:10]):
        item_text = format_item(item)
        text += f"{i+1}. {item_text}\n"
        
        item_id = str(item.get(KEY_ID, item.get(KEY_NAME, "")))
        safe_id = safe_callback_data("add", item_id)
        
        keyboard["inline_keyboard"].append([
            {"text": f"➕ {item.get(KEY_NAME, '')[:20]}", "callback_data": safe_id}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔙 Категорії", "callback_data": "show_categories"},
        {"text": "🏠 Головна", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)

def add_to_cart(chat_id, item_id):
    """Додати в корзину"""
    item = None
    for menu_item in menu_cache:
        if str(menu_item.get(KEY_ID, "")) == str(item_id) or menu_item.get(KEY_NAME) == item_id:
            item = menu_item
            break
    
    if not item:
        return "❌ Страву не знайдено"
    
    with carts_lock:
        user_carts[chat_id].append(item)
    
    name = html_escape(item.get(KEY_NAME, "Страва"))
    return f"✅ <b>{name}</b> додано!"

def show_cart(chat_id):
    """Показати корзину"""
    with carts_lock:
        cart = list(user_carts.get(chat_id, []))
    
    if not cart:
        text = "🛒 Корзина порожня\n\nДодайте страви з меню!"
        keyboard = {
            "inline_keyboard": [[
                {"text": "📖 Меню", "callback_data": "show_categories"}
            ]]
        }
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    total = Decimal('0.00')
    items_count = defaultdict(int)
    
    for item in cart:
        name = item.get(KEY_NAME, "")
        items_count[name] += 1
        price = parse_price(item.get(KEY_PRICE, 0))
        total += price
    
    text = "🛒 <b>Ваше замовлення:</b>\n\n"
    
    for name, count in items_count.items():
        safe_name = html_escape(name)
        text += f"• {safe_name} x{count}\n"
    
    text += f"\n💰 <b>Сума: {total:.2f} грн</b>"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Оформити", "callback_data": "checkout"}],
            [{"text": "🗑️ Очистити", "callback_data": "clear_cart"}],
            [{"text": "➕ Додати ще", "callback_data": "show_categories"}],
            [{"text": "🔙 Назад", "callback_data": "start"}]
        ]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def clear_cart(chat_id):
    """Очистити корзину"""
    with carts_lock:
        user_carts[chat_id] = []
    return "🗑️ Корзину очищено"

def checkout(chat_id):
    """Оформлення"""
    with carts_lock:
        cart = list(user_carts.get(chat_id, []))
    
    if not cart:
        return "❌ Корзина порожня"
    
    try:
        save_order_to_sheets(chat_id, cart)
        
        with carts_lock:
            user_carts[chat_id] = []
        
        text = (
            "✅ <b>Замовлення прийнято!</b>\n\n"
            "📞 Менеджер зв'яжеться з вами.\n\n"
            "Дякуємо! 💙"
        )
        
        keyboard = {
            "inline_keyboard": [[
                {"text": "🏠 Головна", "callback_data": "start"}
            ]]
        }
        
        send_message(chat_id, text, reply_markup=keyboard)
        return None
        
    except Exception as e:
        logger.exception(f"Checkout error: {e}")
        return "❌ Помилка. Спробуйте пізніше."

def show_contacts(chat_id):
    """Контакти"""
    text = """
📞 <b>Контакти Hubsy</b>

📱 Телефон: +380 XX XXX XX XX
📧 Email: hello@hubsy.com
📍 м. Київ

🕐 Щодня 9:00-23:00
"""
    
    keyboard = {
        "inline_keyboard": [[
            {"text": "🔙 Назад", "callback_data": "start"}
        ]]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def ai_recommend(chat_id):
    """AI рекомендації"""
    if not is_gemini_connected():
        text = "❌ AI недоступний"
        keyboard = {
            "inline_keyboard": [[
                {"text": "🔙 Назад", "callback_data": "start"}
            ]]
        }
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    try:
        categories = get_categories()
        prompt = f"Ти помічник ресторану Hubsy. Порекомендуй 2-3 страви. Категорії: {', '.join(categories)}. Коротко 2-3 речення."
        
        recommendation = get_ai_response(prompt)
        
        text = f"✨ <b>AI-Рекомендація:</b>\n\n{recommendation}"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📖 Меню", "callback_data": "show_categories"}],
                [{"text": "🔄 Інша порада", "callback_data": "ai_recommend"}],
                [{"text": "🔙 Назад", "callback_data": "start"}]
            ]
        }
        
        send_message(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.exception(f"AI error: {e}")
        send_message(chat_id, "❌ Помилка AI")

def search_mode(chat_id):
    """Пошук"""
    with states_lock:
        user_states[chat_id] = 'searching'
    
    text = "🔍 <b>Пошук</b>\n\nНапишіть назву страви:"
    
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
        text = f"❌ Нічого не знайдено: '<b>{html_escape(query)}</b>'"
        keyboard = {
            "inline_keyboard": [[
                {"text": "📖 Все меню", "callback_data": "show_categories"}
            ]]
        }
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    text = f"🔍 Результати '<b>{html_escape(query)}</b>':\n\n"
    keyboard = {"inline_keyboard": []}
    
    for item in results[:10]:
        item_text = format_item(item)
        text += f"• {item_text}\n"
        
        item_id = str(item.get(KEY_ID, item.get(KEY_NAME, "")))
        safe_id = safe_callback_data("add", item_id)
        
        keyboard["inline_keyboard"].append([
            {"text": f"➕ {item.get(KEY_NAME, '')[:25]}", "callback_data": safe_id}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔍 Новий пошук", "callback_data": "search_mode"},
        {"text": "🏠 Головна", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)
    
    with states_lock:
        user_states[chat_id] = None

def process_callback_query(callback_query):
    """Обробка callback"""
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        callback_id = callback_query["id"]
        data = callback_query["data"]
        
        logger.info(f"Callback {data} from chat {chat_id}")
        
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
            logger.warning(f"Unknown callback: {data}")
            
    except KeyError as e:
        logger.exception(f"Callback structure error: {e}")
    except Exception as e:
        logger.exception(f"Callback error: {e}")

def process_message(message):
    """Обробка повідомлень"""
    try:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        
        logger.info(f"Message from chat {chat_id}")
        
        with states_lock:
            state = user_states.get(chat_id)
        
        if state == 'searching':
            process_search(chat_id, text)
            return
        
        if text == "/start":
            handle_start(chat_id)
        elif text == "/menu":
            show_categories(chat_id)
        elif text == "/cart":
            show_cart(chat_id)
        else:
            send_message(chat_id, "Спробуйте /start")
                
    except KeyError as e:
        logger.exception(f"Message structure error: {e}")
    except Exception as e:
        logger.exception(f"Message error: {e}")

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'menu_items': len(menu_cache),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Index"""
    return jsonify({
        'status': 'ok',
        'bot': 'Hubsy',
        'version': '2.0'
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook"""
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    
    if not header_secret or header_secret != WEBHOOK_SECRET:
        logger.warning(f"Unauthorized from {request.remote_addr}")
        return jsonify({'status': 'unauthorized'}), 401
    
    try:
        update = request.get_json(force=False)
        
        if not update:
            return jsonify({'status': 'ok'})
        
        logger.info(f"Update {update.get('update_id', '?')}")
        
        if 'message' in update:
            process_message(update['message'])
        elif 'callback_query' in update:
            process_callback_query(update['callback_query'])
        
        return jsonify({'status': 'ok'})
        
    except ValueError as e:
        logger.exception("Invalid JSON")
        return jsonify({'error': 'invalid json'}), 400
    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        return jsonify({'error': 'server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.exception("Internal error")
    return jsonify({"error": "Internal error"}), 500

with app.app_context():
    init_services()

if __name__ == "__main__":
    logger.warning("Use gunicorn for production")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)