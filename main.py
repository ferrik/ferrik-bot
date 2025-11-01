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

# ============================================================================
# ІМПОРТИ - ВИПРАВЛЕНО!
# ============================================================================
# ✅ ПРАВИЛЬНІ ІМПОРТИ - використовуй app.services, app.database
try:
    from app.utils.validators import (
        safe_parse_price, 
        validate_phone, 
        normalize_phone, 
        validate_address
    )
    logger.info("✅ Utils imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Utils import warning: {e}")

# ============================================================================
# ЕМОДЖІ ТА ТЕКСТИ (Персональність бота)
# ============================================================================
EMOJI = {
    'hello': '👋',
    'food': '🍴',
    'pizza': '🍕',
    'burger': '🍔',
    'sushi': '🍣',
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

# ============================================================================
# СТАНИ КОРИСТУВАЧА
# ============================================================================
STATE_IDLE = 'idle'
STATE_BROWSING = 'browsing'
STATE_AWAITING_PHONE = 'awaiting_phone'
STATE_AWAITING_ADDRESS = 'awaiting_address'
STATE_CONFIRMING = 'confirming'

# ============================================================================
# IN-MEMORY STORAGE (поки без БД)
# ============================================================================
user_states = {}
user_carts = {}
user_orders = {}

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
        response = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Send message error: {e}")
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
        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json=payload, timeout=5)
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


# ============================================================================
# ОБРОБНИКИ КОМАНД
# ============================================================================

def handle_start(user_id, username):
    """Обробка /start"""
    is_new = user_id not in user_states
    
    if is_new:
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
        text = f"""
{EMOJI['party']} <b>З поверненням!</b>

Рада тебе знову бачити! {EMOJI['heart']}

Що будемо замовляти сьогодні? {EMOJI['yummy']}
"""
    
    send_message(user_id, text, reply_markup=get_main_keyboard())
    user_states[user_id] = STATE_IDLE


def handle_demo_menu(user_id):
    """Показати демо-меню"""
    text = f"""
{EMOJI['food']} <b>МЕНЮ FERRIK</b> {EMOJI['sparkles']}

<i>Демо-версія. Підключи Google Sheets для реального меню!</i>

<b>Доступні страви:</b>
🍕 Піца Маргарита - 180 грн
🍔 Бургер Класик - 150 грн
🍱 Рол Філадельфія - 220 грн
🥗 Салат Цезар - 120 грн
🍰 Тірамісу - 95 грн

{EMOJI['fire']} ТОП вибір: Рол Філадельфія ⭐⭐⭐⭐⭐
"""
    
    send_message(user_id, text, reply_markup=get_main_keyboard())


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Головна сторінка"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ferrik Bot</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            .container {{
                background: rgba(255,255,255,0.1);
                padding: 40px;
                border-radius: 20px;
                backdrop-filter: blur(10px);
            }}
            h1 {{
                font-size: 3em;
                margin-bottom: 20px;
            }}
            .status {{
                font-size: 1.5em;
                margin: 20px 0;
            }}
            .emoji {{
                font-size: 2em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1><span class="emoji">🍴</span> Ferrik Bot v2.0</h1>
            <div class="status">
                <span class="emoji">✅</span> Status: <strong>Active & Running</strong>
            </div>
            <p>Твій персональний смаковий супутник 👨‍🍳</p>
            <p><em>Відправь /start боту щоб почати!</em></p>
        </div>
    </body>
    </html>
    """


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0',
        'bot': 'ferrik-bot'
    }, 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram"""
    try:
        update = request.get_json()
        
        if not update:
            return {'ok': False}, 400
        
        logger.info(f"📨 Received update from Telegram")
        
        # Обробка повідомлень
        if 'message' in update:
            message = update['message']
            user_id = message['from']['id']
            username = message['from'].get('username', message['from'].get('first_name', ''))
            
            if 'text' in message:
                text = message['text']
                
                if text == '/start':
                    handle_start(user_id, username)
                elif text == '/menu':
                    handle_demo_menu(user_id)
                else:
                    send_message(
                        user_id,
                        f"{EMOJI['food']} Привіт! Напиши /start або /menu для початку 😊",
                        reply_markup=get_main_keyboard()
                    )
        
        # Обробка callback queries
        elif 'callback_query' in update:
            callback = update['callback_query']
            user_id = callback['from']['id']
            callback_id = callback['id']
            data = callback['data']
            
            if data == 'menu':
                handle_demo_menu(user_id)
                answer_callback(callback_id)
            elif data == 'cart':
                send_message(user_id, f"{EMOJI['cart']} Твій кошик порожній!", reply_markup=get_main_keyboard())
                answer_callback(callback_id)
            elif data == 'promos':
                send_message(user_id, f"{EMOJI['gift']} Акції скоро!", reply_markup=get_main_keyboard())
                answer_callback(callback_id)
            else:
                answer_callback(callback_id)
        
        return {'ok': True}, 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return {'ok': False}, 500


# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    logger.info("🚀 Starting Ferrik Bot v2.0...")
    logger.info(f"🔗 Bot Token: {BOT_TOKEN[:20]}..." if BOT_TOKEN else "⚠️ BOT_TOKEN not set")
    logger.info(f"🌐 Running on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
