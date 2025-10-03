import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape as html_escape
from threading import RLock
from tenacity import retry, stop_after_attempt, wait_exponential

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ініціалізація Flask
app = Flask(__name__)

# Thread-safe locks
carts_lock = RLock()
states_lock = RLock()

# Імпорти з обробкою помилок
logger.info("Starting Hubsy Bot...")

try:
    from config import (
        BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID, 
        WEBHOOK_SECRET, validate_config, log_config
    )
    
    # Критична перевірка конфігурації
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN not set")
        raise RuntimeError("BOT_TOKEN is required")
    
    if not WEBHOOK_SECRET or WEBHOOK_SECRET == 'Ferrik123':
        logger.critical("WEBHOOK_SECRET not set or using default")
        raise RuntimeError("WEBHOOK_SECRET must be set to secure value")
    
    logger.info("Config imported successfully")
    
except ImportError as e:
    logger.exception("Config import error")
    raise RuntimeError(f"Failed to import config: {e}")
except Exception as e:
    logger.exception("Config validation error")
    raise

try:
    from services.sheets import (
        init_gspread_client, get_menu_from_sheet, 
        save_order_to_sheets, is_sheets_connected, search_menu_items
    )
    logger.info("Sheets service imported")
except ImportError as e:
    logger.exception("Sheets import error")
    raise RuntimeError(f"Failed to import sheets service: {e}")

try:
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    logger.info("Gemini service imported")
except ImportError as e:
    logger.exception("Gemini import error")
    raise RuntimeError(f"Failed to import gemini service: {e}")

try:
    from services.telegram import tg_send_message, tg_answer_callback, tg_set_webhook
    logger.info("Telegram service imported")
except ImportError as e:
    logger.exception("Telegram service import error")
    raise RuntimeError(f"Failed to import telegram service: {e}")

# Глобальні змінні
menu_cache = []
user_carts = defaultdict(list)
user_states = {}

# Константи для ключів меню
KEY_NAME = "Назва Страви"
KEY_PRICE = "Ціна"
KEY_CATEGORY = "Категорія"
KEY_DESCRIPTION = "Опис"
KEY_WEIGHT = "Вага"
KEY_ID = "ID"

# Максимальна довжина callback_data
MAX_CALLBACK_LENGTH = 64

def safe_callback_data(prefix: str, value: str) -> str:
    """Створює безпечний callback_data обмеженої довжини"""
    # Видаляємо спецсимволи та обмежуємо довжину
    safe_value = "".join(c for c in str(value) if c.isalnum() or c in "-_")
    callback = f"{prefix}_{safe_value}"
    
    if len(callback) > MAX_CALLBACK_LENGTH:
        callback = callback[:MAX_CALLBACK_LENGTH]
    
    return callback

def parse_price(price_str) -> Decimal:
    """Безпечний парсинг ціни в Decimal"""
    try:
        clean_price = str(price_str).replace(",", ".").strip()
        return Decimal(clean_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as e:
        logger.warning(f"Failed to parse price '{price_str}': {e}")
        return Decimal('0.00')

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """Відправка повідомлення з retry та HTML escaping"""
    try:
        # HTML escaping для безпеки
        # Зберігаємо дозволені теги
        safe_text = text.replace("&", "&amp;")
        safe_text = safe_text.replace("<", "&lt;").replace(">", "&gt;")
        
        # Відновлюємо дозволені теги
        safe_text = safe_text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
        safe_text = safe_text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        safe_text = safe_text.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
        
        result = tg_send_message(chat_id, safe_text, reply_markup, parse_mode)
        
        if not result or not result.get('ok'):
            logger.error(f"Send message failed: {result}")
            raise RuntimeError("Failed to send message")
        
        return result
        
    except Exception as e:
        logger.exception(f"Send message error for chat {chat_id}")
        raise

def answer_callback(callback_id, text="", show_alert=False):
    """Відповідь на callback з обробкою помилок"""
    try:
        return tg_answer_callback(callback_id, text, show_alert)
    except Exception as e:
        logger.exception(f"Callback answer error: {e}")
        return None

def init_services():
    """Ініціалізація сервісів з proper error handling"""
    global menu_cache
    
    logger.info("Initializing Hubsy services...")
    
    try:
        log_config()
        if not validate_config():
            logger.error("Config validation failed")
    except Exception as e:
        logger.exception(f"Config logging error: {e}")
    
    # Завантаження меню
    try:
        menu_cache = get_menu_from_sheet()
        if not menu_cache:
            logger.warning("Menu is empty")
        else:
            logger.info(f"Menu cached: {len(menu_cache)} items")
    except Exception as e:
        logger.exception(f"Menu loading error: {e}")
        menu_cache = []
    
    # Ініціалізація AI
    try:
        init_gemini_client()
        if is_gemini_connected():
            logger.info("Gemini initialized")
        else:
            logger.warning("Gemini not connected")
    except Exception as e:
        logger.exception(f"Gemini initialization error: {e}")
    
    # Встановлення webhook
    try:
        from config import RENDER_URL
        result = tg_set_webhook(RENDER_URL)
        if result and result.get('ok'):
            logger.info("Webhook set successfully")
        else:
            logger.error(f"Webhook setup failed: {result}")
    except Exception as e:
        logger.exception(f"Webhook setup error: {e}")

def get_categories():
    """Отримати унікальні категорії"""
    categories = set()
    for item in menu_cache:
        cat = item.get(KEY_CATEGORY, "")
        if cat:
            categories.add(cat)
    return sorted(list(categories))

def get_items_by_category(category):
    """Отримати страви за категорією"""
    return [item for item in menu_cache if item.get(KEY_CATEGORY) == category]

def format_item(item, show_full=False):
    """Форматування страви з екрануванням"""
    name = html_escape(item.get(KEY_NAME, "Без назви"))
    price = item.get(KEY_PRICE, "?")
    
    if show_full:
        desc = html_escape(item.get(KEY_DESCRIPTION, ""))
        weight = html_escape(item.get(KEY_WEIGHT, ""))
        text = f"<b>{name}</b>\n"
        if desc:
            text += f"{desc}\n"
        if weight:
            text += f"⚖️ {weight}\n"
        text += f"💰 <b>{price} грн</b>"
        return text
    else:
        return f"{name} - {price} грн"

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
    """Показати страви категорії"""
    items = get_items_by_category(category)
    
    if not items:
        send_message(chat_id, f"В категорії <b>{html_escape(category)}</b> поки немає страв")
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
    """Додати страву в корзину (thread-safe)"""
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
    return f"✅ <b>{name}</b> додано в корзину!"

def show_cart(chat_id):
    """Показати корзину"""
    with carts_lock:
        cart = list(user_carts.get(chat_id, []))
    
    if not cart:
        text = "🛒 Ваша корзина порожня\n\nПерегляньте меню та додайте страви!"
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
            [{"text": "✅ Оформити замовлення", "callback_data": "checkout"}],
            [{"text": "🗑️ Очистити корзину", "callback_data": "clear_cart"}],
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
    """Оформлення замовлення"""
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
        logger.exception(f"Checkout error: {e}")
        return "❌ Помилка оформлення. Спробуйте пізніше."

def process_callback_query(callback_query):
    """Обробка callback з валідацією"""
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        callback_id = callback_query["id"]
        data = callback_query["data"]
        user_id = callback_query["from"]["id"]
        
        # Логування для безпеки
        logger.info(f"Callback from user {user_id}, chat {chat_id}: {data}")
        
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
        else:
            logger.warning(f"Unknown callback data: {data}")
            
    except KeyError as e:
        logger.exception(f"Callback structure error: {e}")
    except Exception as e:
        logger.exception(f"Callback processing error: {e}")

def process_message(message):
    """Обробка повідомлень з валідацією"""
    try:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        user_id = message["from"]["id"]
        
        logger.info(f"Message from user {user_id}, chat {chat_id}")
        
        if text == "/start":
            handle_start(chat_id)
        elif text == "/menu":
            show_categories(chat_id)
        elif text == "/cart":
            show_cart(chat_id)
        else:
            send_message(chat_id, "Спробуйте /start для перегляду меню")
                
    except KeyError as e:
        logger.exception(f"Message structure error: {e}")
    except Exception as e:
        logger.exception(f"Message processing error: {e}")

# Flask routes
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'menu_items': len(menu_cache),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Index endpoint"""
    return jsonify({
        'status': 'ok',
        'bot': 'Hubsy',
        'version': '2.0-secure'
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Secure webhook endpoint"""
    # Перевірка X-Telegram-Bot-Api-Secret-Token
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    
    if not header_secret or header_secret != WEBHOOK_SECRET:
        logger.warning(
            f"Unauthorized webhook attempt from {request.remote_addr}, "
            f"User-Agent: {request.headers.get('User-Agent')}"
        )
        return jsonify({'status': 'unauthorized'}), 401
    
    try:
        update = request.get_json(force=False, silent=False)
        
        if not update:
            logger.warning("Empty update received")
            return jsonify({'status': 'ok'})
        
        update_id = update.get('update_id', 'unknown')
        logger.info(f"Processing update {update_id}")
        
        if 'message' in update:
            process_message(update['message'])
        elif 'callback_query' in update:
            process_callback_query(update['callback_query'])
        else:
            logger.warning(f"Unknown update type: {list(update.keys())}")
        
        return jsonify({'status': 'ok'})
        
    except ValueError as e:
        logger.exception("Invalid JSON in webhook")
        return jsonify({'status': 'bad request', 'error': 'invalid json'}), 400
    except Exception as e:
        logger.exception(f"Webhook processing error: {e}")
        return jsonify({'status': 'error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.exception("Internal server error")
    return jsonify({"error": "Internal server error"}), 500

# Ініціалізація
with app.app_context():
    init_services()

if __name__ == "__main__":
    logger.warning("Use gunicorn for production: gunicorn -w 4 main:app")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False) 