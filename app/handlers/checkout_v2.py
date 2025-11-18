"""
🧾 CHECKOUT V2 - Оформлення замовлення з Request Contact
FerrikBot v3.3 - Новий UX
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CallbackQueryHandler

from app.utils.cart_manager import get_user_cart, get_cart_total, clear_user_cart
from app.utils.warm_greetings import update_user_stats

logger = logging.getLogger(__name__)


async def checkout_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Початок оформлення замовлення (v2)
    
    Особливості:
    - Request Contact кнопка для телефону
    - Збереження даних між замовленнями
    - Покращений UX підтвердження
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    
    logger.info(f"🧾 Checkout v2 initiated by {user.first_name}")
    
    # Перевіряємо кошик
    cart = get_user_cart(user_id)
    
    if not cart:
        await query.answer("❌ Кошик порожній!", show_alert=True)
        return
    
    # Зберігаємо snapshot кошика
    context.user_data['cart_snapshot'] = cart.copy()
    
    # Перевіряємо чи є збережені дані
    saved_phone = context.user_data.get('phone')
    saved_address = context.user_data.get('address')
    
    if saved_phone and saved_address:
        # Якщо дані є - одразу показуємо підтвердження
        await show_order_confirmation_v2(query, context, saved_phone, saved_address)
    else:
        # Запитуємо телефон
        await request_phone_v2(query, context)


async def request_phone_v2(query, context):
    """
    Запит телефону з Request Contact кнопкою
    
    UX:
    - Кнопка "Надіслати телефон" (швидко)
    - Або можна ввести вручну
    """
    user_id = query.from_user.id
    
    # Підсумок замовлення
    cart = context.user_data.get('cart_snapshot', [])
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    delivery = 0 if total >= 300 else 50
    final_total = total + delivery
    
    message = (
        "📱 **Крок 1 з 2: Телефон**\n\n"
        f"💰 Сума замовлення: {final_total} грн\n\n"
        "Надішли номер телефону для зв'язку:\n"
        "_(або натисни кнопку нижче)_"
    )
    
    # Inline кнопки
    inline_keyboard = [
        [InlineKeyboardButton("❌ Скасувати", callback_data="v2_cancel_checkout")]
    ]
    
    # Відправляємо повідомлення з inline кнопками
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(inline_keyboard)
    )
    
    # Відправляємо Request Contact кнопку окремим повідомленням
    contact_keyboard = [
        [KeyboardButton("📲 Надіслати телефон", request_contact=True)],
        [KeyboardButton("❌ Скасувати")]
    ]
    
    await query.message.reply_text(
        "👇 _Натисни кнопку або напиши номер вручну_",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(
            contact_keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    
    # Встановлюємо стан
    context.user_data['awaiting_phone_v2'] = True


async def request_address_v2(message, context):
    """Запит адреси доставки"""
    phone = context.user_data.get('phone')
    
    text = (
        "📍 **Крок 2 з 2: Адреса**\n\n"
        f"✅ Телефон: {phone}\n\n"
        "Куди доставити?\n"
        "Напиши адресу у форматі:\n"
        "_вул. Шевченка 12, кв. 45_"
    )
    
    keyboard = [
        [InlineKeyboardButton("❌ Скасувати", callback_data="v2_cancel_checkout")]
    ]
    
    await message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Встановлюємо стан
    context.user_data['awaiting_address_v2'] = True
    context.user_data['awaiting_phone_v2'] = False


async def show_order_confirmation_v2(query, context, phone: str, address: str):
    """
    Показати екран підтвердження замовлення (v2)
    
    UX покращення:
    - Деталізований підсумок
    - Великий заголовок "Підтвердити?"
    - Зрозумілі кнопки
    """
    user_id = query.from_user.id
    cart = context.user_data.get('cart_snapshot', [])
    
    if not cart:
        await query.answer("❌ Кошик порожній!", show_alert=True)
        return
    
    # Розрахунки
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    delivery = 0 if total >= 300 else 50
    final_total = total + delivery
    
    # Визначаємо ресторан
    restaurant = cart[0].get('restaurant', 'Ресторан') if cart else 'Ресторан'
    
    # Генеруємо номер замовлення
    order_id = user_id % 10000
    
    # Формуємо повідомлення
    message = (
        f"🧾 **Замовлення №{order_id}**\n\n"
        f"🍴 Ресторан: **{restaurant}**\n"
        f"📦 Склад:\n"
    )
    
    # Список товарів
    for item in cart:
        name = item.get('name', 'Товар')
        qty = item.get('quantity', 1)
        message += f"— {name} ×{qty}\n"
    
    message += "\n"
    
    # Підсумок
    message += f"💰 Сума: **{total} грн**\n"
    message += f"🚚 Доставка: **{delivery} грн**\n"
    
    if delivery == 0:
        message += "_🎉 Безкоштовна!_\n"
    
    message += f"📦 **Разом: {final_total} грн**\n\n"
    
    # Деталі
    message += f"⏱ Доставка: 25–35 хв\n"
    message += f"📞 Телефон: {phone}\n"
    message += f"📍 Адреса: {address}\n\n"
    
    message += "**Підтвердити замовлення?**"
    
    # Кнопки
    keyboard = [
        [InlineKeyboardButton("✅ ПІДТВЕРДИТИ", callback_data="v2_confirm_order")],
        [
            InlineKeyboardButton("✏️ Змінити телефон", callback_data="v2_change_phone"),
            InlineKeyboardButton("✏️ Змінити адресу", callback_data="v2_change_address")
        ],
        [InlineKeyboardButton("❌ Скасувати", callback_data="v2_cancel_checkout")]
    ]
    
    # Видаляємо keyboard якщо він був
    try:
        await query.message.reply_text(
            "Оформлення...",
            reply_markup=ReplyKeyboardRemove()
        )
    except:
        pass
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def confirm_order_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Підтвердження замовлення (v2)
    
    Дії:
    1. Зберегти в Google Sheets
    2. Оновити статистику користувача
    3. Очистити кошик
    4. Показати success екран
    """
    query = update.callback_query
    await query.answer("⏳ Обробка замовлення...")
    
    user = query.from_user
    user_id = user.id
    
    # Отримуємо дані
    cart = context.user_data.get('cart_snapshot', [])
    phone = context.user_data.get('phone', 'Не вказано')
    address = context.user_data.get('address', 'Не вказано')
    
    # Розрахунки
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    delivery = 0 if total >= 300 else 50
    final_total = total + delivery
    
    # Зберігаємо в Sheets
    order_saved = False
    order_id = user_id % 10000
    
    sheets_service = context.bot_data.get('sheets_service')
    if sheets_service and sheets_service.is_connected():
        try:
            order_data = {
                'user_id': user_id,
                'username': user.username or user.first_name,
                'items': cart,
                'total': total,
                'address': address,
                'phone': phone,
                'payment_method': 'Готівка',
                'delivery_cost': delivery,
                'delivery_type': 'Доставка'
            }
            
            order_saved = sheets_service.add_order(order_data)
            
        except Exception as e:
            logger.error(f"❌ Error saving order: {e}")
    
    # Оновлюємо статистику
    try:
        update_user_stats(user_id, final_total)
    except Exception as e:
        logger.error(f"Error updating stats: {e}")
    
    # Очищуємо кошик
    clear_user_cart(user_id)
    
    # Очищуємо тільки checkout дані
    context.user_data.pop('cart_snapshot', None)
    context.user_data.pop('awaiting_phone_v2', None)
    context.user_data.pop('awaiting_address_v2', None)
    # phone та address зберігаємо!
    
    # Success повідомлення
    restaurant = cart[0].get('restaurant', 'Ресторан') if cart else 'Ресторан'
    
    message = (
        "🎉 **ЗАМОВЛЕННЯ ПРИЙНЯТО!**\n\n"
        f"📦 Номер замовлення: **#{order_id}**\n\n"
        "Готуємо та передамо кур'єру протягом 10 хв.\n\n"
        f"⏱ Очікуваний час: **25–35 хв**\n"
        f"💳 До оплати: **{final_total} грн** _(готівка)_\n\n"
    )
    
    if order_saved:
        message += "✅ Замовлення передано в ресторан\n\n"
    
    message += "_Статус можна перевірити: /order_v2_"
    
    # Кнопки
    keyboard = [
        [InlineKeyboardButton("🍕 Замовити ще", callback_data="v2_back_to_start")],
        [InlineKeyboardButton("📊 Мій профіль", callback_data="v2_my_profile")],
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    logger.info(f"✅ Order confirmed by user {user_id}")


async def cancel_checkout_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скасування оформлення"""
    query = update.callback_query
    await query.answer("❌ Оформлення скасовано")
    
    # Очищуємо стани
    context.user_data.pop('cart_snapshot', None)
    context.user_data.pop('awaiting_phone_v2', None)
    context.user_data.pop('awaiting_address_v2', None)
    
    message = (
        "❌ **Оформлення скасовано**\n\n"
        "Товари залишились у кошику.\n"
        "Можеш продовжити покупки або оформити замовлення пізніше."
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Повернутись до кошика", callback_data="v2_view_cart")],
        [InlineKeyboardButton("🍕 Продовжити покупки", callback_data="v2_back_to_start")],
    ]
    
    # Видаляємо keyboard
    try:
        await query.message.reply_text(
            "Скасовано",
            reply_markup=ReplyKeyboardRemove()
        )
    except:
        pass
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def change_phone_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Зміна телефону під час оформлення"""
    query = update.callback_query
    await query.answer()
    
    await request_phone_v2(query, context)


async def change_address_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Зміна адреси під час оформлення"""
    query = update.callback_query
    await query.answer()
    
    message = (
        "📍 **Зміна адреси**\n\n"
        "Введи нову адресу:\n"
        "_вул. Шевченка 12, кв. 45_"
    )
    
    keyboard = [
        [InlineKeyboardButton("❌ Скасувати", callback_data="v2_cancel_checkout")]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.user_data['awaiting_address_v2'] = True


# ============================================================================
# РЕЄСТРАЦІЯ HANDLERS
# ============================================================================

def register_checkout_v2_handlers(application):
    """
    Реєструє checkout v2 handlers
    
    Використання в main.py:
    ───────────────────────────
    from app.handlers.checkout_v2 import register_checkout_v2_handlers
    
    register_checkout_v2_handlers(app)
    """
    
    application.add_handler(CallbackQueryHandler(
        checkout_v2_callback,
        pattern="^v2_checkout$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        confirm_order_v2_callback,
        pattern="^v2_confirm_order$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        cancel_checkout_v2_callback,
        pattern="^v2_cancel_checkout$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        change_phone_v2_callback,
        pattern="^v2_change_phone$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        change_address_v2_callback,
        pattern="^v2_change_address$"
    ))
    
    logger.info("✅ Checkout v2 handlers registered")


__all__ = ['register_checkout_v2_handlers', 'request_address_v2']
