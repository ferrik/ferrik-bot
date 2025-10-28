"""
🎯 Обробники команд - Платформа з багатьма партнерами
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.utils.validators import format_order_summary, calculate_total_price
from app.utils.session import (
    get_user_cart,
    clear_user_cart,
    get_user_session,
    update_user_session
)

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    user = update.effective_user
    sheets_service = context.bot_data.get('sheets_service')
    
    logger.info(f"👤 User {user.id} ({user.username}) started bot")
    
    # Перевірка робочого часу
    if sheets_service and not sheets_service.is_open_now():
        await update.message.reply_text(
            "😔 Вибачте, зараз не робочий час.\n"
            "Ми приймаємо замовлення з 08:00 до 23:00.\n\n"
            "Але ви можете переглянути меню!"
        )
    
    # Вітальне повідомлення
    welcome_msg = (
        "👋 Вітаю у **FerrikFoot** — вашій платформі доставки їжі!\n\n"
        "🍕 Замовляйте страви з кращих ресторанів вашого міста!\n\n"
        "💬 Просто напишіть що хочете замовити, або оберіть:\n"
    )
    
    # Отримуємо список партнерів
    partners = sheets_service.get_partners() if sheets_service else []
    
    keyboard = []
    
    # Якщо партнерів більше 1 - показуємо вибір
    if len(partners) > 1:
        keyboard.append([InlineKeyboardButton("🏪 Вибрати ресторан", callback_data="choose_partner")])
    
    keyboard.extend([
        [
            InlineKeyboardButton("📋 Меню", callback_data="show_menu"),
            InlineKeyboardButton("🛒 Кошик", callback_data="show_cart")
        ],
        [
            InlineKeyboardButton("🎁 Промокоди", callback_data="show_promocodes"),
            InlineKeyboardButton("ℹ️ Допомога", callback_data="show_help")
        ]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_msg,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def choose_partner_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вибір ресторану/партнера"""
    sheets_service = context.bot_data.get('sheets_service')
    
    if not sheets_service:
        await update.message.reply_text("❌ Сервіс недоступний")
        return
    
    partners = sheets_service.get_partners()
    
    if not partners:
        await update.message.reply_text("😔 Наразі немає доступних ресторанів")
        return
    
    # Формуємо повідомлення
    msg_parts = ["🏪 **ОБЕРІТЬ РЕСТОРАН**\n"]
    keyboard = []
    
    for partner in partners:
        # Рейтинг зірками
        stars = "⭐" * int(partner['rating'])
        premium_badge = " 👑" if partner['premium'] else ""
        
        msg_parts.append(
            f"\n**{partner['name']}**{premium_badge}\n"
            f"{stars} {partner['rating']:.1f} | {partner['category']}\n"
        )
        
        keyboard.append([
            InlineKeyboardButton(
                f"{partner['name']}{premium_badge}",
                callback_data=f"partner_{partner['id']}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "\n".join(msg_parts),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /menu"""
    user = update.effective_user
    sheets_service = context.bot_data.get('sheets_service')
    
    logger.info(f"👤 User {user.id} requested menu")
    
    if not sheets_service:
        await update.message.reply_text("❌ Сервіс недоступний")
        return
    
    # Отримуємо вибраного партнера з сесії
    session = get_user_session(user.id)
    partner_id = session.get('selected_partner_id')
    
    # Завантажуємо меню
    menu_items = sheets_service.get_menu(partner_id=partner_id)
    
    if not menu_items:
        await update.message.reply_text(
            "😔 Меню наразі порожнє.\n"
            "Спробуйте пізніше або оберіть інший ресторан."
        )
        return
    
    # Групуємо за категоріями
    categories = {}
    for item in menu_items:
        category = item.get('category', 'Інше')
        if category not in categories:
            categories[category] = []
        categories[category].append(item)
    
    # Формуємо повідомлення
    message_parts = ["📋 **МЕНЮ**\n"]
    
    # Якщо вибрано конкретний ресторан
    if partner_id:
        partner = sheets_service.get_partner_by_id(partner_id)
        if partner:
            message_parts.append(f"🏪 {partner['name']}\n")
    
    # Виводимо по категоріях
    for category, items in categories.items():
        message_parts.append(f"\n**{category}**")
        for item in items[:10]:  # Обмежуємо 10 товарів
            name = item.get('name', 'Unknown')
            price = item.get('price', 0)
            rating = item.get('rating', 0)
            stars = "⭐" * int(rating) if rating > 0 else ""
            
            item_text = f"\n🔹 {name} — {price} грн {stars}"
            
            # Додаємо час доставки
            delivery_time = item.get('delivery_time', 0)
            if delivery_time:
                item_text += f"\n   ⏱️ {delivery_time} хв"
            
            # Алергени
            allergens = item.get('allergens', '')
            if allergens:
                item_text += f"\n   ⚠️ {allergens}"
            
            message_parts.append(item_text)
    
    message_parts.append(
        "\n\n💬 Напишіть, що хочете замовити, "
        "або використайте /cart для перегляду кошика."
    )
    
    menu_text = "\n".join(message_parts)
    
    # Відправляємо (можливо частинами)
    if len(menu_text) > 4000:
        chunks = [menu_text[i:i+4000] for i in range(0, len(menu_text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(menu_text, parse_mode='Markdown')


async def cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /cart"""
    user = update.effective_user
    sheets_service = context.bot_data.get('sheets_service')
    
    logger.info(f"👤 User {user.id} requested cart")
    
    cart = get_user_cart(user.id)
    session = get_user_session(user.id)
    
    if not cart or len(cart) == 0:
        keyboard = [[
            InlineKeyboardButton("📋 Переглянути меню", callback_data="show_menu")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🛒 Ваш кошик порожній.\n\n"
            "Додайте товари з меню!",
            reply_markup=reply_markup
        )
        return
    
    # Підрахунок сум
    subtotal = calculate_total_price(cart)
    
    # Застосування промокоду
    promocode = session.get('promocode')
    discount = 0
    
    if promocode and sheets_service:
        promo_data = sheets_service.validate_promocode(promocode)
        if promo_data:
            discount = subtotal * (promo_data['discount_percent'] / 100)
    
    # Вартість доставки (можна брати з конфігу)
    delivery_cost = 30  # або з sheets_service.get_config('DELIVERY_COST')
    
    total = subtotal - discount + delivery_cost
    
    # Формуємо повідомлення
    order_data = {
        'items': cart,
        'subtotal': subtotal,
        'discount': discount,
        'delivery_cost': delivery_cost,
        'total': total,
        'promocode': promocode
    }
    
    cart_text = format_order_summary(order_data)
    
    # Клавіатура
    keyboard = [
        [
            InlineKeyboardButton("🎁 Промокод", callback_data="enter_promocode"),
            InlineKeyboardButton("🗑 Очистити", callback_data="clear_cart")
        ],
        [
            InlineKeyboardButton("✅ Оформити замовлення", callback_data="checkout")
        ],
        [
            InlineKeyboardButton("📋 Додати ще", callback_data="show_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        cart_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /order - початок оформлення"""
    user = update.effective_user
    sheets_service = context.bot_data.get('sheets_service')
    
    logger.info(f"👤 User {user.id} started order")
    
    # Перевірка робочого часу
    if sheets_service and not sheets_service.is_open_now():
        await update.message.reply_text(
            "😔 Вибачте, зараз не робочий час.\n"
            "Ми приймаємо замовлення з 08:00 до 23:00."
        )
        return
    
    # Перевіряємо кошик
    cart = get_user_cart(user.id)
    
    if not cart or len(cart) == 0:
        await update.message.reply_text(
            "🛒 Ваш кошик порожній.\n\n"
            "Спочатку додайте товари командою /menu"
        )
        return
    
    # Показуємо підсумок
    session = get_user_session(user.id)
    subtotal = calculate_total_price(cart)
    
    # Промокод
    promocode = session.get('promocode')
    discount = 0
    if promocode and sheets_service:
        promo_data = sheets_service.validate_promocode(promocode)
        if promo_data:
            discount = subtotal * (promo_data['discount_percent'] / 100)
    
    delivery_cost = 30
    total = subtotal - discount + delivery_cost
    
    order_data = {
        'items': cart,
        'subtotal': subtotal,
        'discount': discount,
        'delivery_cost': delivery_cost,
        'total': total,
        'promocode': promocode
    }
    
    summary = format_order_summary(order_data)
    
    # Переходимо до введення контактів
    await update.message.reply_text(
        f"{summary}\n\n"
        "📱 Введіть ваш номер телефону:\n"
        "(формат: +380501234567 або 0501234567)"
    )
    
    # Зберігаємо стан
    update_user_session(user.id, {
        'state': 'awaiting_phone',
        'order_data': order_data
    })


async def promocode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /promocode"""
    user = update.effective_user
    sheets_service = context.bot_data.get('sheets_service')
    
    if not sheets_service:
        await update.message.reply_text("❌ Сервіс недоступний")
        return
    
    # Перевіряємо чи є активні промокоди (можна показати список)
    await update.message.reply_text(
        "🎁 **ПРОМОКОДИ**\n\n"
        "Введіть промокод щоб отримати знижку!\n\n"
        "Промокод буде застосовано до вашого поточного замовлення.",
        parse_mode='Markdown'
    )
    
    # Змінюємо стан
    update_user_session(user.id, {'state': 'awaiting_promocode'})


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /history - історія замовлень"""
    user = update.effective_user
    sheets_service = context.bot_data.get('sheets_service')
    
    if not sheets_service:
        await update.message.reply_text("❌ Сервіс недоступний")
        return
    
    orders = sheets_service.get_orders(user_id=user.id)
    
    if not orders:
        await update.message.reply_text(
            "📋 У вас поки немає замовлень.\n\n"
            "Зробіть перше замовлення командою /menu"
        )
        return
    
    # Показуємо останні 5 замовлень
    recent_orders = orders[-5:]
    
    msg_parts = ["📋 **ВАШІ ЗАМОВЛЕННЯ**\n"]
    
    for order in reversed(recent_orders):
        order_id = order.get('ID Замовлення', 'N/A')
        timestamp = order.get('Час Замовлення', '')[:16]  # Обрізаємо до хв
        total = order.get('Загальна сума', 0)
        status = order.get('Статус', 'Невідомо')
        
        # Емодзі для статусу
        status_emoji = {
            'Новий': '🆕',
            'Прийнято': '✅',
            'Готується': '👨‍🍳',
            'В дорозі': '🚗',
            'Доставлено': '✅',
            'Скасовано': '❌'
        }.get(status, '📦')
        
        msg_parts.append(
            f"\n{status_emoji} **Замовлення #{order_id}**\n"
            f"📅 {timestamp}\n"
            f"💰 {total} грн\n"
            f"📍 Статус: {status}"
        )
    
    msg_parts.append("\n\nДля повтору замовлення напишіть номер")
    
    keyboard = [[
        InlineKeyboardButton("📋 Нове замовлення", callback_data="show_menu")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "\n".join(msg_parts),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /help"""
    help_text = (
        "📖 **ДОПОМОГА**\n\n"
        "**Доступні команди:**\n"
        "🔹 /start — Почати роботу\n"
        "🔹 /menu — Переглянути меню\n"
        "🔹 /cart — Переглянути кошик\n"
        "🔹 /order — Оформити замовлення\n"
        "🔹 /promocode — Ввести промокод\n"
        "🔹 /history — Історія замовлень\n"
        "🔹 /partners — Список ресторанів\n"
        "🔹 /cancel — Скасувати поточну дію\n"
        "🔹 /help — Ця довідка\n\n"
        "**Як замовити:**\n"
        "1️⃣ Оберіть ресторан (якщо їх кілька)\n"
        "2️⃣ Перегляньте меню командою /menu\n"
        "3️⃣ Напишіть що хочете (наприклад: \"2 піци Маргарита\")\n"
        "4️⃣ Перевірте кошик командою /cart\n"
        "5️⃣ Оформіть замовлення командою /order\n\n"
        "💡 Ви також можете просто написати своє замовлення, "
        "і AI допоможе вам!\n\n"
        "🎁 Не забудьте використати промокоди для знижок!"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /cancel"""
    user = update.effective_user
    logger.info(f"👤 User {user.id} cancelled operation")
    
    # Очищуємо стан
    update_user_session(user.id, {'state': 'idle'})
    
    keyboard = [[
        InlineKeyboardButton("📋 Меню", callback_data="show_menu"),
        InlineKeyboardButton("🛒 Кошик", callback_data="show_cart")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Операцію скасовано.\n\n"
        "Що бажаєте зробити далі?",
        reply_markup=reply_markup
    )
