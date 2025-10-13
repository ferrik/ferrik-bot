"""
Hubsy Bot - Telegram Bot для замовлення їжі
Version: 3.1.0 - Personalization Edition
"""

import os
import sys
import logging
import uuid
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from collections import defaultdict
from threading import RLock
from datetime import datetime

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("🚀 Starting Hubsy Bot v3.1.0 with Personalization...")

# =============================================================================
# ІМПОРТИ
# =============================================================================

try:
    import bot_config as config
    from services import telegram as tg_service
    from services import sheets as sheets_service
    from services import database as db_service
    
    from storage.user_repository import UserRepository
    from models.user_profile import UserProfile
    from services.personalization_service import PersonalizationService, UserAnalyticsService
    from utils.personalization_helpers import (
        format_user_greeting_message,
        format_profile_message,
        format_level_up_message,
        format_recommendations_message,
        create_recommendations_keyboard,
        create_profile_keyboard
    )
    
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

app = Flask(__name__)

# =============================================================================
# ГЛОБАЛЬНІ ЗМІННІ
# =============================================================================

user_states = {}
user_state_data = {}
user_states_lock = RLock()

user_carts = defaultdict(dict)
user_carts_lock = RLock()

menu_cache = []
menu_cache_lock = RLock()

user_navigation = defaultdict(list)
nav_lock = RLock()

MAX_CART_ITEMS = 50
MAX_ITEM_QUANTITY = 99

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

try:
    UserRepository.init_db()
    logger.info("✅ Personalization database initialized")
except Exception as e:
    logger.error(f"⚠️ Personalization DB init warning: {e}")

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
# НАВІГАЦІЯ
# =============================================================================

def push_navigation(chat_id, state, **data):
    """Додає в історію навігації"""
    with nav_lock:
        user_navigation[chat_id].append({'state': state, 'data': data})
        if len(user_navigation[chat_id]) > 5:
            user_navigation[chat_id].pop(0)

def pop_navigation(chat_id):
    """Повертається назад"""
    with nav_lock:
        nav = user_navigation.get(chat_id, [])
        if len(nav) > 1:
            nav.pop()
            return nav[-1]
        return None

def clear_navigation(chat_id):
    """Очищує навігацію"""
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
    """Отримує breadcrumbs"""
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
        [{"text": "📋 Меню"}, {"text": "👤 Профіль"}],
        [{"text": "⭐ Рекомендації"}, {"text": "🛒 Корзина"}],
    ]
    if AI_ENABLED:
        buttons.append([{"text": "🔍 Пошук"}, {"text": "ℹ️ Допомога"}])
    else:
        buttons.append([{"text": "ℹ️ Допомога"}])
    return {"keyboard": buttons, "resize_keyboard": True}

def create_categories_keyboard():
    """Клавіатура категорій"""
    categories = get_categories()
    keyboard = {"inline_keyboard": []}
    row = []
    for i, category in enumerate(categories):
        row.append({"text": f"📂 {category}", "callback_data": f"cat:{category}"})
        if len(row) == 2 or i == len(categories) - 1:
            keyboard["inline_keyboard"].append(row)
            row = []
    keyboard["inline_keyboard"].append([{"text": "🔙 Назад в меню", "callback_data": "back_main"}])
    return keyboard

def create_item_keyboard(item, category, index, total):
    """Клавіатура для товару"""
    item_name = item.get('Назва Страви', '')
    keyboard = {"inline_keyboard": []}
    keyboard["inline_keyboard"].append([
        {"text": "➕ Додати в корзину", "callback_data": f"add:{item_name}"}
    ])
    
    if total > 1:
        nav_row = []
        if index > 0:
            nav_row.append({"text": "⬅️ Попередня", "callback_data": f"item:{category}:{index-1}"})
        nav_row.append({"text": f"{index + 1}/{total}", "callback_data": "noop"})
        if index < total - 1:
            nav_row.append({"text": "Наступна ➡️", "callback_data": f"item:{category}:{index+1}"})
        keyboard["inline_keyboard"].append(nav_row)
    
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

def handle_start(chat_id, first_name=None):
    """Команда /start з персоналізацією"""
    clear_state(chat_id)
    clear_navigation(chat_id)
    set_state(chat_id, State.MAIN_MENU)
    
    try:
        profile = UserRepository.get_profile(chat_id)
        if not profile:
            profile = UserProfile(user_id=chat_id, name=first_name or "User")
            UserRepository.save_profile(profile)
        text = format_user_greeting_message(profile)
    except Exception as e:
        logger.error(f"Error in personalization: {e}")
        text = (
            "👋 <b>Вітаємо в Hubsy!</b>\n\n"
            "🍽 Замовляйте смачну їжу онлайн\n"
            "🚀 Швидка доставка\n"
            "💳 Зручна оплата\n\n"
            "Оберіть дію:"
        )
    send_message(chat_id, text, reply_markup=create_main_keyboard())

def handle_profile(chat_id):
    """Показати профіль користувача"""
    try:
        profile = UserRepository.get_profile(chat_id)
        if not profile:
            send_message(chat_id, "❌ Профіль не знайдено. Напишіть /start")
            return
        
        order_history = UserRepository.get_user_order_history(chat_id, limit=5)
        profile_text = format_profile_message(profile, order_history)
        keyboard = create_profile_keyboard()
        send_message(chat_id, profile_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error showing profile: {e}")
        send_message(chat_id, "❌ Помилка при завантаженні профілю")

def handle_recommendations(chat_id):
    """Показати рекомендації"""
    try:
        profile = UserRepository.get_profile(chat_id)
        if not profile:
            send_message(chat_id, "❌ Профіль не знайдено")
            return
        
        menu = get_menu()
        recommendations = PersonalizationService.get_recommendations(
            profile=profile, all_menu_items=menu, limit=3
        )
        text = format_recommendations_message(recommendations)
        keyboard = create_recommendations_keyboard(recommendations)
        send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error showing recommendations: {e}")
        send_message(chat_id, "❌ Помилка при загруженні рекомендацій")

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
        send_message(chat_id, "🔍 <b>Пошук тимчасово недоступний</b>\n\nПерегляньте наше меню: 📋 Меню")
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
    keyboard = {"keyboard": [[{"text": "❌ Скасувати"}]], "resize_keyboard": True}
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
        "/profile - Переглянути профіль\n"
        "/recommendations - Персональні рекомендації\n"
        "/help - Ця довідка\n\n"
        "❓ Питання? Зв'яжіться з оператором"
    )
    send_message(chat_id, text, reply_markup=create_main_keyboard())

def handle_cancel(chat_id):
    """Скасування"""
    previous = pop_navigation(chat_id)
    if previous:
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
    
    name = safe_escape(item.get('Назва Страви'))
    quantity = cart[item_name]
    text = f"✅ <b>{name}</b> додано!\n\nКількість: {quantity} шт"
    keyboard = {
        "inline_keyboard": [[
            {"text": "🛒 Перейти в корзину", "callback_data": "goto_cart"},
            {"text": "📋 Продовжити", "callback_data": "continue_shopping"}
        ]]
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
        "keyboard": [[{"text": "📱 Надіслати номер", "request_contact": True}], 
                     [{"text": "❌ Скасувати"}]],
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
        "Наприклад: вул. Хрещатик, 1, кв. 5"
    )
    keyboard = {"keyboard": [[{"text": "❌ Скасувати"}]], "resize_keyboard": True}
    send_message(chat_id, text, reply_markup=keyboard)

def handle_address_received(chat_id, address):
    """Адреса отримана"""
    if len(address) < 10:
        send_message(chat_id, "❌ Адреса занадто коротка. Введіть повну адресу (мінімум 10 символів)")
        return
    
    with user_states_lock:
        if chat_id not in user_state_data:
            user_state_data[chat_id] = {}
        user_state_data[chat_id]['address'] = address
    
    set_state(chat_id, State.CHECKOUT_CONFIRM, address=address)
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
    """Підтвердження замовлення з персоналізацією"""
    
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        send_message(chat_id, "❌ Корзина порожня")
        handle_start(chat_id)
        return
    
    try:
        phone = get_state_data(chat_id, 'phone', 'N/A')
        address = get_state_data(chat_id, 'address', 'N/A')
        
        total = 0.0
        items_list = []
        dish_names = []
        
        for item_name, quantity in cart.items():
            item = find_item_by_name(item_name)
            if item:
                try:
                    price = float(str(item.get('Ціна', 0)).replace(',', '.'))
                    total += price * quantity
                    items_list.append({
                        'name': item_name,
                        'quantity': quantity,
                        'price': price
                    })
                    dish_names.append(item_name)
                except Exception:
                    pass
        
        order_id = str(uuid.uuid4())[:8]
        
        order_saved = db_service.save_order(
            order_id=order_id,
            user_id=chat_id,
            username=None,
            items=items_list,
            total=f"{total:.2f}",
            phone=phone,
            address=address,
            notes=""
        )
        
        if not order_saved:
            raise Exception("Database save failed")
        
        try:
            profile = UserRepository.get_profile(chat_id)
            if profile:
                old_level = profile.level
                UserRepository.add_order_to_profile(chat_id, {
                    'order_id': order_id,
                    'items': dish_names,
                    'total': total,
                    'timestamp': datetime.now().isoformat()
                })
                
                profile = UserRepository.get_profile(chat_id)
                if profile and profile.level > old_level:
                    level_text = format_level_up_message(profile, old_level)
                    send_message(chat_id, level_text)
        except Exception as e:
            logger.warning(f"Personalization update failed: {e}")
        
        summary = format_cart_summary(chat_id)
        success_text = (
            f"✅ <b>Замовлення успішно оформлено!</b>\n\n"
            f"📦 <b>ID замовлення:</b> <code>{order_id}</code>\n"
            f"📞 <b>Телефон:</b> <code>{phone}</code>\n"
            f"📍 <b>Адреса:</b> {safe_escape(address)}\n\n"
            f"{summary}\n\n"
            f"🚚 Очікуйте доставки!\n"
            f"Спасибі за замовлення! 😊"
        )
        
        with user_carts_lock:
            user_carts[chat_id] = {}
        
        clear_state(chat_id)
        clear_navigation(chat_id)
        
        send_message(chat_id, success_text, reply_markup=create_main_keyboard())
        
    except Exception as e:
        logger.error(f"Error confirming order: {e}")
        send_message(chat_id, f"❌ Помилка при оформленні замовлення: {str(e)}")

# =============================================================================
# FLASK ROUTES
# =============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False})
        
        update_id = data.get('update_id')
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            first_name = message['chat'].get('first_name', 'User')
            
            if text == '/start':
                handle_start(chat_id, first_name)
            elif text == '/profile':
                handle_profile(chat_id)
            elif text == '/recommendations':
                handle_recommendations(chat_id)
            elif text == '/help':
                handle_help(chat_id)
            elif text == '/cancel' or text == '❌ Скасувати':
                handle_cancel(chat_id)
            elif text == '📋 Меню':
                handle_menu(chat_id)
            elif text == '👤 Профіль':
                handle_profile(chat_id)
            elif text == '⭐ Рекомендації':
                handle_recommendations(chat_id)
            elif text == '🛒 Корзина':
                handle_cart(chat_id)
            elif text == '🔍 Пошук':
                handle_search(chat_id)
            elif text == 'ℹ️ Допомога':
                handle_help(chat_id)
            elif text == '✅ Оформити замовлення':
                start_checkout(chat_id)
            elif text == '✅ Підтвердити замовлення':
                confirm_order(chat_id)
            elif text == '🔙 Продовжити покупки':
                handle_menu(chat_id)
            elif text == '🗑 Очистити корзину':
                with user_carts_lock:
                    user_carts[chat_id] = {}
                send_message(chat_id, "🗑 Корзина очищена", reply_markup=create_main_keyboard())
            elif 'contact' in message:
                contact = message['contact']
                phone = contact['phone_number']
                handle_phone_received(chat_id, phone)
            else:
                state = get_state(chat_id)
                if state == State.CHECKOUT_ADDRESS:
                    handle_address_received(chat_id, text)
                elif state == State.SEARCHING and AI_ENABLED:
                    try:
                        response = ai_service.search_dishes(text, get_menu())
                        send_message(chat_id, response, reply_markup=create_main_keyboard())
                    except Exception as e:
                        logger.error(f"Search error: {e}")
                        send_message(chat_id, "❌ Помилка пошуку. Спробуйте пізніше.")
                else:
                    send_message(chat_id, "ℹ️ Команда не розпізнана. Виберіть з меню:", reply_markup=create_main_keyboard())
        
        elif 'callback_query' in data:
            callback = data['callback_query']
            chat_id = callback['from']['id']
            callback_data = callback.get('data', '')
            
            if callback_data == 'back_main':
                handle_start(chat_id)
            elif callback_data == 'back_categories':
                handle_menu(chat_id)
            elif callback_data == 'noop':
                pass
            elif callback_data == 'goto_cart':
                handle_cart(chat_id)
            elif callback_data == 'continue_shopping':
                handle_menu(chat_id)
            elif callback_data.startswith('cat:'):
                category = callback_data[4:]
                show_category(chat_id, category)
            elif callback_data.startswith('add:'):
                item_name = callback_data[4:]
                add_to_cart(chat_id, item_name)
            elif callback_data.startswith('item:'):
                parts = callback_data[5:].split(':')
                if len(parts) == 2:
                    category = parts[0]
                    index = int(parts[1])
                    show_item(chat_id, category, index)
        
        return jsonify({"ok": True})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)})

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "ok", "bot": "Hubsy v3.1.0"})

@app.route('/', methods=['GET'])
def index():
    """Index page"""
    return jsonify({
        "name": "Hubsy Bot",
        "version": "3.1.0",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health"
        }
    })

# =============================================================================
# ЗАПУСК
# =============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🌐 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)