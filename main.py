import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape as html_escape
from threading import RLock

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

carts_lock = RLock()
states_lock = RLock()

logger.info("Starting Hubsy Bot...")

try:
    from config import (
        BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID, 
        WEBHOOK_SECRET, validate_config, log_config
    )
    
    if not BOT_TOKEN or not WEBHOOK_SECRET:
        raise RuntimeError("BOT_TOKEN and WEBHOOK_SECRET required")
    
    logger.info("Config imported")
    
except Exception as e:
    logger.exception("Config error")
    raise

try:
    from services.sheets import get_menu_from_sheet, save_order_to_sheets, search_menu_items
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    from services.telegram import tg_send_message, tg_answer_callback, tg_set_webhook
    logger.info("Services imported")
except Exception as e:
    logger.exception("Import error")
    raise

# Глобальні змінні
menu_cache = []
user_carts = defaultdict(list)
user_states = defaultdict(lambda: {'state': 'main', 'data': {}})

# Константи
KEY_NAME = "Назва Страви"
KEY_PRICE = "Ціна"
KEY_CATEGORY = "Категорія"
KEY_DESCRIPTION = "Опис"
KEY_ID = "ID"
KEY_RESTAURANT = "Ресторан"
KEY_RATING = "Рейтинг"
KEY_PHOTO = "Фото"

MAX_CALLBACK_LENGTH = 64

# Емодзі для категорій
CATEGORY_EMOJI = {
    "Піца": "🍕",
    "Бургери": "🍔",
    "Суші": "🍣",
    "Салати": "🥗",
    "Напої": "🥤",
    "Десерти": "🍰",
    "Супи": "🍲"
}

def safe_callback_data(prefix: str, value: str) -> str:
    """Безпечний callback"""
    safe_value = "".join(c for c in str(value) if c.isalnum() or c in "-_")
    return f"{prefix}_{safe_value}"[:MAX_CALLBACK_LENGTH]

def parse_price(price_str) -> Decimal:
    """Парсинг ціни"""
    try:
        clean_price = str(price_str).replace(",", ".").strip()
        return Decimal(clean_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except:
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
            raise RuntimeError("Send failed")
        return result
    except Exception as e:
        logger.exception(f"Send error: {chat_id}")
        raise

def answer_callback(callback_id, text="", show_alert=False):
    """Відповідь на callback"""
    try:
        return tg_answer_callback(callback_id, text, show_alert)
    except Exception as e:
        logger.exception("Callback answer error")
        return None

def init_services():
    """Ініціалізація"""
    global menu_cache
    
    logger.info("Initializing services...")
    
    try:
        log_config()
        validate_config()
    except:
        pass
    
    try:
        menu_cache = get_menu_from_sheet()
        logger.info(f"Menu: {len(menu_cache)} items")
    except Exception as e:
        logger.exception(f"Menu error: {e}")
    
    try:
        init_gemini_client()
        logger.info("Gemini ready")
    except Exception as e:
        logger.exception(f"Gemini error: {e}")
    
    try:
        from config import RENDER_URL
        result = tg_set_webhook(RENDER_URL)
        if result and result.get('ok'):
            logger.info("Webhook OK")
    except Exception as e:
        logger.exception(f"Webhook error: {e}")

def get_user_state(chat_id):
    """Отримати стан користувача"""
    with states_lock:
        return user_states[chat_id]

def set_user_state(chat_id, state, data=None):
    """Встановити стан"""
    with states_lock:
        user_states[chat_id] = {
            'state': state,
            'data': data or {}
        }

def get_categories():
    """Категорії"""
    categories = set()
    for item in menu_cache:
        cat = item.get(KEY_CATEGORY, "")
        if cat:
            categories.add(cat)
    return sorted(list(categories))

def get_items_by_category(category):
    """Страви за категорією"""
    return [item for item in menu_cache if item.get(KEY_CATEGORY) == category]

def format_item(item, show_full=True):
    """Форматування страви"""
    name = html_escape(item.get(KEY_NAME, "Без назви"))
    price = item.get(KEY_PRICE, "?")
    
    if show_full:
        desc = html_escape(item.get(KEY_DESCRIPTION, ""))
        restaurant = html_escape(item.get(KEY_RESTAURANT, ""))
        rating = item.get(KEY_RATING, "")
        
        text = f"<b>{name}</b>\n\n"
        if desc:
            text += f"{desc}\n\n"
        if restaurant:
            text += f"🏪 {restaurant}\n"
        if rating:
            text += f"⭐ Рейтинг: {rating}\n"
        text += f"\n💰 <b>{price} грн</b>"
        return text
    else:
        return f"{name} - {price} грн"

def get_cart_summary(chat_id):
    """Підсумок кошика"""
    with carts_lock:
        cart = user_carts.get(chat_id, [])
    
    if not cart:
        return None, Decimal('0.00')
    
    items_count = defaultdict(int)
    total = Decimal('0.00')
    
    for item in cart:
        name = item.get(KEY_NAME, "")
        items_count[name] += 1
        price = parse_price(item.get(KEY_PRICE, 0))
        total += price
    
    return items_count, total

def handle_start(chat_id, user_name=None):
    """Привітання"""
    set_user_state(chat_id, 'main')
    
    greeting = f"Привіт, {user_name}! 👋\n\n" if user_name else "Привіт! 👋\n\n"
    
    text = (
        f"{greeting}"
        "Я <b>Hubsy</b> — твій цифровий помічник для замовлення їжі.\n\n"
        "Що хочеш зробити?"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🍽️ Меню страв", "callback_data": "menu"}],
            [{"text": "🔥 Популярне сьогодні", "callback_data": "popular"}],
            [
                {"text": "🛒 Кошик", "callback_data": "cart"},
                {"text": "💬 Оператор", "callback_data": "operator"}
            ],
            [{"text": "⚙️ Налаштування", "callback_data": "settings"}]
        ]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def show_menu(chat_id):
    """Вибір категорії"""
    set_user_state(chat_id, 'choosing_category')
    
    categories = get_categories()
    
    if not categories:
        send_message(chat_id, "❌ Меню тимчасово недоступне")
        return
    
    text = "<b>🍽️ Меню</b>\n\nОбери категорію:"
    keyboard = {"inline_keyboard": []}
    
    for cat in categories:
        emoji = CATEGORY_EMOJI.get(cat, "🍽️")
        keyboard["inline_keyboard"].append([
            {"text": f"{emoji} {cat}", "callback_data": safe_callback_data("cat", cat)}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔍 Пошук", "callback_data": "search"},
        {"text": "🏠 Головна", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)

def show_category_items(chat_id, category):
    """Показ страв категорії"""
    items = get_items_by_category(category)
    
    if not items:
        send_message(chat_id, f"❌ В категорії <b>{html_escape(category)}</b> немає страв")
        return
    
    # Зберігаємо контекст
    set_user_state(chat_id, 'browsing_items', {
        'category': category,
        'items': items,
        'current_index': 0
    })
    
    show_item_card(chat_id, items[0], 0, len(items), category)

def show_item_card(chat_id, item, index, total, category):
    """Карточка страви з навігацією"""
    text = format_item(item, show_full=True)
    text += f"\n\n📄 Страва {index + 1} з {total}"
    
    keyboard = {"inline_keyboard": []}
    
    # Навігація
    nav_row = []
    if index > 0:
        nav_row.append({"text": "⬅️ Назад", "callback_data": f"prev_{index}"})
    if index < total - 1:
        nav_row.append({"text": "Далі ➡️", "callback_data": f"next_{index}"})
    
    if nav_row:
        keyboard["inline_keyboard"].append(nav_row)
    
    # Дії
    item_id = item.get(KEY_ID, item.get(KEY_NAME, ""))
    keyboard["inline_keyboard"].append([
        {"text": "➕ Додати в кошик", "callback_data": safe_callback_data("add", item_id)}
    ])
    
    # Повернення
    keyboard["inline_keyboard"].append([
        {"text": "🔙 До категорій", "callback_data": "menu"},
        {"text": "🏠 Головна", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)

def navigate_items(chat_id, direction):
    """Навігація по стравах"""
    state = get_user_state(chat_id)
    
    if state['state'] != 'browsing_items':
        return
    
    items = state['data']['items']
    current = state['data']['current_index']
    category = state['data']['category']
    
    new_index = current + (1 if direction == 'next' else -1)
    new_index = max(0, min(new_index, len(items) - 1))
    
    state['data']['current_index'] = new_index
    show_item_card(chat_id, items[new_index], new_index, len(items), category)

def add_to_cart(chat_id, item_id):
    """Додати в кошик"""
    item = None
    for menu_item in menu_cache:
        if str(menu_item.get(KEY_ID, "")) == str(item_id):
            item = menu_item
            break
    
    if not item:
        return "❌ Страву не знайдено"
    
    with carts_lock:
        user_carts[chat_id].append(item)
    
    name = item.get(KEY_NAME, "Страва")
    price = item.get(KEY_PRICE, "")
    
    return f"✅ Додано!\n\n<b>{name}</b>\nЦіна: {price} грн"

def show_cart(chat_id):
    """Показ кошика"""
    items_count, total = get_cart_summary(chat_id)
    
    if not items_count:
        text = "🛒 <b>Твій кошик порожній</b>\n\nДодай страви з меню!"
        keyboard = {
            "inline_keyboard": [[
                {"text": "🍽️ До меню", "callback_data": "menu"}
            ]]
        }
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    text = "🛒 <b>Твій кошик:</b>\n\n"
    
    for name, count in items_count.items():
        text += f"• {html_escape(name)} x{count}\n"
    
    text += f"\n💰 <b>Всього: {total:.2f} грн</b>"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Оформити замовлення", "callback_data": "checkout"}],
            [{"text": "🗑️ Очистити", "callback_data": "clear_cart"}],
            [{"text": "➕ Додати ще", "callback_data": "menu"}],
            [{"text": "🏠 Головна", "callback_data": "start"}]
        ]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def show_popular(chat_id):
    """Популярні страви"""
    # TODO: Додати аналітику, поки показуємо перші 3
    popular = menu_cache[:3] if menu_cache else []
    
    if not popular:
        send_message(chat_id, "❌ Немає даних про популярні страви")
        return
    
    text = "🔥 <b>Популярне сьогодні:</b>\n\n"
    keyboard = {"inline_keyboard": []}
    
    for item in popular:
        name = item.get(KEY_NAME, "")
        price = item.get(KEY_PRICE, "")
        text += f"• {name} - {price} грн\n"
        
        item_id = item.get(KEY_ID, item.get(KEY_NAME, ""))
        keyboard["inline_keyboard"].append([
            {"text": f"➕ {name}", "callback_data": safe_callback_data("add", item_id)}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🍽️ Все меню", "callback_data": "menu"},
        {"text": "🏠 Головна", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)

def clear_cart(chat_id):
    """Очистити кошик"""
    with carts_lock:
        user_carts[chat_id] = []
    return "🗑️ Кошик очищено"

def checkout(chat_id):
    """Оформлення"""
    with carts_lock:
        cart = list(user_carts.get(chat_id, []))
    
    if not cart:
        return "❌ Кошик порожній"
    
    try:
        save_order_to_sheets(chat_id, cart)
        
        with carts_lock:
            user_carts[chat_id] = []
        
        _, total = get_cart_summary(chat_id)
        
        text = (
            "✅ <b>Замовлення прийнято!</b>\n\n"
            "📞 Наш менеджер зателефонує вам протягом 5 хвилин для підтвердження.\n\n"
            "🎉 Дякуємо, що обрали Hubsy!"
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

def process_callback_query(callback_query):
    """Обробка callback"""
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        callback_id = callback_query["id"]
        data = callback_query["data"]
        user = callback_query["from"]
        user_name = user.get("first_name", "")
        
        logger.info(f"Callback: {data} from {chat_id}")
        
        answer_callback(callback_id, "")
        
        if data == "start":
            handle_start(chat_id, user_name)
        elif data == "menu":
            show_menu(chat_id)
        elif data == "popular":
            show_popular(chat_id)
        elif data == "cart":
            show_cart(chat_id)
        elif data.startswith("cat_"):
            category = data[4:]
            show_category_items(chat_id, category)
        elif data.startswith("add_"):
            item_id = data[4:]
            msg = add_to_cart(chat_id, item_id)
            answer_callback(callback_id, msg, show_alert=True)
        elif data.startswith("next_") or data.startswith("prev_"):
            direction = 'next' if data.startswith("next") else 'prev'
            navigate_items(chat_id, direction)
        elif data == "clear_cart":
            msg = clear_cart(chat_id)
            answer_callback(callback_id, msg, show_alert=True)
            show_cart(chat_id)
        elif data == "checkout":
            msg = checkout(chat_id)
            if msg:
                answer_callback(callback_id, msg, show_alert=True)
        elif data == "operator":
            text = "💬 <b>Зв'язок з оператором</b>\n\nНапишіть своє питання, і оператор відповість найближчим часом."
            send_message(chat_id, text)
        elif data == "settings":
            text = "⚙️ <b>Налаштування</b>\n\nФункція в розробці..."
            send_message(chat_id, text)
        else:
            logger.warning(f"Unknown callback: {data}")
            
    except Exception as e:
        logger.exception(f"Callback error: {e}")

def process_message(message):
    """Обробка повідомлень"""
    try:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        user = message["from"]
        user_name = user.get("first_name", "")
        
        logger.info(f"Message from {chat_id}")
        
        if text == "/start":
            handle_start(chat_id, user_name)
        elif text == "/menu":
            show_menu(chat_id)
        elif text == "/cart":
            show_cart(chat_id)
        else:
            # AI-відповідь або підказка
            send_message(chat_id, "Скористайся /start для перегляду меню 🍽️")
                
    except Exception as e:
        logger.exception(f"Message error: {e}")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'menu_items': len(menu_cache),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    return jsonify({'status': 'ok', 'bot': 'Hubsy', 'version': '2.1'})

@app.route('/webhook', methods=['POST'])
def webhook():
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    
    if not header_secret or header_secret != WEBHOOK_SECRET:
        logger.warning(f"Unauthorized from {request.remote_addr}")
        return jsonify({'status': 'unauthorized'}), 401
    
    try:
        update = request.get_json(force=False)
        if not update:
            return jsonify({'status': 'ok'})
        
        if 'message' in update:
            process_message(update['message'])
        elif 'callback_query' in update:
            process_callback_query(update['callback_query'])
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        return jsonify({'error': 'error'}), 500

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)