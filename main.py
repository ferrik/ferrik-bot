# ============================================================================
# 📄 main.py - FerrikFoot Bot - Основний файл (WEBHOOK VERSION)
# ============================================================================
"""
Telegram FoodBot для замовлення їжі в Тернополі
Мультиресторанність + AI рекомендації + PostgreSQL
Deploy на Render з Webhook
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import TelegramError

# Google
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# Database
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from app.models import (
    Base, Restaurant, MenuItem, Order, OrderItem, 
    User, PromoCode, Review, Config
)

load_dotenv()

# ============================================================================
# КОНФІГ
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
OPERATOR_CHAT_ID = int(os.getenv('OPERATOR_CHAT_ID', 0)) if os.getenv('OPERATOR_CHAT_ID') else None
DATABASE_URL = os.getenv('DATABASE_URL')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com')
PORT = int(os.getenv('PORT', 5000))

# ============================================================================
# БД ІНІЦІАЛІЗАЦІЯ
# ============================================================================

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Ініціалізація БД"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")

init_db()

# ============================================================================
# GOOGLE SHEETS ІНТЕГРАЦІЯ
# ============================================================================

def get_sheets_client():
    """Підключитися до Google Sheets"""
    try:
        if not GOOGLE_CREDENTIALS_JSON:
            raise ValueError("❌ GOOGLE_CREDENTIALS_JSON не встановлена")
        
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict, scopes=scope
        )
        gc = gspread.authorize(credentials)
        return gc.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        logger.error(f"❌ Sheets connection error: {e}")
        return None

# ============================================================================
# GEMINI AI
# ============================================================================

def init_gemini():
    """Ініціалізація Gemini"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("✅ Gemini initialized")
    except Exception as e:
        logger.error(f"❌ Gemini error: {e}")

init_gemini()

def get_ai_recommendations(query: str, menu_items: List[Dict], session: Session) -> str:
    """Отримати AI рекомендації"""
    try:
        # Формуємо меню для контексту
        menu_text = "\n".join([
            f"• {item.name} ({item.price}₴) - {item.restaurant.name}"
            for item in menu_items[:20]
        ])
        
        prompt = f"""Ти асистент для замовлення їжі в Тернополі.

МЕНЮ:
{menu_text}

ЗАПИТ КОРИСТУВАЧА: "{query}"

Дай рекомендацію 2-3 страв з поясненням на українській мові. Формат:
🍽 Назва страви - 120₴
Причина: ...

Будь стислим!"""
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text if response else "❌ Не вдалось отримати рекомендацію"
    except Exception as e:
        logger.error(f"❌ AI error: {e}")
        return "❌ AI асистент тимчасово недоступний"

# ============================================================================
# FLASK APP + BOT SETUP
# ============================================================================

app = Flask(__name__)

# Global bot application
bot_app: Optional[Application] = None

# In-memory storage для сесій
user_carts: Dict[int, List[Dict]] = {}
user_states: Dict[int, Dict[str, Any]] = {}

# ============================================================================
# УТИЛІТНІ ФУНКЦІЇ
# ============================================================================

def get_session():
    """Отримати DB сесію"""
    return SessionLocal()

def get_user_cart(user_id: int) -> List[Dict]:
    """Отримати кошик користувача"""
    return user_carts.get(user_id, [])

def add_to_cart(user_id: int, menu_item: MenuItem, quantity: int = 1):
    """Додати в кошик"""
    if user_id not in user_carts:
        user_carts[user_id] = []
    
    # Перевіряємо чи товар вже в кошику
    for item in user_carts[user_id]:
        if item['id'] == menu_item.id:
            item['quantity'] += quantity
            return
    
    user_carts[user_id].append({
        'id': menu_item.id,
        'name': menu_item.name,
        'price': float(menu_item.price),
        'restaurant_id': menu_item.restaurant_id,
        'quantity': quantity
    })

def clear_cart(user_id: int):
    """Очистити кошик"""
    if user_id in user_carts:
        user_carts[user_id] = []

def get_cart_total(user_id: int) -> float:
    """Розрахувати суму кошика"""
    cart = get_user_cart(user_id)
    return sum(item['price'] * item['quantity'] for item in cart)

# ============================================================================
# KEYBOARDS
# ============================================================================

def get_main_menu_keyboard():
    """Головне меню"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Меню ресторанів", callback_data="menu_restaurants")],
        [InlineKeyboardButton("⭐ AI Рекомендація", callback_data="ai_recommend")],
        [InlineKeyboardButton("🛒 Кошик", callback_data="view_cart")],
        [InlineKeyboardButton("📦 Мої замовлення", callback_data="my_orders")],
        [InlineKeyboardButton("🆘 Допомога", callback_data="help")]
    ])

def get_restaurants_keyboard(session: Session):
    """Клавіатура ресторанів"""
    restaurants = session.query(Restaurant).filter(
        Restaurant.status == 'active'
    ).order_by(Restaurant.is_premium.desc()).all()
    
    keyboard = []
    for rest in restaurants:
        premium_icon = "👑" if rest.is_premium else ""
        rating = f"⭐{rest.rating}" if rest.rating else ""
        text = f"{premium_icon} {rest.name} {rating}".strip()
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"restaurant_{rest.id}")
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def get_menu_keyboard(restaurant_id: int, session: Session):
    """Клавіатура меню ресторану"""
    items = session.query(MenuItem).filter(
        MenuItem.restaurant_id == restaurant_id,
        MenuItem.is_active == True
    ).order_by(MenuItem.category).all()
    
    keyboard = []
    for item in items:
        text = f"🍽 {item.name} - {item.price}₴"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"add_item_{item.id}")
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_restaurants")])
    return InlineKeyboardMarkup(keyboard)

# ============================================================================
# TELEGRAM HANDLERS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_id = update.effective_user.id
    
    # Створити або отримати користувача
    session = get_session()
    user = session.query(User).filter(User.telegram_id == user_id).first()
    
    if not user:
        user = User(
            telegram_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
        session.add(user)
        session.commit()
    
    session.close()
    
    message = f"""👋 Привіт, {update.effective_user.first_name}!

Я FerrikFoot - твій помічник для замовлення їжі в Тернополі 🍕

Обери дію:"""
    
    await update.message.reply_text(message, reply_markup=get_main_menu_keyboard())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка callback кнопок"""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    session = get_session()
    
    try:
        if data == "menu_restaurants":
            await query.answer()
            await query.edit_message_text(
                "🏪 Оберіть ресторан:",
                reply_markup=get_restaurants_keyboard(session)
            )
        
        elif data.startswith("restaurant_"):
            rest_id = int(data.split("_")[1])
            await query.answer()
            restaurant = session.query(Restaurant).filter(
                Restaurant.id == rest_id
            ).first()
            
            if restaurant:
                text = f"📋 Меню {restaurant.name}\n\nОберіть страву:"
                await query.edit_message_text(
                    text,
                    reply_markup=get_menu_keyboard(rest_id, session)
                )
        
        elif data.startswith("add_item_"):
            item_id = int(data.split("_")[2])
            item = session.query(MenuItem).filter(MenuItem.id == item_id).first()
            
            if item:
                add_to_cart(user_id, item)
                await query.answer(f"✅ {item.name} додано в кошик!")
        
        elif data == "view_cart":
            cart = get_user_cart(user_id)
            
            if not cart:
                await query.answer("🛒 Кошик порожній!")
                return
            
            total = get_cart_total(user_id)
            
            message = "🛒 <b>Ваш кошик</b>\n\n"
            for item in cart:
                message += f"🍽 <b>{item['name']}</b>\n"
                message += f"   {item['quantity']} x {item['price']}₴ = {item['quantity'] * item['price']}₴\n\n"
            
            message += f"━━━━━━━━━━━━━━━\n💰 <b>Разом: {total}₴</b>"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Оформити", callback_data="checkout")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
            ])
            
            await query.answer()
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode="HTML")
        
        elif data == "checkout":
            cart = get_user_cart(user_id)
            
            if not cart:
                await query.answer("Кошик порожній!")
                return
            
            # Запросити телефон
            user_state = {
                'state': 'waiting_phone',
                'cart': cart
            }
            user_states[user_id] = user_state
            
            await query.answer()
            await query.edit_message_text(
                "📱 Введіть ваш номер телефону:\n\n"
                "Приклад: +380971234567 або 0971234567"
            )
        
        elif data == "ai_recommend":
            await query.answer()
            await query.edit_message_text(
                "🤖 Розкажіть що ви хочете замовити:\n\n"
                "Приклади:\n"
                "• Щось на обід\n"
                "• Піца для двох\n"
                "• Щось без м'яса\n"
                "• Легкий перекус"
            )
            user_states[user_id] = {'state': 'waiting_ai_query'}
        
        elif data == "back_main":
            await query.answer()
            await query.edit_message_text(
                "🍕 Обери дію:",
                reply_markup=get_main_menu_keyboard()
            )
        
        elif data == "back_restaurants":
            await query.answer()
            await query.edit_message_text(
                "🏪 Оберіть ресторан:",
                reply_markup=get_restaurants_keyboard(session)
            )
        
        elif data == "my_orders":
            orders = session.query(Order).filter(
                Order.telegram_user_id == user_id
            ).order_by(Order.created_at.desc()).limit(5).all()
            
            if not orders:
                await query.answer("Немає замовлень")
                return
            
            message = "📦 <b>Ваші замовлення</b>\n\n"
            for order in orders:
                status_emoji = {
                    'new': '🆕',
                    'cooking': '👨‍🍳',
                    'delivering': '🚚',
                    'delivered': '✅',
                    'cancelled': '❌'
                }.get(order.status, '❓')
                
                message += f"{status_emoji} #{order.external_id[:8]}\n"
                message += f"💰 {order.final_amount}₴ | {order.created_at.strftime('%d.%m %H:%M')}\n"
                message += f"Статус: {order.status}\n\n"
            
            await query.answer()
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
                ]),
                parse_mode="HTML"
            )
        
        elif data == "help":
            help_text = """🆘 <b>ДОПОМОГА</b>

<b>Як зробити замовлення:</b>
1️⃣ Оберіть ресторан
2️⃣ Виберіть страви
3️⃣ Переглядніть кошик
4️⃣ Оформіть замовлення

<b>AI Рекомендація:</b>
Просто розкажіть що хочете! 🤖

<b>Питання?</b>
Напишіть @support
"""
            await query.answer()
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
                ]),
                parse_mode="HTML"
            )
    
    finally:
        session.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка текстових повідомлень"""
    user_id = update.effective_user.id
    text = update.message.text
    session = get_session()
    
    try:
        user_state = user_states.get(user_id, {})
        state = user_state.get('state')
        
        if state == 'waiting_ai_query':
            # AI рекомендація
            menu_items = session.query(MenuItem).filter(
                MenuItem.is_active == True
            ).all()
            
            if not menu_items:
                await update.message.reply_text("❌ Меню недоступне")
                return
            
            await update.message.reply_text("⏳ Шукаю рекомендації...")
            
            recommendations = get_ai_recommendations(text, menu_items, session)
            
            await update.message.reply_text(
                f"🤖 <b>AI Рекомендація:</b>\n\n{recommendations}",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
            
            user_states.pop(user_id, None)
        
        elif state == 'waiting_phone':
            # Валідація телефону
            phone = text.strip()
            if not phone.startswith('+') and not phone.startswith('0'):
                await update.message.reply_text("❌ Неправильний формат. Спробуйте ще раз.")
                return
            
            user_states[user_id]['phone'] = phone
            user_states[user_id]['state'] = 'waiting_address'
            
            await update.message.reply_text(
                "📍 Введіть адресу доставки:\n\n"
                "Приклад: вул. Руська, 12, кв. 5"
            )
        
        elif state == 'waiting_address':
            # Адреса
            user_states[user_id]['address'] = text.strip()
            user_states[user_id]['state'] = 'waiting_confirmation'
            
            phone = user_states[user_id]['phone']
            address = user_states[user_id]['address']
            cart = user_states[user_id]['cart']
            total = sum(item['price'] * item['quantity'] for item in cart)
            
            confirmation = f"""✅ <b>ПІДТВЕРДІТЬ ЗАМОВЛЕННЯ</b>

📋 Товари:
"""
            for item in cart:
                confirmation += f"• {item['name']} x{item['quantity']} - {item['quantity'] * item['price']}₴\n"
            
            confirmation += f"""
📱 Телефон: {phone}
📍 Адреса: {address}
💰 Сума: {total}₴

Все правильно?
Напишіть "Так" для підтвердження або "Ні" для скасування"""
            
            await update.message.reply_text(confirmation, parse_mode="HTML")
        
        elif state == 'waiting_confirmation':
            if text.lower() in ['так', 'yes', 'y']:
                # Створити замовлення
                phone = user_states[user_id]['phone']
                address = user_states[user_id]['address']
                cart = user_states[user_id]['cart']
                
                total = sum(item['price'] * item['quantity'] for item in cart)
                restaurant_id = cart[0]['restaurant_id']
                
                # Отримати ресторан для комісії
                restaurant = session.query(Restaurant).filter(
                    Restaurant.id == restaurant_id
                ).first()
                
                commission_rate = restaurant.commission_rate / 100 if restaurant else 0.15
                commission_amount = total * commission_rate
                
                order = Order(
                    external_id=f"ORD{int(datetime.now().timestamp())}",
                    telegram_user_id=user_id,
                    restaurant_id=restaurant_id,
                    total_amount=total,
                    delivery_cost=30,
                    final_amount=total + 30,
                    address=address,
                    phone=phone,
                    payment_method='cash',
                    status='new',
                    commission_amount=commission_amount
                )
                
                session.add(order)
                session.flush()
                
                # Додати товари
                for item in cart:
                    order_item = OrderItem(
                        order_id=order.id,
                        menu_item_id=item['id'],
                        quantity=item['quantity'],
                        unit_price=item['price'],
                        total_price=item['price'] * item['quantity']
                    )
                    session.add(order_item)
                
                session.commit()
                
                # Повідомлення користувачу
                success_msg = f"""🎉 <b>ЗАМОВЛЕННЯ ПРИЙНЯТО!</b>

<b>Номер замовлення:</b> #{order.external_id}
<b>Сума:</b> {order.final_amount}₴
<b>Адреса:</b> {address}

Ми вам передзвонимо найближчим часом!"""
                
                await update.message.reply_text(
                    success_msg,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
                
                # Повідомлення оператору
                if OPERATOR_CHAT_ID:
                    operator_msg = f"""🆕 <b>НОВЕ ЗАМОВЛЕННЯ</b>

ID: #{order.external_id}
Користувач: @{update.effective_user.username or update.effective_user.id}
Телефон: {phone}
Адреса: {address}

<b>Товари:</b>
"""
                    for item in cart:
                        operator_msg += f"• {item['name']} x{item['quantity']} - {item['quantity'] * item['price']}₴\n"
                    
                    operator_msg += f"\n<b>Разом: {order.final_amount}₴</b>\n"
                    operator_msg += f"Комісія: {commission_amount:.2f}₴"
                    
                    try:
                        await context.bot.send_message(
                            chat_id=OPERATOR_CHAT_ID,
                            text=operator_msg,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"❌ Не вдалось надіслати оператору: {e}")
                
                # Очистити сесію
                clear_cart(user_id)
                user_states.pop(user_id, None)
            
            else:
                await update.message.reply_text(
                    "❌ Замовлення скасовано.",
                    reply_markup=get_main_menu_keyboard()
                )
                clear_cart(user_id)
                user_states.pop(user_id, None)
    
    finally:
        session.close()

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    return jsonify({"status": "ok", "bot": "FerrikFoot v3.0"})

@app.route('/health')
def health():
    db_ok = False
    try:
        session = get_session()
        session.query(Restaurant).first()
        session.close()
        db_ok = True
    except:
        pass
    
    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "database": "✅" if db_ok else "❌",
        "bot": "ready"
    })

# ============================================================================
# 🔧 ВИПРАВЛЕННЯ: Додано обидва роути для webhook
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Telegram webhook endpoint (основний)"""
    return handle_telegram_webhook()


@app.route('/webhook/webhook', methods=['POST'])
def webhook_handler_double():
    """Telegram webhook endpoint (подвійний шлях для сумісності)"""
    return handle_telegram_webhook()


def handle_telegram_webhook():
    """Спільна логіка обробки webhook"""
    try:
        if bot_app is None:
            logger.error("❌ Bot application not initialized")
            return jsonify({"status": "error", "message": "Bot not ready"}), 503

        # Отримати JSON від Telegram
        data = request.get_json(force=True)
        logger.info(f"📥 Received webhook: {data.get('update_id', 'unknown')}")

        # Створити Update об'єкт
        update = Update.de_json(data, bot_app.bot)

        # Асинхронна обробка update з перевіркою ініціалізації
        async def process_webhook_update():
            if not bot_app._initialized:
                await bot_app.initialize()
            await bot_app.process_update(update)

        asyncio.run(process_webhook_update())

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
# ============================================================================
# BOT INITIALIZATION
# ============================================================================

def setup_bot():
    """Налаштувати бота"""
    global bot_app
    
    # Створити Application
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Додати handlers
    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Bot initialized and ready")
    logger.info(f"⚠️ Webhook endpoints:")
    logger.info(f"   • {WEBHOOK_URL}/webhook")
    logger.info(f"   • {WEBHOOK_URL}/webhook/webhook")

# Ініціалізувати бота при старті
setup_bot()

# ============================================================================
# GUNICORN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
