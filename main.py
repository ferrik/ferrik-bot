"""
Hubsy Bot - Telegram Bot для замовлення їжі
Version: 3.0.0 - Production Ready

Features:
- FSM для керування станами
- Правильний UX з навігацією
- Breadcrumbs
- Кнопки "Назад"
- Обробка помилок
- AI fallback
"""

import os
import sys
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from collections import defaultdict
from threading import RLock

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
logger.info("🚀 Starting Hubsy Bot v3.0.0...")

# =============================================================================
# ІМПОРТИ
# =============================================================================

try:
    import bot_config as config
    from services import telegram as tg_service
    from services import sheets as sheets_service
    from services import database as db_service
    
    # Gemini опціонально
    try:
        from services import gemini as ai_service
        AI_ENABLED = True
        logger.info("✅ AI Service enabled")
    except ImportError:
        AI_ENABLED = False
        logger.warning("⚠️  AI Service disabled")
    
    logger.info("✅ All imports successful")
    
except Exception as e:
    logger.critical(f"❌ Import failed: {e}")
    sys.exit(1)

# =============================================================================
# FLASK APP
# =============================================================================

app = Flask(__name__)

# =============================================================================
# ГЛОБАЛЬНІ ЗМІННІ
# =============================================================================

# Стани користувачів (FSM)
user_states = {}
user_state_data = {}
user_states_lock = RLock()

# Корзини
user_carts = defaultdict(dict)
user_carts_lock = RLock()

# Кеш меню
menu_cache = []
menu_cache_lock = RLock()

# Навігація (для кнопок "Назад")
user_navigation = defaultdict(list)
nav_lock = RLock()

# Константи
MAX_CART_ITEMS = 50
MAX_ITEM_QUANTITY = 99

# Стани FSM
class State:
    MAIN_MENU = "main_menu"
    BROWSING_CATEGORIES = "browsing_categories"
    VIEWING_CATEGORY = "viewing_category"
    VIEWING_ITEM = "viewing_item"
    IN_CART = "in_cart"
    SEARCHING = "searching"
    CHECKOUT_PHONE = "checkout_phone"
    CHECKOUT_ADDRESS = "checkout_address"
    CHECKOUT_CONFIRM = "checkout_confirm"

logger.info("✅ Global variables initialized")

# =============================================================================
# HELPER ФУНКЦІЇ
# =============================================================================

def get_menu():
    """Отримує меню з кешу"""
    global menu_cache
    
    with menu_cache_lock:
        if not menu_cache:
            logger.info("📋 Loading menu from Google Sheets...")
            try:
                menu_cache = sheets_service.get_menu_from_sheet()
                logger.info(f"✅ Menu loaded: {len(menu_cache)} items")
            except Exception as e:
                logger.error(f"❌ Failed to load menu: {e}")
                return []
        
        return menu_cache


def get_categories():
    """Отримує список категорій"""
    menu = get_menu()
    categories = set()
    
    for item in menu:
        category = item.get('Категорія', 'Інше')
        if category:
            categories.add(category)
    
    return sorted(list(categories))


def get_items_by_category(category):
    """Отримує товари за категорією"""
    menu = get_menu()
    return [item for item in menu if item.get('Категорія') == category]


def find_item_by_name(name):
    """Знаходить товар за назвою"""
    menu = get_menu()
    for item in menu:
        if item.get('Назва Страви') == name:
            return item
    return None


def safe_escape(text):
    """Безпечно escape HTML"""
    import html
    if text is None:
        return ""
    return html.escape(str(text))


# =============================================================================
# FSM ФУНКЦІЇ
# =============================================================================

def set_state(chat_id, state, **data):
    """Встановлює стан користувача"""
    with user_states_lock:
        user_states[chat_id] = state
        user_state_data[chat_id] = data
        logger.debug(f"State {chat_id}: {state}")


def get_state(chat_id):
    """Отримує поточний стан"""
    return user_states.get(chat_id, State.MAIN_MENU)


def get_state_data(chat_id, key, default=None):
    """Отримує дані стану"""
    return user_state_data.get(chat_id, {}).get(key, default)


def clear_state(chat_id):
    """Очищує стан"""
    with user_states_lock:
        user_states.pop(chat_id, None)
        user_state_data.pop(chat_id, None)


# =============================================================================
# НАВІГАЦІЯ (для кнопок "Назад")
# =============================================================================

def push_navigation(chat_id, state, **data):
    """Додає в історію навігації"""
    with nav_lock:
        user_navigation[chat_id].append({
            'state': state,
            'data': data
        })
        # Обмежити глибину
        if len(user_navigation[chat_id]) > 5:
            user_navigation[chat_id].pop(0)


def pop_navigation(chat_id):
    """Повертається назад"""
    with nav_lock:
        nav = user_navigation.get(chat_id, [])
        if len(nav) > 1:
            nav.pop()  # Видалити поточний
            previous = nav[-1]  # Взяти попередній
            return previous
        return None


def clear_navigation(chat_id):
    """Очищає навігацію"""
    with nav_lock:
        user_navigation[chat_id] = []


# =============================================================================
# ФОРМАТУВАННЯ
# =============================================================================

def format_item(item, include_buttons=True):
    """Форматує товар"""
    name = safe_escape(item.get('Назва Страви', 'Без назви'))
    category = safe_escape(item.get('Категорія', ''))
    price = safe_escape(item.get('Ціна', '0'))
    description = safe_escape(item.get('Опис', ''))
    
    text = f"🍽 <b>{name}</b>\n\n"
    
    if description:
        text += f"{description}\n\n"
    
    text += f"📁 <i>{category}</i>\n"
    text += f"💰 <b>{price} грн</b>"
    
    return text


def format_cart_summary(chat_id):
    """Форматує корзину"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        return "🛒 Ваша корзина порожня"
    
    text = "🛒 <b>Ваша корзина:</b>\n\n"
    total = 0.0
    
    for item_name, quantity in cart.items():
        item = find_item_by_name(item_name)
        if item:
            name = safe_escape(item.get('Назва Страви'))
            try:
                price = float(str(item.get('Ціна', 0)).replace(',', '.'))
            except:
                price = 0.0
            
            item_total = price * quantity
            total += item_total
            
            text += f"▫️ <b>{name}</b>\n"
            text += f"   {price:.2f} грн × {quantity} = {item_total:.2f} грн\n\n"
    
    text += f"━━━━━━━━━━━━━━━━━\n"
    text += f"💰 <b>Разом: {total:.2f} грн</b>"
    
    return text


def get_breadcrumbs(chat_id):
    """Отримує breadcrumbs (шлях користувача)"""
    state = get_state(chat_id)
    
    crumbs = {
        State.MAIN_MENU: "🏠 Головна",
        State.BROWSING_CATEGORIES: "🏠 Головна → 📋 Меню",
        State.VIEWING_CATEGORY: "🏠 Головна → 📋 Меню → 📂 Категорія",
        State.VIEWING_ITEM: "🏠 Головна → 📋 Меню → 📂 Категорія → 🍽 Страва",
        State.IN_CART: "🏠 Головна → 🛒 Корзина",
        State.SEARCHING: "🏠 Головна → 🔍 Пошук",
    }
    
    category = get_state_data(chat_id, 'category')
    if category:
        return crumbs.get(state, "").replace("Категорія", category)
    
    return crumbs.get(state, "🏠 Головна")


# =============================================================================
# КЛАВІАТУРИ
# =============================================================================

def create_main_keyboard():
    """Головне меню"""
    buttons = [
        [{"text": "📋 Меню"}, {"text": "🛒 Корзина"}],
    ]
    
    if AI_ENABLED:
        buttons.append([{"text": "🔍 Пошук"}, {"text": "ℹ️ Допомога"}])
    else:
        buttons.append([{"text": "ℹ️ Допомога"}])
    
    return {
        "keyboard": buttons,
        "resize_keyboard": True
    }


def create_categories_keyboard():
    """Клавіатура категорій"""
    categories = get_categories()
    
    keyboard = {"inline_keyboard": []}
    
    # По 2 кнопки в рядку
    row = []
    for i, category in enumerate(categories):
        row.append({
            "text": f"📂 {category}",
            "callback_data": f"cat:{category}"
        })
        
        if len(row) == 2 or i == len(categories) - 1:
            keyboard["inline_keyboard"].append(row)
            row = []
    
    # Кнопка назад
    keyboard["inline_keyboard"].append([
        {"text": "🔙 Назад в меню", "callback_data": "back_main"}
    ])
    
    return keyboard


def create_item_keyboard(item, category, index, total):
    """Клавіатура для товару"""
    item_name = item.get('Назва Страви', '')
    
    keyboard = {"inline_keyboard": []}
    
    # Кнопка додати
    keyboard["inline_keyboard"].append([
        {"text": "➕ Додати в корзину", "callback_data": f"add:{item_name}"}
    ])
    
    # Навігація якщо є кілька товарів
    if total > 1:
        nav_row = []
        
        if index > 0:
            nav_row.append({
                "text": "⬅️ Попередня",
                "callback_data": f"item:{category}:{index-1}"
            })
        
        nav_row.append({
            "text": f"{index + 1}/{total}",
            "callback_data": "noop"
        })
        
        if index < total - 1:
            nav_row.append({
                "text": "Наступна ➡️",
                "callback_data": f"item:{category}:{index+1}"
            })
        
        keyboard["inline_keyboard"].append(nav_row)
    
    # Кнопка назад
    keyboard["inline_keyboard"].append([
        {"text": "🔙 Назад до категорій", "callback_data": "back_categories"}
    ])
    
    return keyboard


def create_cart_keyboard(has_items=False):
    """Клавіатура корзини"""
    if has_items:
        return {
            "keyboard": [
                [{"text": "✅ Оформити замовлення"}],
                [{"text": "🗑 Очистити корзину"}],
                [{"text": "🔙 Продовжити покупки"}]
            ],
            "resize_keyboard": True
        }
    else:
        return create_main_keyboard()


# =============================================================================
# ВІДПРАВКА ПОВІДОМЛЕНЬ
# =============================================================================

def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """Wrapper для відправки"""
    try:
        # Додати breadcrumbs якщо не головне меню
        state = get_state(chat_id)
        if state != State.MAIN_MENU and not text.startswith('🏠'):
            breadcrumbs = get_breadcrumbs(chat_id)
            text = f"<i>{breadcrumbs}</i>\n\n{text}"
        
        return tg_service.tg_send_message(chat_id, text, reply_markup, parse_mode)
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None


# =============================================================================
# ОБРОБНИКИ КОМАНД
# =============================================================================

def handle_start(chat_id):
    """Команда /start"""
    clear_state(chat_id)
    clear_navigation(chat_id)
    
    set_state(chat_id, State.MAIN_MENU)
    
    text = (
        "👋 <b>Вітаємо в Hubsy!</b>\n\n"
        "🍽 Замовляйте смачну їжу онлайн\n"
        "🚀 Швидка доставка\n"
        "💳 Зручна оплата\n\n"
        "Оберіть дію:"
    )
    
    send_message(chat_id, text, reply_markup=create_main_keyboard())


def handle_menu(chat_id):
    """Показати категорії"""
    push_navigation(chat_id, State.MAIN_MENU)
    set_state(chat_id, State.BROWSING_CATEGORIES)
    
    categories = get_categories()
    
    if not categories:
        send_message(chat_id, "❌ Меню поки що порожнє. Спробуйте пізніше.")
        return
    
    text = f"📋 <b>Наше меню</b>\n\nОберіть категорію ({len(categories)}):"
    
    send_message(chat_id, text, reply_markup=create_categories_keyboard())


def handle_cart(chat_id):
    """Показати корзину"""
    push_navigation(chat_id, get_state(chat_id))
    set_state(chat_id, State.IN_CART)
    
    summary = format_cart_summary(chat_id)
    
    with user_carts_lock:
        has_items = len(user_carts.get(chat_id, {})) > 0
    
    send_message(chat_id, summary, reply_markup=create_cart_keyboard(has_items))


def handle_search(chat_id):
    """Пошук"""
    if not AI_ENABLED:
        send_message(
            chat_id,
            "🔍 <b>Пошук тимчасово недоступний</b>\n\n"
            "Перегляньте наше меню: 📋 Меню"
        )
        return
    
    push_navigation(chat_id, get_state(chat_id))
    set_state(chat_id, State.SEARCHING)
    
    text = (
        "🔍 <b>Пошук страв</b>\n\n"
        "Напишіть що ви шукаєте:\n\n"
        "💡 <i>Наприклад:</i>\n"
        "• \"щось гостре\"\n"
        "• \"вегетаріанські страви\"\n"
        "• \"десерт\"\n\n"
        "Або натисніть /cancel для виходу"
    )
    
    keyboard = {
        "keyboard": [[{"text": "❌ Скасувати"}]],
        "resize_keyboard": True
    }
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_help(chat_id):
    """Допомога"""
    text = (
        "ℹ️ <b>Довідка</b>\n\n"
        "<b>Як зробити замовлення:</b>\n"
        "1️⃣ Виберіть 📋 Меню\n"
        "2️⃣ Оберіть категорію\n"
        "3️⃣ Додайте страви в корзину\n"
        "4️⃣ Перейдіть в 🛒 Корзину\n"
        "5️⃣ Оформіть замовлення\n\n"
        "<b>Команди:</b>\n"
        "/start - Головне меню\n"
        "/cancel - Скасувати поточну дію\n"
        "/cart - Переглянути корзину\n"
        "/help - Ця довідка\n\n"
        "❓ Питання? Зв'яжіться з оператором"
    )
    
    send_message(chat_id, text, reply_markup=create_main_keyboard())


def handle_cancel(chat_id):
    """Скасування"""
    previous = pop_navigation(chat_id)
    
    if previous:
        # Повернутися до попереднього стану
        set_state(chat_id, previous['state'], **previous['data'])
        
        if previous['state'] == State.MAIN_MENU:
            handle_start(chat_id)
        elif previous['state'] == State.BROWSING_CATEGORIES:
            handle_menu(chat_id)
        elif previous['state'] == State.VIEWING_CATEGORY:
            category = previous['data'].get('category')
            if category:
                show_category(chat_id, category)
        else:
            handle_start(chat_id)
    else:
        # Немає історії - повернутися на головну
        handle_start(chat_id)


# =============================================================================
# ОБРОБКА КАТЕГОРІЙ ТА ТОВАРІВ
# =============================================================================

def show_category(chat_id, category):
    """Показує товари категорії"""
    push_navigation(chat_id, get_state(chat_id), category=get_state_data(chat_id, 'category'))
    set_state(chat_id, State.VIEWING_CATEGORY, category=category)
    
    items = get_items_by_category(category)
    
    if not items:
        send_message(chat_id, f"❌ Категорія <b>{category}</b> порожня")
        handle_menu(chat_id)
        return
    
    # Показати перший товар
    show_item(chat_id, category, 0, items)


def show_item(chat_id, category, index, items=None):
    """Показує конкретний товар"""
    if items is None:
        items = get_items_by_category(category)
    
    if not items or index < 0 or index >= len(items):
        send_message(chat_id, "❌ Товар не знайдено")
        return
    
    set_state(chat_id, State.VIEWING_ITEM, category=category, index=index)
    
    item = items[index]
    text = format_item(item)
    
    keyboard = create_item_keyboard(item, category, index, len(items))
    
    send_message(chat_id, text, reply_markup=keyboard)


def add_to_cart(chat_id, item_name):
    """Додає товар в корзину"""
    item = find_item_by_name(item_name)
    
    if not item:
        send_message(chat_id, "❌ Товар не знайдено")
        return
    
    with user_carts_lock:
        cart = user_carts[chat_id]
        
        if len(cart) >= MAX_CART_ITEMS:
            send_message(chat_id, f"❌ Максимум {MAX_CART_ITEMS} різних товарів")
            return
        
        current = cart.get(item_name, 0)
        
        if current >= MAX_ITEM_QUANTITY:
            send_message(chat_id, f"❌ Максимум {MAX_ITEM_QUANTITY} шт одного товару")
            return
        
        cart[item_name] = current + 1
    
    # Повідомлення з швидкими діями
    name = safe_escape(item.get('Назва Страви'))
    quantity = cart[item_name]
    
    text = f"✅ <b>{name}</b> додано!\n\nКількість: {quantity} шт"
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🛒 Перейти в корзину", "callback_data": "goto_cart"},
                {"text": "📋 Продовжити", "callback_data": "continue_shopping"}
            ]
        ]
    }
    
    send_message(chat_id, text, reply_markup=keyboard)


# =============================================================================
# CHECKOUT
# =============================================================================

def start_checkout(chat_id):
    """Початок оформлення"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        send_message(chat_id, "❌ Корзина порожня", reply_markup=create_main_keyboard())
        return
    
    push_navigation(chat_id, State.IN_CART)
    set_state(chat_id, State.CHECKOUT_PHONE)
    
    text = (
        "📞 <b>Оформлення замовлення</b>\n\n"
        "Крок 1/3: Надішліть ваш номер телефону\n\n"
        "Натисніть кнопку нижче або введіть вручну:"
    )
    
    keyboard = {
        "keyboard": [[
            {"text": "📱 Надіслати номер", "request_contact": True}
        ], [
            {"text": "❌ Скасувати"}
        ]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_phone_received(chat_id, phone):
    """Телефон отримано"""
    with user_states_lock:
        if chat_id not in user_state_data:
            user_state_data[chat_id] = {}
        user_state_data[chat_id]['phone'] = phone
    
    set_state(chat_id, State.CHECKOUT_ADDRESS, phone=phone)
    
    text = (
        f"✅ Номер збережено: <code>{phone}</code>\n\n"
        "📍 <b>Крок 2/3:</b> Надішліть адресу доставки\n\n"
        "Наприклад: <i>вул. Хрещатик, 1, кв. 5</i>"
    )
    
    keyboard = {
        "keyboard": [[{"text": "❌ Скасувати"}]],
        "resize_keyboard": True
    }
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_address_received(chat_id, address):
    """Адреса отримана"""
    if len(address) < 10:
        send_message(
            chat_id,
            "❌ Адреса занадто коротка\n\n"
            "Введіть повну адресу (мінімум 10 символів)"
        )
        return
    
    with user_states_lock:
        if chat_id not in user_state_data:
            user_state_data[chat_id] = {}
        user_state_data[chat_id]['address'] = address
    
    set_state(chat_id, State.CHECKOUT_CONFIRM, address=address)
    
    # Показати фінальне підтвердження
    phone = get_state_data(chat_id, 'phone', 'N/A')
    
    summary = format_cart_summary(chat_id)
    
    text = (
        f"{summary}\n\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"📞 Телефон: <code>{phone}</code>\n"
        f"📍 Адреса: {safe_escape(address)}\n\n"
        f"<b>Крок 3/3:</b> Підтвердіть замовлення"
    )
    
    keyboard = {
        "keyboard": [
            [{"text": "✅ Підтвердити замовлення"}],
            [{"text": "❌ Скасувати"}]
        ],
        "resize_keyboard": True
    }
    
    send_message(chat_id, text, reply_markup=keyboard)


def confirm_order(chat_id):
    """Підтвердження замовлення"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        send_message(chat_id, "❌ Корзина порожня")
        handle_start(chat_id)
        return
    
    try:
        phone = get_state_data(chat_id, 'phone', 'N/A')
        address = get_state_data(chat_id, 'address', 'N/A')
        
        # Розрахувати суму
        total = 0.0
        for item_name, quantity in cart.items():
            item = find_item_by_name(item_name)
            if item:
                try:
                    price = float(str(item.get('Ціна', 0)).replace(',', '.'))
                    total += price * quantity
                except:
                    pass
        
        # Зберегти в database
        order_id = db_service.save_order(
            chat_id=chat_id,
            cart=cart,
            contact_info={'phone': phone, 'address': address},
            total=f"{total:.2f}"
        )
        
        if not order_id:
            raise Exception("Database save failed")
        
        # Очистити корзину та стан
        with user_carts_lock:
            user_carts[chat_id] = {}
        
        clear_state(chat_id)
        clear_navigation(chat_id)
        
        # Sheets sync (не критично)
        try:
            sheets_service.save_order_to_sheets(order_id, cart, {'phone': phone, 'address': address})
        except Exception as e:
            logger.error(f"Sheets sync failed: {e}")
        
        # Повідомлення оператору
        if hasattr(config, 'OPERATOR_CHAT_ID') and config.OPERATOR_CHAT_ID:
            try:
                op_text = (
                    f"🆕 <b>Нове замовлення #{order_id}</b>\n\n"
                    f"{format_cart_summary(chat_id)}\n\n"
                    f"📞 {phone}\n"
                    f"📍 {address}"
                )
                send_message(config.OPERATOR_CHAT_ID, op_text)
            except Exception as e:
                logger.error(f"Operator notification failed: {e}")
        
        # Повідомлення користувачу
        text = (
            f"🎉 <b>Замовлення #{order_id} прийнято!</b>\n\n"
            f"💰 Сума: <b>{total:.2f} грн</b>\n\n"
            f"Наш оператор зв'яжеться з вами\nнайближчим часом.\n\n"
            f"Дякуємо за замовлення! ❤️"
        )
        
        send_message(chat_id, text, reply_markup=create_main_keyboard())
        
        logger.info(f"✅ Order {order_id} completed for {chat_id}")
        
    except Exception as e:
        logger.error(f"Order confirmation failed: {e}")
        send_message(
            chat_id,
            "❌ Помилка при оформленні замовлення\n\n"
            "Спробуйте пізніше або зв'яжіться з оператором",
            reply_markup=create_main_keyboard()
        )
        clear_state(chat_id)


# =============================================================================
# WEBHOOK
# =============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint"""
    received_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    
    if received_secret != config.WEBHOOK_SECRET:
        logger.warning(f"⚠️  Unauthorized webhook from {request.remote_addr}")
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        update = request.get_json()
        
        if not update:
            return jsonify({"status": "ok"}), 200
        
        # Обробка message
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            
            # Команди
            if 'text' in message:
                text = message['text']
                
                if text.startswith('/'):
                    # Команди
                    if text == '/start':
                        handle_start(chat_id)
                    elif text == '/menu':
                        handle_menu(chat_id)
                    elif text == '/cart':
                        handle_cart(chat_id)
                    elif text == '/help':
                        handle_help(chat_id)
                    elif text == '/cancel':
                        handle_cancel(chat_id)
                    else:
                        send_message(chat_id, "❌ Невідома команда. Використайте /help")
                
                else:
                    # Обробка відповідно до стану
                    current_state = get_state(chat_id)
                    
                    if current_state == State.SEARCHING:
                        # AI пошук
                        if AI_ENABLED:
                            try:
                                send_message(chat_id, "🔍 Шукаю...")
                                
                                results = ai_service.search_menu(text, get_menu())
                                
                                if results:
                                    send_message(
                                        chat_id,
                                        f"✅ Знайдено {len(results)} результатів:"
                                    )
                                    
                                    for item in results[:5]:
                                        item_text = format_item(item, include_buttons=False)
                                        item_name = item.get('Назва Страви', '')
                                        
                                        keyboard = {
                                            "inline_keyboard": [[
                                                {"text": "➕ В корзину", "callback_data": f"add:{item_name}"}
                                            ]]
                                        }
                                        
                                        send_message(chat_id, item_text, reply_markup=keyboard)
                                else:
                                    send_message(
                                        chat_id,
                                        "😔 Нічого не знайдено\n\n"
                                        "Спробуйте інші слова або перегляньте меню"
                                    )
                                
                                handle_cancel(chat_id)
                                
                            except Exception as e:
                                logger.error(f"Search failed: {e}")
                                send_message(chat_id, "❌ Помилка пошуку")
                                handle_cancel(chat_id)
                    
                    elif current_state == State.CHECKOUT_ADDRESS:
                        # Отримання адреси
                        handle_address_received(chat_id, text)
                    
                    elif current_state == State.CHECKOUT_CONFIRM:
                        # Підтвердження
                        if text == "✅ Підтвердити замовлення":
                            confirm_order(chat_id)
                        elif text == "❌ Скасувати":
                            handle_cancel(chat_id)
                    
                    else:
                        # Кнопки головного меню
                        if text == "📋 Меню":
                            handle_menu(chat_id)
                        elif text == "🛒 Корзина":
                            handle_cart(chat_id)
                        elif text == "🔍 Пошук":
                            handle_search(chat_id)
                        elif text == "ℹ️ Допомога":
                            handle_help(chat_id)
                        elif text == "✅ Оформити замовлення":
                            start_checkout(chat_id)
                        elif text == "🗑 Очистити корзину":
                            with user_carts_lock:
                                user_carts[chat_id] = {}
                            send_message(chat_id, "✅ Корзину очищено", reply_markup=create_main_keyboard())
                        elif text == "🔙 Продовжити покупки":
                            handle_cancel(chat_id)
                        elif text == "❌ Скасувати":
                            handle_cancel(chat_id)
                        else:
                            # Невідома команда
                            send_message(
                                chat_id,
                                "🤔 Не зрозумів. Оберіть дію з меню або використайте /help",
                                reply_markup=create_main_keyboard()
                            )
            
            # Контакт
            elif 'contact' in message:
                contact = message['contact']
                phone = contact.get('phone_number')
                
                if phone:
                    handle_phone_received(chat_id, phone)
                else:
                    send_message(chat_id, "❌ Не вдалося отримати номер телефону")
        
        # Callback queries
        elif 'callback_query' in update:
            callback = update['callback_query']
            callback_id = callback['id']
            chat_id = callback['message']['chat']['id']
            data = callback['data']
            
            # Відповісти на callback
            try:
                tg_service.tg_answer_callback_query(callback_id)
            except:
                pass
            
            # Обробка callback
            if data.startswith('cat:'):
                # Вибрано категорію
                category = data[4:]
                show_category(chat_id, category)
            
            elif data.startswith('item:'):
                # Навігація по товарах
                parts = data.split(':')
                if len(parts) == 3:
                    category = parts[1]
                    index = int(parts[2])
                    show_item(chat_id, category, index)
            
            elif data.startswith('add:'):
                # Додати в корзину
                item_name = data[4:]
                add_to_cart(chat_id, item_name)
            
            elif data == 'goto_cart':
                # Перейти в корзину
                handle_cart(chat_id)
            
            elif data == 'continue_shopping':
                # Продовжити покупки
                state = get_state(chat_id)
                category = get_state_data(chat_id, 'category')
                
                if state == State.VIEWING_ITEM and category:
                    # Повернутися до перегляду категорії
                    index = get_state_data(chat_id, 'index', 0)
                    show_item(chat_id, category, index)
                else:
                    # Повернутися до категорій
                    handle_menu(chat_id)
            
            elif data == 'back_categories':
                # Назад до категорій
                handle_menu(chat_id)
            
            elif data == 'back_main':
                # Назад в головне меню
                handle_start(chat_id)
            
            elif data == 'noop':
                # Нічого не робити (для інформаційних кнопок)
                pass
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# АДМІН ENDPOINTS
# =============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    try:
        menu_ok = len(get_menu()) > 0
        
        return jsonify({
            "status": "healthy" if menu_ok else "degraded",
            "menu_items": len(menu_cache),
            "active_users": len(user_states),
            "carts": len(user_carts),
            "ai_enabled": AI_ENABLED,
            "version": "3.0.0"
        }), 200 if menu_ok else 503
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503


@app.route('/admin/refresh_menu', methods=['POST'])
def admin_refresh_menu():
    """Оновити кеш меню"""
    global menu_cache
    
    try:
        with menu_cache_lock:
            menu_cache = []
        
        menu = get_menu()
        
        return jsonify({
            "status": "ok",
            "items": len(menu),
            "categories": len(get_categories())
        })
    except Exception as e:
        logger.error(f"Menu refresh failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    """Статистика"""
    try:
        with user_carts_lock:
            total_items_in_carts = sum(
                sum(cart.values()) for cart in user_carts.values()
            )
        
        return jsonify({
            "active_users": len(user_states),
            "total_carts": len(user_carts),
            "total_items_in_carts": total_items_in_carts,
            "menu_items": len(menu_cache),
            "categories": len(get_categories())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "service": "Hubsy Bot",
        "status": "running",
        "version": "3.0.0",
        "features": [
            "FSM state management",
            "Smart navigation",
            "Breadcrumbs",
            "AI search" if AI_ENABLED else "Menu browsing",
            "Shopping cart",
            "Order processing"
        ]
    })


# =============================================================================
# ІНІЦІАЛІЗАЦІЯ
# =============================================================================

def initialize_bot():
    """Ініціалізація при старті"""
    logger.info("=" * 60)
    logger.info("🚀 INITIALIZING HUBSY BOT v3.0.0")
    logger.info("=" * 60)
    
    # Завантажити меню
    logger.info("📋 Loading menu...")
    menu = get_menu()
    logger.info(f"✅ Menu loaded: {len(menu)} items in {len(get_categories())} categories")
    
    # Налаштувати webhook
    if hasattr(config, 'WEBHOOK_URL') and config.WEBHOOK_URL:
        logger.info("🔗 Setting up webhook...")
        try:
            success = tg_service.setup_webhook_safe()
            if success:
                logger.info("✅ Webhook configured")
            else:
                logger.warning("⚠️  Webhook setup failed (continuing anyway)")
        except Exception as e:
            logger.warning(f"⚠️  Webhook error: {e}")
    else:
        logger.warning("⚠️  WEBHOOK_URL not set - webhook disabled")
    
    logger.info("=" * 60)
    logger.info("✅ BOT READY!")
    logger.info("=" * 60)


# =============================================================================
# ЗАПУСК
# =============================================================================

if __name__ == '__main__':
    try:
        initialize_bot()
        
        port = getattr(config, 'PORT', 10000)
        debug = getattr(config, 'FLASK_DEBUG', False)
        
        logger.info(f"🌐 Starting server on port {port}")
        logger.info(f"🔧 Debug mode: {debug}")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug
        )
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.critical(f"❌ Failed to start: {e}", exc_info=True)
        sys.exit(1)