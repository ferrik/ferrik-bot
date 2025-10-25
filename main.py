"""
🤖 Ferrik Bot - RENDER READY VERSION

Готовий до deploy на Render без локального тестування
Автоматично створює БД при першому запуску
"""
import os
import sys
import logging
from flask import Flask, request, jsonify

# ============================================================================
# Logging Setup
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Auto-initialize Database (ПЕРЕД імпортами!)
# ============================================================================
def ensure_database():
    """Автоматично створює БД якщо її немає"""
    import sqlite3
    
    db_path = 'bot.db'
    
    if not os.path.exists(db_path):
        logger.info("🔧 Database not found, initializing...")
        
        conn = sqlite3.connect(db_path)
        
        # Спроба завантажити з файлу міграції
        sql_file = 'migrations/001_create_tables.sql'
        if os.path.exists(sql_file):
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    conn.executescript(f.read())
                logger.info("✅ Database initialized from migration file")
            except Exception as e:
                logger.error(f"❌ Error loading migration: {e}")
                # Fallback до базових таблиць
                create_basic_tables(conn)
        else:
            logger.warning("⚠️ Migration file not found, creating basic tables")
            create_basic_tables(conn)
        
        conn.commit()
        conn.close()
        logger.info("✅ Database ready!")
    else:
        logger.info("✅ Database already exists")

def create_basic_tables(conn):
    """Створити мінімальні таблиці якщо міграція не знайдена"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT DEFAULT 'STATE_IDLE',
            state_data TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_carts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            quantity INTEGER DEFAULT 1 CHECK(quantity > 0),
            price REAL DEFAULT 0 CHECK(price >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, item_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_carts_user ON user_carts(user_id)")
    logger.info("✅ Basic tables created")

# Запустити ініціалізацію БД
ensure_database()

# ============================================================================
# Import New Modules (з fallback на старий код)
# ============================================================================
NEW_SYSTEM_ENABLED = False

try:
    from app.config.settings import (
        config, 
        UserState, 
        MIN_ORDER_AMOUNT
    )
    from app.services.session import SessionManager
    from app.utils.validators import (
        safe_parse_price,
        validate_phone,
        normalize_phone,
        validate_address,
        sanitize_input
    )
    NEW_SYSTEM_ENABLED = True
    logger.info("✅ New system modules loaded")
except ImportError as e:
    logger.warning(f"⚠️ New modules not available, using legacy mode: {e}")
    # Встановити fallback значення
    MIN_ORDER_AMOUNT = 100

# ============================================================================
# Import Services
# ============================================================================
import services.telegram as telegram
import services.sheets as sheets
import services.database as database

# ============================================================================
# Flask App
# ============================================================================
app = Flask(__name__)

# ============================================================================
# Global Variables
# ============================================================================
menu_data = []

# SessionManager або fallback словники
if NEW_SYSTEM_ENABLED:
    # Ініціалізувати SessionManager (він сам створить підключення)
    session_manager = SessionManager(db_path='bot.db')
    
    from app.services.session import LegacyDictWrapper
    user_states = LegacyDictWrapper(session_manager, 'states')
    user_carts = LegacyDictWrapper(session_manager, 'carts')
    logger.info("✅ Using SessionManager with auto-created SQLite connection")
else:
    user_states = {}
    user_carts = {}
    logger.info("📦 Using in-memory storage (legacy)")
    
# Константи станів
STATE_IDLE = 'STATE_IDLE'
STATE_AWAITING_PHONE = 'STATE_AWAITING_PHONE'
STATE_AWAITING_ADDRESS = 'STATE_AWAITING_ADDRESS'

# ============================================================================
# Helper Functions
# ============================================================================

def get_user_state(chat_id):
    """Отримати стан користувача"""
    if NEW_SYSTEM_ENABLED:
        return session_manager.get_state(chat_id)
    return user_states.get(chat_id, STATE_IDLE)

def set_user_state(chat_id, state, data=None):
    """Встановити стан"""
    if NEW_SYSTEM_ENABLED:
        session_manager.set_state(chat_id, state, data or {})
    else:
        user_states[chat_id] = {'state': state, 'data': data or {}}

def clear_user_state(chat_id):
    """Очистити стан"""
    if NEW_SYSTEM_ENABLED:
        session_manager.clear_state(chat_id)
    else:
        user_states.pop(chat_id, None)

def parse_price(value):
    """Безпечний парсинг ціни"""
    if NEW_SYSTEM_ENABLED:
        return safe_parse_price(value)
    try:
        return float(str(value).replace('грн', '').replace(' ', '').replace(',', '.').strip())
    except:
        return 0.0

def add_to_cart(chat_id, item):
    """Додати товар в кошик"""
    item_id = str(item['id'])
    price = parse_price(item.get('Ціна', 0))
    
    if NEW_SYSTEM_ENABLED:
        return session_manager.add_to_cart(chat_id, item_id, 1, price)
    else:
        if chat_id not in user_carts:
            user_carts[chat_id] = {}
        if item_id in user_carts[chat_id]:
            user_carts[chat_id][item_id]['quantity'] += 1
        else:
            user_carts[chat_id][item_id] = {
                'name': item.get('Назва', 'Unknown'),
                'price': price,
                'quantity': 1
            }
        return True

def get_cart(chat_id):
    """Отримати кошик"""
    if NEW_SYSTEM_ENABLED:
        cart_items = session_manager.get_cart(chat_id)
        enriched = []
        for cart_item in cart_items:
            menu_item = next((m for m in menu_data if str(m['id']) == cart_item['id']), None)
            if menu_item:
                enriched.append({
                    'id': cart_item['id'],
                    'name': menu_item.get('Назва', 'Unknown'),
                    'price': cart_item['price'],
                    'quantity': cart_item['quantity']
                })
        return enriched
    return user_carts.get(chat_id, {})

def get_cart_total(chat_id):
    """Сума кошика"""
    if NEW_SYSTEM_ENABLED:
        return session_manager.get_cart_total(chat_id)
    
    cart = user_carts.get(chat_id, {})
    total = 0
    for item in cart.values():
        try:
            total += float(item.get('price', 0)) * int(item.get('quantity', 1))
        except:
            pass
    return total

def clear_cart(chat_id):
    """Очистити кошик"""
    if NEW_SYSTEM_ENABLED:
        session_manager.clear_cart(chat_id)
    else:
        user_carts[chat_id] = {}

def get_cart_count(chat_id):
    """Кількість товарів"""
    if NEW_SYSTEM_ENABLED:
        return session_manager.get_cart_count(chat_id)
    return len(user_carts.get(chat_id, {}))

# ============================================================================
# Menu Display
# ============================================================================

def show_menu_with_buttons(chat_id, category=None):
    """Показати меню"""
    if not menu_data:
        telegram.tg_send_message(chat_id, "❌ Меню не завантажене")
        return
    
    items = [i for i in menu_data if not category or i.get('category') == category]
    if not items:
        telegram.tg_send_message(chat_id, "❌ Товари не знайдені")
        return
    
    buttons = []
    for item in items[:10]:  # Перші 10
        item_id = str(item.get('id', ''))
        name = item.get('Назва', 'Без назви')
        price = parse_price(item.get('Ціна', 0))
        
        buttons.append([
            {'text': f"ℹ️ {name} — {price:.0f}грн", 'callback_data': f"info_{item_id}"},
            {'text': "➕", 'callback_data': f"add_{item_id}"}
        ])
    
    cart_count = get_cart_count(chat_id)
    buttons.append([{'text': f"🛒 Кошик ({cart_count})", 'callback_data': "view_cart"}])
    
    telegram.tg_send_message(chat_id, "📋 *Меню*\nОберіть товар:", buttons)

def show_cart_preview(chat_id):
    """Показати кошик"""
    cart = get_cart(chat_id)
    
    if not cart or (isinstance(cart, dict) and len(cart) == 0):
        telegram.tg_send_message(chat_id, "🛒 Ваш кошик порожній")
        return
    
    cart_text = "🛒 *Ваш кошик:*\n\n"
    
    if NEW_SYSTEM_ENABLED and isinstance(cart, list):
        for item in cart:
            cart_text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']:.0f} грн\n"
    else:
        for item_data in cart.values():
            cart_text += f"• {item_data['name']} x{item_data['quantity']} = {item_data['price'] * item_data['quantity']:.0f} грн\n"
    
    total = get_cart_total(chat_id)
    cart_text += f"\n💰 *Всього: {total:.0f} грн*"
    
    buttons = []
    if total >= MIN_ORDER_AMOUNT:
        buttons.append([{'text': '✅ Оформити', 'callback_data': 'checkout'}])
    else:
        cart_text += f"\n\n⚠️ Мін. сума: {MIN_ORDER_AMOUNT} грн"
    
    buttons.append([
        {'text': '🔙 Меню', 'callback_data': 'back_to_menu'},
        {'text': '🗑️ Очистити', 'callback_data': 'clear_cart'}
    ])
    
    telegram.tg_send_message(chat_id, cart_text, buttons)

# ============================================================================
# Checkout
# ============================================================================

def start_checkout(chat_id):
    """Початок оформлення"""
    set_user_state(chat_id, STATE_AWAITING_PHONE)
    telegram.tg_send_message(chat_id, "📞 Введіть номер телефону:")

def handle_phone_input(chat_id, phone):
    """Обробка телефону"""
    if NEW_SYSTEM_ENABLED:
        phone = sanitize_input(phone, 20)
        if not validate_phone(phone):
            telegram.tg_send_message(chat_id, "❌ Невірний формат\nПриклад: +380501234567")
            return
        phone = normalize_phone(phone)
    else:
        if len(phone) < 10:
            telegram.tg_send_message(chat_id, "❌ Занадто короткий номер")
            return
    
    set_user_state(chat_id, STATE_AWAITING_ADDRESS, {'phone': phone})
    telegram.tg_send_message(chat_id, "📍 Введіть адресу доставки:")

def handle_address_input(chat_id, address):
    """Обробка адреси"""
    if NEW_SYSTEM_ENABLED:
        address = sanitize_input(address, 200)
        if not validate_address(address):
            telegram.tg_send_message(chat_id, "❌ Занадто коротка адреса")
            return
        state_data = session_manager.get_state_data(chat_id)
        phone = state_data.get('phone', 'N/A')
    else:
        phone = user_states.get(chat_id, {}).get('data', {}).get('phone', 'N/A')
    
    cart = get_cart(chat_id)
    total = get_cart_total(chat_id)
    
    order_text = f"""✅ *Замовлення оформлене!*

📞 {phone}
📍 {address}

🛒 *Товари:*
"""
    
    if NEW_SYSTEM_ENABLED and isinstance(cart, list):
        items_list = []
        for item in cart:
            order_text += f"• {item['name']} x{item['quantity']}\n"
            items_list.append({'name': item['name'], 'quantity': item['quantity'], 'price': item['price']})
    else:
        items_list = []
        for item_data in cart.values():
            order_text += f"• {item_data['name']} x{item_data['quantity']}\n"
            items_list.append({'name': item_data['name'], 'quantity': item_data['quantity'], 'price': item_data['price']})
    
    order_text += f"\n💰 Всього: {total:.0f} грн\n\n✨ Зв'яжемося найближчим часом!"
    
    telegram.tg_send_message(chat_id, order_text)
    
    try:
        database.save_order(str(chat_id), phone, address, items_list, total)
        logger.info(f"✅ Order saved for {chat_id}")
    except Exception as e:
        logger.error(f"❌ Order save error: {e}")
    
    clear_cart(chat_id)
    clear_user_state(chat_id)

# ============================================================================
# Webhook
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Головний webhook handler"""
    try:
        secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        expected = os.getenv('WEBHOOK_SECRET', 'default_secret')
        
        if secret != expected:
            logger.warning("⚠️ Invalid secret")
            return jsonify({'ok': False}), 403
        
        data = request.json
        
        # Callback query
        if 'callback_query' in data:
            callback = data['callback_query']
            callback_id = callback['id']
            chat_id = callback['message']['chat']['id']
            callback_data = callback['data']
            
            telegram.tg_answer_callback(callback_id)
            
            if callback_data.startswith('add_'):
                item_id = callback_data.split('_')[1]
                item = next((i for i in menu_data if str(i['id']) == item_id), None)
                if item:
                    add_to_cart(chat_id, item)
                    telegram.tg_send_message(chat_id, f"✅ Додано: {item.get('Назва')}")
            
            elif callback_data == 'view_cart':
                show_cart_preview(chat_id)
            
            elif callback_data == 'back_to_menu':
                show_menu_with_buttons(chat_id)
            
            elif callback_data == 'clear_cart':
                clear_cart(chat_id)
                telegram.tg_send_message(chat_id, "🗑️ Кошик очищено")
            
            elif callback_data == 'checkout':
                start_checkout(chat_id)
            
            elif callback_data.startswith('info_'):
                item_id = callback_data.split('_')[1]
                item = next((i for i in menu_data if str(i['id']) == item_id), None)
                if item:
                    price = parse_price(item.get('Ціна', 0))
                    info_text = f"📦 *{item.get('Назва')}*\n\n💰 {price:.0f} грн\n📝 {item.get('Опис', 'Опис відсутній')}"
                    telegram.tg_send_message(chat_id, info_text)
        
        # Message
        elif 'message' in data:
            msg = data['message']
            chat_id = msg['chat']['id']
            text = msg.get('text', '').strip()
            
            # Логування
            logger.info(f"📥 Message from {chat_id}: {text}")
            
            current_state = get_user_state(chat_id)
            
            # Команди (з підтримкою текстових варіантів)
            if text.startswith('/start') or text.lower() == 'start':
                clear_user_state(chat_id)
                telegram.tg_send_message(
                    chat_id,
                    "👋 Вітаємо в Ferrik Bot!\n\n" +
                    "Використовуйте команди:\n" +
                    "/menu - Каталог товарів\n" +
                    "/cart - Кошик"
                )
            
            elif text.startswith('/menu') or text.lower() in ['меню', 'menu', '📋 меню']:
                show_menu_with_buttons(chat_id)
            
            elif text.startswith('/cart') or text.lower() in ['кошик', 'cart', '🛒 кошик']:
                show_cart_preview(chat_id)
            
            elif text.startswith('/help') or text.lower() == 'help':
                telegram.tg_send_message(
                    chat_id,
                    "📖 *Допомога*\n\n" +
                    "Доступні команди:\n" +
                    "/start - Почати роботу\n" +
                    "/menu - Переглянути каталог\n" +
                    "/cart - Відкрити кошик\n" +
                    "/help - Ця довідка"
                )
            
            elif current_state == STATE_AWAITING_PHONE:
                handle_phone_input(chat_id, text)
            
            elif current_state == STATE_AWAITING_ADDRESS:
                handle_address_input(chat_id, text)
            
            else:
                telegram.tg_send_message(chat_id, "❓ Невідома команда. Спробуйте /menu")
        
        return jsonify({'ok': True}), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500

# ============================================================================
# Health Check
# ============================================================================

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'bot': 'Ferrik Bot',
        'version': '2.0',
        'new_system': NEW_SYSTEM_ENABLED,
        'menu_items': len(menu_data)
    })

@app.route('/health')
def health():
    """Detailed health check"""
    import os
    
    return jsonify({
        'status': 'healthy',
        'database': os.path.exists('bot.db'),
        'menu_loaded': len(menu_data) > 0,
        'new_system': NEW_SYSTEM_ENABLED,
        'environment': os.getenv('ENVIRONMENT', 'unknown')
    })

# ============================================================================
# Initialization
# ============================================================================

def initialize():
    """Ініціалізація бота"""
    global menu_data
    
    logger.info("=" * 60)
    logger.info("🚀 Initializing Ferrik Bot")
    logger.info("=" * 60)
    
    # Завантажити меню
    try:
        menu_data = sheets.get_menu_from_sheet()
        logger.info(f"✅ Menu loaded: {len(menu_data)} items")
    except Exception as e:
        logger.error(f"❌ Menu load error: {e}")
        menu_data = []
    
    # Налаштувати webhook
    try:
        webhook_url = os.getenv('WEBHOOK_URL')
        
        if not webhook_url:
            # Render встановлює RENDER_EXTERNAL_URL автоматично
            render_url = os.getenv('RENDER_EXTERNAL_URL')
            if render_url:
                webhook_url = f"{render_url}/webhook"
        
        if webhook_url:
            telegram.tg_set_webhook(webhook_url)
            logger.info(f"✅ Webhook set: {webhook_url}")
        else:
            logger.warning("⚠️ No webhook URL configured")
    
    except Exception as e:
        logger.error(f"❌ Webhook setup error: {e}")
    
    logger.info("=" * 60)
    logger.info("✅ Bot initialization complete!")
    logger.info("=" * 60)

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Отримати порт (Render встановлює PORT автоматично)
    port = int(os.getenv('PORT', 10000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Показати конфігурацію
    logger.info("=" * 60)
    logger.info("🤖 CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"Port: {port}")
    logger.info(f"Debug: {debug}")
    logger.info(f"New System: {NEW_SYSTEM_ENABLED}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'unknown')}")
    logger.info(f"Database: {'bot.db'}")
    logger.info("=" * 60)
    
    # Ініціалізація (ТІЛЬКИ тут, не при імпорті!)
    initialize()
    
    # Запуск Flask
    logger.info(f"🚀 Starting server on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
