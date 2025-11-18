"""
👋 START V2 - WOW вітання (Glovo-style)
FerrikBot v3.3 - Новий UX
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)


def get_emoji_for_category(category: str) -> str:
    """Отримати емоджі для категорії"""
    emoji_map = {
        'Піца': '🍕',
        'Бургери': '🍔',
        'Салати': '🥗',
        'Суші': '🍣',
        'Кава': '☕',
        'Десерти': '🍰',
        'Напої': '🥤',
        'Закуски': '🍟',
        'Мексиканська': '🌮',
        'Азійська': '🍜',
    }
    return emoji_map.get(category, '🍴')


async def start_v2_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Новий /start команда - WOW вітання
    
    Особливості:
    - Персоналізоване привітання з іменем
    - Динамічні категорії з Google Sheets
    - Емоційний тон (емоджі, "смачненьке")
    - Швидкий доступ до ТОП-категорій
    """
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "друже"
    
    logger.info(f"👋 /start_v2 from {first_name} (ID: {user_id})")
    
    # Персоналізоване вітання
    greeting = f"👋 Привіт, {first_name}!"
    
    # Основне повідомлення
    message = (
        f"{greeting}\n"
        f"Я FerrikBot — підкажу щось смачненьке 😋\n\n"
        f"Що хочеш сьогодні?"
    )
    
    # Отримуємо категорії (динамічно або статично)
    categories = get_top_categories(context)
    
    # Формуємо клавіатуру
    keyboard = []
    
    # ТОП-категорії (по 2 в рядку)
    for i in range(0, len(categories), 2):
        row = []
        for cat in categories[i:i+2]:
            emoji = get_emoji_for_category(cat)
            row.append(InlineKeyboardButton(
                f"{emoji} {cat}",
                callback_data=f"v2_quick_category_{cat}"
            ))
        keyboard.append(row)
    
    # Додаткові опції
    keyboard.append([
        InlineKeyboardButton("🏪 Обрати ресторан", callback_data="v2_select_restaurant")
    ])
    
    keyboard.append([
        InlineKeyboardButton("❤️ Мій профіль", callback_data="v2_my_profile"),
        InlineKeyboardButton("❓ Допомога", callback_data="v2_help")
    ])
    
    # Якщо є товари в кошику - показуємо
    cart_count = get_cart_count(user_id, context)
    if cart_count > 0:
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 Кошик ({cart_count})",
                callback_data="v2_view_cart"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup
    )


def get_top_categories(context: ContextTypes.DEFAULT_TYPE) -> list:
    """
    Отримати ТОП-категорії
    
    Логіка:
    1. Спробувати з Google Sheets (найпопулярніші)
    2. Якщо не підключено - використати дефолтні
    """
    sheets_service = context.bot_data.get('sheets_service')
    
    if sheets_service and sheets_service.is_connected():
        try:
            # Спробувати отримати з Sheets
            categories = sheets_service.get_popular_categories(limit=6)
            if categories:
                return categories
        except Exception as e:
            logger.warning(f"Could not fetch categories from Sheets: {e}")
    
    # Дефолтні категорії (якщо Sheets не підключено)
    return ['Піца', 'Бургери', 'Салати', 'Суші', 'Кава', 'Десерти']


def get_cart_count(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отримати кількість товарів у кошику"""
    try:
        from app.utils.cart_manager import get_cart_item_count
        return get_cart_item_count(user_id)
    except:
        return 0


# ============================================================================
# CALLBACK HANDLERS для нового /start
# ============================================================================

async def quick_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Швидкий вибір категорії (без вибору ресторану)
    
    Flow: Start → Категорія → Товари
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    category = query.data.replace("v2_quick_category_", "")
    
    logger.info(f"🔥 Quick category: {category} by {user.first_name}")
    
    # Зберігаємо вибрану категорію
    context.user_data['selected_category'] = category
    
    # Показуємо товари цієї категорії (з усіх ресторанів)
    await show_category_items(query, context, category)


async def show_category_items(query, context, category: str):
    """Показати товари категорії"""
    sheets_service = context.bot_data.get('sheets_service')
    
    # Отримуємо товари
    items = []
    if sheets_service and sheets_service.is_connected():
        try:
            items = sheets_service.get_menu_by_category(category)
        except Exception as e:
            logger.error(f"Error fetching items: {e}")
    
    # Якщо немає - використовуємо sample
    if not items:
        items = get_sample_items_for_category(category)
    
    if not items:
        await query.edit_message_text(
            f"😔 На жаль, товарів у категорії **{category}** зараз немає.\n\n"
            "Спробуй іншу категорію!",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")]
            ])
        )
        return
    
    # Формуємо повідомлення
    emoji = get_emoji_for_category(category)
    message = f"{emoji} **{category.upper()}**\n\n"
    
    # Показуємо перші 5 товарів
    keyboard = []
    for idx, item in enumerate(items[:5], 1):
        item_id = item.get('ID', item.get('id', 0))
        name = item.get('Страви', item.get('name', 'Товар'))
        price = item.get('Ціна', item.get('price', 0))
        restaurant = item.get('Ресторан', item.get('restaurant', ''))
        
        message += f"{idx}. **{name}** — {price} грн\n"
        if restaurant:
            message += f"   📍 {restaurant}\n"
        message += "\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"➕ {name} ({price} грн)",
                callback_data=f"v2_add_{item_id}"
            )
        ])
    
    # Навігація
    keyboard.append([
        InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start"),
        InlineKeyboardButton("🛒 Кошик", callback_data="v2_view_cart")
    ])
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def get_sample_items_for_category(category: str) -> list:
    """Sample товари для демо"""
    samples = {
        'Піца': [
            {'id': 1, 'name': 'Маргарита', 'price': 180, 'restaurant': 'FerrikPizza'},
            {'id': 2, 'name': 'Пепероні', 'price': 200, 'restaurant': 'FerrikPizza'},
        ],
        'Бургери': [
            {'id': 5, 'name': 'Класичний', 'price': 150, 'restaurant': 'BurgerHub'},
            {'id': 6, 'name': 'Чізбургер', 'price': 170, 'restaurant': 'BurgerHub'},
        ],
        'Салати': [
            {'id': 10, 'name': 'Цезар', 'price': 120, 'restaurant': 'FerrikPizza'},
            {'id': 11, 'name': 'Грецький', 'price': 110, 'restaurant': 'FerrikPizza'},
        ],
        'Напої': [
            {'id': 20, 'name': 'Coca-Cola', 'price': 40, 'restaurant': 'FerrikPizza'},
            {'id': 21, 'name': 'Sprite', 'price': 40, 'restaurant': 'FerrikPizza'},
        ],
    }
    return samples.get(category, [])


async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повернутись до головного меню"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    first_name = user.first_name or "друже"
    
    message = (
        f"👋 Привіт, {first_name}!\n"
        f"Я FerrikBot — підкажу щось смачненьке 😋\n\n"
        f"Що хочеш сьогодні?"
    )
    
    categories = get_top_categories(context)
    keyboard = []
    
    for i in range(0, len(categories), 2):
        row = []
        for cat in categories[i:i+2]:
            emoji = get_emoji_for_category(cat)
            row.append(InlineKeyboardButton(
                f"{emoji} {cat}",
                callback_data=f"v2_quick_category_{cat}"
            ))
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("🏪 Обрати ресторан", callback_data="v2_select_restaurant")
    ])
    
    keyboard.append([
        InlineKeyboardButton("❤️ Мій профіль", callback_data="v2_my_profile"),
        InlineKeyboardButton("❓ Допомога", callback_data="v2_help")
    ])
    
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


async def help_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Допомога - новий стиль"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "❓ **Як замовити:**\n\n"
        "1️⃣ Обери ресторан або категорію\n"
        "2️⃣ Додай страви в кошик\n"
        "3️⃣ Надішли телефон + адресу\n"
        "4️⃣ Отримай замовлення 🚗\n\n"
        "💡 **Корисні команди:**\n"
        "• /start - Головне меню\n"
        "• /menu - Список ресторанів\n"
        "• /cart - Твій кошик\n"
        "• /profile - Твій профіль\n\n"
        "💬 **Підтримка:** @ferrik_support"
    )
    
    keyboard = [
        [InlineKeyboardButton("◀️ На початок", callback_data="v2_back_to_start")]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================================
# РЕЄСТРАЦІЯ HANDLERS
# ============================================================================

def register_start_v2_handlers(application):
    """
    Реєструє нові start v2 handlers
    
    Використання в main.py:
    ───────────────────────────
    from app.handlers.start_v2 import register_start_v2_handlers
    
    register_start_v2_handlers(app)
    """
    from telegram.ext import CallbackQueryHandler
    
    # Команда
    application.add_handler(CommandHandler("start_v2", start_v2_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(
        quick_category_callback,
        pattern="^v2_quick_category_"
    ))
    
    application.add_handler(CallbackQueryHandler(
        back_to_start_callback,
        pattern="^v2_back_to_start$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        help_v2_callback,
        pattern="^v2_help$"
    ))
    
    logger.info("✅ Start v2 handlers registered")


__all__ = ['register_start_v2_handlers', 'start_v2_command']
