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
# STARTUP
# ============================================================================

def initialize():
    """Ініціалізація при старті"""
    global menu_data
    
    logger.info("🚀 Starting Hubsy Bot v3.3.0...")
    
    try:
        if database.init_database():
            logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
    
    try:
        if database.USE_POSTGRES:
            logger.info("🐘 Using PostgreSQL")
            if database.sync_menu_from_sheets():
                menu_data = database.get_menu_from_postgres()
            else:
                menu_data = sheets.get_menu_from_sheet()
        else:
            menu_data = sheets.get_menu_from_sheet()
        
        if menu_data:
            logger.info(f"✅ Menu loaded: {len(menu_data)} items")
    except Exception as e:
        logger.error(f"❌ Menu loading failed: {e}")
    
    try:
        gemini.test_gemini_connection()
    except Exception as e:
        logger.error(f"❌ Gemini test failed: {e}")

initialize()

# ============================================================================
# CART FUNCTIONS
# ============================================================================

def add_to_cart(user_id: int, item: Dict[str, Any]):
    if user_id not in user_carts:
        user_carts[user_id] = []
    for cart_item in user_carts[user_id]:
        if cart_item.get('id') == item.get('id'):
            cart_item['quantity'] = cart_item.get('quantity', 1) + 1
            return
    item['quantity'] = 1
    user_carts[user_id].append(item)

def get_cart(user_id: int) -> List[Dict[str, Any]]:
    return user_carts.get(user_id, [])

def clear_cart(user_id: int):
    if user_id in user_carts:
        user_carts[user_id] = []

def remove_from_cart(user_id: int, item_id: str):
    if user_id in user_carts:
        user_carts[user_id] = [item for item in user_carts[user_id] if item.get('id') != item_id]

def get_cart_total(user_id: int) -> float:
    return sum(item.get('price', 0) * item.get('quantity', 1) for item in get_cart(user_id))

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_user_state(user_id: int) -> Dict[str, Any]:
    if user_id not in user_states:
        user_states[user_id] = {"state": None, "data": {}, "selected_restaurant": None}
    return user_states[user_id]

def set_user_state(user_id: int, state: str, data: Dict[str, Any] = None):
    current = get_user_state(user_id)
    current["state"] = state
    if data:
        current.update(data)
    user_states[user_id] = current

def clear_user_state(user_id: int):
    if user_id in user_states:
        user_states[user_id] = {"state": None, "data": {}, "selected_restaurant": None}

# ============================================================================
# KEYBOARDS
# ============================================================================

def get_main_menu():
    return {"keyboard": [["📋 Меню", "🛒 Кошик"], ["⭐ Рекомендації", "🔍 Пошук"], ["📦 Мої замовлення", "🆘 Допомога"]], "resize_keyboard": True}

def get_restaurants_keyboard():
    restaurants = list(set(item.get('Ресторан') for item in menu_data if item.get('Ресторан')))
    keyboard = [restaurants[i:i+2] for i in range(0, len(restaurants), 2)]
    keyboard.append(["◀️ Назад"])
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_category_menu_for_restaurant(restaurant: str):
    items = [item for item in menu_data if item.get('Ресторан') == restaurant]
    categories = list(set(item.get('Категорія') for item in items if item.get('Категорія')))
    keyboard = [categories[i:i+2] for i in range(0, len(categories), 2)]
    keyboard.append(["🛒 Кошик", "◀️ Назад"])
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_dish_inline_keyboard(item_id: str, in_cart: bool = False):
    if not in_cart:
        return {"inline_keyboard": [[{"text": "➕ Додати", "callback_data": f"add_{item_id}"}], [{"text": "◀️ Назад", "callback_data": "back_to_category"}]]}
    return {"inline_keyboard": [[{"text": "➖", "callback_data": f"remove_one_{item_id}"}, {"text": "✅ В кошику", "callback_data": "noop"}, {"text": "➕", "callback_data": f"add_{item_id}"}], [{"text": "◀️ Назад", "callback_data": "back_to_category"}]]}

def get_cart_keyboard():
    return {"inline_keyboard": [[{"text": "✅ Оформити", "callback_data": "checkout"}], [{"text": "🗑 Очистити", "callback_data": "clear_cart"}], [{"text": "◀️ Назад", "callback_data": "back_to_menu"}]]}

# ============================================================================
# HANDLERS
# ============================================================================

def handle_start(chat_id: int, username: str):
    send_message(chat_id, "👋 Вітаємо в <b>Hubsy Bot</b>!\n\nЯ допоможу вам замовити смачну їжу швидко та зручно.\n\n🔹 Переглядайте меню\n🔹 Додавайте страви в кошик\n🔹 Оформляйте замовлення\n\nОберіть дію з меню нижче 👇", reply_markup=get_main_menu())
    database.log_activity(chat_id, "start", {"username": username})

def handle_menu(chat_id: int):
    if not menu_data:
        send_message(chat_id, "❌ Меню тимчасово недоступне.")
        return
    restaurants = list(set(item.get('Ресторан') for item in menu_data if item.get('Ресторан')))
    if not restaurants:
        send_message(chat_id, "❌ Ресторани не знайдено")
        return
    msg = "🏪 <b>ОБЕРІТЬ ЗАКЛАД</b>\n" + "─" * 30 + "\n\n"
    for r in restaurants:
        count = len([x for x in menu_data if x.get('Ресторан') == r])
        msg += f"🍽 <b>{r}</b>\n   {count} страв\n\n"
    send_message(chat_id, msg, reply_markup=get_restaurants_keyboard())
    set_user_state(chat_id, "selecting_restaurant")

def handle_restaurant_selection(chat_id: int, restaurant: str):
    user_data = get_user_state(chat_id)
    user_data['selected_restaurant'] = restaurant
    set_user_state(chat_id, "selecting_category", user_data)
    cart = get_cart(chat_id)
    if cart and cart[0].get('restaurant') != restaurant:
        clear_cart(chat_id)
        send_message(chat_id, "🗑 Кошик очищено - страви мають бути з одного ресторану.")
    msg = f"🏪 <b>{restaurant.upper()}</b>\n" + "─" * 30 + "\n\nОберіть категорію:"
    send_message(chat_id, msg, reply_markup=get_category_menu_for_restaurant(restaurant))

def handle_category(chat_id: int, category: str):
    user_data = get_user_state(chat_id)
    restaurant = user_data.get('selected_restaurant')
    if not restaurant:
        send_message(chat_id, "❌ Оберіть ресторан")
        handle_menu(chat_id)
        return
    items = [item for item in menu_data if item.get('Ресторан') == restaurant and item.get('Категорія') == category]
    if not items:
        send_message(chat_id, f"❌ Немає страв у '{category}'")
        return
    cart = get_cart(chat_id)
    cart_ids = [i.get('id') for i in cart]
    for item in items:
        item_id = item.get('ID')
        name = item.get('Страви', 'Без назви')
        price = item.get('Ціна', 0)
        desc = item.get('Опис', '')
        photo = item.get('Фото URL', '')
        rating = item.get('Рейтинг', 0)
        prep = item.get('Час_приготування', 0)
        msg = f"🍽 <b>{name}</b>\n\n"
        if desc:
            msg += f"📝 {desc}\n\n"
        msg += f"💰 <b>{price} грн</b>\n"
        if rating:
            msg += f"⭐ {rating}/5\n"
        if prep:
            msg += f"⏱ {prep} хв\n"
        in_cart = item_id in cart_ids
        if photo:
            send_photo(chat_id, photo, caption=msg, reply_markup=get_dish_inline_keyboard(item_id, in_cart))
        else:
            send_message(chat_id, msg, reply_markup=get_dish_inline_keyboard(item_id, in_cart))
    send_message(chat_id, f"{'─' * 30}\n📊 {len(items)} страв" + (f"\n🛒 В кошику: {len(cart)}" if cart else ""), reply_markup=get_category_menu_for_restaurant(restaurant))

def handle_cart(chat_id: int):
    cart = get_cart(chat_id)
    if not cart:
        send_message(chat_id, "🛒 Кошик порожній\n\nОберіть страви з меню 👇", reply_markup=get_main_menu())
        return
    total = get_cart_total(chat_id)
    restaurant = cart[0].get('restaurant', 'Невідомий')
    msg = f"🛒 <b>ВАШ КОШИК</b>\n🏪 <b>{restaurant}</b>\n{'─' * 30}\n\n"
    for item in cart:
        msg += f"🔹 <b>{item.get('name')}</b>\n   {item.get('quantity')} x {item.get('price')} = {item.get('quantity') * item.get('price')} грн\n\n"
    msg += f"{'─' * 30}\n💰 <b>Разом: {total} грн</b>"
    send_message(chat_id, msg, reply_markup=get_cart_keyboard())

def handle_checkout(chat_id: int, callback_query_id: str = None):
    if not get_cart(chat_id):
        if callback_query_id:
            answer_callback_query(callback_query_id, "🛒 Кошик порожній")
        return
    send_message(chat_id, "📝 <b>ОФОРМЛЕННЯ ЗАМОВЛЕННЯ</b>\n─────────────────────────────\n\nВведіть дані:\n\n<b>Ім'я</b>\n<b>Телефон</b>\n<b>Адреса</b>\n\nПриклад:\nІван\n+380501234567\nвул. Хрещатик, 1")
    set_user_state(chat_id, "checkout")

# ============================================================================
# CALLBACKS
# ============================================================================

def handle_callback(callback_data: str, chat_id: int, message_id: int, callback_query_id: str):
    if callback_data.startswith("add_"):
        item_id = callback_data.replace("add_", "")
        item = next((x for x in menu_data if str(x.get('ID')) == str(item_id)), None)
        if item:
            user_data = get_user_state(chat_id)
            restaurant = user_data.get('selected_restaurant') or item.get('Ресторан')
            cart = get_cart(chat_id)
            if cart and cart[0].get('restaurant') != restaurant:
                answer_callback_query(callback_query_id, "❌ Тільки з одного ресторану!", show_alert=True)
                return
            add_to_cart(chat_id, {'id': item_id, 'name': item.get('Страви', 'Без назви'), 'price': item.get('Ціна', 0), 'restaurant': restaurant, 'quantity': 1})
            qty = sum(x['quantity'] for x in get_cart(chat_id) if x.get('id') == item_id)
            answer_callback_query(callback_query_id, f"✅ Додано! {qty} шт")
            try:
                edit_message(chat_id, message_id, reply_markup=get_dish_inline_keyboard(item_id, True))
            except:
                pass
    elif callback_data.startswith("remove_one_"):
        item_id = callback_data.replace("remove_one_", "")
        for item in get_cart(chat_id):
            if item.get('id') == item_id:
                if item['quantity'] > 1:
                    item['quantity'] -= 1
                    answer_callback_query(callback_query_id, f"✅ {item['quantity']} шт")
                else:
                    remove_from_cart(chat_id, item_id)
                    answer_callback_query(callback_query_id, "🗑 Видалено")
                    try:
                        edit_message(chat_id, message_id, reply_markup=get_dish_inline_keyboard(item_id, False))
                    except:
                        pass
                break
    elif callback_data == "checkout":
        handle_checkout(chat_id, callback_query_id)
    elif callback_data == "clear_cart":
        clear_cart(chat_id)
        answer_callback_query(callback_query_id, "🗑 Очищено")
        handle_cart(chat_id)
    elif callback_data == "back_to_menu":
        handle_menu(chat_id)
    elif callback_data == "back_to_category":
        user_data = get_user_state(chat_id)
        if user_data.get('selected_restaurant'):
            handle_restaurant_selection(chat_id, user_data['selected_restaurant'])
        else:
            handle_menu(chat_id)

# ============================================================================
# WEBHOOK
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.json
        logger.info(f"📥 Webhook: {update.get('update_id')}")
        
        if 'message' in update:
            msg = update['message']
            chat_id = msg['chat']['id']
            username = msg['from'].get('username', 'Unknown')
            
            if 'text' in msg:
                text = msg['text']
                
                if text == '/start':
                    handle_start(chat_id, username)
                elif text in ['/menu', '📋 Меню']:
                    handle_menu(chat_id)
                elif text in ['/cart', '🛒 Кошик']:
                    handle_cart(chat_id)
                elif text == '◀️ Назад':
                    send_message(chat_id, "Головне меню:", reply_markup=get_main_menu())
                    clear_user_state(chat_id)
                else:
                    user_data = get_user_state(chat_id)
                    if user_data.get("state") == "selecting_restaurant":
                        handle_restaurant_selection(chat_id, text)
                    elif user_data.get("state") == "selecting_category":
                        if text == "🛒 Кошик":
                            handle_cart(chat_id)
                        elif text == "◀️ Назад":
                            handle_menu(chat_id)
                        else:
                            handle_category(chat_id, text)
                    elif user_data.get("state") == "checkout":
                        lines = text.strip().split('\n')
                        if len(lines) >= 3:
                            name, phone, address = lines[0], lines[1], '\n'.join(lines[2:])
                            cart = get_cart(chat_id)
                            total = get_cart_total(chat_id)
                            order_id = f"ORD{int(time.time())}"
                            if database.save_order(order_id, chat_id, username, cart, total, phone, address, f"Name: {name}"):
                                send_message(chat_id, f"✅ <b>ЗАМОВЛЕННЯ #{order_id}</b>\n\n👤 {name}\n📞 {phone}\n📍 {address}\n\n💰 {total} грн\n\nМи зв'яжемося з вами!", reply_markup=get_main_menu())
                                if config.OPERATOR_CHAT_ID:
                                    op_msg = f"🆕 <b>#{order_id}</b>\n\n👤 {name}\n📞 {phone}\n📍 {address}\n\n<b>Страви:</b>\n"
                                    for item in cart:
                                        op_msg += f"• {item['name']} x{item['quantity']} - {item['price']*item['quantity']} грн\n"
                                    op_msg += f"\n💰 {total} грн"
                                    send_message(config.OPERATOR_CHAT_ID, op_msg)
                                clear_cart(chat_id)
                                clear_user_state(chat_id)
                        else:
                            send_message(chat_id, "❌ Формат: Ім'я\nТелефон\nАдреса")
        
        elif 'callback_query' in update:
            cb = update['callback_query']
            handle_callback(cb['data'], cb['message']['chat']['id'], cb['message']['message_id'], cb['id'])
        
        return jsonify({"ok": True}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False}), 500

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    return jsonify({"status": "ok", "bot": "Hubsy Bot", "version": "3.3.0"})

@app.route('/health')
def health():
    db_ok, db_info = database.test_connection()
    return jsonify({"status": "healthy" if db_ok else "degraded", "database": db_info, "menu_items": len(menu_data)})

@app.route('/sync-menu', methods=['POST'])
def sync_menu():
    global menu_data
    try:
        if database.USE_POSTGRES:
            if database.sync_menu_from_sheets():
                menu_data = database.get_menu_from_postgres()
                return jsonify({"status": "success", "message": f"Synced: {len(menu_data)} items"}), 200
            return jsonify({"status": "error", "message": "Sync failed"}), 500
        return jsonify({"status": "error", "message": "Not using PostgreSQL"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', config.PORT))
    app.run(host='0.0.0.0', port=port, debug=config.DEBUG)
