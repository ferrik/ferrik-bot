"""
🎯 Обробники команд - ЛЮДЯНА ВЕРСІЯ
Теплі привітання, персоналізація, бейджи та достижения
"""
import logging
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
    get_referral_link,
    get_weekly_challenge,
    get_user_challenge_progress,
    ACHIEVEMENTS,
)

logger = logging.getLogger(__name__)

# ============================================================================
# ПРИВІТАННЯ - ТЕПЛІ ТА ПЕРСОНАЛЬНІ
# ============================================================================

WARM_GREETINGS = {
    'first_time': """👋 **Вітаю у FerrikFoot!** 🍕

Я **Ferrik** — твій супер-помічник зі смаку 😋

Знаю, що ти голодний! Вибери, що бажаєш:

✨ **Порадити страву** за твоїм настроєм
🎁 **Подарую 50 бонусів** на перше замовлення
📋 **Показати меню** з кращих ресторанів
💬 **Розуміти** твої бажання як людина (не бот)

Чого чекаємо? Зробимо тебе щасливим! 🚀""",

    'returning_once': """Оу, ти повернувся! 👋

Сподіваюсь, попереднє замовлення було смачним? 🍽️

Що сьогодні заказуємо?""",

    'regular': """Привіт, чемпіон! 👑

Знову голодний? 😋
Я вже знаю твої уподобання!

Спробуємо щось нове чи замовимо улюблене? 🍕""",

    'VIP': """Привіт, мегафан! 🌟

Ти уже **{badge}** у FerrikFoot!
Спасибі що залишаєшся з нами 🙌

Для тебе спеціально: **{bonus} бонусів** за наступне замовлення!

Що на меню? 👨‍🍳""",
}


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start - ПЕРСОНАЛІЗОВАНИЙ"""
    user = update.effective_user
    
    logger.info(f"👤 User {user.id} (@{user.username}) started bot")
    
    # Отримуємо сесію
    session = get_user_session(user.id)
    stats = get_user_stats(user.id)
    
    # Визначаємо тип привітання
    if stats['order_count'] == 0:
        # ПЕРШИЙ РАЗДЗВІД - МАКСИМАЛЬНО ТЕПЛИЙ
        greeting = WARM_GREETINGS['first_time']
        # Даємо бонус за реєстрацію
        update_user_session(user.id, {'bonus_points': 50})
        
    elif stats['order_count'] == 1:
        greeting = WARM_GREETINGS['returning_once']
    
    elif stats['order_count'] < 10:
        greeting = WARM_GREETINGS['regular']
    
    else:
        # VIP користувач
        badge = stats['badge']
        bonus = stats['bonus_points']
        greeting = WARM_GREETINGS['VIP'].format(
            badge=badge['name'],
            bonus=bonus
        )
    
    # Клавіатура
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
    
    # Якщо новий користувач - показуємо реферальну систему
    if stats['order_count'] == 0:
        referral_link = get_referral_link(user.id)
        greeting += f"\n\n**Поділись з друзями:**\n`{referral_link}`\n_(Обидва отримаєте по 100 бонусів!)_"
        keyboard.append([
            InlineKeyboardButton("📤 Поділитись ботом", callback_data="share_bot")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        greeting,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# ПРОФІЛЬ КОРИСТУВАЧА - ПОКАЗУВАТИ БЕЙДЖІ І СТАТИСТИКУ
# ============================================================================

async def show_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати профіль користувача з статистикою"""
    query = update.callback_query
    user = query.from_user
    
    stats = get_user_stats(user.id)
    badge = stats['badge']
    
    profile_text = f"""**👤 ТЕ ПРОФІЛЬ**

**Статус:** {badge['emoji']} {badge['name']}
_(Ще {stats['next_badge_in']} замовлень до наступного рівня!)_

📊 **СТАТИСТИКА:**
• Замовлення: **{stats['order_count']}** 🍕
• Загалом витрачено: **{stats['total_spent']} грн** 💰
• Середня вартість: **{stats['avg_order_value']} грн**
• Бонус-поінти: **{stats['bonus_points']}** ⭐

🏆 **ДОСЯГНЕННЯ:** {stats['achievements_count']} розблоковано

❤️ **УЛЮБЛЕНА СТРАВА:** {stats['favorite_item'] or 'Ще не обрав'}

📅 **З НАМИ З:** {stats['created_at'][:10]}
"""

    if stats['order_count'] > 0:
        profile_text += f"\n📌 **ОСТАННЄ ЗАМОВЛЕННЯ:** {stats['last_order_date'][:10]}"
    
    keyboard = [
        [InlineKeyboardButton("🎁 Мої досягнення", callback_data="show_achievements")],
        [InlineKeyboardButton("👥 Мої рефералі", callback_data="show_referrals")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        profile_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# ЧЕЛЛЕНДЖІ - МОТИВАЦІЯ ЗАМОВЛЯТИ
# ============================================================================

async def show_challenge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати щотижневий челлендж"""
    query = update.callback_query
    user = query.from_user
    
    challenge_data = get_user_challenge_progress(user.id)
    challenge = challenge_data['challenge']
    
    challenge_text = f"""**🎯 ЧЕЛЛЕНДЖ ТИЖНЯ**

{challenge['title']}

**Завдання:** {challenge['description']}

📊 **ПРОГРЕС:**
{challenge_data['percentage']}% [{'█' * (challenge_data['percentage']//10)}{'░' * (10 - challenge_data['percentage']//10)}]

**Виконано:** {challenge_data['current_progress']}/{challenge['target']}
**Залишилось:** {challenge_data['remaining']}

🏆 **НАГРАДА:** {challenge['reward']} бонусів! ⭐

{'✅ ЧЕЛЛЕНДЖ ЗАВЕРШЕНО! 🎉' if challenge_data['completed'] else 'Ще трохи потрібно! 💪'}
"""

    keyboard = [
        [InlineKeyboardButton("📋 Меню", callback_data="show_menu")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup