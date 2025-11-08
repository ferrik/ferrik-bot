"""
🍕 MENU V2 - Гібридний інтерфейс меню
Інтеграція з існуючими сервісами (cart_manager, sheets_service)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.utils.cart_manager import (
    get_user_cart,
    add_to_cart,
    get_cart_total,
    get_cart_item_count,
    is_cart_empty
)
from app.utils.session import get_user_session, get_user_stats, update_user_session

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_sheets_service(context):
    """Отримати SheetsService з bot_data"""
    return context.bot_data.get('sheets_service')


def format_cart_summary(user_id: int) -> str:
    """Форматувати кошик для відображення"""
    cart = get_user_cart(user_id)
    
    if is_cart_empty(user_id):
        return "🛒 Кошик порожній"
    
    text = "🛒 *Твій кошик:*\n\n"
    
    for item in cart:
        name = item.get('name', 'Unknown')
        price = item.get('price', 0)
        qty = item.get('quantity', 1)
        subtotal = price * qty
        
        text += f"• {name} x{qty} — {subtotal} грн\n"
    
    total = get_cart_total(user_id)
    text += f"\n💵 *Разом: {total:.0f} грн*"
    
    return text


def get_daily_special(sheets_service):
    """Отримати страву дня з Google Sheets"""
    if not sheets_service:
        return None
    
    # Отримуємо конфігурацію спеціальної пропозиції
    special_id = sheets_service.get_config('DAILY_SPECIAL_ID')
    if not special_id:
        return None
    
    item = sheets_service.get_item_by_id(special_id)
    if not item:
        return None
    
    # Розрахувати знижку
    discount_percent = int(sheets_service.get_config('DAILY_SPECIAL_DISCOUNT') or 20)
    original_price = item['price']
    discounted_price = int(original_price * (1 - discount_percent / 100))
    
    return {
        **item,
        'original_price': original_price,
        'discounted_price': discounted_price,
        'discount': discount_percent
    }


# ============================================================================
# КОМАНДА /menu_v2 - Гібридне меню
# ============================================================================

async def menu_v2_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показати гібридне меню з категоріями
    """
    user = update.effective_user
    logger.info(f"📋 /menu_v2 від користувача {user.id}")
    
    sheets_service = get_sheets_service(context)
    
    # Breadcrumbs
    breadcrumbs = "🏠 Головна"
    
    # Заголовок
    message_text = f"{breadcrumbs}\n\n📋 *Меню FerrikBot*\n\n"
    
    # Страва дня
    special = get_daily_special(sheets_service)
    if special:
        message_text += (
            f"🔥 *Страва дня:* {special['name']}\n"
            f"~~{special['original_price']} грн~~ → *{special['discounted_price']} грн* "
            f"(-{special['discount']}%)\n\n"
        )
    
    # Отримати категорії
    if sheets_service:
        categories = sheets_service.get_categories()
    else:
        categories = ['Піца', 'Бургери', 'Мексиканська кухня', 'Салати', 'Напої', 'Десерти']
    
    # Виводимо категорії текстом (по 3 в рядку)
    for i in range(0, len(categories), 3):
        row = categories[i:i+3]
        message_text += " | ".join([f"🍴 {cat}" for cat in row]) + "\n"
    
    message_text += "\n💡 _Натисни на категорію або напиши, що хочеш!_"
    
    # Клавіатура
    keyboard = []
    
    # Страва дня
    if special:
        keyboard.append([
            InlineKeyboardButton("🔥 Страва дня", callback_data="v2_special_offer")
        ])
    
    # Категорії (по 2 в рядку)
    cat_buttons = [
        InlineKeyboardButton(
            f"🍴 {cat}",
            callback_data=f"v2_category_{cat}"
        )
        for cat in categories
    ]
    
    for i in range(0, len(cat_buttons), 2):
        keyboard.append(cat_buttons[i:i+2])
    
    # Швидкий доступ
    cart_count = get_cart_item_count(user.id)
    cart_text = f"🛒 Кошик ({cart_count})" if cart_count > 0 else "🛒 Кошик"
    
    keyboard.append([
        InlineKeyboardButton(cart_text, callback_data="v2_view_cart"),
        InlineKeyboardButton("💰 Акції", callback_data="v2_special_offer"),
        InlineKeyboardButton("📦 Історія", callback_data="v2_order_history")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Головне меню
# ============================================================================

async def main_menu_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повернутися до головного меню"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    sheets_service = get_sheets_service(context)
    
    breadcrumbs = "🏠 Головна"
    message_text = f"{breadcrumbs}\n\n📋 *Меню FerrikBot*\n\n"
    
    # Страва дня
    special = get_daily_special(sheets_service)
    if special:
        message_text += (
            f"🔥 *Страва дня:* {special['name']}\n"
            f"~~{special['original_price']} грн~~ → *{special['discounted_price']} грн*\n\n"
        )
    
    # Категорії
    if sheets_service:
        categories = sheets_service.get_categories()
    else:
        categories = ['Піца', 'Бургери', 'Мексиканська кухня', 'Салати', 'Напої']
    
    for i in range(0, len(categories), 3):
        row = categories[i:i+3]
        message_text += " | ".join([f"🍴 {cat}" for cat in row]) + "\n"
    
    message_text += "\n💡 _Обери категорію!_"
    
    # Клавіатура
    keyboard = []
    
    if special:
        keyboard.append([InlineKeyboardButton("🔥 Страва дня", callback_data="v2_special_offer")])
    
    cat_buttons = [
        InlineKeyboardButton(f"🍴 {cat}", callback_data=f"v2_category_{cat}")
        for cat in categories
    ]
    
    for i in range(0, len(cat_buttons), 2):
        keyboard.append(cat_buttons[i:i+2])
    
    cart_count = get_cart_item_count(user.id)
    cart_text = f"🛒 Кошик ({cart_count})" if cart_count > 0 else "🛒 Кошик"
    
    keyboard.append([
        InlineKeyboardButton(cart_text, callback_data="v2_view_cart"),
        InlineKeyboardButton("💰 Акції", callback_data="v2_special_offer")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Показати категорію
# ============================================================================

async def show_category_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати товари категорії"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    category_name = query.data.replace("v2_category_", "")
    
    sheets_service = get_sheets_service(context)
    
    # Зберегти поточну категорію
    context.user_data['current_category_v2'] = category_name
    
    # Breadcrumbs
    breadcrumbs = f"🏠 Головна > 🍴 {category_name}"
    
    # Отримати товари
    if sheets_service:
        menu_items = [
            item for item in sheets_service.get_menu()
            if item['category'] == category_name and item['active']
        ]
    else:
        # Mock data для тестування
        menu_items = [
            {'id': '1', 'name': 'Маргарита', 'price': 180, 'description': 'Класична піца', 'time': '25 хв'},
            {'id': '2', 'name': 'Пепероні', 'price': 220, 'description': 'З салямі', 'time': '25 хв'},
        ]
    
    if not menu_items:
        await query.edit_message_text(
            f"{breadcrumbs}\n\n❌ Товарів у категорії *{category_name}* немає.",
            parse_mode='Markdown'
        )
        return
    
    # Формуємо повідомлення
    message_text = f"{breadcrumbs}\n\n🍴 *{category_name.upper()}*\n\n"
    
    for idx, item in enumerate(menu_items[:10], 1):  # Обмежуємо 10 товарів
        name = item.get('name', 'Unknown')
        price = item.get('price', 0)
        desc = item.get('description', '')
        time_info = item.get('delivery_time', item.get('time', ''))
        
        message_text += f"{idx}. *{name}* — {price:.0f} грн\n"
        message_text += f"   _{desc}_\n"
        if time_info:
            message_text += f"   ⏱️ {time_info} хв\n"
        message_text += "\n"
    
    message_text += "━━━━━━━━━━━━━━━━━━━━\n"
    message_text += "_Натисни на товар щоб додати в кошик_"
    
    # Клавіатура з товарами
    keyboard = []
    
    for idx, item in enumerate(menu_items[:10], 1):
        keyboard.append([
            InlineKeyboardButton(
                f"{idx}. {item['name']} — {item['price']:.0f} грн",
                callback_data=f"v2_add_{item['id']}"
            )
        ])
    
    # Навігація
    keyboard.append([
        InlineKeyboardButton("◀️ Назад", callback_data="v2_main_menu"),
        InlineKeyboardButton("🛒 Кошик", callback_data="v2_view_cart")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Додати в кошик
# ============================================================================

async def add_to_cart_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Додати товар в кошик"""
    query = update.callback_query
    
    user = query.from_user
    item_id = query.data.replace("v2_add_", "")
    
    sheets_service = get_sheets_service(context)
    
    # Знайти товар
    if sheets_service:
        item = sheets_service.get_item_by_id(item_id)
    else:
        # Mock для тестування
        item = {'id': item_id, 'name': 'Тестовий товар', 'price': 100}
    
    if not item:
        await query.answer("❌ Товар не знайдено", show_alert=True)
        return
    
    # Додати в кошик через існуючий CartManager
    cart_item = {
        'id': item['id'],
        'name': item['name'],
        'price': item['price'],
        'quantity': 1
    }
    
    add_to_cart(user.id, cart_item)
    
    await query.answer(f"✅ {item['name']} додано!")
    
    logger.info(f"✅ {item['name']} додано в кошик користувача {user.id}")
    
    # Показати підсумок
    current_cat = context.user_data.get('current_category_v2', 'Категорія')
    breadcrumbs = f"🏠 Головна > 🍴 {current_cat}"
    
    cart_summary = format_cart_summary(user.id)
    
    message_text = (
        f"{breadcrumbs}\n\n"
        f"✅ *{item['name']}* додано в кошик!\n\n"
        f"{cart_summary}\n\n"
        f"Що далі?"
    )
    
    # Кнопки
    keyboard = []
    
    # Продовжити в категорії
    if current_cat:
        keyboard.append([
            InlineKeyboardButton(
                f"📋 Більше з {current_cat}",
                callback_data=f"v2_category_{current_cat}"
            )
        ])
    
    # Інші опції
    keyboard.append([
        InlineKeyboardButton("🛒 Кошик", callback_data="v2_view_cart"),
        InlineKeyboardButton("📋 Меню", callback_data="v2_main_menu")
    ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Оформити замовлення", callback_data="checkout")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Страва дня
# ============================================================================

async def special_offer_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати страву дня"""
    query = update.callback_query
    await query.answer()
    
    sheets_service = get_sheets_service(context)
    special = get_daily_special(sheets_service)
    
    if not special:
        await query.edit_message_text(
            "❌ Спеціальна пропозиція недоступна зараз 😔"
        )
        return
    
    message_text = (
        f"🔥 *СТРАВА ДНЯ* 🔥\n\n"
        f"*{special['name']}*\n"
        f"{special.get('description', 'Смачно!')}\n\n"
        f"💰 Ціна: ~~{special['original_price']} грн~~ → *{special['discounted_price']} грн*\n"
        f"🎁 Знижка {special['discount']}%!\n\n"
        f"Встигни замовити! 🔥"
    )
    
    keyboard = [
        [InlineKeyboardButton(
            f"🛒 Додати за {special['discounted_price']} грн",
            callback_data=f"v2_add_{special['id']}"
        )],
        [InlineKeyboardButton("◀️ Назад до меню", callback_data="v2_main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Переглянути кошик
# ============================================================================

async def view_cart_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати кошик"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if is_cart_empty(user.id):
        message_text = (
            "🛒 *Кошик порожній*\n\n"
            "Обери щось смачне з меню! 😋"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 Перейти до меню", callback_data="v2_main_menu")]
        ]
    else:
        cart_summary = format_cart_summary(user.id)
        
        message_text = (
            f"{cart_summary}\n\n"
            f"Готовий оформити замовлення?"
        )
        
        cart = get_user_cart(user.id)
        keyboard = []
        
        # Кнопки видалення товарів
        for item in cart:
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ Видалити {item['name']}",
                    callback_data=f"remove_from_cart_{item['id']}"  # Використовуємо існуючий handler
                )
            ])
        
        # Оформити
        keyboard.append([
            InlineKeyboardButton("✅ Оформити замовлення", callback_data="checkout")
        ])
        
        # Навігація
        keyboard.append([
            InlineKeyboardButton("📋 Продовжити покупки", callback_data="v2_main_menu")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Історія замовлень
# ============================================================================

async def order_history_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати історію замовлень"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    sheets_service = get_sheets_service(context)
    
    if not sheets_service:
        await query.edit_message_text("❌ Сервіс недоступний")
        return
    
    orders = sheets_service.get_orders(user_id=user.id)
    
    if not orders:
        message_text = (
            "📦 *Історія замовлень*\n\n"
            "У тебе поки немає замовлень.\n"
            "Зроби перше замовлення! 🎉"
        )
    else:
        message_text = "📦 *Історія замовлень:*\n\n"
        
        for order in orders[-5:]:  # Останні 5
            order_id = order.get('№ Замовлення', 'N/A')
            timestamp = order.get('Час Замовлення', '')[:10]  # Тільки дата
            total = order.get('Загальна сума', 0)
            status = order.get('Статус', 'Unknown')
            
            message_text += f"🔹 Замовлення #{order_id}\n"
            message_text += f"   📅 {timestamp}\n"
            message_text += f"   💰 {total} грн\n"
            message_text += f"   📊 {status}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("📋 До меню", callback_data="v2_main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# РЕЄСТРАЦІЯ HANDLERS
# ============================================================================

def register_menu_v2_handlers(application):
    """
    Реєструє гібридне меню v2
    
    Використовуй в main.py:
    ───────────────────────────
    from app.handlers.menu_v2 import register_menu_v2_handlers
    
    # У функції setup_handlers():
    register_menu_v2_handlers(app)
    """
    
    # Команда
    application.add_handler(CommandHandler("menu_v2", menu_v2_command))
    
    # Callback handlers (з префіксом v2_ щоб не конфліктувати з існуючими)
    application.add_handler(CallbackQueryHandler(main_menu_v2_callback, pattern="^v2_main_menu$"))
    application.add_handler(CallbackQueryHandler(show_category_v2, pattern="^v2_category_"))
    application.add_handler(CallbackQueryHandler(add_to_cart_v2, pattern="^v2_add_"))
    application.add_handler(CallbackQueryHandler(special_offer_v2, pattern="^v2_special_offer$"))
    application.add_handler(CallbackQueryHandler(view_cart_v2, pattern="^v2_view_cart$"))
    application.add_handler(CallbackQueryHandler(order_history_v2, pattern="^v2_order_history$"))
    
    logger.info("✅ Menu v2 handlers registered")
