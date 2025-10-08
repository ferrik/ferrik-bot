"""
Hubsy Bot - Telegram Bot для замовлення їжі
Version 3.0 - Покращений UX та безпека

Автор: Claude AI + ferrik
Дата: 2025-10-08
"""

import os
import sys
import logging
import html
from collections import defaultdict
from threading import RLock
from datetime import datetime

from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Завантажити .env
load_dotenv()

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("🚀 Starting Hubsy Bot v3.0...")

# =============================================================================
# ІМПОРТ CONFIG
# =============================================================================

try:
    import bot_config as config
    
    BOT_TOKEN = config.BOT_TOKEN
    WEBHOOK_SECRET = config.WEBHOOK_SECRET
    GOOGLE_SHEET_ID = config.GOOGLE_SHEET_ID
    OPERATOR_CHAT_ID = getattr(config, 'OPERATOR_CHAT_ID', None)
    
    logger.info("✅ Config loaded")
    
except Exception as e:
    logger.critical(f"Config error: {e}")
    sys.exit(1)

# =============================================================================
# ІМПОРТИ СЕРВІСІВ
# =============================================================================

try:
    from services import telegram as tg_service
    from services import sheets as sheets_service
    from services import database as db_service
    
    # Gemini опціонально
    AI_ENABLED = False
    try:
        from services import gemini as ai_service
        if hasattr(config, 'GEMINI_API_KEY') and config.GEMINI_API_KEY:
            AI_ENABLED = True
            logger.info("✅ AI search enabled")
    except:
        pass
    
    logger.info("✅ Services loaded")
    
except Exception as e:
    logger.error(f"Services import error: {e}")
    sys.exit(1)

# =============================================================================
# FLASK APP
# =============================================================================

app = Flask(__name__)

# =============================================================================
# ГЛОБАЛЬНІ ЗМІННІ
# =============================================================================

# Стани (структуровано)
user_sessions = defaultdict(dict)
user_sessions_lock = RLock()

# Корзини
user_carts = defaultdict(dict)
user_carts_lock = RLock()

# Кеш меню
menu_cache = []
menu_cache_lock = RLock()
menu_last_update = None

# Константи
MAX_CART_ITEMS = 50
MAX_ITEM_QUANTITY = 99
MENU_CACHE_TTL = 15 * 60  # 15 хвилин

logger.info("✅ Initialized")

# =============================================================================
# СТАНИ КОРИСТУВАЧА (FSM Light)
# =============================================================================

class UserState:
    """Стани користувача"""
    MAIN_MENU = "main"
    BROWSING_CATEGORIES = "categories"
    BROWSING_ITEMS = "items"
    VIEWING_ITEM = "item"
    IN_CART = "cart"
    SEARCHING = "search"
    CHECKOUT_PHONE = "checkout_phone"
    CHECKOUT_ADDRESS = "checkout_address"
    CHECKOUT_CONFIRM = "checkout_confirm"


def get_session(chat_id):
    """Отримує сесію користувача"""
    with user_sessions_lock:
        if chat_id not in user_sessions:
            user_sessions[chat_id] = {
                'state': UserState.MAIN_MENU,
                'data': {},
                'history': []
            }
        return user_sessions[chat_id]


def set_state(chat_id, new_state, **data):
    """Встановлює стан"""
    session = get_session(chat_id)
    
    # Зберегти попередній стан для "Назад"
    if session['state'] != new_state:
        session['history'].append(session['state'])
        # Обмежити історію
        if len(session['history']) > 10:
            session['history'] = session['history'][-10:]
    
    session['state'] = new_state
    session['data'].update(data)
    
    logger.debug(f"User {chat_id}: state changed to {new_state}")


def get_state(chat_id):
    """Отримує поточний стан"""
    return get_session(chat_id)['state']


def get_data(chat_id, key, default=None):
    """Отримує дані зі стану"""
    return get_session(chat_id)['data'].get(key, default)


def go_back(chat_id):
    """Повернутися до попереднього стану"""
    session = get_session(chat_id)
    if session['history']:
        previous_state = session['history'].pop()
        session['state'] = previous_state
        return previous_state
    return session['state']


# =============================================================================
# МЕНЮ
# =============================================================================

def get_menu(force_refresh=False):
    """Отримує меню з кешем"""
    global menu_cache, menu_last_update
    
    with menu_cache_lock:
        # Перевірка TTL
        now = datetime.now()
        if menu_last_update and not force_refresh:
            age = (now - menu_last_update).total_seconds()
            if age < MENU_CACHE_TTL and menu_cache:
                logger.debug(f"Menu cache hit (age: {age:.0f}s)")
                return menu_cache
        
        # Завантажити з Sheets
        logger.info("📥 Loading menu from Sheets...")
        try:
            menu_cache = sheets_service.get_menu_from_sheet()
            menu_last_update = now
            logger.info(f"✅ Menu loaded: {len(menu_cache)} items")
            return menu_cache
        except Exception as e:
            logger.error(f"Failed to load menu: {e}")
            return menu_cache if menu_cache else []


def get_categories():
    """Унікальні категорії"""
    menu = get_menu()
    categories = sorted(set(item.get('Категорія', 'Інше') for item in menu))
    return [cat for cat in categories if cat]


def get_items_by_category(category):
    """Товари за категорією"""
    menu = get_menu()
    return [item for item in menu if item.get('Категорія') == category]


def find_item(item_name):
    """Знайти товар за назвою"""
    menu = get_menu()
    for item in menu:
        if item.get('Назва Страви') == item_name:
            return item
    return None


# =============================================================================
# ФОРМАТУВАННЯ (з безпечним HTML)
# =============================================================================

def safe_escape(text):
    """Безпечний HTML escape"""
    return html.escape(str(text or ""))


def format_item(item):
    """Форматує товар"""
    name = safe_escape(item.get('Назва Страви', 'Без назви'))
    category = safe_escape(item.get('Категорія', ''))
    price = safe_escape(item.get('Ціна', '0'))
    desc = safe_escape(item.get('Опис', ''))
    
    text = f"🍽 <b>{name}</b>\n\n"
    if desc:
        text += f"{desc}\n\n"
    text += f"📂 {category}\n"
    text += f"💰 <b>{price} грн</b>"
    
    return text


def format_cart_summary(chat_id):
    """Summary корзини"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        return "🛒 Корзина порожня\n\nДодайте товари з меню!"
    
    text = "🛒 <b>Ваша корзина:</b>\n\n"
    total = 0
    
    for item_name, qty in cart.items():
        item = find_item(item_name)
        if item:
            name = safe_escape(item['Назва Страви'])
            price = float(item.get('Ціна', 0))
            subtotal = price * qty
            total += subtotal
            
            text += f"• {name}\n"
            text += f"  {price:.2f} грн × {qty} = {subtotal:.2f} грн\n\n"
    
    text += f"━━━━━━━━━━━━━━━━\n"
    text += f"💰 <b>Разом: {total:.2f} грн</b>"
    
    return text


def get_breadcrumbs(chat_id):
    """Навігаційні breadcrumbs"""
    state = get_state(chat_id)
    
    breadcrumbs = {
        UserState.MAIN_MENU: "🏠 Головна",
        UserState.BROWSING_CATEGORIES: "🏠 Головна → 📋 Меню",
        UserState.BROWSING_ITEMS: "🏠 Головна → 📋 Меню → Категорія",
        UserState.IN_CART: "🏠 Головна → 🛒 Корзина",
        UserState.SEARCHING: "🏠 Головна → 🔍 Пошук",
    }
    
    return breadcrumbs.get(state, "")


# =============================================================================
# TELEGRAM HELPERS
# =============================================================================

def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """Відправити повідомлення"""
    try:
        # Додати breadcrumbs якщо не головна сторінка
        state = get_state(chat_id)
        if state != UserState.MAIN_MENU:
            breadcrumb = get_breadcrumbs(chat_id)
            if breadcrumb:
                text = f"<i>{breadcrumb}</i>\n\n{text}"
        
        return tg_service.tg_send_message(chat_id, text, reply_markup, parse_mode)
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None


def create_keyboard(buttons, one_time=False):
    """Створити клавіатуру"""
    return {
        "keyboard": buttons,
        "resize_keyboard": True,
        "one_time_keyboard": one_time
    }


def create_inline_keyboard(buttons):
    """Inline клавіатура"""
    return {"inline_keyboard": buttons}


# =============================================================================
# КЛАВІАТУРИ
# =============================================================================

def main_menu_keyboard():
    """Головне меню"""
    buttons = [
        [{"text": "📋 Меню"}, {"text": "🛒 Корзина"}]
    ]
    
    if AI_ENABLED:
        buttons.append([{"text": "🔍 Пошук"}, {"text": "ℹ️ Допомога"}])
    else:
        buttons.append([{"text": "ℹ️ Допомога"}])
    
    return create_keyboard(buttons)


def categories_keyboard():
    """Клавіатура категорій"""
    categories = get_categories()
    
    buttons = []
    for i in range(0, len(categories), 2):
        row = [{"text": f"📂 {cat}", "callback_data": f"cat:{cat}"} 
               for cat in categories[i:i+2]]
        buttons.append(row)
    
    buttons.append([{"text": "🏠 Головна", "callback_data": "home"}])
    
    return create_inline_keyboard(buttons)


def item_keyboard(item_name):
    """Клавіатура товару"""
    return create_inline_keyboard([
        [{"text": "➕ В корзину", "callback_data": f"add:{item_name}"}],
        [
            {"text": "◀️ Назад", "callback_data": "back"},
            {"text": "🏠 Головна", "callback_data": "home"}
        ]
    ])


def cart_keyboard(has_items=False):
    """Клавіатура корзини"""
    if has_items:
        return create_keyboard([
            [{"text": "✅ Оформити замовлення"}],
            [{"text": "🗑 Очистити"}, {"text": "🔙 До меню"}]
        ])
    else:
        return create_keyboard([
            [{"text": "📋 Переглянути меню"}],
            [{"text": "🏠 Головна"}]
        ])


# =============================================================================
# ОБРОБНИКИ КОМАНД
# =============================================================================

def handle_start(chat_id):
    """Команда /start"""
    set_state(chat_id, UserState.MAIN_MENU)
    
    text = (
        "👋 <b>Вітаємо в Hubsy Bot!</b>\n\n"
        "🍽 Замовляйте улюблені страви\n"
        "⚡️ Швидко та зручно\n"
        "🚀 Доставка за 30-40 хвилин\n\n"
        "Оберіть дію:"
    )
    
    send_message(chat_id, text, reply_markup=main_menu_keyboard())


def handle_menu(chat_id):
    """Показати меню"""
    set_state(chat_id, UserState.BROWSING_CATEGORIES)
    
    categories = get_categories()
    
    text = (
        "📋 <b>Наше меню</b>\n\n"
        f"Оберіть категорію ({len(categories)} доступно):"
    )
    
    send_message(chat_id, text, reply_markup=categories_keyboard())


def handle_category(chat_id, category):
    """Показати товари категорії"""
    items = get_items_by_category(category)
    
    if not items:
        send_message(chat_id, f"❌ Категорія <b>{category}</b> порожня")
        return
    
    set_state(chat_id, UserState.BROWSING_ITEMS, category=category, item_index=0)
    
    # Показати перший товар
    show_item(chat_id, items[0], 0, len(items))


def show_item(chat_id, item, index, total):
    """Показати товар з навігацією"""
    text = format_item(item)
    
    # Додати навігацію якщо більше 1 товару
    if total > 1:
        text += f"\n\n<i>Товар {index + 1} з {total}</i>"
    
    # Клавіатура з навігацією
    category = get_data(chat_id, 'category')
    buttons = []
    
    # Навігація
    if total > 1:
        nav_row = []
        if index > 0:
            nav_row.append({"text": "◀️", "callback_data": f"prev:{category}:{index}"})
        nav_row.append({"text": f"{index + 1}/{total}", "callback_data": "noop"})
        if index < total - 1:
            nav_row.append({"text": "▶️", "callback_data": f"next:{category}:{index}"})
        buttons.append(nav_row)
    
    # Додати в корзину
    item_name = item['Назва Страви']
    buttons.append([{"text": "➕ В корзину", "callback_data": f"add:{item_name}"}])
    
    # Назад
    buttons.append([
        {"text": "◀️ До категорій", "callback_data": "back"},
        {"text": "🏠 Головна", "callback_data": "home"}
    ])
    
    send_message(chat_id, text, reply_markup=create_inline_keyboard(buttons))


def handle_add_to_cart(chat_id, item_name):
    """Додати в корзину"""
    item = find_item(item_name)
    
    if not item:
        send_message(chat_id, "❌ Товар не знайдено")
        return
    
    with user_carts_lock:
        cart = user_carts[chat_id]
        
        if len(cart) >= MAX_CART_ITEMS:
            send_message(chat_id, f"❌ Максимум {MAX_CART_ITEMS} видів товарів")
            return
        
        qty = cart.get(item_name, 0)
        
        if qty >= MAX_ITEM_QUANTITY:
            send_message(chat_id, f"❌ Максимум {MAX_ITEM_QUANTITY} шт")
            return
        
        cart[item_name] = qty + 1
    
    # Відповідь
    name = safe_escape(item['Назва Страви'])
    new_qty = cart[item_name]
    
    text = f"✅ <b>{name}</b> додано!\n\nКількість: {new_qty} шт"
    
    # Швидкі дії
    keyboard = create_inline_keyboard([
        [
            {"text": "➕ Ще один", "callback_data": f"add:{item_name}"},
            {"text": "🛒 Корзина", "callback_data": "cart"}
        ],
        [{"text": "◀️ Продовжити покупки", "callback_data": "back"}]
    ])
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_cart(chat_id):
    """Показати корзину"""
    set_state(chat_id, UserState.IN_CART)
    
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    summary = format_cart_summary(chat_id)
    
    send_message(chat_id, summary, reply_markup=cart_keyboard(bool(cart)))


def handle_clear_cart(chat_id):
    """Очистити корзину"""
    with user_carts_lock:
        user_carts[chat_id] = {}
    
    send_message(
        chat_id,
        "✅ Корзину очищено",
        reply_markup=main_menu_keyboard()
    )
    set_state(chat_id, UserState.MAIN_MENU)


def handle_search(chat_id):
    """Пошук"""
    if not AI_ENABLED:
        send_message(
            chat_id,
            "❌ Пошук тимчасово недоступний\n\nПерегляньте меню: /menu"
        )
        return
    
    set_state(chat_id, UserState.SEARCHING)
    
    text = (
        "🔍 <b>AI Пошук</b>\n\n"
        "Опишіть що шукаєте:\n"
        "• \"щось гостре\"\n"
        "• \"вегетаріанське\"\n"
        "• \"десерт\"\n\n"
        "Або /cancel для скасування"
    )
    
    keyboard = create_keyboard([[{"text": "❌ Скасувати"}]], one_time=True)
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_search_query(chat_id, query):
    """Обробка пошукового запиту"""
    send_message(chat_id, "🔍 Шукаю...")
    
    try:
        results = ai_service.search_menu(query, get_menu())
        
        if results:
            text = f"✨ Знайдено <b>{len(results)}</b> результатів:\n"
            send_message(chat_id, text)
            
            # Показати перші 5
            for item in results[:5]:
                item_text = format_item(item)
                item_name = item['Назва Страви']
                
                keyboard = create_inline_keyboard([
                    [{"text": "➕ В корзину", "callback_data": f"add:{item_name}"}]
                ])
                
                send_message(chat_id, item_text, reply_markup=keyboard)
        else:
            text = (
                "😔 Нічого не знайдено\n\n"
                "Спробуйте інші слова або\n"
                "перегляньте всі категорії: /menu"
            )
            send_message(chat_id, text)
        
        set_state(chat_id, UserState.MAIN_MENU)
        send_message(chat_id, "Що далі?", reply_markup=main_menu_keyboard())
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        send_message(chat_id, "❌ Помилка пошуку")


def handle_help(chat_id):
    """Допомога"""
    text = (
        "ℹ️ <b>Як замовити:</b>\n\n"
        "1️⃣ Оберіть <b>📋 Меню</b>\n"
        "2️⃣ Виберіть категорію\n"
        "3️⃣ Додайте товари в <b>🛒 Корзину</b>\n"
        "4️⃣ Оформіть замовлення\n\n"
        "<b>Команди:</b>\n"
        "/start - Головне меню\n"
        "/menu - Показати меню\n"
        "/cart - Корзина\n"
        "/cancel - Скасувати дію\n"
        "/help - Ця довідка\n\n"
        "❓ Питання? Пишіть @support"
    )
    
    send_message(chat_id, text, reply_markup=main_menu_keyboard())


# =============================================================================
# CHECKOUT
# =============================================================================

def handle_checkout_start(chat_id):
    """Почати оформлення"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        send_message(chat_id, "❌ Корзина порожня")
        return
    
    set_state(chat_id, UserState.CHECKOUT_PHONE)
    
    text = (
        "📝 <b>Оформлення замовлення</b>\n\n"
        "Крок 1 з 3\n\n"
        "Надішліть ваш номер телефону:"
    )
    
    keyboard = create_keyboard([
        [{"text": "📱 Надіслати номер", "request_contact": True}],
        [{"text": "❌ Скасувати"}]
    ], one_time=True)
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_contact(chat_id, contact):
    """Отримано контакт"""
    phone = contact.get('phone_number')
    
    if not phone:
        send_message(chat_id, "❌ Помилка отримання номера")
        return
    
    set_state(chat_id, UserState.CHECKOUT_ADDRESS, phone=phone)
    
    text = (
        "📝 <b>Оформлення замовлення</b>\n\n"
        "Крок 2 з 3\n\n"
        f"✅ Телефон: {phone}\n\n"
        "Тепер надішліть адресу доставки:"
    )
    
    keyboard = create_keyboard([[{"text": "❌ Скасувати"}]], one_time=True)
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_address(chat_id, address):
    """Отримано адресу"""
    if len(address) < 10:
        send_message(chat_id, "❌ Адреса занадто коротка (мінімум 10 символів)")
        return
    
    phone = get_data(chat_id, 'phone')
    
    set_state(chat_id, UserState.CHECKOUT_CONFIRM, address=address)
    
    # Фінальне підтвердження
    summary = format_cart_summary(chat_id)
    
    text = (
        "📝 <b>Підтвердження замовлення</b>\n\n"
        "Крок 3 з 3\n\n"
        f"{summary}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📱 Телефон: {phone}\n"
        f"📍 Адреса: {safe_escape(address)}\n\n"
        "Все вірно?"
    )
    
    keyboard = create_keyboard([
        [{"text": "✅ Підтвердити замовлення"}],
        [{"text": "❌ Скасувати"}]
    ], one_time=True)
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_confirm_order(chat_id):
    """Підтвердження замовлення"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        send_message(chat_id, "❌ Корзина порожня")
        return
    
    phone = get_data(chat_id, 'phone')
    address = get_data(chat_id, 'address')
    
    try:
        # Розрахувати суму
        total = 0
        for item_name, qty in cart.items():
            item = find_item(item_name)
            if item:
                total += float(item.get('Ціна', 0)) * qty
        
        # Зберегти
        contact_info = {'phone': phone, 'address': address}
        order_id = db_service.save_order(chat_id, cart, contact_info, str(total))
        
        if not order_id:
            raise Exception("Save failed")
        
        # Очистити корзину
        with user_carts_lock:
            user_carts[chat_id] = {}
        
        set_state(chat_id, UserState.MAIN_MENU)
        
        # Sheets sync (не критично)
        try:
            sheets_service.save_order_to_sheets(order_id, cart, contact_info)
        except:
            pass
        
        # Оператору
        if OPERATOR_CHAT_ID:
            try:
                op_text = (
                    f"🆕 <b>Замовлення #{order_id}</b>\n\n"
                    f"{format_cart_summary(chat_id)}\n\n"
                    f"📱 {phone}\n"
                    f"📍 {address}"
                )
                send_message(OPERATOR_CHAT_ID, op_text)
            except:
                pass
        
        # Користувачу
        text = (
            f"✅ <b>Замовлення #{order_id} прийнято!</b>\n\n"
            f"💰 Сума: {total:.2f} грн\n\n"
            "🎉 Дякуємо!\n"
            "Наш оператор зв'яжеться з вами\n"
            "протягом 5-10 хвилин\n\n"
            "Очікуйте дзвінка!"
        )
        
        send_message(chat_id, text, reply_markup=main_menu_keyboard())
        
        logger.info(f"✅ Order {order_id} created")
        
    except Exception as e:
        logger.error(f"Checkout failed: {e}")
        send_message(
            chat_id,
            "❌ Помилка оформлення\n\nСпробуйте пізніше або зверніться до оператора",
            reply_markup=main_menu_keyboard()
        )


# =============================================================================
# WEBHOOK
# =============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint"""
    # Перевірка secret
    secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    
    if secret != WEBHOOK_SECRET:
        logger.warning(f"❌ Auth failed from {request.remote_addr}")
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        update = request.get_json()
        
        if not update:
            return jsonify({"status": "ok"}), 200
        
        # Message
        if 'message' in update:
            msg = update['message']
            chat_id = msg['chat']['id']
            
            # Текст
            if 'text' in msg:
                text = msg['text']
                
                # Команди
                if text.startswith('/'):
                    if text == '/start':
                        handle_start(chat_id)
                    elif text == '/menu':
                        handle_menu(chat_id)
                    elif text == '/cart':
                        handle_cart(chat_id)
                    elif text == '/help':
                        handle_help(chat_id)
                    elif text == '/cancel':
                        set_state(chat_id, UserState.MAIN_MENU)
                        send_message(chat_id, "✅ Скасовано", reply_markup=main_menu_keyboard())
                    else:
                        send_message(chat_id, "❌ Невідома команда\n\n/help для допомоги")
                
                else: