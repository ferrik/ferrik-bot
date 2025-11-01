"""
🍴 Ferrik Bot - Твій смаковий супутник
Версія 2.0 - Тепліший, розумніший, привабливіший!
"""
import os
import json
import logging
from datetime import datetime
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Локальні імпорти
from services.database import Database
from services.sheets import SheetsService
from app.utils.validators import (
    safe_parse_price, validate_phone, 
    normalize_phone, validate_address
)

# ============================================================================
# КОНФІГУРАЦІЯ
# ============================================================================
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
db = Database()
sheets = SheetsService()

# ============================================================================
# ЕМОДЖІ ТА ТЕКСТИ (Персональність бота)
# ============================================================================
EMOJI = {
    'hello': '👋',
    'food': '🍴',
    'pizza': '🍕',
    'burger': '🍔',
    'sushi': '🍱',
    'cart': '🛒',
    'money': '💰',
    'fire': '🔥',
    'star': '⭐',
    'gift': '🎁',
    'heart': '❤️',
    'rocket': '🚀',
    'sparkles': '✨',
    'chef': '👨‍🍳',
    'location': '📍',
    'phone': '📱',
    'time': '⏰',
    'check': '✅',
    'loading': '⏳',
    'party': '🎉',
    'wink': '😉',
    'yummy': '😋',
    'search': '🔍',
    'settings': '⚙️',
    'history': '📜',
    'badge': '🏆',
    'crown': '👑'
}

WELCOME_MESSAGES = [
    "Гей! Я Ferrik — твій смаковий супутник! {emoji} Готовий допомогти знайти щось смачненьке?",
    "Вітаю! {emoji} Я тут, щоб зробити твій день смачнішим! Що будемо їсти сьогодні?",
    "Привіт, друже! {emoji} Я Ferrik, і я знаю, що тобі сподобається. Розпочнемо пригоду?",
]

MOOD_PROMPTS = {
    'happy': f"{EMOJI['fire']} Бачу гарний настрій! Ось що підійде:",
    'hungry': f"{EMOJI['chef']} Розумію, час поїсти! Швидкі страви:",
    'lazy': f"{EMOJI['yummy']} Хочеш щось без зусиль? Топові комбо:",
    'romantic': f"{EMOJI['heart']} Романтична вечеря? Маю ідеї:",
}

# ============================================================================
# СТАНИ КОРИСТУВАЧА
# ============================================================================
STATE_IDLE = 'idle'
STATE_BROWSING = 'browsing'
STATE_AWAITING_PHONE = 'awaiting_phone'
STATE_AWAITING_ADDRESS = 'awaiting_address'
STATE_CONFIRMING = 'confirming'

# ============================================================================
# ДОПОМІЖНІ ФУНКЦІЇ TELEGRAM API
# ============================================================================
def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """Надіслати повідомлення"""
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Send message error: {e}")
        return None


def send_photo(chat_id, photo_url, caption=None, reply_markup=None):
    """Надіслати фото"""
    payload = {
        'chat_id': chat_id,
        'photo': photo_url,
        'parse_mode': 'HTML'
    }
    if caption:
        payload['caption'] = caption
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(f"{TELEGRAM_API}/sendPhoto", json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Send photo error: {e}")
        return None


def edit_message(chat_id, message_id, text, reply_markup=None):
    """Редагувати повідомлення"""
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(f"{TELEGRAM_API}/editMessageText", json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Edit message error: {e}")
        return None


def answer_callback(callback_id, text=None, show_alert=False):
    """Відповісти на callback"""
    payload = {
        'callback_query_id': callback_id,
        'show_alert': show_alert
    }
    if text:
        payload['text'] = text
    
    try:
        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json=payload)
    except Exception as e:
        logger.error(f"❌ Answer callback error: {e}")


# ============================================================================
# КЛАВІАТУРИ
# ============================================================================
def get_main_keyboard():
    """Головна клавіатура з емоджі"""
    return {
        'inline_keyboard': [
            [
                {'text': f"{EMOJI['food']} Меню", 'callback_data': 'menu'},
                {'text': f"{EMOJI['search']} Пошук", 'callback_data': 'search'}
            ],
            [
                {'text': f"{EMOJI['cart']} Кошик", 'callback_data': 'cart'},
                {'text': f"{EMOJI['gift']} Акції", 'callback_data': 'promos'}
            ],
            [
                {'text': f"{EMOJI['history']} Історія", 'callback_data': 'history'},
                {'text': f"{EMOJI['badge']} Досягнення", 'callback_data': 'badges'}
            ]
        ]
    }


def get_menu_keyboard(items):
    """Клавіатура меню з візуальними елементами"""
    keyboard = []
    
    # Групуємо по категоріях
    categories = {}
    for item in items:
        cat = item.get('Категорія', 'Інше')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    # Створюємо кнопки
    for cat, cat_items in categories.items():
        cat_emoji = get_category_emoji(cat)
        keyboard.append([{
            'text': f"{cat_emoji} {cat} ({len(cat_items)})",
            'callback_data': f"cat_{cat}"
        }])
    
    keyboard.append([{'text': f"{EMOJI['cart']} Мій кошик", 'callback_data': 'cart'}])
    
    return {'inline_keyboard': keyboard}


def get_item_keyboard(item_id, in_cart=False):
    """Клавіатура для окремої страви"""
    keyboard = []
    
    if in_cart:
        keyboard.append([
            {'text': f"{EMOJI['check']} Вже в кошику", 'callback_data': 'noop'},
        ])
    else:
        keyboard.append([
            {'text': f"➕ Додати в кошик", 'callback_data': f"add_{item_id}"},
        ])
    
    keyboard.append([
        {'text': f"⬅️ Назад до меню", 'callback_data': 'menu'}
    ])
    
    return {'inline_keyboard': keyboard}


def get_cart_keyboard():
    """Клавіатура кошика"""
    return {
        'inline_keyboard': [
            [
                {'text': f"{EMOJI['check']} Оформити замовлення", 'callback_data': 'checkout'}
            ],
            [
                {'text': f"🗑️ Очистити кошик", 'callback_data': 'clear_cart'},
                {'text': f"➕ Додати ще", 'callback_data': 'menu'}
            ]
        ]
    }


def get_category_emoji(category):
    """Емоджі для категорій"""
    emojis = {
        'Піца': '🍕',
        'Бургери': '🍔',
        'Суші': '🍱',
        'Салати': '🥗',
        'Десерти': '🍰',
        'Напої': '🥤',
        'Супи': '🍲',
        'Паста': '🍝',
        'Закуски': '🍟',
    }
    return emojis.get(category, '🍴')


# ============================================================================
# БІЗНЕС-ЛОГІКА
# ============================================================================
def get_user_state(user_id):
    """Отримати стан користувача"""
    state = db.get_user_state(user_id)
    return state if state else STATE_IDLE


def set_user_state(user_id, state, data=None):
    """Встановити стан користувача"""
    db.set_user_state(user_id, state, data)


def get_user_cart(user_id):
    """Отримати кошик користувача"""
    return db.get_cart(user_id)


def add_to_cart(user_id, item):
    """Додати товар у кошик"""
    db.add_to_cart(
        user_id,
        item['ID'],
        item['Страви'],
        safe_parse_price(item['Ціна']),
        1
    )


def clear_cart(user_id):
    """Очистити кошик"""
    db.clear_cart(user_id)


def get_user_level(user_id):
    """Отримати рівень користувача (геймифікація)"""
    orders = db.get_user_orders(user_id)
    order_count = len(orders)
    
    if order_count == 0:
        return {'level': 'Новачок', 'emoji': '🌱', 'next': 3}
    elif order_count < 5:
        return {'level': 'Любитель', 'emoji': '🍴', 'next': 5}
    elif order_count < 10:
        return {'level': 'Гурман', 'emoji': '👨‍🍳', 'next': 10}
    elif order_count < 20:
        return {'level': 'Майстер', 'emoji': '⭐', 'next': 20}
    else:
        return {'level': 'Легенда', 'emoji': '👑', 'next': None}


# ============================================================================
# ОБРОБНИКИ КОМАНД
# ============================================================================
def handle_start(user_id, username):
    """Обробка /start"""
    # Перевірка, чи це новий користувач
    is_new = db.get_user_state(user_id) is None
    
    if is_new:
        # Вітальне повідомлення для нових
        text = f"""
{EMOJI['sparkles']} <b>Вітаю в Ferrik!</b> {EMOJI['sparkles']}

Привіт, {username or 'друже'}! Я — твій персональний смаковий супутник {EMOJI['chef']}

<b>Що я вмію:</b>
{EMOJI['food']} Показати найсмачніше меню
{EMOJI['fire']} Підказати ТОП страви дня
{EMOJI['gift']} Знайти акції та знижки
{EMOJI['heart']} Запам'ятати твої уподобання

<i>Почнемо з меню?</i> {EMOJI['wink']}
"""
    else:
        # Повернувся користувач
        level = get_user_level(user_id)
        text = f"""
{EMOJI['party']} <b>З поверненням, {level['emoji']} {level['level']}!</b>

Рада тебе знову бачити! {EMOJI['heart']}

Що будемо замовляти сьогодні? {EMOJI['yummy']}
"""
    
    send_message(user_id, text, reply_markup=get_main_keyboard())
    set_user_state(user_id, STATE_IDLE)


def handle_menu(user_id):
    """Показати меню"""
    try:
        items = sheets.get_menu_items()
        
        if not items:
            send_message(
                user_id,
                f"{EMOJI['loading']} Меню оновлюється... Спробуй за хвилинку! {EMOJI['wink']}"
            )
            return
        
        # Красиве привітання з меню
        text = f"""
{EMOJI['food']} <b>Меню Ferrik</b> {EMOJI['sparkles']}

<i>Обирай категорію і я покажу найсмачніше!</i> {EMOJI['chef']}

{EMOJI['fire']} <b>Сьогодні популярно:</b> Піца Маргарита, Бургер Класик
"""
        
        send_message(user_id, text, reply_markup=get_menu_keyboard(items))
        
    except Exception as e:
        logger.error(f"❌ Menu error: {e}")
        send_message(
            user_id,
            f"{EMOJI['loading']} Упс! Щось пішло не так. Спробуй ще раз {EMOJI['wink']}"
        )


def handle_category(user_id, category):
    """Показати страви категорії"""
    try:
        items = sheets.get_menu_items()
        cat_items = [i for i in items if i.get('Категорія') == category]
        
        if not cat_items:
            send_message(user_id, f"В цій категорії поки пусто {EMOJI['wink']}")
            return
        
        # Показуємо кожну страву красиво
        for item in cat_items[:5]:  # Перші 5 страв
            show_item(user_id, item)
        
        if len(cat_items) > 5:
            send_message(
                user_id,
                f"{EMOJI['sparkles']} І ще {len(cat_items)-5} смачних страв!"
            )
        
    except Exception as e:
        logger.error(f"❌ Category error: {e}")


def show_item(user_id, item):
    """Показати окрему страву"""
    # Формуємо красивий опис
    name = item.get('Страви', 'Без назви')
    desc = item.get('Опис', '')
    price = safe_parse_price(item.get('Ціна', 0))
    rating = item.get('Рейтинг', 0)
    time = item.get('Час_приготування', 30)
    
    # Зірочки рейтингу
    stars = EMOJI['star'] * int(rating) if rating else ''
    
    caption = f"""
<b>{name}</b> {stars}

{desc}

💰 <b>{price:.0f} грн</b>
⏰ {time} хв

{EMOJI['fire']} <i>Топ вибір сьогодні!</i>
"""
    
    # Перевірка, чи вже в кошику
    cart = get_user_cart(user_id)
    in_cart = any(c['item_id'] == item['ID'] for c in cart)
    
    photo_url = item.get('Фото URL', '')
    
    if photo_url:
        send_photo(
            user_id,
            photo_url,
            caption=caption,
            reply_markup=get_item_keyboard(item['ID'], in_cart)
        )
    else:
        send_message(
            user_id,
            caption,
            reply_markup=get_item_keyboard(item['ID'], in_cart)
        )


def handle_add_to_cart(user_id, item_id, callback_id):
    """Додати в кошик"""
    try:
        items = sheets.get_menu_items()
        item = next((i for i in items if i['ID'] == item_id), None)
        
        if not item:
            answer_callback(callback_id, "Страва не знайдена", show_alert=True)
            return
        
        add_to_cart(user_id, item)
        
        answer_callback(
            callback_id,
            f"{EMOJI['check']} Додано! {item['Страви']}"
        )
        
        # Показуємо кошик
        send_message(
            user_id,
            f"{EMOJI['party']} Чудовий вибір! {EMOJI['cart']} Перейти до кошика?",
            reply_markup={'inline_keyboard': [[
                {'text': f"{EMOJI['cart']} Переглянути кошик", 'callback_data': 'cart'},
                {'text': f"➕ Додати ще", 'callback_data': 'menu'}
            ]]}
        )
        
    except Exception as e:
        logger.error(f"❌ Add to cart error: {e}")
        answer_callback(callback_id, "Помилка", show_alert=True)


def handle_cart(user_id):
    """Показати кошик"""
    cart = get_user_cart(user_id)
    
    if not cart:
        send_message(
            user_id,
            f"{EMOJI['cart']} <b>Твій кошик порожній</b>\n\n<i>Час додати щось смачненьке!</i> {EMOJI['yummy']}",
            reply_markup={'inline_keyboard': [[
                {'text': f"{EMOJI['food']} До меню", 'callback_data': 'menu'}
            ]]}
        )
        return
    
    # Формуємо список
    text = f"{EMOJI['cart']} <b>Твій кошик:</b>\n\n"
    total = 0
    
    for item in cart:
        qty = item['quantity']
        price = item['price']
        subtotal = qty * price
        total += subtotal
        
        text += f"• <b>{item['name']}</b>\n"
        text += f"  {qty} × {price:.0f} грн = {subtotal:.0f} грн\n\n"
    
    text += f"\n{EMOJI['money']} <b>Разом: {total:.0f} грн</b>"
    text += f"\n\n{EMOJI['sparkles']} <i>Готовий оформити?</i>"
    
    send_message(user_id, text, reply_markup=get_cart_keyboard())


def handle_checkout(user_id):
    """Початок оформлення"""
    cart = get_user_cart(user_id)
    
    if not cart:
        send_message(user_id, "Кошик порожній!")
        return
    
    set_user_state(user_id, STATE_AWAITING_PHONE)
    
    text = f"""
{EMOJI['phone']} <b>Крок 1/2: Твій номер телефону</b>

Будь ласка, надішли номер телефону для зв'язку:

<i>Формат: +380XXXXXXXXX або 0XXXXXXXXX</i>
"""
    
    send_message(user_id, text)


def handle_phone_input(user_id, phone):
    """Обробка введення телефону"""
    if not validate_phone(phone):
        send_message(
            user_id,
            f"{EMOJI['phone']} <b>Упс!</b> Номер некоректний.\n\nСпробуй ще раз: +380XXXXXXXXX"
        )
        return
    
    normalized = normalize_phone(phone)
    set_user_state(user_id, STATE_AWAITING_ADDRESS, {'phone': normalized})
    
    text = f"""
{EMOJI['check']} Дякую!

{EMOJI['location']} <b>Крок 2/2: Адреса доставки</b>

Вкажи повну адресу (вулиця, будинок, квартира):
"""
    
    send_message(user_id, text)


def handle_address_input(user_id, address):
    """Обробка введення адреси"""
    if not validate_address(address):
        send_message(
            user_id,
            f"{EMOJI['location']} Вкажи повну адресу з номером будинку, будь ласка"
        )
        return
    
    # Отримуємо дані
    state_data = db.get_user_state(user_id)
    phone = state_data.get('state_data', {}).get('phone')
    cart = get_user_cart(user_id)
    
    # Формуємо замовлення
    total = sum(item['quantity'] * item['price'] for item in cart)
    items_json = json.dumps(cart, ensure_ascii=False)
    
    # Зберігаємо
    order_id = db.create_order(user_id, phone, address, items_json, total)
    
    # Відправляємо в Google Sheets
    try:
        sheets.add_order({
            'order_id': order_id,
            'user_id': user_id,
            'phone': phone,
            'address': address,
            'items': items_json,
            'total': total,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Sheets error: {e}")
    
    # Очищуємо кошик
    clear_cart(user_id)
    set_user_state(user_id, STATE_IDLE)
    
    # Підтвердження
    text = f"""
{EMOJI['party']} <b>Замовлення прийнято!</b> {EMOJI['party']}

📝 <b>Номер замовлення:</b> #{order_id}
{EMOJI['money']} <b>Сума:</b> {total:.0f} грн
{EMOJI['time']} <b>Час доставки:</b> ~45-60 хв

Ми зв'яжемося з тобою найближчим часом!

{EMOJI['heart']} <b>Дякуємо за замовлення!</b> {EMOJI['yummy']}

<i>Повертайся ще — у нас завжди є щось смачненьке!</i>
"""
    
    send_message(user_id, text, reply_markup=get_main_keyboard())
    
    # Бонус для перших замовлень
    orders = db.get_user_orders(user_id)
    if len(orders) == 1:
        send_message(
            user_id,
            f"{EMOJI['gift']} <b>Вітаємо з першим замовленням!</b>\n\nОтримуй знижку 10% на наступне замовлення з промокодом: FERRIK10"
        )


# ============================================================================
# WEBHOOK HANDLER
# ============================================================================
@app.route('/webhook', methods=['POST'])  # ⬅️ ВИПРАВЛЕНО: було /webhook/webhook
def webhook():
    """Основний обробник webhook"""
    try:
        update = request.get_json()
        logger.info(f"📨 Received update: {json.dumps(update, ensure_ascii=False)[:200]}")
        
        # Обробка повідомлень
        if 'message' in update:
            message = update['message']
            user_id = message['from']['id']
            username = message['from'].get('username', '')
            
            # Команди
            if 'text' in message:
                text = message['text']
                
                if text == '/start':
                    handle_start(user_id, username)
                elif text == '/menu':
                    handle_menu(user_id)
                elif text == '/cart':
                    handle_cart(user_id)
                else:
                    # Обробка стану
                    state = get_user_state(user_id)
                    
                    if state == STATE_AWAITING_PHONE:
                        handle_phone_input(user_id, text)
                    elif state == STATE_AWAITING_ADDRESS:
                        handle_address_input(user_id, text)
                    else:
                        # Пошук по меню (AI-подібно)
                        send_message(
                            user_id,
                            f"{EMOJI['search']} Шукаю «{text}»...\n\n<i>Функція пошуку в розробці!</i> {EMOJI['wink']}",
                            reply_markup=get_main_keyboard()
                        )
        
        # Обробка callback
        elif 'callback_query' in update:
            callback = update['callback_query']
            user_id = callback['from']['id']
            callback_id = callback['id']
            data = callback['data']
            
            # Роутинг callback
            if data == 'menu':
                handle_menu(user_id)
            elif data == 'cart':
                handle_cart(user_id)
            elif data == 'checkout':
                handle_checkout(user_id)
            elif data == 'clear_cart':
                clear_cart(user_id)
                answer_callback(callback_id, f"{EMOJI['check']} Кошик очищено")
                handle_cart(user_id)
            elif data.startswith('cat_'):
                category = data[4:]
                handle_category(user_id, category)
            elif data.startswith('add_'):
                item_id = data[4:]
                handle_add_to_cart(user_id, item_id, callback_id)
            elif data == 'promos':
                send_message(user_id, f"{EMOJI['gift']} Акції скоро!")
            elif data == 'history':
                orders = db.get_user_orders(user_id)
                send_message(
                    user_id,
                    f"{EMOJI['history']} Ти зробив {len(orders)} замовлень! {EMOJI['fire']}"
                )
            elif data == 'badges':
                level = get_user_level(user_id)
                send_message(
                    user_id,
                    f"{level['emoji']} <b>Твій рівень: {level['level']}</b>\n\nПродовжуй замовляти!"
                )
            else:
                answer_callback(callback_id)
        
        return {'ok': True}
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return {'ok': False}, 500


@app.route('/', methods=['GET'])
def index():
    """Головна сторінка"""
    return f"""
    <h1>{EMOJI['rocket']} Ferrik Bot is running!</h1>
    <p>Status: {EMOJI['check']} Active</p>
    <p>Version: 2.0 - Enhanced Experience</p>
    """


# ============================================================================
# ЗАПУСК
# ============================================================================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
