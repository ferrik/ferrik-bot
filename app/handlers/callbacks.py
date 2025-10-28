"""
🔘 Обробник callback queries - ОНОВЛЕНА ВЕРСІЯ
Нові фічи: Surprise Me, Profile, Achievements, Challenges
"""
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime

from app.utils.validators import format_order_summary, calculate_total_price
from app.utils.session import (
    get_user_cart,
    clear_user_cart,
    get_user_session,
    update_user_session,
    get_user_stats,
    get_user_badge,
    add_to_cart,
    get_referral_link,
    get_weekly_challenge,
    get_user_challenge_progress,
    register_order,
    ACHIEVEMENTS,
)

logger = logging.getLogger(__name__)

# ============================================================================
# SURPRISE ME - ПОДАРОК ВІД ФЕРИКА
# ============================================================================

async def surprise_me_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI генерує комбо з автоматичною знижкою"""
    query = update.callback_query
    user = query.from_user
    sheets_service = context.bot_data.get('sheets_service')
    
    if not sheets_service:
        await query.edit_message_text("❌ Сервіс недоступний")
        return
    
    try:
        # Отримуємо меню
        menu = sheets_service.get_menu()
        if not menu or len(menu) < 3:
            await query.edit_message_text("😔 Меню занадто мале для сюрпризу!")
            return
        
        # Селеціонуємо 2-3 товари випадково
        surprise_items = random.sample(menu, min(3, len(menu)))
        
        # Даємо знижку 15-20%
        discount = random.randint(15, 20)
        
        # Формуємо сюрприз
        message = f"""🎁 **СЮРПРИЗ ВІД ФЕРИКА!** 🎁

{random.choice([
    "Я для тебе щось спеціальне вибрав! 😋",
    "Вірю, тобі сподобається! 🔥",
    "Це - мій особистий вибір! ⭐",
    "Спеціально для тебе! 💝",
])}

**КОМБО СЮРПРИЗ:**"""
        
        items_for_cart = []
        for item in surprise_items:
            message += f"\n🔹 {item['name']} — {item['price']} грн"
            items_for_cart.append({
                'id': item['id'],
                'name': item['name'],
                'price': item['price'],
                'quantity': 1
            })
        
        total = calculate_total_price(items_for_cart)
        discounted = total * (1 - discount / 100)
        saved = total - discounted
        
        message += f"\n\n💰 **Звичайно:** {total} грн"
        message += f"\n🎯 **Зі знижкою {discount}%:** {discounted:.0f} грн"
        message += f"\n💚 **Ви заощадили:** {saved:.0f} грн"
        message += f"\n\n✨ Це ж фана́стично! 🚀"
        
        keyboard = [
            [InlineKeyboardButton("✅ Беру сюрприз!", callback_data="accept_surprise")],
            [InlineKeyboardButton("❌ Не той сюрприз", callback_data="show_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Зберігаємо сюрприз в сесію
        update_user_session(user.id, {
            'surprise_items': items_for_cart,
            'surprise_discount': discount
        })
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    except Exception as e:
        logger.error(f"❌ Error in surprise_me: {e}")
        await query.edit_message_text("❌ Помилка! Спробуйте пізніше")


async def accept_surprise_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Прийняти сюрприз і додати в кошик"""
    query = update.callback_query
    user = query.from_user
    
    session = get_user_session(user.id)
    surprise_items = session.get('surprise_items', [])
    surprise_discount = session.get('surprise_discount', 0)
    
    # Додаємо в кошик
    for item in surprise_items:
        add_to_cart(user.id, item)
    
    # Застосовуємо знижку
    cart = get_user_cart(user.id)
    total = calculate_total_price(cart)
    
    message = f"""🎉 **СЮРПРИЗ АКТИВИРОВАН!** 🎉

✅ Всі {len(surprise_items)} товари додані до кошика!
💚 Знижка {surprise_discount}% автоматично застосована!

💰 **Сума:** {total} грн
🎯 **Зі знижкою:** {total * (1 - surprise_discount/100):.0f} грн

Готовий оформити замовлення? 🚀"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Оформити!", callback_data="checkout")],
        [InlineKeyboardButton("📋 Ще щось додати", callback_data="show_menu")],
        [InlineKeyboardButton("🛒 Перегляд кошика", callback_data="show_cart")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# ACHIEVEMENTS - ПОКАЗАТИ ДОСЯГНЕННЯ
# ============================================================================

async def show_achievements_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати досягнення користувача"""
    query = update.callback_query
    user = query.from_user
    
    stats = get_user_stats(user.id)
    achievements = stats['achievements_count']
    
    message = "🏆 **ТВОЇ ДОСЯГНЕННЯ**\n\n"
    
    if achievements == 0:
        message += "Поки немає досягнень! 😔\n\n"
        message += "Але ти можеш розпочати прямо зараз! 💪\n"
        message += "• Зроби перше замовлення\n"
        message += "• Залиши відгук\n"
        message += "• Привіди друга\n"
    else:
        session = get_user_session(user.id)
        achieved = session.get('achievements', [])
        
        for achievement_key in achieved:
            if achievement_key in ACHIEVEMENTS:
                ach = ACHIEVEMENTS[achievement_key]
                message += f"{ach['emoji']} **{ach['title']}**\n"
                message += f"   Бонус: +{ach['bonus']} ⭐\n\n"
    
    message += "\n📌 **НАСТУПНІ達СЯГНЕННЯ:**\n"
    
    # Показуємо можливі досягнення
    upcoming = {
        'first_order': '🎯 Перше замовлення',
        'order_5': '👨‍🍳 П\'ять замовлень',
        'order_10': '🏆 Десять замовлень',
        'refer_friend': '👥 Привести друга',
    }
    
    for key, desc in upcoming.items():
        message += f"• {desc}\n"
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад до профілю", callback_data="show_profile")],
        [InlineKeyboardButton("📋 Меню", callback_data="show_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# REFERRALS - РЕФЕРАЛЬНА СИСТЕМА
# ============================================================================

async def show_referrals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати реферальну систему"""
    query = update.callback_query
    user = query.from_user
    
    session = get_user_session(user.id)
    referred_users = session.get('referred_users', [])
    referral_link = get_referral_link(user.id)
    
    message = f"""👥 **РЕФЕРАЛЬНА СИСТЕМА**

🔗 **ТІ ПОСИЛАННЯ:**
`{referral_link}`

_(Натисни щоб скопіювати)_

💚 **ПРЕМІА:**
• Ти отримуєш **100 бонусів** за кожного друга
• Твій друг отримує **100 бонусів** на першому замовленні
• Обидва вигрували! 🎉

👥 **ПРИВЕДЕНО ДРУЗІВ:** {len(referred_users)}

💰 **ЗАГАЛЬНИЙ БОНУС:** {len(referred_users) * 100} ⭐

📊 **ТОП РЕФЕРЕАЛИ:**
1. Зробити своїм друзям подарунок! 🎁
2. Готово! Чекай на їхні замовлення! ⏰

✨ **ОДИН УМОВ:**
Друг повинен замовити щоб обидва отримали бонус! 🎯"""
    
    keyboard = [
        [InlineKeyboardButton("📤 Поділитись в Telegram", callback_data="share_referral")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="show_profile")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# BACK NAVIGATION
# ============================================================================

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повернутися в головне меню"""
    query = update.callback_query
    
    keyboard = [
        [
            InlineKeyboardButton("🎁 Сюрприз!", callback_data="surprise_me"),
            InlineKeyboardButton("📋 Меню", callback_data="show_menu"),
        ],
        [
            InlineKeyboardButton("🛒 Кошик", callback_data="show_cart"),
            InlineKeyboardButton("⭐ Мій профіль", callback_data="show_profile"),
        ],
        [
            InlineKeyboardButton("🎯 Челлендж", callback_data="show_challenge"),
            InlineKeyboardButton("ℹ️ Допомога", callback_data="show_help"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏠 **ГОЛОВНЕ МЕНЮ**\n\n"
        "Вибери, що бажаєш зробити! 😊",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# ЗАГАЛЬНИЙ МАРШРУТИЗАТОР
# ============================================================================

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Головний обробник callback queries"""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error answering query: {e}")
        return
    
    user = query.from_user
    callback_data = query.data
    
    logger.info(f"👤 User {user.id} callback: {callback_data}")
    
    # ===== Маршрутизація callbacks =====
    
    # Меню та навігація
    if callback_data == "show_menu":
        await show_menu_callback(update, context)
    
    elif callback_data == "show_cart":
        await show_cart_callback(update, context)
    
    elif callback_data == "show_help":
        await show_help_callback(update, context)
    
    elif callback_data == "show_profile":
        await show_profile_callback(update, context)
    
    elif callback_data == "show_challenge":
        await show_challenge_callback(update, context)
    
    # Сюрприз
    elif callback_data == "surprise_me":
        await surprise_me_callback(update, context)
    
    elif callback_data == "accept_surprise":
        await accept_surprise_callback(update, context)
    
    # Кошик
    elif callback_data == "clear_cart":
        await clear_cart_callback(update, context)
    
    elif callback_data == "checkout":
        await checkout_callback(update, context)
    
    elif callback_data == "confirm_order":
        await confirm_order_callback(update, context)
    
    elif callback_data == "cancel_order":
        await cancel_order_callback(update, context)
    
    # Досягнення та рефералі
    elif callback_data == "show_achievements":
        await show_achievements_callback(update, context)
    
    elif callback_data == "show_referrals":
        await show_referrals_callback(update, context)
    
    # Назад
    elif callback_data == "back_to_menu":
        await back_to_menu_callback(update, context)
    
    else:
        await query.edit_message_text(f"❓ Невідома команда: {callback_data}")


# ============================================================================
# ДОПОМІЖНІ ФУНКЦІЇ (СТАРІ)
# ============================================================================

async def show_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати меню"""
    query = update.callback_query
    sheets_service = context.bot_data.get('sheets_service')
    
    if not sheets_service:
        await query.edit_message_text("❌ Сервіс недоступний")
        return
    
    try:
        menu_items = sheets_service.get_menu()
        
        if not menu_items:
            await query.edit_message_text("😔 Меню наразі порожнє")
            return
        
        message_parts = ["📋 **МЕНЮ**\n"]
        categories = {}
        
        for item in menu_items:
            cat = item.get('category', 'Інше')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        for category, items in list(categories.items())[:3]:  # Обмежуємо для preview
            message_parts.append(f"\n**{category}**")
            for item in items[:3]:
                name = item.get('name', '')
                price = item.get('price', 0)
                rating = item.get('rating', 0)
                stars = "⭐" * int(rating)
                message_parts.append(f"🔹 {name} — {price} грн {stars}")
        
        message_parts.append("\n💬 Напишіть назву страви щоб додати!")
        
        keyboard = [
            [InlineKeyboardButton("🛒 Мій кошик", callback_data="show_cart")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "\n".join(message_parts),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    except Exception as e:
        logger.error(f"❌ Error in show_menu: {e}")
        await query.edit_message_text("❌ Помилка")


async def show_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати кошик"""
    query = update.callback_query
    user = query.from_user
    
    cart = get_user_cart(user.id)
    
    if not cart or len(cart) == 0:
        keyboard = [[InlineKeyboardButton("📋 Меню", callback_data="show_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🛒 Ваш кошик порожній!\n\n"
            "Додайте щось смачне! 🍕",
            reply_markup=reply_markup
        )
        return
    
    order_data = {'items': cart}
    summary = format_order_summary(order_data)
    
    keyboard = [
        [
            InlineKeyboardButton("🎁 Промокод", callback_data="enter_promocode"),
            InlineKeyboardButton("✅ Оформити", callback_data="checkout")