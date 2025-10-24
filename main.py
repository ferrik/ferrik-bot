"""
Hubsy Bot - ВИПРАВЛЕНА ВЕРСІЯ
Telegram бот для замовлення їжі з прямим добавленням товарів
"""

import logging
import os
import time
import json
from flask import Flask, request, jsonify
from typing import Dict, Any, List, Optional

import config
from services import sheets, gemini, database, telegram

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

menu_data: List[Dict[str, Any]] = []
user_states: Dict[int, Dict[str, Any]] = {}
user_carts: Dict[int, List[Dict[str, Any]]] = {}

def initialize():
    global menu_data
    logger.info("🚀 Starting Hubsy Bot v3.4.0 (FIXED)...")
    
    try:
        if database.init_database():
            logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
    
    try:
        menu_data = sheets.get_menu_from_sheet()
        if menu_data:
            logger.info(f"✅ Menu loaded: {len(menu_data)} items")
    except Exception as e:
        logger.error(f"❌ Menu loading failed: {e}")
    
    try:
        gemini.test_gemini_connection()
    except Exception as e:
        logger.error(f"⚠️  Gemini test failed: {e}")

initialize()

def add_to_cart(user_id: int, item: Dict[str, Any]):
    if user_id not in user_carts:
        user_carts[user_id] = []
    
    for cart_item in user_carts[user_id]:
        if cart_item.get('id') == item.get('id'):
            cart_item['quantity'] = cart_item.get('quantity', 1) + 1
            logger.info(f"Updated qty for {item.get('name')} in cart {user_id}")
            return
    
    item['quantity'] = 1
    user_carts[user_id].append(item)
    logger.info(f"Added {item.get('name')} to cart {user_id}")

def get_cart(user_id: int) -> List[Dict[str, Any]]:
    return user_carts.get(user_id, [])

def get_cart_total(user_id: int) -> float:
    cart = get_cart(user_id)
    total = 0
    for item in cart:
        try:
            price = float(str(item.get('price', 0)).replace(',', '.'))
            qty = int(item.get('quantity', 1))
            total += price * qty
        except (ValueError, TypeError):
            continue
    return round(total, 2)

def clear_cart(user_id: int):
    if user_id in user_carts:
        user_carts[user_id] = []

def remove_from_cart(user_id: int, item_id: str):
    if user_id in user_carts:
        user_carts[user_id] = [item for item in user_carts[user_id] if item.get('id') != item_id]

def get_user_state(user_id: int) -> Dict[str, Any]:
    if user_id not in user_states:
        user_states[user_id] = {"state": None, "data": {}}
    return user_states[user_id]

def set_user_state(user_id: int, state: str, data: Dict[str, Any] = None):
    current = get_user_state(user_id)
    current["state"] = state
    if data:
        current.update(data)

def clear_user_state(user_id: int):
    if user_id in user_states:
        user_states[user_id] = {"state": None, "data": {}}

# ============================================================================
# ✨ НОВА ФУНКЦІЯ: Показати товари з inline кнопками для додавання
# ============================================================================

def show_menu_with_buttons(chat_id: int, category: str = None):
    """Показує меню з кнопками ➕ для додавання в кошик"""
    try:
        items = menu_data
        if category:
            items = [item for item in items if item.get('Категорія') == category]
        
        if not items:
            telegram.tg_send_message(chat_id, "❌ Товари не знайдені")
            return
        
        # Показуємо перші 5 товарів
        telegram.tg_send_message(chat_id, f"🍽️ <b>Меню {category if category else 'всього'}</b>\n({len(items)} позицій)")
        
        for item in items[:5]:
            item_id = item.get('ID')
            name = item.get('Страви', 'N/A')
            price = item.get('Ціна', 0)
            desc = item.get('Опис', '')
            
            text = f"<b>{name}</b>\n💰 {price} грн"
            if desc:
                text += f"\n📝 {desc}"
            
            keyboard = {
                "inline_keyboard": [[
                    {"text": "➕ Додати", "callback_data": f"add_item_{item_id}"},
                    {"text": f"ℹ️ {price}грн", "callback_data": f"noop_{item_id}"}
                ]]
            }
            
            telegram.tg_send_message(chat_id, text, keyboard)
        
        # Кнопка для перегляду кошика
        show_cart_button = {
            "inline_keyboard": [[
                {"text": "🛒 Переглянути кошик", "callback_data": "show_cart"},
                {"text": "✅ Оформити", "callback_data": "checkout"}
            ]]
        }
        telegram.tg_send_message(chat_id, "─" * 30, show_cart_button)
        
    except Exception as e:
        logger.error(f"Error showing menu: {e}")
        telegram.tg_send_message(chat_id, f"❌ Помилка: {e}")

def show_cart_preview(chat_id: int):
    """Показує кошик"""
    cart = get_cart(chat_id)
    if not cart:
        telegram.tg_send_message(chat_id, "🛒 Кошик порожній\n\n[Натисніть 📖 Меню]")
        return
    
    total = get_cart_total(chat_id)
    text = "🛒 <b>Ваш кошик:</b>\n\n"
    
    for item in cart:
        name = item.get('name', 'N/A')
        price = item.get('price', 0)
        qty = item.get('quantity', 1)
        text += f"• {name} x{qty} = {float(price) * qty:.0f} грн\n"
    
    text += f"\n<b>Разом: {total:.2f} грн</b>"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Оформити замовлення", "callback_data": "checkout"}],
            [{"text": "🍽️ Додати ще", "callback_data": "show_menu"}],
            [{"text": "🗑️ Очистити", "callback_data": "clear_cart"}]
        ]
    }
    
    telegram.tg_send_message(chat_id, text, keyboard)

# ============================================================================
# ✨ НОВА ФУНКЦІЯ: Оформлення замовлення з контактними даними
# ============================================================================

def start_checkout(chat_id: int, callback_id: str = None):
    """Запускає процес оформлення з запитом контактних даних"""
    cart = get_cart(chat_id)
    
    if not cart:
        if callback_id:
            telegram.tg_answer_callback(callback_id, "🛒 Кошик порожній", show_alert=True)
        return
    
    total = get_cart_total(chat_id)
    
    # Мінімальна сума
    MIN_ORDER = 200
    if total < MIN_ORDER:
        telegram.tg_send_message(chat_id, 
            f"⚠️ Мінімальна сума замовлення: {MIN_ORDER} грн\n"
            f"У вас: {total:.2f} грн\n"
            f"Додайте ще на {MIN_ORDER - total:.2f} грн")
        return
    
    # Запитуємо телефон
    telegram.tg_send_message(chat_id, 
        "📱 <b>ОФОРМЛЕННЯ ЗАМОВЛЕННЯ</b>\n\n"
        "Введіть ваш номер телефону:\n"
        "<code>+380971234567</code>")
    
    set_user_state(chat_id, "checkout_phone")

def handle_phone_input(chat_id: int, text: str):
    """Обробляє введений телефон"""
    phone = text.strip()
    
    if not phone:
        telegram.tg_send_message(chat_id, "❌ Введіть номер телефону")
        return
    
    # Зберігаємо телефон
    set_user_state(chat_id, "checkout_address", {"phone": phone})
    
    telegram.tg_send_message(chat_id,
        f"✅ Номер прийнято: {phone}\n\n"
        "📍 Введіть адресу доставки:\n"
        "<i>вул. Руська, 12, кв. 5</i>")

def handle_address_input(chat_id: int, text: str):
    """Обробляє введену адресу і завершує замовлення"""
    address = text.strip()
    state_data = get_user_state(chat_id)
    phone = state_data.get("data", {}).get("phone", "N/A")
    
    cart = get_cart(chat_id)
    total = get_cart_total(chat_id)
    
    if not cart:
        telegram.tg_send_message(chat_id, "❌ Кошик порожній")
        return
    
    # Генеруємо ID замовлення
    order_id = f"ORD-{int(time.time())}"
    
    # Форматуємо товари
    items_text = "\n".join([
        f"• {item.get('name')} x{item.get('quantity', 1)} = {float(item.get('price', 0)) * item.get('quantity', 1):.0f} грн"
        for item in cart
    ])
    
    # ✨ ВИРІШЕННЯ: Зберігаємо замовлення в базу
    order_saved = database.save_order(
        order_id=order_id,
        user_id=chat_id,
        username=chat_id,
        items=cart,
        total=total,
        phone=phone,
        address=address,
        notes=""
    )
    
    if order_saved:
        # Підтвердження користувачу
        confirmation = (
            f"✅ <b>ЗАМОВЛЕННЯ #{order_id}</b>\n\n"
            f"<b>Товари:</b>\n{items_text}\n\n"
            f"<b>Сума:</b> {total:.2f} грн\n"
            f"<b>Телефон:</b> {phone}\n"
            f"<b>Адреса:</b> {address}\n\n"
            f"Дякуємо за замовлення! 😊"
        )
        
        keyboard = {
            "inline_keyboard": [[
                {"text": "📖 Меню", "callback_data": "show_menu"},
                {"text": "📞 Контакти", "callback_data": "contacts"}
            ]]
        }
        
        telegram.tg_send_message(chat_id, confirmation, keyboard)
        
        # Повідомлення оператору
        if config.OPERATOR_CHAT_ID:
            op_msg = (
                f"🔔 <b>НОВЕ ЗАМОВЛЕННЯ #{order_id}</b>\n\n"
                f"👤 Користувач: {chat_id}\n"
                f"📞 Телефон: {phone}\n"
                f"📍 Адреса: {address}\n\n"
                f"<b>Товари:</b>\n{items_text}\n\n"
                f"💰 <b>Сума: {total:.2f} грн</b>"
            )
            telegram.tg_send_message(config.OPERATOR_CHAT_ID, op_msg)
        
        # Очищаємо кошик
        clear_cart(chat_id)
        clear_user_state(chat_id)
    else:
        telegram.tg_send_message(chat_id, "❌ Помилка при збереженні замовлення")

# ============================================================================
# WEBHOOK
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.json
        
        # Перевірка webhook secret
        if config.WEBHOOK_SECRET:
            secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
            if secret_token != config.WEBHOOK_SECRET:
                logger.warning("❌ Invalid webhook secret")
                return jsonify({"ok": False}), 401
        
        logger.info(f"📥 Update: {update.get('update_id')}")
        
        # ============ ПОВІДОМЛЕННЯ ============
        if 'message' in update:
            msg = update['message']
            chat_id = msg['chat']['id']
            text = msg.get('text', '').strip()
            
            user_state = get_user_state(chat_id).get("state")
            
            # Обробляємо стани
            if user_state == "checkout_phone":
                handle_phone_input(chat_id, text)
                return jsonify({"ok": True})
            
            elif user_state == "checkout_address":
                handle_address_input(chat_id, text)
                return jsonify({"ok": True})
            
            # Команди
            if text == '/start':
                telegram.tg_send_message(chat_id,
                    "👋 Вітаємо в <b>Hubsy Bot</b>!\n\n"
                    "Оберіть дію:",
                    {"keyboard": [
                        ["📖 Меню", "🛒 Кошик"],
                        ["🆘 Допомога"]
                    ], "resize_keyboard": True})
                
            elif text in ['📖 Меню', '/menu']:
                show_menu_with_buttons(chat_id)
            
            elif text in ['🛒 Кошик', '/cart']:
                show_cart_preview(chat_id)
            
            elif text == '🆘 Допомога' or text == '/help':
                telegram.tg_send_message(chat_id, "ℹ️ Допомога в розробці")
        
        # ============ CALLBACK QUERIES (inline кнопки) ============
        elif 'callback_query' in update:
            cb = update['callback_query']
            chat_id = cb['message']['chat']['id']
            callback_data = cb.get('data', '')
            callback_id = cb['id']
            
            logger.info(f"Callback: {callback_data}")
            
            # Додавання товару в кошик
            if callback_data.startswith("add_item_"):
                item_id = callback_data.replace("add_item_", "")
                item = next((x for x in menu_data if str(x.get('ID')) == str(item_id)), None)
                
                if item:
                    add_to_cart(chat_id, {
                        'id': item_id,
                        'name': item.get('Страви', 'N/A'),
                        'price': item.get('Ціна', 0)
                    })
                    
                    cart_count = sum(i.get('quantity', 1) for i in get_cart(chat_id))
                    telegram.tg_answer_callback(callback_id, 
                        f"✅ {item.get('Страви')} додано!\n🛒 У кошику: {cart_count} поз.")
            
            # Показати кошик
            elif callback_data == "show_cart":
                show_cart_preview(chat_id)
                telegram.tg_answer_callback(callback_id)
            
            # Оформити замовлення
            elif callback_data == "checkout":
                start_checkout(chat_id, callback_id)
                telegram.tg_answer_callback(callback_id)
            
            # Показати меню
            elif callback_data == "show_menu":
                show_menu_with_buttons(chat_id)
                telegram.tg_answer_callback(callback_id)
            
            # Очистити кошик
            elif callback_data == "clear_cart":
                clear_cart(chat_id)
                telegram.tg_answer_callback(callback_id, "🗑️ Кошик очищено")
                show_cart_preview(chat_id)
            
            else:
                telegram.tg_answer_callback(callback_id)
        
        return jsonify({"ok": True}), 200
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"ok": False}), 500

@app.route('/')
def index():
    return jsonify({"status": "ok", "bot": "Hubsy Bot", "version": "3.4.0"})

@app.route('/health')
def health():
    db_ok, db_info = database.test_connection()
    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "database": db_info,
        "menu_items": len(menu_data)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', config.PORT))
    app.run(host='0.0.0.0', port=port, debug=config.DEBUG)
