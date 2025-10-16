"""
Hubsy Bot - Main Application
Telegram бот для замовлення їжі з інтеграцією Google Sheets та Gemini AI
"""

import logging
import os
import time
from flask import Flask, request, jsonify
from typing import Dict, Any, List, Optional

import config
from services import sheets, gemini
from services.telegram import (
    tg_send_message as send_message,
    tg_send_photo as send_photo,
    tg_answer_callback as answer_callback_query
)
from services import database

# Logging setup
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Global data
menu_data: List[Dict[str, Any]] = []
user_states: Dict[int, Dict[str, Any]] = {}
user_carts: Dict[int, List[Dict[str, Any]]] = {}

# ============================================================================
# STARTUP - Ініціалізація при завантаженні модуля
# ============================================================================

def initialize():
    """Ініціалізація при старті"""
    global menu_data
    
    logger.info("🚀 Starting Hubsy Bot v3.2.0...")
    
    # Ініціалізація бази даних
    if not database.init_database():
        logger.error("❌ Database initialization failed")
        return False
    
    logger.info("✅ Database initialized")
    
    # Завантаження меню
    try:
        menu_data = sheets.load_menu()
        if menu_data:
            logger.info(f"✅ Menu loaded: {len(menu_data)} items")
        else:
            logger.warning("⚠️ Menu is empty")
    except Exception as e:
        logger.error(f"❌ Menu loading failed: {e}")
    
    # Тест Gemini
    gemini.test_gemini_connection()
    
    return True

# Викликаємо ініціалізацію при завантаженні модуля
initialize()

# ============================================================================
# CART FUNCTIONS (In-Memory)
# ============================================================================

def add_to_cart(user_id: int, item: Dict[str, Any]):
    """Додати товар в кошик"""
    if user_id not in user_carts:
        user_carts[user_id] = []
    
    # Перевіряємо чи товар вже в кошику
    for cart_item in user_carts[user_id]:
        if cart_item.get('id') == item.get('id'):
            cart_item['quantity'] = cart_item.get('quantity', 1) + 1
            return
    
    # Додаємо новий товар
    item['quantity'] = 1
    user_carts[user_id].append(item)


def get_cart(user_id: int) -> List[Dict[str, Any]]:
    """Отримати кошик користувача"""
    return user_carts.get(user_id, [])


def clear_cart(user_id: int):
    """Очистити кошик"""
    if user_id in user_carts:
        user_carts[user_id] = []


def remove_from_cart(user_id: int, item_id: str):
    """Видалити товар з кошика"""
    if user_id in user_carts:
        user_carts[user_id] = [
            item for item in user_carts[user_id] 
            if item.get('id') != item_id
        ]


def get_cart_total(user_id: int) -> float:
    """Розрахувати загальну суму кошика"""
    cart = get_cart(user_id)
    total = sum(
        item.get('price', 0) * item.get('quantity', 1) 
        for item in cart
    )
    return total


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_user_state(user_id: int) -> Dict[str, Any]:
    """Отримати стан користувача"""
    if user_id not in user_states:
        user_states[user_id] = {
            "state": None,
            "data": {}
        }
    return user_states[user_id]


def set_user_state(user_id: int, state: str, data: Dict[str, Any] = None):
    """Встановити стан користувача"""
    user_states[user_id] = {
        "state": state,
        "data": data or {}
    }


def clear_user_state(user_id: int):
    """Очистити стан користувача"""
    if user_id in user_states:
        user_states[user_id] = {"state": None, "data": {}}


# ============================================================================
# KEYBOARD LAYOUTS
# ============================================================================

def get_main_menu():
    """Головне меню"""
    return {
        "keyboard": [
            ["📋 Меню", "🛒 Кошик"],
            ["⭐ Рекомендації", "🔍 Пошук"],
            ["📦 Мої замовлення", "🆘 Допомога"]
        ],
        "resize_keyboard": True
    }


def get_category_menu(categories: List[str]):
    """Меню категорій"""
    keyboard = []
    for i in range(0, len(categories), 2):
        row = categories[i:i+2]
        keyboard.append(row)
    keyboard.append(["◀️ Назад"])
    
    return {
        "keyboard": keyboard,
        "resize_keyboard": True
    }


def get_item_keyboard(item_id: str):
    """Клавіатура для товару"""
    return {
        "inline_keyboard": [
            [
                {"text": "➕ Додати в кошик", "callback_data": f"add_{item_id}"}
            ],
            [
                {"text": "◀️ Назад до категорій", "callback_data": "back_to_categories"}
            ]
        ]
    }


def get_cart_keyboard():
    """Клавіатура кошика"""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Оформити замовлення", "callback_data": "checkout"}
            ],
            [
                {"text": "🗑 Очистити кошик", "callback_data": "clear_cart"}
            ],
            [
                {"text": "◀️ Назад до меню", "callback_data": "back_to_menu"}
            ]
        ]
    }


# ============================================================================
# MESSAGE HANDLERS
# ============================================================================

def handle_start(chat_id: int, username: str):
    """Обробник команди /start"""
    welcome_message = f"""
👋 Вітаємо в <b>Hubsy Bot</b>!

Я допоможу вам замовити смачну їжу швидко та зручно.

🔹 Переглядайте меню
🔹 Додавайте страви в кошик
🔹 Оформляйте замовлення

Оберіть дію з меню нижче 👇
"""
    
    send_message(chat_id, welcome_message, reply_markup=get_main_menu())
    database.log_activity(chat_id, "start", {"username": username})


def handle_menu(chat_id: int):
    """Показати меню"""
    if not menu_data:
        send_message(chat_id, "❌ Меню тимчасово недоступне. Спробуйте пізніше.")
        return
    
    # Отримуємо унікальні категорії
    categories = list(set(
        item.get('Категорія', 'Інше') 
        for item in menu_data 
        if item.get('Категорія')
    ))
    
    if not categories:
        send_message(chat_id, "❌ Категорії не знайдено")
        return
    
    message = "📋 <b>НАШЕ МЕНЮ</b>\n" + "─" * 30 + "\n\nОберіть категорію:"
    
    send_message(
        chat_id,
        message,
        reply_markup=get_category_menu(categories)
    )
    
    set_user_state(chat_id, "selecting_category")
    database.log_activity(chat_id, "view_menu")


def handle_category(chat_id: int, category: str):
    """Показати страви категорії"""
    items = [item for item in menu_data if item.get('Категорія') == category]
    
    if not items:
        send_message(chat_id, f"❌ Немає страв у категорії '{category}'")
        return
    
    message = f"🍽 <b>{category.upper()}</b>\n" + "─" * 30 + "\n\n"
    
    for item in items:
        name = item.get('Страви', item.get('Назва Страви', 'Без назви'))
        price = item.get('Ціна', 0)
        description = item.get('Опис', '')
        item_id = item.get('ID', '')
        
        message += f"🔹 <b>{name}</b>\n"
        message += f"💰 {price} грн\n"
        if description:
            message += f"📝 {description[:100]}...\n"
        message += "\n"
    
    send_message(chat_id, message, reply_markup=get_main_menu())
    database.log_activity(chat_id, "view_category", {"category": category})


def handle_cart(chat_id: int):
    """Показати кошик"""
    cart = get_cart(chat_id)
    
    if not cart:
        send_message(
            chat_id,
            "🛒 Ваш кошик порожній\n\nОберіть страви з меню 👇",
            reply_markup=get_main_menu()
        )
        return
    
    total = get_cart_total(chat_id)
    
    message = "🛒 <b>ВАШ КОШИК</b>\n" + "─" * 30 + "\n\n"
    
    for item in cart:
        name = item.get('name', 'Без назви')
        price = item.get('price', 0)
        quantity = item.get('quantity', 1)
        
        message += f"🔹 <b>{name}</b>\n"
        message += f"   {quantity} x {price} грн = {quantity * price} грн\n\n"
    
    message += "─" * 30 + "\n"
    message += f"💰 <b>Разом: {total} грн</b>"
    
    send_message(chat_id, message, reply_markup=get_cart_keyboard())
    database.log_activity(chat_id, "view_cart")


def handle_recommendations(chat_id: int):
    """Показати рекомендації"""
    if not menu_data:
        send_message(chat_id, "❌ Меню недоступне")
        return
    
    # Отримуємо популярні страви з бази
    popular = database.get_popular_items(limit=5)
    
    if popular:
        message = "⭐ <b>РЕКОМЕНДАЦІЇ</b>\n" + "─" * 30 + "\n\n"
        message += "🔥 <b>Популярні страви:</b>\n\n"
        
        for dish_name, count in popular:
            # Знаходимо страву в меню
            dish = next((item for item in menu_data if item.get('Страви') == dish_name or item.get('Назва Страви') == dish_name), None)
            if dish:
                price = dish.get('Ціна', 0)
                message += f"🔹 <b>{dish_name}</b>\n"
                message += f"   💰 {price} грн | 👥 Замовили {count} раз\n\n"
    else:
        # Якщо немає популярних - показуємо перші страви
        message = "⭐ <b>РЕКОМЕНДАЦІЇ</b>\n" + "─" * 30 + "\n\n"
        
        for item in menu_data[:5]:
            name = item.get('Страви', item.get('Назва Страви', 'Без назви'))
            price = item.get('Ціна', 0)
            description = item.get('Опис', '')
            
            message += f"🔹 <b>{name}</b>\n"
            message += f"   💰 {price} грн\n"
            if description:
                message += f"   📝 {description[:80]}...\n"
            message += "\n"
    
    send_message(chat_id, message, reply_markup=get_main_menu())
    database.log_activity(chat_id, "view_recommendations")


def handle_search(chat_id: int):
    """Початок пошуку"""
    message = """
🔍 <b>ПОШУК</b>
─────────────────────────────

Напишіть що ви шукаєте:
• Назву страви
• Інгредієнт
• Тип кухні

Наприклад: "піца", "з куркою", "вегетаріанське"
"""
    
    send_message(chat_id, message, reply_markup={"remove_keyboard": True})
    set_user_state(chat_id, "searching")
    database.log_activity(chat_id, "start_search")


def handle_my_orders(chat_id: int):
    """Показати історію замовлень"""
    orders = database.get_user_orders(chat_id, limit=5)
    
    if not orders:
        send_message(
            chat_id,
            "📦 У вас поки немає замовлень\n\nОберіть страви з меню і зробіть перше замовлення! 🍽",
            reply_markup=get_main_menu()
        )
        return
    
    message = "📦 <b>МОЇ ЗАМОВЛЕННЯ</b>\n" + "─" * 30 + "\n\n"
    
    for order in orders:
        order_id = order.get('id', 'N/A')
        total = order.get('total', 0)
        status = order.get('status', 'unknown')
        created_at = order.get('created_at', 'N/A')
        
        status_emoji = {
            'new': '🆕',
            'confirmed': '✅',
            'preparing': '👨‍🍳',
            'ready': '🎉',
            'delivered': '✅',
            'cancelled': '❌'
        }.get(status, '❓')
        
        message += f"{status_emoji} <b>#{order_id[:8]}</b>\n"
        message += f"   💰 {total} грн | 📅 {created_at[:16]}\n"
        message += f"   Статус: {status}\n\n"
    
    send_message(chat_id, message, reply_markup=get_main_menu())
    database.log_activity(chat_id, "view_orders")


def handle_help(chat_id: int):
    """Показати допомогу"""
    help_text = """
🆘 <b>ДОПОМОГА</b>
─────────────────────────────

<b>Як зробити замовлення:</b>
1️⃣ Оберіть "📋 Меню"
2️⃣ Виберіть категорію
3️⃣ Додайте страви в кошик
4️⃣ Перейдіть в "🛒 Кошик"
5️⃣ Оформіть замовлення

<b>Команди:</b>
/start - Почати роботу
/menu - Показати меню
/cart - Переглянути кошик
/help - Ця довідка

<b>Потрібна допомога?</b>
Напишіть @support або зателефонуйте:
📞 +380 XX XXX XX XX
"""
    
    send_message(chat_id, help_text, reply_markup=get_main_menu())
    database.log_activity(chat_id, "view_help")


def handle_checkout(chat_id: int, callback_query_id: str = None):
    """Оформлення замовлення"""
    cart = get_cart(chat_id)
    
    if not cart:
        if callback_query_id:
            answer_callback_query(callback_query_id, "🛒 Кошик порожній")
        return
    
    message = """
📝 <b>ОФОРМЛЕННЯ ЗАМОВЛЕННЯ</b>
─────────────────────────────

Введіть ваші дані у форматі:

<b>Ім'я</b>
<b>Телефон</b>
<b>Адреса доставки</b>

Приклад:
Іван Петренко
+380501234567
вул. Хрещатик, 1, кв. 10
"""
    
    send_message(chat_id, message)
    set_user_state(chat_id, "checkout")
    database.log_activity(chat_id, "start_checkout")


# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

def handle_callback(callback_data: str, chat_id: int, message_id: int, callback_query_id: str):
    """Обробка callback запитів"""
    
    if callback_data.startswith("add_"):
        # Додати товар в кошик
        item_id = callback_data.replace("add_", "")
        item = next((x for x in menu_data if str(x.get('ID')) == str(item_id)), None)
        
        if item:
            add_to_cart(chat_id, {
                'id': item_id,
                'name': item.get('Страви', item.get('Назва Страви', 'Без назви')),
                'price': item.get('Ціна', 0),
                'quantity': 1
            })
            answer_callback_query(callback_query_id, "✅ Додано в кошик!")
            database.log_activity(chat_id, "add_to_cart", {"item_id": item_id})
        else:
            answer_callback_query(callback_query_id, "❌ Товар не знайдено")
    
    elif callback_data == "checkout":
        handle_checkout(chat_id, callback_query_id)
        answer_callback_query(callback_query_id, "📝 Оформлення замовлення")
    
    elif callback_data == "clear_cart":
        clear_cart(chat_id)
        answer_callback_query(callback_query_id, "🗑 Кошик очищено")
        handle_cart(chat_id)
        database.log_activity(chat_id, "clear_cart")
    
    elif callback_data == "back_to_menu":
        handle_menu(chat_id)
        answer_callback_query(callback_query_id, "📋 Меню")
    
    elif callback_data == "back_to_categories":
        handle_menu(chat_id)
        answer_callback_query(callback_query_id, "📋 Категорії")


# ============================================================================
# WEBHOOK HANDLER
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробка webhook від Telegram"""
    try:
        update = request.json
        logger.info(f"📥 Webhook: {update.get('update_id')}")
        
        # Обробка повідомлення
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            username = message['from'].get('username', 'Unknown')
            
            logger.info(f"📨 Message from {chat_id} ({username}): {message.get('text', 'No text')}")
            
            # Текстове повідомлення
            if 'text' in message:
                text = message['text']
                
                # Команди
                if text == '/start':
                    handle_start(chat_id, username)
                elif text == '/menu' or text == '📋 Меню':
                    handle_menu(chat_id)
                elif text == '/cart' or text == '🛒 Кошик':
                    handle_cart(chat_id)
                elif text == '/help' or text == '🆘 Допомога':
                    handle_help(chat_id)
                elif text == '⭐ Рекомендації':
                    handle_recommendations(chat_id)
                elif text == '🔍 Пошук':
                    handle_search(chat_id)
                elif text == '📦 Мої замовлення':
                    handle_my_orders(chat_id)
                elif text == '◀️ Назад':
                    send_message(chat_id, "Головне меню:", reply_markup=get_main_menu())
                    clear_user_state(chat_id)
                
                # Обробка станів
                else:
                    user_data = get_user_state(chat_id)
                    
                    if user_data.get("state") == "selecting_category":
                        # Вибрана категорія
                        handle_category(chat_id, text)
                        clear_user_state(chat_id)
                    
                    elif user_data.get("state") == "searching":
                        # Пошук через Gemini
                        try:
                            query = text
                            
                            # Використовуємо правильну функцію з gemini модуля
                            search_results = gemini.search_menu(query, menu_data)
                            
                            if search_results:
                                # Знайдено страви
                                response = f"🔍 <b>Знайдено {len(search_results)} страв:</b>\n\n"
                                
                                for item in search_results[:5]:  # Показуємо максимум 5
                                    name = item.get('Страви', item.get('Назва Страви', 'Без назви'))
                                    price = item.get('Ціна', 0)
                                    description = item.get('Опис', '')
                                    
                                    response += f"🍽 <b>{name}</b>\n"
                                    response += f"💰 {price} грн\n"
                                    if description:
                                        response += f"📝 {description[:100]}...\n"
                                    response += "\n"
                                
                                send_message(chat_id, response, reply_markup=get_main_menu())
                                
                                # Додатково можна отримати AI коментар
                                ai_comment = gemini.get_ai_response(query, menu_data)
                                if ai_comment:
                                    send_message(chat_id, f"🤖 <b>AI Рекомендація:</b>\n\n{ai_comment}")
                            else:
                                # Нічого не знайдено
                                send_message(
                                    chat_id, 
                                    "❌ Не знайдено страв за вашим запитом 😕\n\n"
                                    "Спробуйте інше формулювання або оберіть категорію з меню.",
                                    reply_markup=get_main_menu()
                                )
                            
                            clear_user_state(chat_id)
                        except Exception as e:
                            logger.error(f"Search error: {e}")
                            send_message(chat_id, "❌ Помилка пошуку 😕\n\nСпробуйте ще раз або оберіть із меню.")
                    
                    elif user_data.get("state") == "checkout":
                        # Обробка даних замовлення
                        try:
                            lines = text.strip().split('\n')
                            if len(lines) >= 3:
                                name = lines[0]
                                phone = lines[1]
                                address = '\n'.join(lines[2:])
                                
                                cart = get_cart(chat_id)
                                total = get_cart_total(chat_id)
                                
                                # Генеруємо ID замовлення
                                order_id = f"ORD{int(time.time())}"
                                
                                # Зберігаємо замовлення
                                success = database.save_order(
                                    order_id=order_id,
                                    user_id=chat_id,
                                    username=username,
                                    items=cart,
                                    total=total,
                                    phone=phone,
                                    address=address,
                                    notes=f"Name: {name}"
                                )
                                
                                if success:
                                    # Повідомлення клієнту
                                    confirmation = f"""
✅ <b>ЗАМОВЛЕННЯ ПРИЙНЯТО!</b>
─────────────────────────────

<b>Номер замовлення:</b> #{order_id}

<b>Ваші дані:</b>
👤 {name}
📞 {phone}
📍 {address}

<b>Сума:</b> {total} грн

Ми зв'яжемося з вами найближчим часом!
"""
                                    send_message(chat_id, confirmation, reply_markup=get_main_menu())
                                    
                                    # Повідомлення оператору
                                    if config.OPERATOR_CHAT_ID:
                                        operator_msg = f"""
🆕 <b>НОВЕ ЗАМОВЛЕННЯ #{order_id}</b>

👤 {name}
📞 {phone}
📍 {address}

<b>Страви:</b>
"""
                                        for item in cart:
                                            operator_msg += f"• {item['name']} x{item['quantity']} - {item['price']*item['quantity']} грн\n"
                                        
                                        operator_msg += f"\n💰 <b>Разом: {total} грн</b>"
                                        
                                        send_message(config.OPERATOR_CHAT_ID, operator_msg)
                                    
                                    # Очищаємо кошик
                                    clear_cart(chat_id)
                                    clear_user_state(chat_id)
                                    
                                    database.log_activity(chat_id, "order_placed", {"order_id": order_id, "total": total})
                                else:
                                    send_message(chat_id, "❌ Помилка збереження замовлення. Спробуйте ще раз.")
                            else:
                                send_message(chat_id, "❌ Неправильний формат. Спробуйте ще раз:\n\nІм'я\nТелефон\nАдреса")
                        except Exception as e:
                            logger.error(f"Checkout error: {e}")
                            send_message(chat_id, "❌ Помилка оформлення. Спробуйте ще раз.")
        
        # Обробка callback query
        elif 'callback_query' in update:
            callback = update['callback_query']
            chat_id = callback['message']['chat']['id']
            message_id = callback['message']['message_id']
            callback_data = callback['data']
            callback_query_id = callback['id']
            
            logger.info(f"🔘 Callback: {callback_data} from {chat_id}")
            
            handle_callback(callback_data, chat_id, message_id, callback_query_id)
        
        return jsonify({"ok": True}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================================
# STARTUP
# ============================================================================

@app.route('/')
def index():
    """Health check"""
    return jsonify({
        "status": "ok",
        "bot": "Hubsy Bot",
        "version": "3.2.0"
    })


@app.route('/health')
def health():
    """Детальна перевірка здоров'я"""
    db_ok, db_info = database.test_connection()
    gemini_ok = gemini.test_gemini_connection()
    
    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "database": db_info,
        "gemini": "ok" if gemini_ok else "unavailable",
        "menu_items": len(menu_data)
    })


# Ініціалізація при завантаженні модуля (для gunicorn)
def initialize():
    """Ініціалізація при старті"""
    global menu_data
    
    logger.info("🚀 Initializing Hubsy Bot v3.2.0...")
    
    # Ініціалізація бази даних
    try:
        if database.init_database():
            logger.info("✅ Database initialized")
        else:
            logger.error("❌ Database initialization failed")
    except Exception as e:
        logger.error(f"❌ Database init error: {e}")
    
    # Завантаження меню
    try:
        menu_data = sheets.load_menu()
        if menu_data:
            logger.info(f"✅ Menu loaded: {len(menu_data)} items")
        else:
            logger.warning("⚠️ Menu is empty")
    except Exception as e:
        logger.error(f"❌ Menu loading failed: {e}")
    
    # Тест Gemini
    try:
        gemini.test_gemini_connection()
    except Exception as e:
        logger.error(f"❌ Gemini test failed: {e}")

# Викликаємо ініціалізацію
initialize()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', config.PORT))
    logger.info(f"🌐 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=config.DEBUG)
