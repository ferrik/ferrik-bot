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
    tg_answer_callback as answer_callback_query,
    tg_edit_message as edit_message
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
    try:
        if database.init_database():
            logger.info("✅ Database initialized")
        else:
            logger.error("❌ Database initialization failed")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
    
    # Завантаження меню
    try:
        if database.USE_POSTGRES:
            # PostgreSQL: синхронізуємо з Sheets, потім читаємо з БД
            logger.info("🐘 Using PostgreSQL for menu storage")
            
            # Синхронізуємо меню з Google Sheets
            if database.sync_menu_from_sheets():
                # Читаємо з PostgreSQL
                menu_data = database.get_menu_from_postgres()
            else:
                # Fallback: читаємо з Sheets якщо синхронізація не вдалася
                logger.warning("⚠️ Sync failed, reading from Sheets")
                menu_data = sheets.get_menu_from_sheet()
        else:
            # SQLite: читаємо напряму з Sheets
            logger.info("📁 Using Google Sheets for menu")
            menu_data = sheets.get_menu_from_sheet()
        
        if menu_data:
            logger.info(f"✅ Menu loaded: {len(menu_data)} items")
            # Debug: показуємо перший елемент
            if menu_data:
                logger.info(f"📋 First item: {menu_data[0].get('Страви', 'N/A')}")
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
            "data": {},
            "selected_restaurant": None
        }
    return user_states[user_id]


def set_user_state(user_id: int, state: str, data: Dict[str, Any] = None):
    """Встановити стан користувача"""
    current = get_user_state(user_id)
    current["state"] = state
    if data:
        current.update(data)
    user_states[user_id] = current


def clear_user_state(user_id: int):
    """Очистити стан користувача"""
    if user_id in user_states:
        user_states[user_id] = {"state": None, "data": {}, "selected_restaurant": None}


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


def get_restaurants_keyboard():
    """Клавіатура з закладами"""
    if not menu_data:
        return get_main_menu()
    
    # Отримуємо унікальні ресторани
    restaurants = list(set(
        item.get('Ресторан', 'Без ресторану') 
        for item in menu_data 
        if item.get('Ресторан')
    ))
    
    keyboard = []
    for i in range(0, len(restaurants), 2):
        row = restaurants[i:i+2]
        keyboard.append(row)
    keyboard.append(["◀️ Назад"])
    
    return {
        "keyboard": keyboard,
        "resize_keyboard": True
    }


def get_category_menu_for_restaurant(restaurant: str):
    """Меню категорій для конкретного ресторану"""
    # Фільтруємо страви по ресторану
    restaurant_items = [item for item in menu_data if item.get('Ресторан') == restaurant]
    
    # Отримуємо категорії
    categories = list(set(
        item.get('Категорія', 'Інше') 
        for item in restaurant_items 
        if item.get('Категорія')
    ))
    
    keyboard = []
    for i in range(0, len(categories), 2):
        row = categories[i:i+2]
        keyboard.append(row)
    keyboard.append(["🛒 Кошик", "◀️ Назад"])
    
    return {
        "keyboard": keyboard,
        "resize_keyboard": True
    }


def get_dish_inline_keyboard(item_id: str, in_cart: bool = False):
    """Inline кнопки для страви"""
    buttons = []
    
    if not in_cart:
        buttons.append([{"text": "➕ Додати в кошик", "callback_data": f"add_{item_id}"}])
    else:
        buttons.append([
            {"text": "➖", "callback_data": f"remove_one_{item_id}"},
            {"text": "✅ В кошику", "callback_data": "noop"},
            {"text": "➕", "callback_data": f"add_{item_id}"}
        ])
    
    buttons.append([{"text": "◀️ Назад", "callback_data": "back_to_category"}])
    
    return {"inline_keyboard": buttons}


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
    """Показати меню - вибір ресторану"""
    if not menu_data:
        send_message(chat_id, "❌ Меню тимчасово недоступне. Спробуйте пізніше.")
        return
    
    # Отримуємо унікальні ресторани
    restaurants = list(set(
        item.get('Ресторан', 'Без ресторану') 
        for item in menu_data 
        if item.get('Ресторан')
    ))
    
    if not restaurants:
        send_message(chat_id, "❌ Ресторани не знайдено")
        return
    
    message = "🏪 <b>ОБЕРІТЬ ЗАКЛАД</b>\n" + "─" * 30 + "\n\n"
    message += "Оберіть ресторан для замовлення:\n\n"
    
    # Показуємо кількість страв в кожному ресторані
    for restaurant in restaurants:
        count = len([x for x in menu_data if x.get('Ресторан') == restaurant])
        message += f"🍽 <b>{restaurant}</b>\n   {count} страв у меню\n\n"
    
    send_message(chat_id, message, reply_markup=get_restaurants_keyboard())
    set_user_state(chat_id, "selecting_restaurant")
    database.log_activity(chat_id, "view_restaurants")


def handle_restaurant_selection(chat_id: int, restaurant: str):
    """Обробка вибору ресторану"""
    # Зберігаємо вибраний ресторан
    user_data = get_user_state(chat_id)
    user_data['selected_restaurant'] = restaurant
    set_user_state(chat_id, "selecting_category", user_data)
    
    # Очищаємо кошик якщо змінили ресторан
    current_cart = get_cart(chat_id)
    if current_cart and current_cart[0].get('restaurant') != restaurant:
        clear_cart(chat_id)
        send_message(
            chat_id, 
            "🗑 Кошик очищено, оскільки ви обрали інший ресторан.\n\n"
            "Усі страви в замовленні повинні бути з одного закладу."
        )
    
    # Показуємо категорії
    restaurant_items = [item for item in menu_data if item.get('Ресторан') == restaurant]
    categories = list(set(
        item.get('Категорія', 'Інше') 
        for item in restaurant_items 
        if item.get('Категорія')
    ))
    
    message = f"🏪 <b>{restaurant.upper()}</b>\n" + "─" * 30 + "\n\n"
    message += "Оберіть категорію:"
    
    send_message(chat_id, message, reply_markup=get_category_menu_for_restaurant(restaurant))
    database.log_activity(chat_id, "select_restaurant", {"restaurant": restaurant})


def handle_category(chat_id: int, category: str):
    """Показати страви категорії"""
    user_data = get_user_state(chat_id)
    restaurant = user_data.get('selected_restaurant')
    
    if not restaurant:
        send_message(chat_id, "❌ Спочатку оберіть ресторан")
        handle_menu(chat_id)
        return
    
    # Фільтруємо по ресторану та категорії
    items = [
        item for item in menu_data 
        if item.get('Ресторан') == restaurant and item.get('Категорія') == category
    ]
    
    if not items:
        send_message(chat_id, f"❌ Немає страв у категорії '{category}'")
        return
    
    cart = get_cart(chat_id)
    cart_ids = [item.get('id') for item in cart]
    
    # Відправляємо кожну страву окремим повідомленням з кнопками
    for item in items:
        item_id = item.get('ID')
        name = item.get('Страви', 'Без назви')
        price = item.get('Ціна', 0)
        description = item.get('Опис', '')
        photo_url = item.get('Фото URL', '')
        rating = item.get('Рейтинг', 0)
        prep_time = item.get('Час_приготування', 0)
        
        message = f"🍽 <b>{name}</b>\n\n"
        
        if description:
            message += f"📝 {description}\n\n"
        
        message += f"💰 <b>{price} грн</b>\n"
        
        if rating:
            message += f"⭐ {rating}/5\n"
        
        if prep_time:
            message += f"⏱ Приготування: {prep_time} хв\n"
        
        in_cart = item_id in cart_ids
        
        # Якщо є фото - відправляємо з фото
        if photo_url:
            send_photo(
                chat_id, 
                photo_url, 
                caption=message,
                reply_markup=get_dish_inline_keyboard(item_id, in_cart)
            )
        else:
            send_message(
                chat_id, 
                message,
                reply_markup=get_dish_inline_keyboard(item_id, in_cart)
            )
    
    # Показуємо кнопку кошика
    cart_text = f"\n\n📊 Показано страв: {len(items)}"
    if cart:
        cart_text += f"\n🛒 В кошику: {len(cart)} страв"
    
    send_message(
        chat_id, 
        f"─" * 30 + cart_text,
        reply_markup=get_category_menu_for_restaurant(restaurant)
    )
    
    database.log_activity(chat_id, "view_category", {"category": category, "restaurant": restaurant})


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
    restaurant = cart[0].get('restaurant', 'Невідомий ресторан')
    
    message = f"🛒 <b>ВАШ КОШИК</b>\n"
    message += f"🏪 <b>{restaurant}</b>\n"
    message += "─" * 30 + "\n\n"
    
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
            dish = next((item for item in menu_data if item.get('Страви') == dish_name), None)
            if dish:
                price = dish.get('Ціна', 0)
                restaurant = dish.get('Ресторан', '')
                message += f"🔹 <b>{dish_name}</b>\n"
                message += f"   💰 {price} грн | 🏪 {restaurant}\n"
                message += f"   👥 Замовили {count} раз\n\n"
    else:
        # Якщо немає популярних - показуємо перші страви
        message = "⭐ <b>РЕКОМЕНДАЦІЇ</b>\n" + "─" * 30 + "\n\n"
        
        for item in menu_data[:5]:
            name = item.get('Страви', 'Без назви')
            price = item.get('Ціна', 0)
            restaurant = item.get('Ресторан', '')
            description = item.get('Опис', '')
            
            message += f"🔹 <b>{name}</b>\n"
            message += f"   💰 {price} грн | 🏪 {restaurant}\n"
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
2️⃣ Виберіть ресторан
3️⃣ Виберіть категорію
4️⃣ Додайте страви кнопкою ➕
5️⃣ Перейдіть в "🛒 Кошик"
6️⃣ Оформіть замовлення

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
            user_data = get_user_state(chat_id)
            restaurant = user_data.get('selected_restaurant') or item.get('Ресторан')
            
            # Перевіряємо чи всі товари з того ж ресторану
            cart = get_cart(chat_id)
            if cart and cart[0].get('restaurant') != restaurant:
                answer_callback_query(
                    callback_query_id, 
                    "❌ Всі страви повинні бути з одного ресторану!", 
                    show_alert=True
                )
                return
            
            # Додаємо в кошик
            add_to_cart(chat_id, {
                'id': item_id,
                'name': item.get('Страви', 'Без назви'),
                'price': item.get('Ціна', 0),
                'restaurant': restaurant,
                'quantity': 1
            })
            
            # Оновлюємо кнопки
            cart = get_cart(chat_id)
            quantity = sum(x['quantity'] for x in cart if x.get('id') == item_id)
            
            answer_callback_query(callback_query_id, f"✅ Додано! В кошику: {quantity} шт")
            
            # Оновлюємо повідомлення з новими кнопками
            try:
                edit_message(
                    chat_id, 
                    message_id, 
                    reply_markup=get_dish_inline_keyboard(item_id, in_cart=True)
                )
            except:
                pass
            
            database.log_activity(chat_id, "add_to_cart", {"item_id": item_id})
        else:
            answer_callback_query(callback_query_id, "❌ Товар не знайдено")
    
    elif callback_data.startswith("remove_one_"):
        # Видалити одну штуку з кошика
        item_id = callback_data.replace("remove_one_", "")
        cart = get_cart(chat_id)
        
        # Знаходимо товар і зменшуємо кількість
        for item in cart:
            if item.get('id') == item_id:
                if item['quantity'] > 1:
                    item['quantity'] -= 1
                    answer_callback_query(callback_query_id, f"✅ Кількість: {item['quantity']}")
                else:
                    remove_from_cart(chat_id, item_id)
                    answer_callback_query(callback_query_id, "🗑 Видалено з кошика")
                    
                    # Оновлюємо кнопки
                    try:
                        edit_message(
                            chat_id, 
                            message_id, 
                            reply_markup=get_dish_inline_keyboard(item_id, in_cart=False)
                        )
                    except:
                        pass
                break
        
        database.log_activity(chat_id, "remove_from_cart", {"item_id": item_id})
    
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
        answer_callback_query(callback_query_id, "🏪 Ресторани")
    
    elif callback_data == "back_to_category":
        user_data = get_user_state(chat_id)
        restaurant = user_data.get('selected_restaurant')
        if restaurant:
            handle_restaurant_selection(chat_id, restaurant)
        else:
            handle_menu(chat_id)
        answer_callback_query(callback_query_id, "◀️ Назад")
    
    elif callback_data == "noop":
        # Не робимо нічого (для кнопки "В кошику")
        pass


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
            
            logger
