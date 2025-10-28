"""
🔘 Обробник callback queries (inline кнопки)
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime

from app.utils.validators import format_order_summary
from app.utils.session import (
    get_user_session,
    update_user_session,
    get_user_cart,
    clear_user_cart
)

logger = logging.getLogger(__name__)


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Головний обробник callback queries
    """
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user = query.from_user
    
    logger.info(f"👤 User {user.id} callback: {callback_data}")
    
    # Маршрутизація callbacks
    if callback_data == "show_menu":
        await show_menu_callback(update, context)
    
    elif callback_data == "show_cart":
        await show_cart_callback(update, context)
    
    elif callback_data == "show_help":
        await show_help_callback(update, context)
    
    elif callback_data == "clear_cart":
        await clear_cart_callback(update, context)
    
    elif callback_data == "checkout":
        await checkout_callback(update, context)
    
    elif callback_data == "confirm_order":
        await confirm_order_callback(update, context)
    
    elif callback_data == "cancel_order":
        await cancel_order_callback(update, context)
    
    else:
        await query.edit_message_text("❓ Невідома команда")


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
        
        # Формуємо меню
        message_parts = ["📋 **МЕНЮ**\n"]
        
        categories = {}
        for item in menu_items:
            category = item.get('category', 'Інше')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        for category, items in categories.items():
            message_parts.append(f"\n**{category}**")
            for item in items[:10]:  # Обмежуємо кількість
                name = item.get('name', 'Unknown')
                price = item.get('price', 0)
                message_parts.append(f"🔹 {name} — {price} грн")
        
        message_parts.append("\n💬 Напишіть, що хочете замовити!")
        
        menu_text = "\n".join(message_parts)
        
        await query.edit_message_text(
            menu_text,
            parse_mode='Markdown'
        )
    
    except Exception as e:
        logger.error(f"❌ Error in show_menu: {e}")
        await query.edit_message_text("❌ Помилка при завантаженні меню")


async def show_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати кошик"""
    query = update.callback_query
    user = query.from_user
    
    cart = get_user_cart(user.id)
    
    if not cart or len(cart) == 0:
        keyboard = [[
            InlineKeyboardButton("📋 Переглянути меню", callback_data="show_menu")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🛒 Ваш кошик порожній.\n\n"
            "Додайте товари з меню!",
            reply_markup=reply_markup
        )
        return
    
    # Формуємо повідомлення
    order_data = {'items': cart}
    cart_text = format_order_summary(order_data)
    
    # Клавіатура
    keyboard = [
        [
            InlineKeyboardButton("🗑 Очистити", callback_data="clear_cart"),
            InlineKeyboardButton("✅ Оформити", callback_data="checkout")
        ],
        [
            InlineKeyboardButton("📋 Додати ще", callback_data="show_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        cart_text,
        reply_markup=reply_markup
    )


async def show_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати допомогу"""
    query = update.callback_query
    
    help_text = (
        "📖 **ДОПОМОГА**\n\n"
        "**Доступні команди:**\n"
        "🔹 /start — Почати роботу\n"
        "🔹 /menu — Переглянути меню\n"
        "🔹 /cart — Переглянути кошик\n"
        "🔹 /order — Оформити замовлення\n"
        "🔹 /help — Довідка\n\n"
        "💡 Просто напишіть, що хочете замовити!"
    )
    
    keyboard = [[
        InlineKeyboardButton("📋 Меню", callback_data="show_menu"),
        InlineKeyboardButton("🛒 Кошик", callback_data="show_cart")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def clear_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистити кошик"""
    query = update.callback_query
    user = query.from_user
    
    clear_user_cart(user.id)
    
    keyboard = [[
        InlineKeyboardButton("📋 Переглянути меню", callback_data="show_menu")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🗑 Кошик очищено!\n\n"
        "Додайте нові товари з меню.",
        reply_markup=reply_markup
    )


async def checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Почати оформлення замовлення"""
    query = update.callback_query
    user = query.from_user
    
    cart = get_user_cart(user.id)
    
    if not cart or len(cart) == 0:
        await query.edit_message_text("🛒 Кошик порожній!")
        return
    
    # Показуємо підсумок
    order_data = {'items': cart}
    summary = format_order_summary(order_data)
    
    # Переходимо до введення контактів
    await query.edit_message_text(
        f"{summary}\n\n"
        "📱 Введіть ваш номер телефону:\n"
        "(формат: +380501234567 або 0501234567)"
    )
    
    # Зберігаємо стан
    update_user_session(user.id, {
        'state': 'awaiting_phone',
        'order_data': order_data
    })


async def confirm_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Підтвердження та створення замовлення"""
    query = update.callback_query
    user = query.from_user
    
    # Отримуємо дані замовлення
    session = get_user_session(user.id)
    order_data = session.get('order_data', {})
    
    sheets_service = context.bot_data.get('sheets_service')
    
    if not sheets_service:
        await query.edit_message_text("❌ Сервіс недоступний")
        return
    
    try:
        # Додаємо метадані
        order_data['user_id'] = user.id
        order_data['username'] = user.username or 'N/A'
        order_data['timestamp'] = datetime.now().isoformat()
        order_data['status'] = 'Новий'
        
        # Зберігаємо в Google Sheets
        order_id = sheets_service.save_order(order_data)
        
        # Очищуємо кошик та сесію
        clear_user_cart(user.id)
        update_user_session(user.id, {'state': 'idle'})
        
        # Повідомлення про успіх
        success_text = (
            "✅ **ЗАМОВЛЕННЯ ПРИЙНЯТО!**\n\n"
            f"📝 Номер замовлення: #{order_id}\n\n"
            "Ми зв'яжемося з вами найближчим часом!\n\n"
            "📞 Контакти:\n"
            f"Телефон: {order_data.get('phone', 'N/A')}\n"
            f"Адреса: {order_data.get('address', 'N/A')}\n\n"
            "Дякуємо за замовлення! 🎉"
        )
        
        keyboard = [[
            InlineKeyboardButton("📋 Нове замовлення", callback_data="show_menu")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"✅ Order #{order_id} created by user {user.id}")
        
        # Сповіщення адмінів (якщо налаштовано)
        telegram_config = context.bot_data.get('telegram_config')
        if telegram_config and telegram_config.admin_ids:
            admin_notification = (
                f"🔔 **НОВЕ ЗАМОВЛЕННЯ #{order_id}**\n\n"
                f"👤 Користувач: @{user.username or user.id}\n"
                f"{format_order_summary(order_data)}"
            )
            
            for admin_id in telegram_config.admin_ids:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_notification,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"❌ Failed to notify admin {admin_id}: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error creating order: {e}")
        await query.edit_message_text(
            "❌ Помилка при створенні замовлення.\n\n"
            "Спробуйте пізніше або зв'яжіться з нами."
        )


async def cancel_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скасування замовлення"""
    query = update.callback_query
    user = query.from_user
    
    # Очищуємо стан
    update_user_session(user.id, {'state': 'idle'})
    
    keyboard = [[
        InlineKeyboardButton("📋 Меню", callback_data="show_menu"),
        InlineKeyboardButton("🛒 Кошик", callback_data="show_cart")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "❌ Замовлення скасовано.\n\n"
        "Що бажаєте зробити?",
        reply_markup=reply_markup
    )
