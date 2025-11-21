"""
👋 START V2 WOW - Емоційний AI Food Assistant
FerrikBot v3.3 - Revolutionary UX
"""
import logging
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

logger = logging.getLogger(__name__)


def get_time_based_greeting(first_name: str) -> str:
    """Привітання залежно від часу доби"""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        greetings = [
            f"🌅 Доброго ранку, {first_name}!\nЩо сьогодні на сніданок?",
            f"☕ Ранок, {first_name}!\nДавай підберу щось смачне?",
            f"🥐 Привіт, {first_name}!\nЗарядимося енергією?",
        ]
    elif 12 <= hour < 17:
        greetings = [
            f"🌞 Привіт, {first_name}!\nЧас обідати!",
            f"🍽️ День добрий, {first_name}!\nЩо б з'їсти сьогодні?",
            f"⚡ Хей, {first_name}!\nПідкріпимось?",
        ]
    elif 17 <= hour < 22:
        greetings = [
            f"🌆 Добрий вечір, {first_name}!\nЧас нагородити себе смачним вечором 😋",
            f"🍕 Вечір, {first_name}!\nЩось тепле та затишне?",
            f"✨ Привіт, {first_name}!\nЗаслужив на щось особливе сьогодні?",
        ]
    else:
        greetings = [
            f"🌙 Доброї ночі, {first_name}!\nПізній перекус? 🍟",
            f"🌃 Привіт, {first_name}!\nЩось легке на ніч?",
            f"😋 Хей, {first_name}!\nНічні страви вже готові!",
        ]
    
    return random.choice(greetings)


def get_mood_question() -> str:
    """Питання про настрій"""
    questions = [
        "Як настрій? Обери атмосферу:",
        "Що зараз підходить?",
        "Яка сьогодні вайб-енергія?",
        "Обери свій mood:",
    ]
    return random.choice(questions)


async def start_v2_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    WOW вітання - емоційний AI-асистент
    """
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "друже"
    
    logger.info(f"👋 /start_v2 from {first_name} (ID: {user_id})")
    
    # Персоналізоване привітання з часом доби
    greeting = get_time_based_greeting(first_name)
    
    # Основне повідомлення
    message = (
        f"{greeting}\n\n"
        f"{get_mood_question()}"
    )
    
    # MOOD-BASED меню (емоційні категорії)
    keyboard = [
        # Ряд 1: Настрій
        [
            InlineKeyboardButton("😌 Спокійний вечір", callback_data="v2_mood_calm"),
            InlineKeyboardButton("⚡ Енергія!", callback_data="v2_mood_energy")
        ],
        # Ряд 2: Ситуації
        [
            InlineKeyboardButton("🥳 Party Time", callback_data="v2_mood_party"),
            InlineKeyboardButton("❤️ Романтика", callback_data="v2_mood_romantic")
        ],
        # Ряд 3: Особливе
        [
            InlineKeyboardButton("🧊 Кіно + перекус", callback_data="v2_mood_movie"),
            InlineKeyboardButton("🔥 Хочу гостре", callback_data="v2_mood_spicy")
        ],
        # Ряд 4: AI-помічник
        [
            InlineKeyboardButton("🤖 Підбери мені", callback_data="v2_ai_suggest"),
        ],
        # Ряд 5: Класичне
        [
            InlineKeyboardButton("📋 Класичне меню", callback_data="v2_classic_menu"),
            InlineKeyboardButton("🏪 Ресторани", callback_data="v2_select_restaurant")
        ],
    ]
    
    # Якщо є товари в кошику
    cart_count = get_cart_count(user_id, context)
    if cart_count > 0:
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 Кошик ({cart_count}) - переглянути",
                callback_data="v2_view_cart"
            )
        ])
    
    # Швидке повторне замовлення
    if has_previous_orders(user_id, context):
        keyboard.append([
            InlineKeyboardButton(
                "🔁 Моє стандартне",
                callback_data="v2_repeat_last"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Відправка або редагування
    if update.message:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=reply_markup
        )


# ============================================================================
# MOOD-BASED CALLBACKS
# ============================================================================

async def mood_calm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Спокійний вечір"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "😌 **Спокійний вечір...**\n\n"
        "Тепла їжа, затишок, час для себе.\n"
        "Ось що підійде ідеально:\n\n"
        "🍜 Крем-супи та м'які страви\n"
        "🍝 Паста з ніжними соусами\n"
        "🥗 Легкі салати\n"
        "☕ Теплі напої\n\n"
        "Обери категорію або я підберу сам?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🍜 Супи", callback_data="v2_category_Супи"),
            InlineKeyboardButton("🍝 Паста", callback_data="v2_category_Паста")
        ],
        [
            InlineKeyboardButton("🥗 Салати", callback_data="v2_category_Салати"),
            InlineKeyboardButton("☕ Напої", callback_data="v2_category_Напої")
        ],
        [
            InlineKeyboardButton("🤖 Підбери мені", callback_data="v2_ai_calm_suggest")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
        ]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def mood_energy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Енергія!"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "⚡ **ЕНЕРГІЯ!**\n\n"
        "Треба зарядитись і летіти далі?\n"
        "Тоді тобі сюди:\n\n"
        "🍔 Бургери — ситно!\n"
        "🌮 Мексиканська — гостро!\n"
        "🍕 Піца — швидко!\n"
        "🥤 Energy drinks — бодро!\n\n"
        "Поїхали? 🚀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🍔 Бургери", callback_data="v2_category_Бургери"),
            InlineKeyboardButton("🌮 Мексика", callback_data="v2_category_Мексиканська")
        ],
        [
            InlineKeyboardButton("🍕 Піца", callback_data="v2_category_Піца"),
            InlineKeyboardButton("⚡ Energy", callback_data="v2_category_Energy")
        ],
        [
            InlineKeyboardButton("🤖 Зібрати сет", callback_data="v2_ai_energy_set")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
        ]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def mood_party_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Party Time"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "🥳 **PARTY TIME!**\n\n"
        "Друзі, компанія, веселощі?\n"
        "Є готові сети:\n\n"
        "🍕 Party Box #1 — 4 піци + 4 напої\n"
        "   _599 грн замість 720 грн_\n\n"
        "🍔 Party Box #2 — бургери + закуски\n"
        "   _499 грн замість 580 грн_\n\n"
        "🌮 Party Box #3 — мексиканський мікс\n"
        "   _549 грн замість 650 грн_\n\n"
        "Або зібрати свій набір?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🍕 Party Box #1", callback_data="v2_party_box_1"),
        ],
        [
            InlineKeyboardButton("🍔 Party Box #2", callback_data="v2_party_box_2"),
        ],
        [
            InlineKeyboardButton("🌮 Party Box #3", callback_data="v2_party_box_3"),
        ],
        [
            InlineKeyboardButton("🤖 Зібрати свій", callback_data="v2_ai_party_custom")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
        ]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def mood_romantic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Романтика"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "❤️ **Щось романтичне...**\n\n"
        "Особливий вечір на двох?\n"
        "Підготував ідеальні варіанти:\n\n"
        "🍝 Паста для двох + вино\n"
        "🍣 Суші сет + десерт\n"
        "🍕 Італійський вечір\n"
        "🥂 Романтична вечеря\n\n"
        "Вибирай або дозволь мені зібрати ідеальну комбінацію ✨"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🍝 Паста для двох", callback_data="v2_romantic_pasta"),
        ],
        [
            InlineKeyboardButton("🍣 Суші сет", callback_data="v2_romantic_sushi"),
        ],
        [
            InlineKeyboardButton("🍕 Італійський", callback_data="v2_romantic_italian"),
        ],
        [
            InlineKeyboardButton("✨ Підбери мені", callback_data="v2_ai_romantic")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
        ]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def mood_movie_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кіно + перекус"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "🧊 **Кіно + перекус**\n\n"
        "Фільм починається за годину?\n"
        "Швидкі та смачні варіанти:\n\n"
        "🍿 Попкорн сети\n"
        "🍕 Піца + напої\n"
        "🍔 Бургери + фрі\n"
        "🌮 Начос + соуси\n\n"
        "Що замовляємо?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🍿 Попкорн сет", callback_data="v2_movie_popcorn"),
            InlineKeyboardButton("🍕 Піца сет", callback_data="v2_movie_pizza")
        ],
        [
            InlineKeyboardButton("🍔 Бургер сет", callback_data="v2_movie_burger"),
            InlineKeyboardButton("🌮 Начос", callback_data="v2_movie_nachos")
        ],
        [
            InlineKeyboardButton("🤖 Підбери під фільм", callback_data="v2_ai_movie")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
        ]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def mood_spicy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Хочу гостре"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "🔥 **ГОСТРЕ!**\n\n"
        "Любиш погарячіше?\n"
        "Страви для справжніх любителів:\n\n"
        "🌶️ Гостра піца\n"
        "🔥 Спайсі бургери\n"
        "🌮 Мексиканське пекло\n"
        "🍜 Гострі супи\n\n"
        "⚠️ Попередження: дійсно гостро! 🔥"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🌶️ Гостра піца", callback_data="v2_spicy_pizza"),
            InlineKeyboardButton("🔥 Spicy burger", callback_data="v2_spicy_burger")
        ],
        [
            InlineKeyboardButton("🌮 Мексика 🔥", callback_data="v2_spicy_mexican"),
            InlineKeyboardButton("🍜 Гострі супи", callback_data="v2_spicy_soup")
        ],
        [
            InlineKeyboardButton("🔥 Найгостріше", callback_data="v2_spicy_extreme")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
        ]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================================
# AI SUGGEST
# ============================================================================

async def ai_suggest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI підбирає меню"""
    query = update.callback_query
    await query.answer("🤖 Аналізую твої вподобання...")
    
    user_id = query.from_user.id
    
    message = (
        "🤖 **AI Food Assistant**\n\n"
        "Підкажи мені трохи більше, і я підберу ідеальне меню:\n\n"
        "Який у тебе бюджет?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💸 До 150 грн", callback_data="v2_ai_budget_150"),
            InlineKeyboardButton("💰 150-300 грн", callback_data="v2_ai_budget_300")
        ],
        [
            InlineKeyboardButton("💎 300-500 грн", callback_data="v2_ai_budget_500"),
            InlineKeyboardButton("👑 Без обмежень", callback_data="v2_ai_budget_unlimited")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
        ]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================================
# ШВИДКЕ ПОВТОРНЕ ЗАМОВЛЕННЯ
# ============================================================================

async def repeat_last_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторити останнє замовлення"""
    query = update.callback_query
    await query.answer("🔁 Завантажую твоє стандартне...")
    
    # TODO: Завантажити останнє замовлення з історії
    
    message = (
        "🔁 **Твоє стандартне замовлення:**\n\n"
        "🍕 Маргарита\n"
        "🥤 Cola 0.5л\n\n"
        "💰 Разом: 220 грн\n\n"
        "Замовити знову?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Так, замовити!", callback_data="v2_repeat_confirm")
        ],
        [
            InlineKeyboardButton("✏️ Змінити щось", callback_data="v2_repeat_edit")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
        ]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================================
# HELPERS
# ============================================================================

def get_cart_count(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отримати кількість товарів у кошику"""
    try:
        from app.utils.cart_manager import get_cart_item_count
        return get_cart_item_count(user_id)
    except:
        return 0


def has_previous_orders(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Перевірити чи є попередні замовлення"""
    # TODO: Перевірити в базі
    return True  # Завжди показуємо для демо


async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повернутись до start"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    first_name = user.first_name or "друже"
    
    greeting = get_time_based_greeting(first_name)
    message = f"{greeting}\n\n{get_mood_question()}"
    
    # Повторити клавіатуру з start
    keyboard = [
        [
            InlineKeyboardButton("😌 Спокійний вечір", callback_data="v2_mood_calm"),
            InlineKeyboardButton("⚡ Енергія!", callback_data="v2_mood_energy")
        ],
        [
            InlineKeyboardButton("🥳 Party Time", callback_data="v2_mood_party"),
            InlineKeyboardButton("❤️ Романтика", callback_data="v2_mood_romantic")
        ],
        [
            InlineKeyboardButton("🧊 Кіно + перекус", callback_data="v2_mood_movie"),
            InlineKeyboardButton("🔥 Хочу гостре", callback_data="v2_mood_spicy")
        ],
        [
            InlineKeyboardButton("🤖 Підбери мені", callback_data="v2_ai_suggest"),
        ],
        [
            InlineKeyboardButton("📋 Класичне меню", callback_data="v2_classic_menu"),
            InlineKeyboardButton("🏪 Ресторани", callback_data="v2_select_restaurant")
        ],
    ]
    
    cart_count = get_cart_count(user.id, context)
    if cart_count > 0:
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 Кошик ({cart_count})",
                callback_data="v2_view_cart"
            )
        ])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================================
# РЕЄСТРАЦІЯ
# ============================================================================

def register_start_v2_wow_handlers(application):
    """Реєструє WOW handlers"""
    from telegram.ext import CallbackQueryHandler
    
    application.add_handler(CommandHandler("start_v2", start_v2_command))
    
    # Mood callbacks
    application.add_handler(CallbackQueryHandler(mood_calm_callback, pattern="^v2_mood_calm$"))
    application.add_handler(CallbackQueryHandler(mood_energy_callback, pattern="^v2_mood_energy$"))
    application.add_handler(CallbackQueryHandler(mood_party_callback, pattern="^v2_mood_party$"))
    application.add_handler(CallbackQueryHandler(mood_romantic_callback, pattern="^v2_mood_romantic$"))
    application.add_handler(CallbackQueryHandler(mood_movie_callback, pattern="^v2_mood_movie$"))
    application.add_handler(CallbackQueryHandler(mood_spicy_callback, pattern="^v2_mood_spicy$"))
    
    # AI callbacks
    application.add_handler(CallbackQueryHandler(ai_suggest_callback, pattern="^v2_ai_suggest$"))
    
    # Repeat callbacks
    application.add_handler(CallbackQueryHandler(repeat_last_callback, pattern="^v2_repeat_last$"))
    
    # Back
    application.add_handler(CallbackQueryHandler(back_to_start_callback, pattern="^v2_back_to_start$"))
    
    logger.info("✅ Start v2 WOW handlers registered")


__all__ = ['register_start_v2_wow_handlers']
