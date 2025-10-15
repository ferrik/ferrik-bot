"""
Hubsy Bot - Telegram Bot для замовлення їжі
Version: 3.2.0 - Enhanced UX with vivid messages
"""

import os
import sys
import logging
import uuid
import random
import json
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
logger.info("🚀 Starting Hubsy Bot v3.2.0 with Enhanced UX...")

# =============================================================================
# ІМПОРТИ
# =============================================================================

PERSONALIZATION_ENABLED = False
AI_ENABLED = False

try:
    import bot_config as config
    from services import telegram as tg_service
    from services import sheets as sheets_service
    from services import database as db_service
    logger.info("✅ Core services imported")
except Exception as e:
    logger.critical(f"❌ Critical import failed: {e}")
    sys.exit(1)

try:
    from services import gemini as ai_service
    AI_ENABLED = True
    logger.info("✅ AI Service enabled")
except Exception as ae:
    AI_ENABLED = False
    logger.warning(f"⚠️  AI Service disabled: {ae}")

# Перевірка БД при старті
try:
    db_service.init_database()
    ok, info = db_service.test_connection()
    if ok:
        logger.info(f"✅ Database OK: {info}")
    else:
        logger.error(f"❌ Database FAILED: {info}")
except Exception as e:
    logger.error(f"DB check error: {e}")

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

# =============================================================================
# РАНДОМНІ ФРАЗИ
# =============================================================================

GREETINGS = [
    "👋 Привіт! Готовий щось смачненьке замовити?",
    "🍽️ Ласкаво просимо назад!",
    "😋 Голодний? Ми це зафіксуємо! 😄",
    "🎉 Вітаємо! Час перекусити!",
    "👨‍🍳 Шеф чекає на твоє замовлення!",
]

MENU_STARTERS = [
    "🍽️ Ось наші найсмачніші категорії!",
    "👨‍🍳 Шеф радить спробувати щось із цього 👇",
    "🌟 Наша спеціалізація чекає на тебе!",
    "🎯 Обери, що сподобається 😋",
]

CART_EMPTY = [
    "🛒 Корзина порожня... 😢",
    "Твоя корзина чекає на перші страви!",
    "Поки що нічого не додав. Давай це виправимо! 🛍️",
]

SUCCESS_MESSAGES = [
    "✅ Успішно додано! Гарний вибір! 👌",
    "🎉 Чудово! Це буде смачно!",
    "😋 Вибір номер один! Додано в корзину!",
    "👍 Супер! Ще щось?",
]

ERROR_MESSAGES = [
    "🤔 Не зовсім розумію... Виберіть з меню 👇",
    "😕 Це мені невідомо. Спробуйте ще раз!",
    "❓ Команда не розпізнана. Натисніть щось з кнопок!",
]

def random_greeting():
    return random.choice(GREETINGS)

def random_menu_starter():
    return random.choice(MENU_STARTERS)

def random_success():
    return random.choice(SUCCESS_MESSAGES)

def random_error():
    return random.choice(ERROR_MESSAGES)

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
        if data:
            if chat_id not in user_state_data:
                user_state_data[chat_id] = {}
            user_state_data[chat_id].update(data)
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
# ФОРМАТУВАННЯ
# =============================================================================

def format_item(item):
    """Форматує товар з красивим дизайном"""
    name = safe_escape(item.get('Назва Страви', 'Без назви'))
    category = safe_escape(item.get('Категорія', ''))
    price = safe_escape(item.get('Ціна', '0'))
    description = safe_escape(item.get('Опис', ''))
    rating = item.get('Рейтинг', '⭐⭐⭐⭐⭐')
    delivery_time = item.get('Час Доставки (хв)', '30-45')
    
    text = f"🍽️ <b>{name}</b>\n{'─'*30}\n\n"
    if description:
        text += f"📝 {description}\n\n"
    text += f"📁 <b>Категорія:</b> {category}\n"
    text += f"⏱️ <b>Час:</b> {delivery_time} хв\n"
    text += f"🌟 <b>Рейтинг:</b> {rating}\n\n"
    text += f"💰 <b>Ціна: {price} ₴</b>"
    return text

def format_cart(chat_id):
    """Форматує корзину"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        return f"🛒 <b>Кошик порожній</b>\n\n{random.choice(CART_EMPTY)}\n\n📋 Перейдіть у меню!"
    
    text = "🛒 <b>ВАШ КОШИК</b>\n" + "─"*30 + "\n\n"
    total = 0.0
    
    for i, (item_name, qty) in enumerate(cart.items(), 1):
        item = find_item_by_name(item_name)
        if item:
            name = safe_escape(item.get('Назва Страви'))
            try:
                price = float(str(item.get('Ціна', 0)).replace(',', '.'))
            except:
                price = 0.0
            item_total = price * qty
            total += item_total
            text += f"{i}️⃣ <b>{name}</b>\n   {price:.2f} ₴ × {qty} = {item_total:.2f} ₴\n\n"
    
    text += "─"*30 + f"\n💳 <b>ВСЬОГО: {total:.2f} ₴</b>"
    return text

# =============================================================================
# КЛАВІАТУРИ
# =============================================================================

def kb_main():
    """Головне меню"""
    return {
        "keyboard": [
            [{"text": "📋 Меню"}, {"text": "⭐ Рекомендації"}],
            [{"text": "🛒 Кошик"}, {"text": "👤 Профіль"}],
            [{"text": "🔍 Пошук"}, {"text": "🆘 Допомога"}]
        ],
        "resize_keyboard": True
    }

def kb_categories():
    """Клавіатура категорій"""
    categories = get_categories()
    kb = {"inline_keyboard": []}
    for cat in categories:
        kb["inline_keyboard"].append([{"text": f"🍽️ {cat}", "callback_data": f"cat:{cat}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "back"}])
    return kb

def kb_item(item, cat, idx, total):
    """Клавіатура для товару"""
    name = item.get('Назва Страви', '')
    kb = {"inline_keyboard": [[{"text": "➕ Додати", "callback_data": f"add:{name}"}]]}
    
    if total > 1:
        nav = []
        if idx > 0:
            nav.append({"text": "⬅️", "callback_data": f"item:{cat}:{idx-1}"})
        nav.append({"text": f"{idx+1}/{total}", "callback_data": "noop"})
        if idx < total - 1:
            nav.append({"text": "➡️", "callback_data": f"item:{cat}:{idx+1}"})
        kb["inline_keyboard"].append(nav)
    
    photo_url = item.get('Фото URL', '')
    if photo_url:
        kb["inline_keyboard"].append([{"text": "📸 Показати фото", "url": photo_url}])
    
    kb["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "back_cat"}])
    return kb

def kb_cart():
    """Клавіатура корзини"""
    return {
        "keyboard": [
            [{"text": "✅ Оформити"}],
            [{"text": "🗑️ Очистити"}, {"text": "📋 Меню"}]
        ],
        "resize_keyboard": True
    }

# =============================================================================
# ВІДПРАВКА ПОВІДОМЛЕНЬ
# =============================================================================

def send_msg(chat_id, text, markup=None):
    """Wrapper для відправки з логуванням"""
    try:
        logger.info(f"📤 Sending to {chat_id}: {text[:50]}...")
        result = tg_service.tg_send_message(chat_id, text, markup, "HTML")
        if result and result.get("ok"):
            logger.info(f"✅ Message delivered to {chat_id}")
        else:
            logger.error(f"❌ Message failed to {chat_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Send error to {chat_id}: {e}", exc_info=True)
        return None

# =============================================================================
# ОБРОБНИКИ КОМАНД
# =============================================================================

def handle_start(chat_id, first_name=None):
    """Команда /start"""
    try:
        clear_state(chat_id)
        set_state(chat_id, State.MAIN_MENU)
        
        text = (
            f"{random_greeting()}\n\n"
            "🍽️ <i>Замовляйте смачну їжу онлайн</i>\n"
            "🚀 <i>Доставка за 30-45 хв</i>\n"
            "💳 <i>Оплата при отриманні</i>\n"
            "⭐ <i>Гарячі і свіжі страви</i>\n\n"
            f"{'─'*30}\n"
            "<b>Що ви хочете зробити?</b>"
        )
        
        send_msg(chat_id, text, kb_main())
    except Exception as e:
        logger.error(f"Error in handle_start: {e}", exc_info=True)

def handle_menu(chat_id):
    """Показати категорії"""
    try:
        set_state(chat_id, State.BROWSING_CATEGORIES)
        categories = get_categories()
        
        if not categories:
            send_msg(chat_id, "❌ Меню порожнє. Спробуйте пізніше.", kb_main())
            return
        
        text = (
            "📋 <b>НАШЕ МЕНЮ</b>\n"
            f"{'─'*30}\n\n"
            f"{random_menu_starter()}\n\n"
            f"✨ <i>Доступно {len(categories)} категорій</i>\n\n"
            "<b>Оберіть цікаву для вас:</b>"
        )
        
        send_msg(chat_id, text, kb_categories())
    except Exception as e:
        logger.error(f"Error in handle_menu: {e}", exc_info=True)

def show_item(chat_id, category, index):
    """Показує конкретний товар"""
    try:
        items = get_items_by_category(category)
        
        if not items or index < 0 or index >= len(items):
            send_msg(chat_id, "❌ Товар не знайдено", kb_main())
            return
        
        set_state(chat_id, State.VIEWING_ITEM, category=category, index=index)
        
        item = items[index]
        text = format_item(item)
        photo = item.get('Фото URL', '')
        kb = kb_item(item, category, index, len(items))
        
        if photo and photo.startswith('http'):
            try:
                tg_service.tg_send_photo(chat_id, photo, caption=text, reply_markup=kb)
            except Exception as photo_err:
                logger.error(f"Photo send failed: {photo_err}")
                send_msg(chat_id, text, kb)
        else:
            send_msg(chat_id, text, kb)
    except Exception as e:
        logger.error(f"Error in show_item: {e}", exc_info=True)

def add_to_cart(chat_id, item_name):
    """Додає товар в корзину"""
    try:
        item = find_item_by_name(item_name)
        
        if not item:
            send_msg(chat_id, "❌ Товар не знайдено")
            return
        
        with user_carts_lock:
            cart = user_carts[chat_id]
            
            if len(cart) >= MAX_CART_ITEMS:
                send_msg(chat_id, f"❌ Максимум {MAX_CART_ITEMS} різних товарів")
                return
            
            current = cart.get(item_name, 0)
            if current >= MAX_ITEM_QUANTITY:
                send_msg(chat_id, f"❌ Максимум {MAX_ITEM_QUANTITY} шт")
                return
            
            cart[item_name] = current + 1
        
        name = safe_escape(item.get('Назва Страви'))
        price = safe_escape(item.get('Ціна', '0'))
        qty = cart[item_name]
        
        text = (
            f"{random_success()}\n\n"
            f"🍽️ <b>{name}</b>\n"
            f"💰 {price} ₴\n"
            f"📦 В кошику: <b>{qty}</b> шт\n\n"
            f"{'─'*30}\n"
            "Що далі?"
        )
        
        kb = {
            "inline_keyboard": [
                [
                    {"text": "🛒 До кошика", "callback_data": "cart"},
                    {"text": "📋 Ще щось", "callback_data": "menu"}
                ]
            ]
        }
        
        send_msg(chat_id, text, kb)
    except Exception as e:
        logger.error(f"Error in add_to_cart: {e}", exc_info=True)

def handle_cart(chat_id):
    """Показати корзину"""
    try:
        set_state(chat_id, State.IN_CART)
        text = format_cart(chat_id)
        
        with user_carts_lock:
            has_items = len(user_carts.get(chat_id, {})) > 0
        
        kb = kb_cart() if has_items else kb_main()
        send_msg(chat_id, text, kb)
    except Exception as e:
        logger.error(f"Error in handle_cart: {e}", exc_info=True)

def handle_profile(chat_id):
    """Показати профіль"""
    try:
        text = (
            "👤 <b>ВАШ ПРОФІЛЬ</b>\n"
            f"{'─'*30}\n\n"
            "🛍️ <b>Замовлень:</b> 0\n"
            "💸 <b>Бонусів:</b> 0 ₴\n"
            "🌟 <b>Статус:</b> Новачок\n"
            "🎁 <b>Знижка:</b> 0%\n\n"
            "<i>Зробіть замовлення й отримайте бонуси!</i>"
        )
        send_msg(chat_id, text, kb_main())
    except Exception as e:
        logger.error(f"Error in handle_profile: {e}", exc_info=True)

def handle_recommendations(chat_id):
    """Показати рекомендації"""
    try:
        text = (
            "⭐ <b>РЕКОМЕНДАЦІЇ</b>\n"
            f"{'─'*30}\n\n"
            "👨‍🍳 <i>Цього дня:</i>\n\n"
            "1️⃣ Чорний бургер - 149₴\n"
            "   <i>Бестселер! 🔥</i>\n\n"
            "2️⃣ Латте - 89₴\n"
            "   <i>Ідеально до бургера ☕</i>\n\n"
            "💡 Перейдіть у меню щоб замовити!"
        )
        send_msg(chat_id, text, kb_main())
    except Exception as e:
        logger.error(f"Error in handle_recommendations: {e}", exc_info=True)

def handle_help(chat_id):
    """Допомога"""
    try:
        text = (
            "🆘 <b>ДОПОМОГА</b>\n"
            f"{'─'*30}\n\n"
            "<b>Як замовити:</b>\n"
            "1️⃣ 📋 Меню — оберіть категорію\n"
            "2️⃣ Виберіть страву\n"
            "3️⃣ ➕ Додайте в кошик\n"
            "4️⃣ 🛒 Кошик — оформіть\n\n"
            "<b>📞 Контакти:</b>\n"
            "☎️ +38 (99) 123-45-67\n"
            "📧 support@hubsy.ua\n\n"
            "🤔 Питання? Пишіть!"
        )
        send_msg(chat_id, text, kb_main())
    except Exception as e:
        logger.error(f"Error in handle_help: {e}", exc_info=True)

def handle_search(chat_id):
    """Пошук"""
    try:
        if not AI_ENABLED:
            send_msg(chat_id, "🔍 Пошук тимчасово недоступний", kb_main())
            return
        
        set_state(chat_id, State.SEARCHING)
        text = (
            "🔍 <b>ПОШУК</b>\n"
            f"{'─'*30}\n\n"
            "Напишіть що шукаєте:\n\n"
            "💡 Наприклад:\n"
            "• щось гостре 🌶️\n"
            "• вегетаріанське 🥗\n"
            "• десерт 🍰"
        )
        kb = {"keyboard": [[{"text": "❌ Скасувати"}]], "resize_keyboard": True}
        send_msg(chat_id, text, kb)
    except Exception as e:
        logger.error(f"Error in handle_search: {e}", exc_info=True)

def start_checkout(chat_id):
    """Початок оформлення"""
    try:
        with user_carts_lock:
            cart = user_carts.get(chat_id, {})
        
        if not cart:
            send_msg(chat_id, "❌ Кошик порожній 😢", kb_main())
            return
        
        set_state(chat_id, State.CHECKOUT_PHONE)
        
        text = (
            "📞 <b>ОФОРМЛЕННЯ</b>\n"
            f"{'─'*30}\n\n"
            "Крок 1️⃣/3️⃣\n\n"
            "📱 Надішліть номер телефону"
        )
        
        kb = {
            "keyboard": [
                [{"text": "📱 Надіслати", "request_contact": True}],
                [{"text": "❌ Скасувати"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        
        send_msg(chat_id, text, kb)
    except Exception as e:
        logger.error(f"Error in start_checkout: {e}", exc_info=True)

def handle_phone(chat_id, phone):
    """Телефон отримано"""
    try:
        set_state(chat_id, State.CHECKOUT_ADDRESS, phone=phone)
        
        text = (
            f"✅ Номер: <code>{phone}</code>\n\n"
            "Крок 2️⃣/3️⃣\n\n"
            "📍 <b>Надішліть адресу доставки</b>\n\n"
            "<i>Наприклад: вул. Хрещатик, 1, кв. 5</i>"
        )
        
        kb = {"keyboard": [[{"text": "❌ Скасувати"}]], "resize_keyboard": True}
        send_msg(chat_id, text, kb)
    except Exception as e:
        logger.error(f"Error in handle_phone: {e}", exc_info=True)

def handle_address(chat_id, address):
    """Адреса отримана"""
    try:
        if len(address) < 10:
            send_msg(chat_id, "❌ Адреса коротка\n\nМінімум 10 символів")
            return
        
        set_state(chat_id, State.CHECKOUT_CONFIRM, address=address)
        
        phone = get_state_data(chat_id, 'phone', 'N/A')
        summary = format_cart(chat_id)
        
        text = (
            f"{summary}\n\n"
            f"{'─'*30}\n\n"
            f"📞 <b>Телефон:</b> <code>{phone}</code>\n"
            f"📍 <b>Адреса:</b> {safe_escape(address)}\n\n"
            "Крок 3️⃣/3️⃣\n\n"
            "<b>Підтвердіть ✅</b>"
        )
        
        kb = {
            "keyboard": [
                [{"text": "✅ Підтвердити"}],
                [{"text": "❌ Скасувати"}]
            ],
            "resize_keyboard": True
        }
        
        send_msg(chat_id, text, kb)
    except Exception as e:
        logger.error(f"Error in handle_address: {e}", exc_info=True)

def confirm_order(chat_id