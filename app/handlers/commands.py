"""
🎯 ОБРОБНИКИ КОМАНД - З WARM GREETINGS
Скопіюйте весь файл!
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.utils.session import get_user_session, get_user_stats, update_user_session
from app.utils.warm_greetings import WarmGreetings

logger = logging.getLogger(__name__)

# ============================================================================
# /start - ТЕПЛИЙ ЗАПУСК!
# ============================================================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /start
    Використовує WarmGreetings для персоналізованого привітання
    """
    user = update.effective_user
    
    logger.info(f"👤 User {user.id} (@{user.username}) started bot")
    
    # 1️⃣ ОТРИМУЄМО ДАНІ КОРИСТУВАЧА
    session = get_user_session(user.id)
    stats = get_user_stats(user.id)
    
    # 2️⃣ ВИБИРАЄМО ПРИВІТАННЯ НА ОСНОВІ ІСТОРІЇ
    greeting = WarmGreetings.get_greeting_by_order_count(
        order_count=stats['order_count'],
        badge=stats['badge']['name'],
        bonus=stats['bonus_points']
    )
    
    logger.info(f"📨 Greeting type: order_count={stats['order_count']}")
    
    # 3️⃣ СТВОРЮЄМО КЛАВІАТУРУ З КНОПКАМИ
    keyboard = [
        [
            InlineKeyboardButton("🎁 Сюрприз!", callback_data="surprise_me"),
            InlineKeyboardButton("📋 Меню", callback_data="show_menu"),
        ],
        [
            InlineKeyboardButton("🛒 Кошик", callback_data="show_cart"),
            InlineKeyboardButton("⭐ Профіль", callback_data="show_profile"),
        ],
        [
            InlineKeyboardButton("🎯 Челлендж", callback_data="show_challenge"),
            InlineKeyboardButton("ℹ️ Допомога", callback_data="show_help"),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 4️⃣ ВІДПРАВЛЯЄМО ПРИВІТАННЯ
    await update.message.reply_text(
        greeting,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.info(f"✅ Welcome message sent to {user.id}")


# ============================================================================
# /menu - ПОКАЗАТИ МЕНЮ
# ============================================================================

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /menu - показує меню"""
    user = update.effective_user
    
    logger.info(f"📋 User {user.id} requested menu")
    
    # Заглушка (на практиці тут буде завантаження з Google Sheets)
    menu_text = """📋 **МЕНЮ**

**Піці:**
🔹 Маргарита — 120 грн ⭐⭐⭐⭐
🔹 Пепероні — 150 грн ⭐⭐⭐⭐⭐

**Напої:**
🔹 Cola 0.5л — 30 грн
🔹 Сік — 40 грн

💬 Напишіть назву щоб додати у кошик!"""
    
    keyboard = [
        [InlineKeyboardButton("🛒 Мій кошик", callback_data="show_cart")],
        [InlineKeyboardButton("🎁 Сюрприз", callback_data="surprise_me")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        menu_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# /cart - ПОКАЗАТИ КОШИК
# ============================================================================

async def cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cart - показує кошик"""
    user = update.effective_user
    
    logger.info(f"🛒 User {user.id} requested cart")
    
    from app.utils.session import get_user_cart
    cart = get_user_cart(user.id)
    
    if not cart or len(cart) == 0:
        await update.message.reply_text(
            "🛒 **Ваш кошик порожній!** 😔\n\n"
            "Додайте щось смачне з меню! 🍕",
            parse_mode='Markdown'
        )
        return
    
    # Формуємо кошик
    cart_text = "🛒 **Ваш кошик:**\n\n"
    total = 0
    
    for idx, item in enumerate(cart, 1):
        name = item.get('name', 'Unknown')
        price = item.get('price', 0)
        qty = item.get('quantity', 1)
        subtotal = price * qty
        total += subtotal
        
        cart_text += f"{idx}. {name}\n"
        cart_text += f"   {qty} × {price} грн = **{subtotal} грн**\n\n"
    
    cart_text += f"\n💰 **Всього: {total} грн**"
    
    keyboard = [
        [InlineKeyboardButton("🎁 Промокод", callback_data="enter_promocode")],
        [InlineKeyboardButton("✅ Оформити", callback_data="checkout")],
        [InlineKeyboardButton("🗑️ Очистити", callback_data="clear_cart")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        cart_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# /order - ОФОРМИТИ ЗАМОВЛЕННЯ
# ============================================================================

async def order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /order - почати оформлення"""
    user = update.effective_user
    
    logger.info(f"📦 User {user.id} started checkout")
    
    from app.utils.session import get_user_cart
    cart = get_user_cart(user.id)
    
    if not cart or len(cart) == 0:
        await update.message.reply_text(
            "🛒 **Кошик порожній!** 😔\n\n"
            "Нема чого замовляти!",
            parse_mode='Markdown'
        )
        return
    
    # Встановлюємо стан "очікуємо телефон"
    update_user_session(user.id, {'state': 'awaiting_phone'})
    
    await update.message.reply_text(
        "📱 **Введіть ваш номер телефону:**\n\n"
        "_(наприклад: +380501234567 або 0501234567)_",
        parse_mode='Markdown'
    )


# ============================================================================
# /help - ДОПОМОГА
# ============================================================================

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - допомога"""
    help_text = """❓ **ДОПОМОГА**

**Мої команди:**
/start — Почати роботу
/menu — Переглянути меню
/cart — Мій кошик
/order — Оформити замовлення
/profile — Мій профіль
/help — Ця допомога

**Як замовити:**
1️⃣ Напишіть назву страви або натисніть [📋 Меню]
2️⃣ Виберіть що хочете
3️⃣ Натисніть [✅ Оформити]
4️⃣ Введіть телефон та адресу

**Питання?**
📞 Напишіть /support для зв'язку з нами"""
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )


# ============================================================================
# /cancel - СКАСУВАТИ
# ============================================================================

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cancel - скасувати операцію"""
    user = update.effective_user
    
    logger.info(f"❌ User {user.id} cancelled operation")
    
    update_user_session(user.id, {'state': 'idle'})
    
    keyboard = [
        [InlineKeyboardButton("📋 Меню", callback_data="show_menu")],
        [InlineKeyboardButton("/start", callback_data="back_to_menu")]
    ]
    
    await update.message.reply_text(
        "❌ **Операція скасована**\n\n"
        "Почніть з нуля! 👋",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ============================================================================
# ДОПОМІЖНА ФУНКЦІЯ - РЕЄСТРАЦІЯ HANDLERS
# ============================================================================

def register_command_handlers(application):
    """
    Реєстрація всіх command handlers
    
    Використовуйте в main.py:
    ───────────────────────────
    from app.handlers.commands import register_command_handlers
    
    # У функції setup_handlers():
    register_command_handlers(app)
    """
    from telegram.ext import CommandHandler
    
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("menu", menu_handler))
    application.add_handler(CommandHandler("cart", cart_handler))
    application.add_handler(CommandHandler("order", order_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("cancel", cancel_handler))
    
    logger.info("✅ Command handlers registered")
