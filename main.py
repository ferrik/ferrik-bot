import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict, Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape as html_escape
from threading import RLock
from urllib.parse import quote_plus, unquote_plus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

carts_lock = RLock()
states_lock = RLock()
history_lock = RLock()

logger.info("Starting Hubsy Bot (Secure Version)...")

# Критична перевірка конфігурації
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
        raise RuntimeError("WEBHOOK_SECRET is required")
    
    logger.info("Config validated")
    
except ImportError as e:
    logger.critical(f"Config import failed: {e}")
    raise RuntimeError("Cannot start without config") from e
except Exception as e:
    logger.exception("Config error")
    raise

# Імпорти з fallback
try:
    from services.sheets import get_menu_from_sheet, save_order_to_sheets, search_menu_items
    from services.gemini import init_gemini_client, get_ai_response, is_gemini_connected
    from services.telegram import tg_send_message, tg_answer_callback, tg_set_webhook
    logger.info("Services imported")
except ImportError as e:
    logger.critical(f"Service import failed: {e}")
    raise RuntimeError("Cannot start without services") from e

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

MAX_CALLBACK_LENGTH = 60  # Безпечний ліміт

CATEGORY_EMOJI = {
    "Піца": "🍕", "Бургери": "🍔", "Суші": "🍣",
    "Салати": "🥗", "Напої": "🥤", "Десерти": "🍰", "Супи": "🍲"
}

def safe_callback_data(prefix: str, value: str) -> str:
    """Безпечний callback_data з URL encoding"""
    try:
        # Видаляємо спецсимволи
        safe_value = "".join(c for c in str(value) if c.isalnum() or c in "-_")
        # URL encode
        encoded = quote_plus(safe_value)
        callback = f"{prefix}_{encoded}"
        
        # Обрізаємо до безпечної довжини
        if len(callback) > MAX_CALLBACK_LENGTH:
            callback = callback[:MAX_CALLBACK_LENGTH]
        
        return callback
    except Exception as e:
        logger.error(f"Callback data error: {e}")
        return f"{prefix}_error"

def parse_callback_data(data: str):
    """Декодування callback_data"""
    try:
        if '_' not in data:
            return data, ""
        
        prefix, value = data.split('_', 1)
        decoded_value = unquote_plus(value)
        return prefix, decoded_value
    except Exception as e:
        logger.error(f"Parse callback error: {e}")
        return data, ""

def parse_price(price_str) -> Decimal:
    """Безпечний парсинг ціни в Decimal"""
    try:
        clean_price = str(price_str).replace(",", ".").replace(" ", "").strip()
        if not clean_price:
            return Decimal('0.00')
        price = Decimal(clean_price)
        return price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.warning(f"Price parse error '{price_str}': {e}")
        return Decimal('0.00')

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """Відправка з HTML escaping"""
    try:
        # Ескейпуємо HTML
        safe_text = html_escape(text)
        
        # Відновлюємо дозволені теги
        safe_text = safe_text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
        safe_text = safe_text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        safe_text = safe_text.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
        
        result = tg_send_message(chat_id, safe_text, reply_markup, parse_mode)
        
        if not result or not result.get('ok'):
            logger.error(f"Send failed: {result}")
            raise RuntimeError("Send message failed")
        
        return result
        
    except Exception as e:
        logger.exception(f"Send error for chat {chat_id}")
        raise

def answer_callback(callback_id, text="", show_alert=False):
    """Відповідь на callback"""
    try:
        return tg_answer_callback(callback_id, text, show_alert)
    except Exception as e:
        logger.exception("Callback answer error")
        return None

def init_services():
    """Ініціалізація з proper error handling"""
    global menu_cache
    
    logger.info("Initializing services...")
    
    try:
        log_config()
        if not validate_config():
            logger.warning("Config validation failed")
    except Exception as e:
        logger.exception(f"Config validation error: {e}")
    
    try:
        menu_cache = get_menu_from_sheet()
        if menu_cache:
            logger.info(f"Menu loaded: {len(menu_cache)} items")
        else:
            logger.warning("Menu is empty")
    except Exception as e:
        logger.exception(f"Menu load error: {e}")
        menu_cache = []
    
    try:
        init_gemini_client()
        if is_gemini_connected():
            logger.info("Gemini initialized")
        else:
            logger.warning("Gemini not connected")
    except Exception as e:
        logger.exception(f"Gemini init error: {e}")
    
    try:
        from config import RENDER_URL
        result = tg_set_webhook(RENDER_URL)
        if result and result.get('ok'):
            logger.info("Webhook set successfully")
        else:
            logger.error(f"Webhook setup failed: {result}")
    except Exception as e:
        logger.exception(f"Webhook error: {e}")

def get_user_state(chat_id):
    """Thread-safe state getter"""
    with states_lock:
        return user_states[chat_id].copy()

def set_user_state(chat_id, state, data=None):
    """Thread-safe state setter"""
    with states_lock:
        user_states[chat_id] = {'state': state, 'data': data or {}}

def add_to_history(chat_id, item):
    """Thread-safe history"""
    with history_lock:
        user_history[chat_id].append({
            'item': item.copy(),
            'timestamp': datetime.now().isoformat()
        })
        if len(user_history[chat_id]) > 20:
            user_history[chat_id] = user_history[chat_id][-20:]

def track_popularity(item_id):
    """Thread-safe analytics"""
    menu_analytics[item_id] += 1

def get_popular_items(limit=3):
    """Топ популярних"""
    try:
        if not menu_analytics:
            sorted_menu = sorted(
                menu_cache, 
                key=lambda x: parse_price(x.get(KEY_RATING, 0)), 
                reverse=True
            )
            return sorted_menu[:limit]
        
        popular_ids = [item_id for item_id, count in menu_analytics.most_common(limit)]
        return [item for item in menu_cache if item.get(KEY_ID) in popular_ids]
    except Exception as e:
        logger.exception(f"Get popular error: {e}")
        return []

def get_user_preferences(chat_id):
    """Аналіз уподобань"""
    try:
        with history_lock:
            history = user_history.get(chat_id, [])
        
        if not history:
            return None
        
        categories = Counter()
        for entry in history:
            item = entry.get('item', {})
            cat = item.get(KEY_CATEGORY, '')
            if cat:
                categories[cat] += 1
        
        return categories.most_common(1)[0][0] if categories else None
    except Exception as e:
        logger.exception(f"Get preferences error: {e}")
        return None

def ai_search(query, chat_id):
    """AI пошук з fallback"""
    if not is_gemini_connected():
        return search_menu_items(query), None
    
    try:
        categories = get_categories()
        menu_list = [f"{item[KEY_NAME]}" for item in menu_cache[:10]]
        
        prompt = f"""Користувач шукає: "{query}"

Категорії: {', '.join(categories)}
Страви: {', '.join(menu_list)}

Поверни ТІЛЬКИ назву категорії або страви."""

        ai_result = get_ai_response(prompt).strip()
        
        if ai_result in categories:
            return get_items_by_category(ai_result), ai_result
        
        results = [item for item in menu_cache if ai_result.lower() in item[KEY_NAME].lower()]
        return results, None
        
    except Exception as e:
        logger.exception(f"AI search error: {e}")
        return search_menu_items(query), None

def get_ai_recommendation(chat_id):
    """AI рекомендація"""
    if not is_gemini_connected():
        return "AI недоступний зараз."
    
    try:
        preferred = get_user_preferences(chat_id)
        categories = get_categories()
        
        context = f"Користувач любить: {preferred}. " if preferred else ""
        
        prompt = f"""{context}Порекомендуй 2 страви.
Категорії: {', '.join(categories)}
Коротко, дружньо."""

        return get_ai_response(prompt)
        
    except Exception as e:
        logger.exception(f"AI recommendation error: {e}")
        return "Спробуйте наше меню!"

def get_categories():
    """Унікальні категорії"""
    try:
        categories = set()
        for item in menu_cache:
            cat = item.get(KEY_CATEGORY, "")
            if cat:
                categories.add(cat)
        return sorted(list(categories))
    except Exception as e:
        logger.exception(f"Get categories error: {e}")
        return []

def get_items_by_category(category):
    """Страви за категорією"""
    try:
        return [item for item in menu_cache if item.get(KEY_CATEGORY) == category]
    except Exception as e:
        logger.exception(f"Get items error: {e}")
        return []

def format_item(item, show_full=True):
    """Форматування з escape"""
    try:
        name = item.get(KEY_NAME, "Без назви")
        price = item.get(KEY_PRICE, "?")
        
        if show_full:
            desc = item.get(KEY_DESCRIPTION, "")
            restaurant = item.get(KEY_RESTAURANT, "")
            rating = item.get(KEY_RATING, "")
            
            # HTML буде ескейпнуто в send_message
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
    except Exception as e:
        logger.exception(f"Format item error: {e}")
        return "Помилка форматування"

def get_cart_summary(chat_id):
    """Підсумок корзини"""
    try:
        with carts_lock:
            cart = list(user_carts.get(chat_id, []))
        
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
    except Exception as e:
        logger.exception(f"Cart summary error: {e}")
        return None, Decimal('0.00')

def handle_start(chat_id, user_name=None):
    """Привітання"""
    try:
        set_user_state(chat_id, 'main')
        
        preferred = get_user_preferences(chat_id)
        greeting = f"Привіт, {user_name}! 👋\n\n" if user_name else "Привіт! 👋\n\n"
        
        if preferred:
            greeting += f"<i>Бачу ти любиш {preferred}</i>\n\n"
        
        text = f"{greeting}Я <b>Hubsy</b> — твій помічник.\n\nЩо хочеш зробити?"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🍽️ Меню", "callback_data": "menu"}],
                [{"text": "🔥 Популярне", "callback_data": "popular"}],
                [
                    {"text": "🔍 Пошук", "callback_data": "search"},
                    {"text": "✨ AI", "callback_data": "ai_recommend"}
                ],
                [{"text": "🛒 Кошик", "callback_data": "cart"}]
            ]
        }
        
        send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        logger.exception(f"Start handler error: {e}")
        send_message(chat_id, "Помилка. Спробуйте /start")

def show_menu(chat_id):
    """Показ категорій"""
    try:
        set_user_state(chat_id, 'choosing_category')
        
        categories = get_categories()
        
        if not categories:
            send_message(chat_id, "❌ Меню недоступне")
            return
        
        text = "<b>🍽️ Меню</b>\n\nОбери категорію:"
        keyboard = {"inline_keyboard": []}
        
        for cat in categories:
            emoji = CATEGORY_EMOJI.get(cat, "🍽️")
            cb = safe_callback_data("cat", cat)
            keyboard["inline_keyboard"].append([
                {"text": f"{emoji} {cat}", "callback_data": cb}
            ])
        
        keyboard["inline_keyboard"].append([
            {"text": "🔍 Пошук", "callback_data": "search"},
            {"text": "🏠 Головна", "callback_data": "start"}
        ])
        
        send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        logger.exception(f"Show menu error: {e}")

def show_category_items(chat_id, category):
    """Страви категорії"""
    try:
        items = get_items_by_category(category)
        
        if not items:
            send_message(chat_id, f"В <b>{category}</b> немає страв")
            return
        
        set_user_state(chat_id, 'browsing_items', {
            'category': category,
            'items': items,
            'current_index': 0
        })
        
        show_item_card(chat_id, items[0], 0, len(items), category)
    except Exception as e:
        logger.exception(f"Show category error: {e}")

def show_item_card(chat_id, item, index, total, category):
    """Карточка страви"""
    try:
        text = format_item(item, show_full=True)
        text += f"\n\n📄 {index + 1}/{total}"
        
        keyboard = {"inline_keyboard": []}
        
        nav_row = []
        if index > 0:
            nav_row.append({"text": "⬅️", "callback_data": f"prev_{index}"})
        nav_row.append({"text": f"{index + 1}/{total}", "callback_data": "noop"})
        if index < total - 1:
            nav_row.append({"text": "➡️", "callback_data": f"next_{index}"})
        
        keyboard["inline_keyboard"].append(nav_row)
        
        item_id = str(item.get(KEY_ID, item.get(KEY_NAME, "")))
        cb = safe_callback_data("add", item_id)
        keyboard["inline_keyboard"].append([
            {"text": "➕ Додати", "callback_data": cb}
        ])
        
        keyboard["inline_keyboard"].append([
            {"text": "🔙 Категорії", "callback_data": "menu"},
            {"text": "🏠 Головна", "callback_data": "start"}
        ])
        
        send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        logger.exception(f"Show card error: {e}")

def navigate_items(chat_id, direction):
    """Навігація"""
    try:
        state = get_user_state(chat_id)
        
        if state['state'] != 'browsing_items':
            return
        
        items = state['data']['items']
        current = state['data']['current_index']
        category = state['data']['category']
        
        new_index = current + (1 if direction == 'next' else -1)
        new_index = max(0, min(new_index, len(items) - 1))
        
        set_user_state(chat_id, 'browsing_items', {
            'category': category,
            'items': items,
            'current_index': new_index
        })
        
        show_item_card(chat_id, items[new_index], new_index, len(items), category)
    except Exception as e:
        logger.exception(f"Navigate error: {e}")

def add_to_cart(chat_id, item_id):
    """Додати в корзину"""
    try:
        item = None
        for menu_item in menu_cache:
            if str(menu_item.get(KEY_ID, "")) == str(item_id):
                item = menu_item
                break
        
        if not item:
            return "❌ Не знайдено"
        
        with carts_lock:
            user_carts[chat_id].append(item.copy())
        
        track_popularity(item_id)
        add_to_history(chat_id, item)
        
        name = item.get(KEY_NAME, "")
        price = item.get(KEY_PRICE, "")
        
        return f"✅ Додано!\n\n{name}\n{price} грн"
    except Exception as e:
        logger.exception(f"Add to cart error: {e}")
        return "❌ Помилка"

def show_cart(chat_id):
    """Показ корзини"""
    try:
        items_count, total = get_cart_summary(chat_id)
        
        if not items_count:
            text = "🛒 <b>Кошик порожній</b>"
            keyboard = {"inline_keyboard": [[{"text": "🍽️ Меню", "callback_data": "menu"}]]}
            send_message(chat_id, text, reply_markup=keyboard)
            return
        
        text = "🛒 <b>Твій кошик:</b>\n\n"
        
        for name, count in items_count.items():
            text += f"• {name} x{count}\n"
        
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
    except Exception as e:
        logger.exception(f"Show cart error: {e}")

def show_popular(chat_id):
    """Популярні страви"""
    try:
        popular = get_popular_items(3)
        
        if not popular:
            send_message(chat_id, "❌ Немає даних")
            return
        
        text = "🔥 <b>Топ:</b>\n\n"
        keyboard = {"inline_keyboard": []}
        
        for item in popular:
            name = item.get(KEY_NAME, "")
            price = item.get(KEY_PRICE, "")
            text += f"• {name} - {price} грн\n"
            
            item_id = str(item.get(KEY_ID, ""))
            cb = safe_callback_data("add", item_id)
            keyboard["inline_keyboard"].append([
                {"text": f"➕ {name[:20]}", "callback_data": cb}
            ])
        
        keyboard["inline_keyboard"].append([
            {"text": "🍽️ Меню", "callback_data": "menu"},
            {"text": "🏠 Головна", "callback_data": "start"}
        ])
        
        send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        logger.exception(f"Show popular error: {e}")

def start_search(chat_id):
    """Пошук"""
    try:
        set_user_state(chat_id, 'searching')
        
        text = "🔍 <b>Пошук</b>\n\nНапиши що шукаєш:"
        keyboard = {"inline_keyboard": [[{"text": "❌ Скасувати", "callback_data": "start"}]]}
        
        send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        logger.exception(f"Start search error: {e}")

def process_search(chat_id, query):
    """Обробка пошуку"""
    try:
        results, category = ai_search(query, chat_id)
        
        if not results:
            text = f"❌ Не знайшов '<b>{query}</b>'"
            keyboard = {"inline_keyboard": [[
                {"text": "🔍 Новий", "callback_data": "search"},
                {"text": "🍽️ Меню", "callback_data": "menu"}
            ]]}
            send_message(chat_id, text, reply_markup=keyboard)
            set_user_state(chat_id, 'main')
            return
        
        if category:
            send_message(chat_id, f"✅ Знайшов: <b>{category}</b>")
            show_category_items(chat_id, category)
        else:
            text = f"🔍 '<b>{query}</b>':\n\n"
            keyboard = {"inline_keyboard": []}
            
            for item in results[:5]:
                name = item.get(KEY_NAME, "")
                price = item.get(KEY_PRICE, "")
                text += f"• {name} - {price} грн\n"
                
                item_id = str(item.get(KEY_ID, ""))
                cb = safe_callback_data("add", item_id)
                keyboard["inline_keyboard"].append([
                    {"text": f"➕ {name[:25]}", "callback_data": cb}
                ])
            
            keyboard["inline_keyboard"].append([
                {"text": "🔍 Новий", "callback_data": "search"},
                {"text": "🏠 Головна", "callback_data": "start"}
            ])
            
            send_message(chat_id, text, reply_markup=keyboard)
        
        set_user_state(chat_id, 'main')
    except Exception as e:
        logger.exception(f"Process search error: {e}")

def show_ai_recommendation(chat_id):
    """AI порада"""
    try:
        text = "✨ Думаю..."
        send_message(chat_id, text)
        
        recommendation = get_ai_recommendation(chat_id)
        
        text = f"✨ <b>AI-Порада:</b>\n\n{recommendation}"
        
        keyboard = {"inline_keyboard": [
            [{"text": "🍽️ Меню", "callback_data": "menu"}],
            [{"text": "🔄 Інша", "callback_data": "ai_recommend"}],
            [{"text": "🏠 Головна", "callback_data": "start"}]
        ]}
        
        send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        logger.exception(f"AI recommend error: {e}")

def clear_cart(chat_id):
    """Очистити корзину"""
    try:
        with carts_lock:
            user_carts[chat_id] = []
        return "🗑️ Очищено"
    except Exception as e:
        logger.exception(f"Clear cart error: {e}")
        return "❌ Помилка"

def checkout(chat_id):
    """Оформлення"""
    try:
        with carts_lock:
            cart = list(user_carts.get(chat_id, []))
        
        if not cart:
            return "❌ Порожньо"
        
        save_order_to_sheets(chat_id, cart)
        
        _, total = get_cart_summary(chat_id)
        
        with carts_lock:
            user_carts[chat_id] = []
        
        text = (
            "✅ <b>Замовлення прийнято!</b>\n\n"
            f"💰 {total:.2f} грн\n"
            "📞 Зателефонуємо за 5 хв\n\n"
            "Дякуємо!"
        )
        
        keyboard = {"inline_keyboard": [[{"text": "🏠 Головна", "callback_data": "start"}]]}
        
        send_message(chat_id, text, reply_markup=keyboard)
        return None
        
    except Exception as e:
        logger.exception(f"Checkout error: {e}")
        return "❌ Помилка"

def process_callback_query(callback_query):
    """Обробка callback з валідацією"""
    try:
        # Перевірка структури
        if 'message' not in callback_query:
            logger.warning("Callback without message (inline)")
            return
        
        if 'chat' not in callback_query['message']:
            logger.warning("Callback without chat")
            return
        
        chat_id = callback_query["message"]["chat"]["id"]
        callback_id = callback_query["id"]
        data = callback_query["data"]
        user = callback_query.get("from", {})
        user_name = user.get("first_name", "")
        
        logger.info(f"Callback: {data[:20]}... from {chat_id}")
        
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
        elif data == "search":
            start_search(chat_id)
        elif data == "ai_recommend":
            show_ai_recommendation(chat_id)
        elif data.startswith("cat_"):
            _, category = parse_callback_data(data)
            show_category_items(chat_id, category)
        elif data.startswith("add_"):
            _, item_id = parse_callback_data(data)
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
            logger.warning(f"Unknown callback: {data}")
            
    except KeyError as e:
        logger.exception(f"Callback structure error: {e}")
    except Exception as e:
        logger.exception(f"Callback error: {e}")

def process_message(message):
    """Обробка повідомлень з валідацією"""
    try:
        # Валідація структури
        if 'chat' not in message:
            logger.warning("Message without chat")
            return
        
        if 'from' not in message:
            logger.warning("Message without from")
            return
        
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        user = message["from"]
        user_name = user.get("first_name", "")
        
        logger.info(f"Message from {chat_id}: {text[:30]}...")
        
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
                
    except KeyError as e:
        logger.exception(f"Message structure error: {e}")
    except Exception as e:
        logger.exception(f"Message error: {e}")

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    try:
        return jsonify({
            'status': 'healthy',
            'menu_items': len(menu_cache),
            'popular_tracked': len(menu_analytics),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.exception("Health check error")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """Index"""
    return jsonify({
        'status': 'ok',
        'bot': 'Hubsy',
        'version': '3.0-secure'
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Secure webhook with dual authentication"""
    # Перевірка 1: X-Telegram-Bot-Api-Secret-Token header
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    
    if header_secret:
        if header_secret != WEBHOOK_SECRET:
            logger.warning(
                f"Invalid webhook header from {request.remote_addr}, "
                f"User-Agent: {request.headers.get('User-Agent')}"
            )
            return jsonify({'status': 'unauthorized'}), 401
    else:
        # Якщо header немає - це старий метод, логуємо
        logger.warning(f"Webhook without header from {request.remote_addr}")
        return jsonify({'status': 'unauthorized'}), 401
    
    try:
        # Валідація JSON
        update = request.get_json(force=False, silent=False)
        
        if not update:
            logger.warning("Empty webhook payload")
            return jsonify({'status': 'ok'})
        
        if not isinstance(update, dict):
            logger.error("Invalid webhook payload type")
            return jsonify({'status': 'bad request'}), 400
        
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
        return jsonify({'status': 'error', 'error': 'internal error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.exception("Internal server error")
    return jsonify({"error": "Internal server error"}), 500

with app.app_context():
    init_services()

if __name__ == "__main__":
    logger.warning("Use gunicorn for production: gunicorn -w 4 main:app")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
