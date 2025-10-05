import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict, Counter
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
history_lock = RLock()

logger.info("Starting Hubsy Bot Phase 2...")

try:
    from config import (
        BOT_TOKEN, GEMINI_API_KEY, SPREADSHEET_ID, 
        WEBHOOK_SECRET, validate_config, log_config
    )
    
    if not BOT_TOKEN or not WEBHOOK_SECRET:
        raise RuntimeError("BOT_TOKEN and WEBHOOK_SECRET required")
    
    logger.info("Config OK")
    
except Exception as e:
    logger.exception("Config error")
    raise

try:
    from services.sheets import get_menu_from_sheet, save_order_to_sheets, search_menu_items, reload_menu
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    from services.telegram import tg_send_message, tg_answer_callback, tg_set_webhook
    from services.database import (
        init_database, save_order as db_save_order, get_order, 
        update_order_status, log_activity
    )
    from handlers.admin import (
        is_admin, show_admin_menu, show_statistics, show_new_orders,
        show_order_details, change_order_status, show_popular_items, reload_menu as admin_reload_menu
    )
    logger.info("Services OK")
except Exception as e:
    logger.exception("Import error")
    raise

menu_cache = []
user_carts = defaultdict(list)
user_states = defaultdict(lambda: {'state': 'main', 'data': {}})
user_history = defaultdict(list)
menu_analytics = Counter()

KEY_NAME = "Назва Страви"
KEY_PRICE = "Ціна"
KEY_CATEGORY = "Категорія"
KEY_DESCRIPTION = "Опис"
KEY_ID = "ID"
KEY_RESTAURANT = "Ресторан"
KEY_RATING = "Рейтинг"
KEY_PHOTO = "Фото"

MAX_CALLBACK_LENGTH = 64

CATEGORY_EMOJI = {
    "Піца": "🍕", "Бургери": "🍔", "Суші": "🍣",
    "Салати": "🥗", "Напої": "🥤", "Десерти": "🍰", "Супи": "🍲"
}

def safe_callback_data(prefix: str, value: str) -> str:
    safe_value = "".join(c for c in str(value) if c.isalnum() or c in "-_")
    return f"{prefix}_{safe_value}"[:MAX_CALLBACK_LENGTH]

def parse_price(price_str) -> Decimal:
    try:
        clean_price = str(price_str).replace(",", ".").strip()
        return Decimal(clean_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except:
        return Decimal('0.00')

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
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
    try:
        return tg_answer_callback(callback_id, text, show_alert)
    except Exception as e:
        logger.exception("Callback error")
        return None

def init_services():
    global menu_cache
    
    logger.info("Initializing...")
    
    # Ініціалізація бази даних
    try:
        if init_database():
            logger.info("Database OK")
        else:
            logger.error("Database init failed")
    except Exception as e:
        logger.exception(f"Database error: {e}")
    
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
        if is_gemini_connected():
            logger.info("AI ready")
    except Exception as e:
        logger.exception(f"AI error: {e}")
    
    try:
        from config import RENDER_URL
        result = tg_set_webhook(RENDER_URL)
        if result and result.get('ok'):
            logger.info("Webhook OK")
    except Exception as e:
        logger.exception(f"Webhook error: {e}")

def get_user_state(chat_id):
    with states_lock:
        return user_states[chat_id]

def set_user_state(chat_id, state, data=None):
    with states_lock:
        user_states[chat_id] = {'state': state, 'data': data or {}}

def add_to_history(chat_id, item):
    with history_lock:
        user_history[chat_id].append({
            'item': item,
            'timestamp': datetime.now().isoformat()
        })
        if len(user_history[chat_id]) > 20:
            user_history[chat_id] = user_history[chat_id][-20:]

def track_popularity(item_id):
    menu_analytics[item_id] += 1

def get_popular_items(limit=3):
    if not menu_analytics:
        sorted_menu = sorted(
            menu_cache, 
            key=lambda x: float(str(x.get(KEY_RATING, 0)).replace(',', '.')), 
            reverse=True
        )
        return sorted_menu[:limit]
    
    popular_ids = [item_id for item_id, count in menu_analytics.most_common(limit)]
    return [item for item in menu_cache if item.get(KEY_ID) in popular_ids]

def get_user_preferences(chat_id):
    with history_lock:
        history = user_history.get(chat_id, [])
    
    if not history:
        return None
    
    categories = Counter()
    for entry in history:
        item = entry['item']
        cat = item.get(KEY_CATEGORY, '')
        if cat:
            categories[cat] += 1
    
    return categories.most_common(1)[0][0] if categories else None

def ai_search(query, chat_id):
    if not is_gemini_connected():
        return search_menu_items(query), None
    
    try:
        categories = get_categories()
        menu_list = [f"{item[KEY_NAME]} ({item[KEY_CATEGORY]})" for item in menu_cache[:20]]
        
        prompt = f"""Користувач шукає: "{query}"

Доступні категорії: {', '.join(categories)}
Деякі страви: {', '.join(menu_list)}

Проаналізуй та поверни ТІЛЬКИ назву категорії або страви.
Відповідь (одне слово):"""

        ai_result = get_ai_response(prompt).strip()
        
        if ai_result in categories:
            return get_items_by_category(ai_result), ai_result
        
        results = [item for item in menu_cache if ai_result.lower() in item[KEY_NAME].lower()]
        return results, None
        
    except Exception as e:
        logger.error(f"AI search error: {e}")
        return search_menu_items(query), None

def get_ai_recommendation(chat_id):
    if not is_gemini_connected():
        return "AI недоступний. Спробуйте пізніше."
    
    try:
        preferred_category = get_user_preferences(chat_id)
        categories = get_categories()
        
        context = ""
        if preferred_category:
            context = f"Користувач часто замовляє: {preferred_category}. "
        
        prompt = f"""{context}Порекомендуй 2-3 страви.

Категорії: {', '.join(categories)}

Коротко (2-3 речення), дружньо."""

        return get_ai_response(prompt)
        
    except Exception as e:
        logger.error(f"AI error: {e}")
        return "Спробуйте наше популярне меню!"

def get_categories():
    categories = set()
    for item in menu_cache:
        cat = item.get(KEY_CATEGORY, "")
        if cat:
            categories.add(cat)
    return sorted(list(categories))

def get_items_by_category(category):
    return [item for item in menu_cache if item.get(KEY_CATEGORY) == category]

def format_item(item, show_full=True):
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
            text += f"⭐ {rating}\n"
        text += f"\n💰 <b>{price} грн</b>"
        return text
    else:
        return f"{name} - {price} грн"

def get_cart_summary(chat_id):
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
    set_user_state(chat_id, 'main')
    
    preferred = get_user_preferences(chat_id)
    greeting = f"Привіт, {user_name}! 👋\n\n" if user_name else "Привіт! 👋\n\n"
    
    if preferred:
        greeting += f"<i>Бачу ти любиш {preferred} 😉</i>\n\n"
    
    text = (
        f"{greeting}"
        "Я <b>Hubsy</b> — твій розумний помічник.\n\n"
        "Що хочеш зробити?"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🍽️ Меню", "callback_data": "menu"}],
            [{"text": "🔥 Популярне", "callback_data": "popular"}],
            [
                {"text": "🔍 Пошук", "callback_data": "search"},
                {"text": "✨ AI-Порада", "callback_data": "ai_recommend"}
            ],
            [{"text": "🛒 Кошик", "callback_data": "cart"}],
            [{"text": "📜 Історія", "callback_data": "history"}]
        ]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def show_menu(chat_id):
    set_user_state(chat_id, 'choosing_category')
    
    categories = get_categories()
    
    if not categories:
        send_message(chat_id, "❌ Меню недоступне")
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
    items = get_items_by_category(category)
    
    if not items:
        send_message(chat_id, f"❌ В <b>{html_escape(category)}</b> немає страв")
        return
    
    set_user_state(chat_id, 'browsing_items', {
        'category': category,
        'items': items,
        'current_index': 0
    })
    
    show_item_card(chat_id, items[0], 0, len(items), category)

def show_item_card(chat_id, item, index, total, category):
    text = format_item(item, show_full=True)
    text += f"\n\n📄 Страва {index + 1} з {total}"
    
    keyboard = {"inline_keyboard": []}
    
    nav_row = []
    if index > 0:
        nav_row.append({"text": "⬅️", "callback_data": f"prev_{index}"})
    nav_row.append({"text": f"{index + 1}/{total}", "callback_data": "noop"})
    if index < total - 1:
        nav_row.append({"text": "➡️", "callback_data": f"next_{index}"})
    
    keyboard["inline_keyboard"].append(nav_row)
    
    item_id = item.get(KEY_ID, item.get(KEY_NAME, ""))
    keyboard["inline_keyboard"].append([
        {"text": "➕ Додати", "callback_data": safe_callback_data("add", item_id)}
    ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔙 Категорії", "callback_data": "menu"},
        {"text": "🏠 Головна", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)

def navigate_items(chat_id, direction):
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
    item = None
    for menu_item in menu_cache:
        if str(menu_item.get(KEY_ID, "")) == str(item_id):
            item = menu_item
            break
    
    if not item:
        return "❌ Не знайдено"
    
    with carts_lock:
        user_carts[chat_id].append(item)
    
    track_popularity(item_id)
    add_to_history(chat_id, item)
    
    name = item.get(KEY_NAME, "")
    price = item.get(KEY_PRICE, "")
    
    return f"✅ Додано!\n\n{name}\n{price} грн"

def show_cart(chat_id):
    items_count, total = get_cart_summary(chat_id)
    
    if not items_count:
        text = "🛒 <b>Кошик порожній</b>\n\nДодай щось смачне!"
        keyboard = {"inline_keyboard": [[{"text": "🍽️ До меню", "callback_data": "menu"}]]}
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    text = "🛒 <b>Твій кошик:</b>\n\n"
    
    for name, count in items_count.items():
        text += f"• {html_escape(name)} x{count}\n"
    
    text += f"\n💰 <b>Всього: {total:.2f} грн</b>"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Оформити", "callback_data": "checkout"}],
            [{"text": "🗑️ Очистити", "callback_data": "clear_cart"}],
            [{"text": "➕ Додати", "callback_data": "menu"}],
            [{"text": "🏠 Головна", "callback_data": "start"}]
        ]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)

def show_popular(chat_id):
    popular = get_popular_items(3)
    
    if not popular:
        send_message(chat_id, "❌ Немає даних")
        return
    
    text = "🔥 <b>Топ сьогодні:</b>\n\n"
    keyboard = {"inline_keyboard": []}
    
    for item in popular:
        name = item.get(KEY_NAME, "")
        price = item.get(KEY_PRICE, "")
        rating = item.get(KEY_RATING, "")
        text += f"• {name} - {price} грн"
        if rating:
            text += f" ⭐ {rating}"
        text += "\n"
        
        item_id = item.get(KEY_ID, "")
        keyboard["inline_keyboard"].append([
            {"text": f"➕ {name[:20]}", "callback_data": safe_callback_data("add", item_id)}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🍽️ Все меню", "callback_data": "menu"},
        {"text": "🏠 Головна", "callback_data": "start"}
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)

def show_history(chat_id):
    with history_lock:
        history = user_history.get(chat_id, [])
    
    if not history:
        text = "📜 <b>Історія порожня</b>\n\nТи ще нічого не замовляв."
        keyboard = {"inline_keyboard": [[{"text": "🍽️ До меню", "callback_data": "menu"}]]}
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    recent_items = []
    seen = set()
    for entry in reversed(history):
        item_name = entry['item'].get(KEY_NAME)
        if item_name not in seen:
            recent_items.append(entry['item'])
            seen.add(item_name)
        if len(recent_items) >= 5:
            break
    
    text = "📜 <b>Твоя історія:</b>\n\n"
    keyboard = {"inline_keyboard": []}
    
    for item in recent_items:
        name = item.get(KEY_NAME, "")
        price = item.get(KEY_PRICE, "")
        text += f"• {name} - {price} грн\n"
        
        item_id = item.get(KEY_ID, "")
        keyboard["inline_keyboard"].append([
            {"text": f"🔄 {name[:20]}", "callback_data": safe_callback_data("add", item_id)}
        ])
    
    keyboard["inline_keyboard"].append([{"text": "🏠 Головна", "callback_data": "start"}])
    
    send_message(chat_id, text, reply_markup=keyboard)

def start_search(chat_id):
    set_user_state(chat_id, 'searching')
    
    text = "🔍 <b>Розумний пошук</b>\n\nНапиши що шукаєш:\n\n<i>Наприклад: \"щось солодке\", \"піца\"</i>"
    
    keyboard = {"inline_keyboard": [[{"text": "❌ Скасувати", "callback_data": "start"}]]}
    
    send_message(chat_id, text, reply_markup=keyboard)

def process_search(chat_id, query):
    results, category = ai_search(query, chat_id)
    
    if not results:
        text = f"❌ Не знайшов '<b>{html_escape(query)}</b>'\n\nСпробуй інакше"
        keyboard = {"inline_keyboard": [[
            {"text": "🔍 Новий пошук", "callback_data": "search"},
            {"text": "🍽️ Меню", "callback_data": "menu"}
        ]]}
        send_message(chat_id, text, reply_markup=keyboard)
        set_user_state(chat_id, 'main')
        return
    
    if category:
        send_message(chat_id, f"✅ Знайшов: <b>{category}</b>")
        show_category_items(chat_id, category)
    else:
        text = f"🔍 Результати '<b>{html_escape(query)}</b>':\n\n"
        keyboard = {"inline_keyboard": []}
        
        for item in results[:5]:
            name = item.get(KEY_NAME, "")
            price = item.get(KEY_PRICE, "")
            text += f"• {name} - {price} грн\n"
            
            item_id = item.get(KEY_ID, "")
            keyboard["inline_keyboard"].append([
                {"text": f"➕ {name[:25]}", "callback_data": safe_callback_data("add", item_id)}
            ])
        
        keyboard["inline_keyboard"].append([
            {"text": "🔍 Новий", "callback_data": "search"},
            {"text": "🏠 Головна", "callback_data": "start"}
        ])
        
        send_message(chat_id, text, reply_markup=keyboard)
    
    set_user_state(chat_id, 'main')

def show_ai_recommendation(chat_id):
    text = "✨ <b>Думаю...</b>"
    send_message(chat_id, text)
    
    recommendation = get_ai_recommendation(chat_id)
    
    text = f"✨ <b>AI-Порада:</b>\n\n{recommendation}"
    
    keyboard = {"inline_keyboard": [
        [{"text": "🍽️ До меню", "callback_data": "menu"}],
        [{"text": "🔄 Інша", "callback_data": "ai_recommend"}],
        [{"text": "🏠 Головна", "callback_data": "start"}]
    ]}
    
    send_message(chat_id, text, reply_markup=keyboard)

def clear_cart(chat_id):
    with carts_lock:
        user_carts[chat_id] = []
    return "🗑️ Очищено"

def checkout(chat_id):
    with carts_lock:
        cart = list(user_carts.get(chat_id, []))
    
    if not cart:
        return "❌ Кошик порожній"
    
    try:
        # Генеруємо ID замовлення
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        order_id = f"ORD-{timestamp}-{chat_id}"
        
        # Підготовка даних
        items_for_db = []
        total = Decimal('0.00')
        
        for item in cart:
            name = item.get(KEY_NAME, "")
            price_raw = item.get(KEY_PRICE, 0)
            price = parse_price(price_raw)
            total += price
            
            items_for_db.append({
                'id': item.get(KEY_ID, ''),
                'name': name,
                'price': float(price)
            })
        
        # Зберігаємо в БД
        db_save_order(order_id, chat_id, "", items_for_db, float(total))
        
        # Зберігаємо в Sheets (як резерв)
        save_order_to_sheets(chat_id, cart)
        
        # Логуємо активність
        log_activity(chat_id, 'order_created', {'order_id': order_id, 'total': float(total)})
        
        # Очищаємо корзину
        with carts_lock:
            user_carts[chat_id] = []
        
        text = (
            "✅ <b>Замовлення прийнято!</b>\n\n"
            f"📦 Номер: <code>{order_id[-8:]}</code>\n"
            f"💰 Сума: {total:.2f} грн\n\n"
            "📞 Менеджер зателефонує за 5 хв\n\n"
            "Дякуємо! 💙"
       )
        
        keyboard = {"inline_keyboard": [[{"text": "🏠 Головна", "callback_data": "start"}]]}
        
        send_message(chat_id, text, reply_markup=keyboard)
        
        # Повідомлення оператору
        try:
            from config import OPERATOR_CHAT_ID
            if OPERATOR_CHAT_ID:
                notify_operator_new_order(OPERATOR_CHAT_ID, order_id, chat_id, items_for_db, total)
        except:
            pass
        
        return None
        
    except Exception as e:
        logger.exception(f"Checkout error: {e}")
        return "❌ Помилка"

def process_callback_query(callback_query):
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        callback_id = callback_query["id"]
        data = callback_query["data"]
        user = callback_query["from"]
        user_name = user.get("first_name", "")
        
        logger.info(f"Callback: {data}")
        
        answer_callback(callback_id, "")
        
        if data == "noop":
            return
        elif data == "start":
            handle_start(chat_id, user_name)
        elif data == "menu":
            show_menu(chat_id)
        elif data == "popular":
            show_popular(chat_id)
        elif data == "cart":
            show_cart(chat_id)
        elif data == "history":
            show_history(chat_id)
        elif data == "search":
            start_search(chat_id)
        elif data == "ai_recommend":
            show_ai_recommendation(chat_id)
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
        else:
            logger.warning(f"Unknown: {data}")
            
    except Exception as e:
        logger.exception(f"Callback error: {e}")

def process_message(message):
    try:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        user = message["from"]
        user_name = user.get("first_name", "")
        
        logger.info(f"Message from {chat_id}")
        
        state = get_user_state(chat_id)
        
        if state['state'] == 'searching':
            process_search(chat_id, text)
            return
        
        if text == "/start":
            handle_start(chat_id, user_name)
        elif text == "/menu":
            show_menu(chat_id)
        elif text == "/cart":
            show_cart(chat_id)
        elif text == "/help":
            handle_start(chat_id, user_name)
        else:
            if is_gemini_connected():
                process_search(chat_id, text)
            else:
                send_message(chat_id, "Використай /start")
                
    except Exception as e:
        logger.exception(f"Message error: {e}")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'menu_items': len(menu_cache),
        'popular_tracked': len(menu_analytics),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    return jsonify({'status': 'ok', 'bot': 'Hubsy', 'version': '2.5-AI'})

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