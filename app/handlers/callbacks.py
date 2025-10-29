"""
🔘 ОБРОБНИКИ CALLBACK QUERIES - З SURPRISE ME
Скопіюйте весь файл!
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.utils.session import (
    get_user_session,
    get_user_stats,
    update_user_session,
    get_user_cart,
    add_to_cart,
    clear_user_cart,
)
from app.utils.surprise_me import SurpriseMe
from app.utils.warm_greetings import WarmGreetings

logger = logging.getLogger(__name__)

# ============================================================================
# 🎁 SURPRISE ME - ГОЛОВНИЙ CALLBACK
# ============================================================================

async def surprise_me_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback: surprise_me
    Генерує AI комбо зі знижкою та додає в кошик
    """
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"🎁 User {user.id} clicked Surprise Me")
    
    try:
        # 1️⃣ ОТРИМУЄМО МЕНЮ (заглушка - у реалю з Google Sheets)
        menu_items = [
            {'id': '1', 'name': 'Піца Маргарита', 'category': 'Pizza', 'price': 120},
            {'id': '2', 'name': 'Піца Пепероні', 'category': 'Pizza', 'price': 150},
            {'id': '3', 'name': 'Цезар салат', 'category': 'Salad', 'price': 80},
            {'id': '4', 'name': 'Чорна Форест', 'category': 'Dessert', 'price': 90},
            {'id': '5', 'name': 'Cola 0.5л', 'category': 'Drink', 'price': 30},
            {'id': '6', 'name': 'Філадельфія рол', 'category': 'Sushi', 'price': 180},
        ]
        
        if not menu_items or len(menu_items) < 2:
            await query.answer("❌ Меню недоступне!", show_alert=True)
            return
        
        # 2️⃣ ГЕНЕРУЄМО СЮРПРИЗ
        stats = get_user_stats(user.id)
        surprise = SurpriseMe.generate_surprise(
            menu_items,
            user_order_count=stats['order_count'],
            user_favorites=[]
        )
        
        if not surprise:
            await query.answer("❌ Не можу генерувати сюрприз!", show_alert=True)
            return
        
        # 3️⃣ ФОРМАТУЄМО ПОВІДОМЛЕННЯ
        message = SurpriseMe.format_surprise_message(surprise)
        
        # 4️⃣ ЗБЕРІГАЄМО В СЕСІЮ (на випадок прийняття)
        surprise_items = SurpriseMe.apply_surprise_to_cart(surprise)
        update_user_session(user.id, {
            'current_surprise': surprise,
            'surprise_items': surprise_items,
        })
        
        logger.info(f"✅ Surprise generated: {len(surprise['items'])} items, {surprise['discount']}% discount")
        
        # 5️⃣ КНОПКИ
        keyboard = [
            [InlineKeyboardButton("✅ Беру сюрприз!", callback_data="accept_surprise")],
            [InlineKeyboardButton("❌ Генерувати ще", callback_data="surprise_me")],
            [InlineKeyboardButton("📋 До меню", callback_data="show_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 6️⃣ РЕДАГУЄМО ПОВІДОМЛЕННЯ
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        await query.answer()  # Закрити loading
        
    except Exception as e:
        logger.error(f"❌ Error in surprise_me: {e}")
        await query.answer("❌ Помилка! Спробуйте пізніше", show_alert=True)


# ============================================================================
# ✅ ACCEPT SURPRISE - ДОДАТИ В КОШИК
# ============================================================================

async def accept_surprise_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback: accept_surprise
    Додає сюрприз в кошик користувача
    """
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"✅ User {user.id} accepted surprise")
    
    try:
        # 1️⃣ ОТРИМУЄМО СЮРПРИЗ З СЕСІЇ
        session = get_user_session(user.id)
        surprise_items = session.get('surprise_items', [])
        current_surprise = session.get('current_surprise', {})
        
        if not surprise_items:
            await query.answer("❌ Сюрприз не знайдено!", show_alert=True)
            return
        
        # 2️⃣ ДОДАЄМО КОЖЕН ТОВАР У КОШИК
        for item in surprise_items:
            add_to_cart(user.id, item)
        
        logger.info(f"✅ Added {len(surprise_items)} items to cart")
        
        # 3️⃣ ФОРМУЄМО ПОВІДОМЛЕННЯ
        discount = current_surprise.get('discount', 0)
        total = current_surprise.get('total_discounted', 0)
        
        message = f"""🎉 **СЮРПРИЗ АКТИВІРОВАН!** 🎉

✅ Додано {len(surprise_items)} товари до кошика!
💚 Знижка {discount}% автоматично застосована!

💰 **Сума:** {current_surprise.get('total_original', 0)} грн
🎯 **Зі знижкою:** {total:.0f} грн

Готовий оформити замовлення? 🚀"""
        
        # 4️⃣ КНОПКИ
        keyboard = [
            [InlineKeyboardButton("✅ Оформити!", callback_data="checkout")],
            [InlineKeyboardButton("📋 Ще щось додати", callback_data="show_menu")],
            [InlineKeyboardButton("🛒 Перегляд кошика", callback_data="show_cart")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 5️⃣ РЕДАГУЄМО ПОВІДОМЛЕННЯ
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        await query.answer("🎉 Добавлено в кошик!", show_alert=False)
        
    except Exception as e:
        logger.error(f"❌ Error accepting surprise: {e}")
        await query.answer("❌ Помилка при додаванні!", show_alert=True)


# ============================================================================
# 📋 SHOW MENU - ПОКАЗАТИ МЕНЮ
# ============================================================================

async def show_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: show_menu - показує меню"""
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"📋 User {user.id} opened menu")
    
    menu_text = """📋 **МЕНЮ**

**🍕 ПІЦІ:**
🔹 Маргарита — 120 грн ⭐⭐⭐⭐
🔹 Пепероні — 150 грн ⭐⭐⭐⭐⭐
🔹 Чотири сири — 180 грн ⭐⭐⭐⭐

**🥗 САЛАТИ:**
🔹 Цезар — 80 грн ⭐⭐⭐⭐
🔹 Грецький — 90 грн ⭐⭐⭐⭐

**🍣 СУШІ:**
🔹 Філадельфія — 180 грн ⭐⭐⭐⭐⭐
🔹 Каліфорнія — 160 грн ⭐⭐⭐⭐

**🥤 НАПОЇ:**
🔹 Cola, Sprite, Fanta — 30 грн
🔹 Сік — 40 грн

💬 Напишіть назву щоб додати у кошик!"""
    
    keyboard = [
        [InlineKeyboardButton("🛒 Мій кошик", callback_data="show_cart")],
        [InlineKeyboardButton("🎁 Сюрприз", callback_data="surprise_me")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        menu_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    await query.answer()


# ============================================================================
# 🛒 SHOW CART - ПОКАЗИТИ КОШИК
# ============================================================================

async def show_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: show_cart - показує кошик"""
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"🛒 User {user.id} opened cart")
    
    cart = get_user_cart(user.id)
    
    if not cart or len(cart) == 0:
        keyboard = [[InlineKeyboardButton("📋 Меню", callback_data="show_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🛒 **Ваш кошик порожній!** 😔\n\n"
            "Додайте щось смачне! 🍕",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.answer()
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
        [InlineKeyboardButton("📋 Ще товарів", callback_data="show_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        cart_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    await query.answer()


# ============================================================================
# 👤 SHOW PROFILE - ПРОФІЛЬ КОРИСТУВАЧА
# ============================================================================

async def show_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: show_profile - показує профіль"""
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"👤 User {user.id} opened profile")
    
    stats = get_user_stats(user.id)
    badge = stats['badge']
    
    profile_text = f"""**👤 ТЕ ПРОФІЛЬ**

**Статус:** {badge['emoji']} {badge['name']}

📊 **СТАТИСТИКА:**
• Замовлення: **{stats['order_count']}** 🍕
• Бонуси: **{stats['bonus_points']}** ⭐
• Допомога: /help

✨ Спасибі що з нами! 💚"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Меню", callback_data="show_menu")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        profile_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    await query.answer()


# ============================================================================
# 🎯 SHOW CHALLENGE - ЧЕЛЛЕНДЖ
# ============================================================================

async def show_challenge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: show_challenge - показує челлендж"""
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"🎯 User {user.id} opened challenge")
    
    challenge_text = """**🎯 ЧЕЛЛЕНДЖ ТИЖНЯ**

🌅 **СНІДАНОК ЧЕМПІОНА**
Замовте 3 різні сніданки!

📊 Прогрес: 0/3
[░░░░░░░░░░]

🏆 Награда: 150 бонусів! ⭐

💪 Дай, ти справиш! 🔥"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Меню", callback_data="show_menu")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        challenge_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    await query.answer()


# ============================================================================
# ⬅️ BACK TO MENU - НАЗАД
# ============================================================================

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: back_to_menu - назад до головного меню"""
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"⬅️ User {user.id} went back to menu")
    
    stats = get_user_stats(user.id)
    greeting = WarmGreetings.get_greeting_by_order_count(stats['order_count'])
    
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
    
    await query.edit_message_text(
        greeting,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    await query.answer()


# ============================================================================
# ℹ️ SHOW HELP - ДОПОМОГА
# ============================================================================

async def show_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: show_help - допомога"""
    query = update.callback_query
    
    help_text = """❓ **ДОПОМОГА**

**Команди:**
/start — Почати
/menu — Меню
/cart — Кошик
/order — Замовити
/help — Допомога

**Як замовити:**
1️⃣ Вибери товари з меню
2️⃣ Натисни [✅ Оформити]
3️⃣ Введи телефон та адресу

**Питання?**
📞 Напиши нам!"""
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    await query.answer()


# ============================================================================
# 🗑️ CLEAR CART - ОЧИСТИТИ КОШИК
# ============================================================================

async def clear_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: clear_cart - очистити кошик"""
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"🗑️ User {user.id} cleared cart")
    
    clear_user_cart(user.id)
    
    await query.answer("🗑️ Кошик очищено!", show_alert=False)
    
    keyboard = [
        [InlineKeyboardButton("📋 Меню", callback_data="show_menu")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🛒 **Кошик очищено!** 🗑️\n\n"
        "Почни заново! 🍕",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# 🔘 ГОЛОВНИЙ CALLBACK ROUTER
# ============================================================================

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ГОЛОВНИЙ ROUTER для всіх callback queries
    Розпізнає callback_data і викликає потрібну функцію
    """
    query = update.callback_query
    callback_data = query.data
    
    logger.info(f"🔘 Callback: {callback_data}")
    
    try:
        # МАРШРУТИЗАЦІЯ
        if callback_data == "surprise_me":
            await surprise_me_callback(update, context)
        
        elif callback_data == "accept_surprise":
            await accept_surprise_callback(update, context)
        
        elif callback_data == "show_menu":
            await show_menu_callback(update, context)
        
        elif callback_data == "show_cart":
            await show_cart_callback(update, context)
        
        elif callback_data == "show_profile":
            await show_profile_callback(update, context)
        
        elif callback_data == "show_challenge":
            await show_challenge_callback(update, context)
        
        elif callback_data == "show_help":
            await show_help_callback(update, context)
        
        elif callback_data == "back_to_menu":
            await back_to_menu_callback(update, context)
        
        elif callback_data == "clear_cart":
            await clear_cart_callback(update, context)
        
        # ЗАГЛУШКА для невідомих
        else:
            logger.warning(f"⚠️ Unknown callback: {callback_data}")
            await query.answer(f"❓ Невідома команда: {callback_data}", show_alert=True)
    
    except Exception as e:
        logger.error(f"❌ Error in callback: {e}")
        await query.answer("❌ Помилка! Спробуйте пізніше", show_alert=True)


# ============================================================================
# ДОПОМІЖНА ФУНКЦІЯ
# ============================================================================

def register_callback_handlers(application):
    """
    Реєстрація callback handler
    
    Використовуйте в main.py:
    ───────────────────────────
    from app.handlers.callbacks import register_callback_handlers
    
    # У функції setup_handlers():
    register_callback_handlers(app)
    """
    from telegram.ext import CallbackQueryHandler
    
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    logger.info("✅ Callback handlers registered")
