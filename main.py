import os, sys, logging, uuid, random, json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from collections import defaultdict
from threading import RLock
from datetime import datetime

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import bot_config as config
    from services import telegram as tg_service
    from services import sheets as sheets_service
    from services import database as db_service
except Exception as e:
    logger.critical(f"Import failed: {e}")
    sys.exit(1)

app = Flask(__name__)

user_states = {}
user_carts = defaultdict(dict)
menu_cache = []
user_states_lock = RLock()
user_carts_lock = RLock()
menu_cache_lock = RLock()

MAX_CART_ITEMS = 50
MAX_ITEM_QUANTITY = 99

class State:
    MAIN_MENU = "main_menu"
    BROWSING_CATEGORIES = "browsing_categories"
    VIEWING_ITEM = "viewing_item"
    IN_CART = "in_cart"
    CHECKOUT_PHONE = "checkout_phone"
    CHECKOUT_ADDRESS = "checkout_address"
    CHECKOUT_CONFIRM = "checkout_confirm"

GREETINGS = [
    "👋 Привіт! Готовий щось смачненьке?",
    "🍽️ Ласкаво просимо!",
    "😋 Голодний?",
    "🎉 Вітаємо!",
    "👨‍🍳 Шеф чекає на тебе!",
]

def get_menu():
    global menu_cache
    with menu_cache_lock:
        if not menu_cache:
            try:
                menu_cache = sheets_service.get_menu_from_sheet()
            except Exception as e:
                logger.error(f"Failed to load menu: {e}")
                return []
        return menu_cache

def get_categories():
    menu = get_menu()
    categories = set()
    for item in menu:
        category = item.get('Категорія', 'Інше')
        if category:
            categories.add(category)
    return sorted(list(categories))

def get_items_by_category(category):
    menu = get_menu()
    return [item for item in menu if item.get('Категорія') == category]

def find_item_by_name(name):
    menu = get_menu()
    for item in menu:
        if item.get('Назва Страви') == name:
            return item
    return None

def safe_escape(text):
    import html
    if text is None:
        return ""
    return html.escape(str(text))

def send_msg(chat_id, text, markup=None):
    try:
        return tg_service.tg_send_message(chat_id, text, markup, "HTML")
    except Exception as e:
        logger.error(f"Send error: {e}")

def format_item(item):
    name = safe_escape(item.get('Назва Страви', 'Без назви'))
    category = safe_escape(item.get('Категорія', ''))
    price = safe_escape(item.get('Ціна', '0'))
    description = safe_escape(item.get('Опис', ''))
    
    text = f"🍽️ <b>{name}</b>\n{'─'*30}\n\n"
    if description:
        text += f"📝 {description}\n\n"
    text += f"📁 {category}\n💰 <b>{price} ₴</b>"
    return text

def format_cart(chat_id):
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    
    if not cart:
        return "🛒 <b>Кошик порожній</b>\n\n📋 Перейдіть у меню!"
    
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

def kb_main():
    return {"keyboard": [
        [{"text": "📋 Меню"}, {"text": "⭐ Рекомендації"}],
        [{"text": "🛒 Кошик"}, {"text": "👤 Профіль"}],
        [{"text": "🔍 Пошук"}, {"text": "🆘 Допомога"}]
    ], "resize_keyboard": True}

def kb_categories():
    categories = get_categories()
    kb = {"inline_keyboard": []}
    for cat in categories:
        kb["inline_keyboard"].append([{"text": f"🍽️ {cat}", "callback_data": f"cat:{cat}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "back"}])
    return kb

def kb_item(item, cat, idx, total):
    name = item.get('Назва Страви', '')
    kb = {"inline_keyboard": [
        [{"text": "➕ Додати", "callback_data": f"add:{name}"}]
    ]}
    if total > 1:
        nav = []
        if idx > 0:
            nav.append({"text": "⬅️", "callback_data": f"item:{cat}:{idx-1}"})
        nav.append({"text": f"{idx+1}/{total}", "callback_data": "noop"})
        if idx < total - 1:
            nav.append({"text": "➡️", "callback_data": f"item:{cat}:{idx+1}"})
        kb["inline_keyboard"].append(nav)
    kb["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "back_cat"}])
    return kb

def kb_cart():
    return {"keyboard": [[{"text": "✅ Оформити"}], [{"text": "📋 Меню"}]], "resize_keyboard": True}

def handle_start(chat_id):
    user_states[chat_id] = State.MAIN_MENU
    text = f"{random.choice(GREETINGS)}\n\n🍽️ Замовляйте їжу онлайн\n🚀 Доставка 30-45 хв\n💳 Оплата при отриманні\n\n{'─'*30}\n<b>Що ви хочете?</b>"
    send_msg(chat_id, text, kb_main())

def handle_menu(chat_id):
    user_states[chat_id] = State.BROWSING_CATEGORIES
    categories = get_categories()
    if not categories:
        send_msg(chat_id, "❌ Меню порожнє")
        return
    text = f"📋 <b>НАШЕ МЕНЮ</b>\n{'─'*30}\n\n✨ Доступно {len(categories)} категорій\n\n<b>Оберіть:</b>"
    send_msg(chat_id, text, kb_categories())

def show_item(chat_id, category, index):
    items = get_items_by_category(category)
    if not items or index < 0 or index >= len(items):
        send_msg(chat_id, "❌ Товар не знайдено")
        return
    user_states[chat_id] = State.VIEWING_ITEM
    item = items[index]
    text = format_item(item)
    photo = item.get('Фото URL', '')
    kb = kb_item(item, category, index, len(items))
    if photo and photo.startswith('http'):
        try:
            tg_service.tg_send_photo(chat_id, photo, caption=text, reply_markup=kb)
        except:
            send_msg(chat_id, text, kb)
    else:
        send_msg(chat_id, text, kb)

def add_to_cart(chat_id, item_name):
    item = find_item_by_name(item_name)
    if not item:
        send_msg(chat_id, "❌ Товар не знайдено")
        return
    with user_carts_lock:
        cart = user_carts[chat_id]
        if len(cart) >= MAX_CART_ITEMS:
            send_msg(chat_id, f"❌ Максимум {MAX_CART_ITEMS} товарів")
            return
        current = cart.get(item_name, 0)
        if current >= MAX_ITEM_QUANTITY:
            send_msg(chat_id, f"❌ Максимум {MAX_ITEM_QUANTITY} шт")
            return
        cart[item_name] = current + 1
    name = safe_escape(item.get('Назва Страви'))
    price = safe_escape(item.get('Ціна', '0'))
    qty = cart[item_name]
    text = f"✅ <b>{name}</b> додано!\n\n💰 {price} ₴\n📦 В кошику: {qty} шт\n\n{'─'*30}\nЩо далі?"
    kb = {"inline_keyboard": [[{"text": "🛒 До кошика", "callback_data": "cart"}, {"text": "📋 Ще", "callback_data": "menu"}]]}
    send_msg(chat_id, text, kb)

def handle_cart(chat_id):
    user_states[chat_id] = State.IN_CART
    text = format_cart(chat_id)
    with user_carts_lock:
        has_items = len(user_carts.get(chat_id, {})) > 0
    kb = kb_cart() if has_items else kb_main()
    send_msg(chat_id, text, kb)

def handle_profile(chat_id):
    text = f"👤 <b>ВАШ ПРОФІЛЬ</b>\n{'─'*30}\n\n🛍️ Замовлень: 0\n💸 Бонусів: 0 ₴\n🌟 Статус: Новачок\n🎁 Знижка: 0%\n\n<i>Зробіть замовлення й отримайте бонуси!</i>"
    send_msg(chat_id, text, kb_main())

def handle_recommendations(chat_id):
    text = f"⭐ <b>РЕКОМЕНДАЦІЇ</b>\n{'─'*30}\n\n👨‍🍳 <i>Цього дня:</i>\n\n1️⃣ Чорний бургер - 149₴\n2️⃣ Латте - 89₴\n\n💡 Перейдіть у меню!"
    send_msg(chat_id, text, kb_main())

def handle_help(chat_id):
    text = f"🆘 <b>ДОПОМОГА</b>\n{'─'*30}\n\n<b>Як замовити:</b>\n1️⃣ 📋 Меню\n2️⃣ Виберіть їжу\n3️⃣ ➕ Додайте\n4️⃣ 🛒 Оформіть\n\n📞 +38(99)123-45-67"
    send_msg(chat_id, text, kb_main())

def start_checkout(chat_id):
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    if not cart:
        send_msg(chat_id, "❌ Кошик порожній", kb_main())
        return
    user_states[chat_id] = State.CHECKOUT_PHONE
    text = f"📞 <b>ОФОРМЛЕННЯ</b>\n{'─'*30}\n\nКрок 1️⃣/3️⃣\n\n📱 Надішліть номер телефону"
    kb = {"keyboard": [[{"text": "📱 Надіслати", "request_contact": True}], [{"text": "❌ Скасувати"}]], "resize_keyboard": True, "one_time_keyboard": True}
    send_msg(chat_id, text, kb)

def handle_phone(chat_id, phone):
    user_states[chat_id] = State.CHECKOUT_ADDRESS
    with user_states_lock:
        if chat_id not in user_states:
            user_states[chat_id] = {}
    text = f"✅ Номер: {phone}\n\nКрок 2️⃣/3️⃣\n\n📍 Адреса доставки"
    kb = {"keyboard": [[{"text": "❌ Скасувати"}]], "resize_keyboard": True}
    send_msg(chat_id, text, kb)

def handle_address(chat_id, address):
    if len(address) < 10:
        send_msg(chat_id, "❌ Адреса коротка\n\nМінімум 10 символів")
        return
    user_states[chat_id] = State.CHECKOUT_CONFIRM
    summary = format_cart(chat_id)
    text = f"{summary}\n\n{'─'*30}\n\n📍 Адреса: {safe_escape(address)}\n\nКрок 3️⃣/3️⃣\n\n<b>Підтвердіть ✅</b>"
    kb = {"keyboard": [[{"text": "✅ Підтвердити"}], [{"text": "❌ Скасувати"}]], "resize_keyboard": True}
    send_msg(chat_id, text, kb)

def confirm_order(chat_id):
    with user_carts_lock:
        cart = user_carts.get(chat_id, {})
    if not cart:
        send_msg(chat_id, "❌ Кошик порожній")
        return
    try:
        total = sum(float(str(find_item_by_name(name).get('Ціна', 0)).replace(',', '.')) * qty for name, qty in cart.items() if find_item_by_name(name))
        order_id = str(uuid.uuid4())[:8].upper()
        items = [{"name": name, "quantity": qty, "price": 0} for name, qty in cart.items()]
        db_service.save_order(order_id, chat_id, None, items, f"{total:.2f}", "N/A", "N/A", "")
        text = f"🎉 <b>ЗАМОВЛЕННЯ ПРИЙНЯТО!</b>\n\n✅ ID: <code>{order_id}</code>\n\n💳 До оплати: {total:.2f} ₴\n\n🚚 Доставка за 30-45 хв\n\n🙏 Спасибі! Приємного апетиту!"
        with user_carts_lock:
            user_carts[chat_id] = {}
        user_states[chat_id] = State.MAIN_MENU
        send_msg(chat_id, text, kb_main())
    except Exception as e:
        logger.error(f"Order error: {e}")
        send_msg(chat_id, "❌ Помилка оформлення")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False})
        
        if 'message' in data:
            msg = data['message']
            chat_id = msg['chat']['id']
            text = msg.get('text', '').strip()
            
            if text == '/start':
                handle_start(chat_id)
            elif text == '📋 Меню':
                handle_menu(chat_id)
            elif text == '👤 Профіль':
                handle_profile(chat_id)
            elif text == '⭐ Рекомендації':
                handle_recommendations(chat_id)
            elif text == '🛒 Кошик':
                handle_cart(chat_id)
            elif text == '🆘 Допомога':
                handle_help(chat_id)
            elif text == '🔍 Пошук':
                send_msg(chat_id, "🔍 Пошук тимчасово недоступний", kb_main())
            elif text == '✅ Оформити':
                start_checkout(chat_id)
            elif text == '✅ Підтвердити':
                confirm_order(chat_id)
            elif text == '📋 Меню' or text == '❌ Скасувати':
                handle_start(chat_id)
            elif 'contact' in msg:
                phone = msg['contact']['phone_number']
                handle_phone(chat_id, phone)
            else:
                state = user_states.get(chat_id, State.MAIN_MENU)
                if state == State.CHECKOUT_ADDRESS:
                    handle_address(chat_id, text)
                else:
                    send_msg(chat_id, "🤔 Не розумію. Виберіть з меню 👇", kb_main())
        
        elif 'callback_query' in data:
            cb = data['callback_query']
            chat_id = cb['from']['id']
            cb_data = cb.get('data', '')
            
            if cb_data == 'back':
                handle_menu(chat_id)
            elif cb_data == 'back_cat':
                handle_menu(chat_id)
            elif cb_data == 'noop':
                pass
            elif cb_data == 'cart':
                handle_cart(chat_id)
            elif cb_data == 'menu':
                handle_menu(chat_id)
            elif cb_data.startswith('cat:'):
                category = cb_data[4:]
                show_item(chat_id, category, 0)
            elif cb_data.startswith('add:'):
                item_name = cb_data[4:]
                add_to_cart(chat_id, item_name)
            elif cb_data.startswith('item:'):
                parts = cb_data[5:].split(':')
                if len(parts) == 2:
                    show_item(chat_id, parts[0], int(parts[1]))
        
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"ok": False})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def index():
    return jsonify({"bot": "Hubsy v3.2"})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)