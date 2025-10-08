"""
Hubsy Bot - Telegram Bot для замовлення їжі
Secure Version з виправленнями

Автор: Claude AI + ferrik
Дата: 2025-10-08
"""

import os
import sys
import logging
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
logger.info("Starting Hubsy Bot (Secure Version)...")

# =============================================================================
# ІМПОРТ CONFIG
# =============================================================================

try:
    import bot_config as config
    
    # Backward compatibility aliases
    BOT_TOKEN = config.BOT_TOKEN
    WEBHOOK_SECRET = config.WEBHOOK_SECRET
    GOOGLE_SHEET_ID = config.GOOGLE_SHEET_ID
    SPREADSHEET_ID = config.GOOGLE_SHEET_ID  # Alias
    OPERATOR_CHAT_ID = config.OPERATOR_CHAT_ID
    
    logger.info("✅ Config loaded successfully")
    
except ImportError as e:
    logger.critical(f"Config import failed: {e}")
    print(f"\nError: Cannot start without config\n")
    sys.exit(1)

# =============================================================================
# ІМПОРТИ СЕРВІСІВ
# =============================================================================

try:
    from services import telegram as tg_service
    from services import sheets as sheets_service
    from services import database as db_service
    
    # Gemini опціонально
    try:
        from services import gemini as ai_service
        AI_ENABLED = True
    except ImportError:
        logger.warning("Gemini service not available")
        AI_ENABLED = False
    
    logger.info("✅ Services imported")
    
except ImportError as e:
    logger.error(f"Failed to import services: {e}")
    logger.error("Make sure all service files exist in services/ directory")
    sys.exit(1)

# =============================================================================
# FLASK APP
# =============================================================================

app = Flask(__name__)

# =============================================================================
# ГЛОБАЛЬНІ ЗМІННІ (поступово мігруємо на Redis)
# =============================================================================

from collections import defaultdict
from threading import RLock

# Стани користувачів
user_states = {}
user_states_lock = RLock()

# Корзини
user_carts = defaultdict(dict)
user_carts_lock = RLock()

# Кеш меню
menu_cache = []
menu_cache_lock = RLock()

# Константи
MAX_CART_ITEMS = getattr(config, 'MAX_CART_ITEMS', 50)
MAX_ITEM_QUANTITY = getattr(config, 'MAX_ITEM_QUANTITY', 99)

logger.info("✅ Global variables initialized")

# =============================================================================
# HELPER ФУНКЦІЇ
# =============================================================================

def get_menu():
    """Отримує меню з кешу або завантажує"""
    global menu_cache
    
    with menu_cache_lock:
        if not menu_cache:
            logger.info("Loading menu from Google Sheets...")
            try:
                menu_cache = sheets_service.get_menu_from_sheet()
                logger.info(f"✅ Menu loaded: {len(menu_cache)} items")
            except Exception as e:
                logger.error(f"Failed to load menu: {e}")
                return []
        
        return menu_cache


def refresh_menu():
    """Оновлює кеш меню"""
    global menu_cache
    
    try:
        with menu_cache_lock:
            menu_cache = sheets_service.get_menu_from_sheet()
        logger.info(f"✅ Menu refreshed: {len(menu_cache)} items")
        return True
    except Exception as e:
        logger.error(f"Failed to refresh menu: {e}")
        return False


def get_categories():
    """Отримує унікальні категорії"""
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


# =============================================================================
# ФОРМАТУВАННЯ
# =============================================================================

import html

def safe_html_escape(text):
    """Безпечно escape HTML"""
    if text is None:
        return ""
    return html.escape(str(text))


def format_item(item):
    """Форматує товар для відображення"""
    name = safe_html_escape(item.get('Назва Страви', 'Без назви'))
    category = safe_html_escape(item.get('Категорія', 'Без категорії'))
    price = safe_html_escape(item.get('Ціна', '0'))
    description = safe_html_escape(item.get('Опис', ''))
    
    text = f"<b>{name}</b>\n"
    text += f"<i>Категорія:</i> {category}\n"
    
    if description:
        text += f"{description}\n"
    
    text += f"<b>Ціна:</b> {price} грн"
    
    return text


def get_cart_summary(chat_id):
    """Формує summary корзини"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        return "🛒 Ваша корзина порожня"
    
    summary = "🛒 <b>Ваша корзина:</b>\n\n"
    total = 0
    
    for item_name, quantity in cart.items():
        item = find_item_by_name(item_name)
        if item:
            name = safe_html_escape(item.get('Назва Страви', 'N/A'))
            price = float(item.get('Ціна', 0))
            item_total = price * quantity
            total += item_total
            
            summary += f"▫️ <b>{name}</b>\n"
            summary += f"   {price:.2f} грн x {quantity} = {item_total:.2f} грн\n\n"
    
    summary += f"💰 <b>Разом:</b> {total:.2f} грн"
    
    return summary


# =============================================================================
# TELEGRAM API
# =============================================================================

def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """Відправляє повідомлення"""
    try:
        return tg_service.tg_send_message(chat_id, text, reply_markup, parse_mode)
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        return None


def create_main_keyboard():
    """Головна клавіатура"""
    return {
        "keyboard": [
            [{"text": "📋 Меню"}, {"text": "🛒 Корзина"}],
            [{"text": "🔍 Пошук"}, {"text": "ℹ️ Допомога"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }


def create_categories_keyboard():
    """Клавіатура категорій"""
    categories = get_categories()
    
    keyboard = {"inline_keyboard": []}
    
    for category in categories:
        keyboard["inline_keyboard"].append([
            {"text": category, "callback_data": f"category:{category}"}
        ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔙 Назад", "callback_data": "back_to_main"}
    ])
    
    return keyboard


def create_item_keyboard(item):
    """Клавіатура для товару"""
    item_name = item.get('Назва Страви', 'unknown')
    
    return {
        "inline_keyboard": [
            [{"text": "➕ Додати в корзину", "callback_data": f"add:{item_name}"}],
            [{"text": "🔙 Назад", "callback_data": "back_to_categories"}]
        ]
    }


# =============================================================================
# ОБРОБНИКИ КОМАНД
# =============================================================================

def handle_start(chat_id):
    """Команда /start"""
    welcome_text = (
        "👋 Вітаємо в Hubsy Bot!\n\n"
        "Тут ви можете:\n"
        "📋 Переглянути меню\n"
        "🛒 Оформити замовлення\n"
    )
    
    if AI_ENABLED:
        welcome_text += "🔍 Знайти страви за допомогою AI\n"
    
    welcome_text += "\nОберіть дію з меню:"
    
    send_message(chat_id, welcome_text, reply_markup=create_main_keyboard())
    
    with user_states_lock:
        user_states[chat_id] = None


def handle_menu(chat_id):
    """Показати меню"""
    text = "📋 <b>Оберіть категорію:</b>"
    send_message(chat_id, text, reply_markup=create_categories_keyboard())


def handle_cart(chat_id):
    """Показати корзину"""
    summary = get_cart_summary(chat_id)
    
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if cart:
        keyboard = {
            "keyboard": [
                [{"text": "✅ Оформити замовлення"}],
                [{"text": "🗑 Очистити корзину"}],
                [{"text": "🔙 Назад"}]
            ],
            "resize_keyboard": True
        }
        send_message(chat_id, summary, reply_markup=keyboard)
    else:
        send_message(chat_id, summary, reply_markup=create_main_keyboard())


def handle_search(chat_id):
    """Пошук"""
    if not AI_ENABLED:
        send_message(
            chat_id,
            "🔍 Функція пошуку тимчасово недоступна.\n"
            "Перегляньте меню: /menu"
        )
        return
    
    text = (
        "🔍 <b>Пошук страв</b>\n\n"
        "Напишіть що ви шукаєте:\n"
        "Наприклад: 'щось гостре' або 'вегетаріанські страви'"
    )
    
    with user_states_lock:
        user_states[chat_id] = 'searching'
    
    send_message(chat_id, text)


def handle_help(chat_id):
    """Допомога"""
    text = (
        "ℹ️ <b>Допомога</b>\n\n"
        "Команди:\n"
        "/start - Головне меню\n"
        "/menu - Показати меню\n"
        "/cart - Переглянути корзину\n"
        "/help - Ця довідка\n\n"
        "Як замовити:\n"
        "1. Оберіть 📋 Меню\n"
        "2. Виберіть категорію\n"
        "3. Додайте товари в 🛒 Корзину\n"
        "4. Оформіть замовлення"
    )
    
    send_message(chat_id, text, reply_markup=create_main_keyboard())


def handle_cancel(chat_id):
    """Команда /cancel"""
    with user_states_lock:
        user_states[chat_id] = None
    
    send_message(chat_id, "✅ Дію скасовано", reply_markup=create_main_keyboard())


# =============================================================================
# ОБРОБКА CALLBACK QUERIES
# =============================================================================

def handle_callback_category(chat_id, category):
    """Вибрано категорію"""
    items = get_items_by_category(category)
    
    if not items:
        send_message(chat_id, f"❌ Категорія '{category}' порожня")
        return
    
    # Показуємо перший товар
    item = items[0]
    text = format_item(item)
    
    keyboard = create_item_keyboard(item)
    
    if len(items) > 1:
        keyboard["inline_keyboard"].insert(1, [
            {"text": "⬅️", "callback_data": f"prev:{category}:0"},
            {"text": f"1/{len(items)}", "callback_data": "noop"},
            {"text": "➡️", "callback_data": f"next:{category}:0"}
        ])
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_callback_add_to_cart(chat_id, item_name):
    """Додати в корзину"""
    item = find_item_by_name(item_name)
    
    if not item:
        send_message(chat_id, "❌ Товар не знайдено")
        return
    
    with user_carts_lock:
        cart = user_carts[chat_id]
        
        if len(cart) >= MAX_CART_ITEMS:
            send_message(chat_id, f"❌ Максимум {MAX_CART_ITEMS} товарів у корзині")
            return
        
        current_quantity = cart.get(item_name, 0)
        
        if current_quantity >= MAX_ITEM_QUANTITY:
            send_message(chat_id, f"❌ Максимум {MAX_ITEM_QUANTITY} шт одного товару")
            return
        
        cart[item_name] = current_quantity + 1
    
    send_message(chat_id, f"✅ {item_name} додано в корзину!")


# =============================================================================
# CHECKOUT
# =============================================================================

def handle_checkout_start(chat_id):
    """Початок оформлення"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        send_message(chat_id, "❌ Корзина порожня", reply_markup=create_main_keyboard())
        return
    
    text = "📝 Для оформлення надішліть ваш номер телефону"
    
    keyboard = {
        "keyboard": [[
            {"text": "📱 Надіслати номер", "request_contact": True}
        ]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    
    with user_states_lock:
        user_states[chat_id] = 'awaiting_contact'
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_contact_received(chat_id, contact):
    """Отримано контакт"""
    phone = contact.get('phone_number')
    
    if not phone:
        send_message(chat_id, "❌ Не вдалося отримати номер")
        return
    
    # Зберігаємо телефон
    with user_states_lock:
        if chat_id not in user_states:
            user_states[chat_id] = {}
        if isinstance(user_states[chat_id], dict):
            user_states[chat_id]['phone'] = phone
        else:
            user_states[chat_id] = {'phone': phone}
    
    text = "📍 Тепер надішліть адресу доставки"
    
    with user_states_lock:
        user_states[chat_id] = 'awaiting_address'
    
    send_message(chat_id, text)


def handle_address_received(chat_id, address):
    """Отримано адресу"""
    if len(address) < 10:
        send_message(chat_id, "❌ Адреса занадто коротка (мінімум 10 символів)")
        return
    
    # Фінальне підтвердження
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    summary = get_cart_summary(chat_id)
    
    # Отримати телефон
    phone = "N/A"
    with user_states_lock:
        state_data = user_states.get(chat_id, {})
        if isinstance(state_data, dict):
            phone = state_data.get('phone', 'N/A')
    
    text = f"{summary}\n\n"
    text += f"📱 Телефон: {phone}\n"
    text += f"📍 Адреса: {safe_html_escape(address)}\n\n"
    text += "Підтвердити замовлення?"
    
    keyboard = {
        "keyboard": [
            [{"text": "✅ Підтвердити"}],
            [{"text": "❌ Скасувати"}]
        ],
        "resize_keyboard": True
    }
    
    # Зберегти адресу
    with user_states_lock:
        state_data = user_states.get(chat_id, {})
        if isinstance(state_data, dict):
            state_data['address'] = address
            user_states[chat_id] = 'awaiting_confirmation'
        else:
            user_states[chat_id] = {'address': address, 'state': 'awaiting_confirmation'}
    
    send_message(chat_id, text, reply_markup=keyboard)


def handle_order_confirmation(chat_id):
    """Підтвердження замовлення"""
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        send_message(chat_id, "❌ Корзина порожня")
        return
    
    try:
        # Отримати контакти
        contact_info = {}
        with user_states_lock:
            state_data = user_states.get(chat_id, {})
            if isinstance(state_data, dict):
                contact_info = state_data
        
        phone = contact_info.get('phone', 'N/A')
        address = contact_info.get('address', 'N/A')
        
        # Розрахувати total
        total = 0
        for item_name, quantity in cart.items():
            item = find_item_by_name(item_name)
            if item:
                price = float(item.get('Ціна', 0))
                total += price * quantity
        
        # Зберегти в database
        order_id = db_service.save_order(
            chat_id=chat_id,
            cart=cart,
            contact_info={'phone': phone, 'address': address},
            total=str(total)
        )
        
        if not order_id:
            raise Exception("Database save failed")
        
        # Очистити корзину
        with user_carts_lock:
            user_carts[chat_id] = {}
        
        with user_states_lock:
            user_states[chat_id] = None
        
        # Sheets sync (не критично)
        try:
            sheets_service.save_order_to_sheets(order_id, cart, contact_info)
        except Exception as e:
            logger.error(f"Sheets sync failed: {e}")
        
        # Повідомлення оператору
        if OPERATOR_CHAT_ID:
            try:
                operator_msg = f"🆕 <b>Нове замовлення #{order_id}</b>\n\n"
                operator_msg += get_cart_summary(chat_id)
                operator_msg += f"\n\n📱 Телефон: {phone}\n📍 Адреса: {address}"
                
                send_message(OPERATOR_CHAT_ID, operator_msg)
            except Exception as e:
                logger.error(f"Failed to notify operator: {e}")
        
        # Повідомлення користувачу
        user_msg = f"✅ <b>Замовлення #{order_id} прийнято!</b>\n\n"
        user_msg += f"💰 Сума: {total:.2f} грн\n\n"
        user_msg += "Наш оператор зв'яжеться з вами найближчим часом.\nДякуємо! 🎉"
        
        send_message(chat_id, user_msg, reply_markup=create_main_keyboard())
        
        logger.info(f"✅ Order {order_id} created for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Checkout failed: {e}")
        send_message(
            chat_id,
            "❌ Помилка при оформленні. Спробуйте пізніше.",
            reply_markup=create_main_keyboard()
        )


# =============================================================================
# WEBHOOK HANDLER
# =============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint"""
    # Перевірка secret
    received_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    
    if received_secret != WEBHOOK_SECRET:
        logger.warning(f"⚠️  Webhook auth failed from {request.remote_addr}")
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        update = request.get_json()
        
        if not update:
            return jsonify({"status": "ok"}), 200
        
        # Обробка повідомлення
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            
            # Команди
            if 'text' in message:
                text = message['text']
                
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
                        handle_cancel(chat_id)
                    else:
                        send_message(chat_id, "❌ Невідома команда. /help для допомоги")
                
                else:
                    # Текст відповідно до стану
                    current_state = user_states.get(chat_id)
                    
                    if current_state == 'searching' and AI_ENABLED:
                        # AI пошук
                        try:
                            results = ai_service.search_menu(text, get_menu())
                            
                            if results:
                                send_message(chat_id, f"🔍 Знайдено {len(results)} результатів:")
                                
                                for item in results[:5]:
                                    item_text = format_item(item)
                                    send_message(chat_id, item_text, reply_markup=create_item_keyboard(item))
                            else:
                                send_message(chat_id, "😔 Нічого не знайдено")
                            
                            with user_states_lock:
                                user_states[chat_id] = None
                            
                            send_message(chat_id, "Що далі?", reply_markup=create_main_keyboard())
                        except Exception as e:
                            logger.error(f"Search failed: {e}")
                            send_message(chat_id, "❌ Помилка пошуку")
                    
                    elif current_state == 'awaiting_address':
                        handle_address_received(chat_id, text)
                    
                    elif current_state == 'awaiting_confirmation':
                        if text == "✅ Підтвердити":
                            handle_order_confirmation(chat_id)
                        elif text == "❌ Скасувати":
                            handle_cancel(chat_id)
                    
                    else:
                        # Кнопки меню
                        if text == "📋 Меню":
                            handle_menu(chat_id)
                        elif text == "🛒 Корзина":
                            handle_cart(chat_id)
                        elif text == "🔍 Пошук":
                            handle_search(chat_id)
                        elif text == "ℹ️ Допомога":
                            handle_help(chat_id)
                        elif text == "✅ Оформити замовлення":
                            handle_checkout_start(chat_id)
                        elif text == "🗑 Очистити корзину":
                            with user_carts_lock:
                                user_carts[chat_id] = {}
                            send_message(chat_id, "✅ Корзину очищено", reply_markup=create_main_keyboard())
                        elif text == "🔙 Назад":
                            handle_start(chat_id)
                        else:
                            send_message(chat_id, "Оберіть дію з меню", reply_markup=create_main_keyboard())
            
            # Контакт
            elif 'contact' in message:
                handle_contact_received(chat_id, message['contact'])
        
        # Callback queries
        elif 'callback_query' in update:
            callback = update['callback_query']
            callback_id = callback['id']
            chat_id = callback['message']['chat']['id']
            data = callback['data']
            
            # Відповісти на callback
            tg_service.tg_answer_callback_query(callback_id)
            
            if data.startswith('category:'):
                category = data.split(':', 1)[1]
                handle_callback_category(chat_id, category)
            
            elif data.startswith('add:'):
                item_name = data.split(':', 1)[1]
                handle_callback_add_to_cart(chat_id, item_name)
            
            elif data == 'back_to_categories':
                handle_menu(chat_id)
            
            elif data == 'back_to_main':
                handle_start(chat_id)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500


# =============================================================================
# HEALTH & ADMIN ENDPOINTS
# =============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    try:
        menu_ok = len(get_menu()) > 0
        
        return jsonify({
            "status": "healthy" if menu_ok else "degraded",
            "menu_items": len(menu_cache),
            "version": "2.0.0-secure"
        }), 200 if menu_ok else 503
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


@app.route('/admin/refresh_menu', methods=['POST'])
def admin_refresh_menu():
    """Оновити меню"""
    success = refresh_menu()
    
    if success:
        return jsonify({"status": "ok", "items": len(menu_cache)})
    else:
        return jsonify({"status": "error"}), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "service": "Hubsy Bot",
        "status": "running",
        "version": "2.0.0-secure"
    })


# =============================================================================
# ІНІЦІАЛІЗАЦІЯ
# =============================================================================

def initialize_bot():
    """Ініціалізація при старті"""
    logger.info("=" * 60)
    logger.info("INITIALIZING HUBSY BOT")
    logger.info("=" * 60)
    
    # Завантажити меню
    logger.info("Loading menu...")
    menu = get_menu()
    logger.info(f"✅ Menu loaded: {len(menu)} items")
    
    # Налаштувати webhook (якщо є URL)
    if hasattr(config, 'WEBHOOK_URL') and config.WEBHOOK_URL:
        logger.info("Setting up webhook...")
        try:
            success = tg_service.setup_webhook_safe()
            if success:
                logger.info("✅ Webhook configured")
            else:
                logger.warning("⚠️  Webhook setup failed (non-critical)")
        except Exception as e:
            logger.warning(f"⚠️  Webhook setup error: {e}")
    else:
        logger.warning("⚠️  WEBHOOK_URL not set, skipping webhook setup")
    
    logger.info("=" * 60)
    logger.info("✅ BOT INITIALIZED SUCCESSFULLY")
    logger.info("=" * 60)


# =============================================================================
# ЗАПУСК
# =============================================================================

if __name__ == '__main__':
    try:
        initialize_bot()
        
        port = getattr(config, 'PORT', 10000)
        
        logger.info(f"Starting server on port {port}")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=getattr(config, 'FLASK_DEBUG', False)
        )
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        raise
