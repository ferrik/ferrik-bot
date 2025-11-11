"""
🍕 FERRIKBOT - Command Handlers
Обробка всіх команд (/start, /menu, /cart тощо)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)


# ============================================================================
# КОМАНДА /start
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /start з GDPR перевіркою та warm greetings
    """
    user = update.effective_user
    
    logger.info(f"👤 User {user.id} (@{user.username}) started bot")
    
    # 🔐 GDPR: Перевірка згоди
    try:
        from app.handlers.gdpr import has_consented, show_gdpr_consent
        
        if not has_consented(user.id):
            logger.info(f"📋 Showing GDPR consent to user {user.id}")
            await show_gdpr_consent(update, context)
            return
    except ImportError:
        logger.warning("⚠️ GDPR module not available")
    
    # Отримати статистику користувача (якщо є)
    try:
        from app.utils.warm_greetings import get_user_stats
        stats = get_user_stats(user.id)
        order_count = stats.get('order_count', 0)
    except ImportError:
        order_count = 0
    
    logger.info(f"📨 Greeting type: order_count={order_count}")
    
    # Персоналізоване привітання
    if order_count == 0:
        # Новий користувач
        greeting = (
            f"👋 Привіт, {user.first_name}!\n\n"
            f"Я *FerrikBot* — твій особистий помічник для замовлення їжі.\n\n"
            f"🍕 Швидко\n"
            f"🚚 Зручно\n"
            f"😋 Смачно\n\n"
            f"Що хочеш замовити сьогодні?"
        )
    elif order_count < 3:
        # Постійний клієнт
        greeting = (
            f"👋 З поверненням, {user.first_name}!\n\n"
            f"Рада знову тебе бачити! 🎉\n"
            f"Твоє замовлення #{order_count + 1} буде особливим!\n\n"
            f"Що обираєш цього разу?"
        )
    else:
        # VIP клієнт
        greeting = (
            f"⭐ Вітаю, {user.first_name}!\n\n"
            f"Ти наш VIP клієнт! 🌟\n"
            f"Вже {order_count} замовлень — дякуємо за довіру!\n\n"
            f"Маємо спеціальну пропозицію для тебе..."
        )
    
    # Клавіатура з кнопками
    keyboard = [
        [
            InlineKeyboardButton("📋 Меню", callback_data="v2_show_menu"),
            InlineKeyboardButton("🛒 Кошик", callback_data="view_cart")
        ],
        [
            InlineKeyboardButton("🎲 Здивуй мене!", callback_data="surprise_me"),
            InlineKeyboardButton("🎁 Акції", callback_data="v2_special_offer")
        ],
        [
            InlineKeyboardButton("❓ Допомога", callback_data="show_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        greeting,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.info(f"✅ Welcome message sent to {user.id}")


# ============================================================================
# КОМАНДА /menu
# ============================================================================

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показати меню (старе)
    Перенаправляє на /menu_v2
    """
    user = update.effective_user
    logger.info(f"📋 Menu command від {user.id}")
    
    keyboard = [
        [InlineKeyboardButton("📋 Відкрити меню", callback_data="v2_show_menu")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 *Меню FerrikBot*\n\n"
        "Натисніть кнопку нижче, щоб переглянути наше меню:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# КОМАНДА /cart
# ============================================================================

async def cart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати кошик користувача"""
    user = update.effective_user
    logger.info(f"🛒 Cart command від {user.id}")
    
    try:
        from app.utils.cart_manager import get_user_cart, get_cart_total
        
        cart = get_user_cart(user.id)
        
        if not cart:
            keyboard = [
                [InlineKeyboardButton("📋 Переглянути меню", callback_data="v2_show_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🛒 *Ваш кошик порожній*\n\n"
                "Додайте щось смачненьке через меню! 😋",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        # Формуємо текст кошика
        items_text = "\n".join([
            f"{i+1}. {item.get('name', 'Товар')} x{item.get('quantity', 1)} = {item.get('price', 0) * item.get('quantity', 1)} грн"
            for i, item in enumerate(cart)
        ])
        
        total = get_cart_total(user.id)
        delivery_cost = 50
        final_total = total + delivery_cost
        
        message = (
            f"🛒 *Ваш кошик:*\n\n"
            f"{items_text}\n\n"
            f"💰 Сума: {total} грн\n"
            f"🚚 Доставка: {delivery_cost} грн\n"
            f"*Разом: {final_total} грн*"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Оформити", callback_data="checkout_start"),
                InlineKeyboardButton("🗑️ Очистити", callback_data="cart_clear")
            ],
            [
                InlineKeyboardButton("📋 Додати ще", callback_data="v2_show_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except ImportError:
        await update.message.reply_text(
            "❌ Кошик тимчасово недоступний. Спробуйте пізніше."
        )
    except Exception as e:
        logger.error(f"❌ Cart error: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Помилка при завантаженні кошика."
        )


# ============================================================================
# КОМАНДА /order
# ============================================================================

async def order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Швидке оформлення замовлення"""
    user = update.effective_user
    logger.info(f"📦 Order command від {user.id}")
    
    try:
        from app.utils.cart_manager import get_user_cart
        
        cart = get_user_cart(user.id)
        
        if not cart:
            await update.message.reply_text(
                "❌ Кошик порожній!\n\n"
                "Спершу додайте товари через /menu"
            )
            return
        
        # Перенаправити на checkout
        from app.utils.session import update_user_session
        update_user_session(user.id, {'state': 'awaiting_phone'})
        
        await update.message.reply_text(
            "📦 *Оформлення замовлення*\n\n"
            "Крок 1/3: Введіть ваш номер телефону\n\n"
            "Формат:\n"
            "• +380501234567\n"
            "• 0501234567",
            parse_mode='Markdown'
        )
        
    except ImportError:
        await update.message.reply_text(
            "❌ Функція тимчасово недоступна."
        )
    except Exception as e:
        logger.error(f"❌ Order error: {e}")
        await update.message.reply_text(
            "❌ Помилка при оформленні."
        )


# ============================================================================
# КОМАНДА /help
# ============================================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати довідку"""
    user = update.effective_user
    logger.info(f"❓ Help command від {user.id}")
    
    help_text = (
        "❓ *Довідка FerrikBot*\n\n"
        "*Основні команди:*\n"
        "/start - Головне меню\n"
        "/menu - Переглянути меню\n"
        "/cart - Мій кошик\n"
        "/order - Оформити замовлення\n"
        "/help - Ця довідка\n\n"
        "*GDPR команди:*\n"
        "/delete_data - Видалити всі дані\n"
        "/export_data - Експортувати дані\n\n"
        "*Як замовити:*\n"
        "1️⃣ Відкрийте меню через /menu\n"
        "2️⃣ Оберіть страви (натисніть на кнопки)\n"
        "3️⃣ Перевірте кошик через /cart\n"
        "4️⃣ Оформіть замовлення\n"
        "5️⃣ Вкажіть телефон та адресу\n"
        "6️⃣ Підтвердіть замовлення\n\n"
        "*Час доставки:* 30-45 хвилин\n"
        "*Мінімальне замовлення:* 100 грн\n"
        "*Вартість доставки:* 50 грн\n\n"
        "*Питання?* Напишіть /support"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📋 Меню", callback_data="v2_show_menu"),
            InlineKeyboardButton("🛒 Кошик", callback_data="view_cart")
        ],
        [
            InlineKeyboardButton("🔙 На головну", callback_data="back_to_start")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# КОМАНДА /support
# ============================================================================

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Підтримка користувачів"""
    user = update.effective_user
    logger.info(f"💬 Support command від {user.id}")
    
    support_text = (
        "💬 *Підтримка FerrikBot*\n\n"
        "Є питання або проблема? Ми допоможемо!\n\n"
        "*Зв'язок з нами:*\n"
        "📧 Email: support@ferrikbot.com\n"
        "📱 Telegram: @ferrikbot_support\n\n"
        "*Часті питання:*\n"
        "• Як змінити адресу доставки?\n"
        "• Як використати промокод?\n"
        "• Як відмінити замовлення?\n"
        "• Як оплатити онлайн?\n\n"
        "Відповіді: https://ferrikbot.com/faq"
    )
    
    keyboard = [
        [InlineKeyboardButton("📄 FAQ", url="https://ferrikbot.com/faq")],
        [InlineKeyboardButton("🔙 Назад", callback_data="show_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        support_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# КОМАНДА /orders (Історія замовлень)
# ============================================================================

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати історію замовлень"""
    user = update.effective_user
    logger.info(f"📦 Orders history від {user.id}")
    
    # TODO: Реалізувати отримання з Google Sheets
    await update.message.reply_text(
        "📦 *Історія замовлень*\n\n"
        "Функція в розробці. Скоро буде доступна!\n\n"
        "Ви зможете:\n"
        "• Переглядати історію замовлень\n"
        "• Повторювати попередні замовлення\n"
        "• Відстежувати статус доставки",
        parse_mode='Markdown'
    )


# ============================================================================
# КОМАНДА /promo (Промокоди)
# ============================================================================

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати активні промокоди"""
    user = update.effective_user
    logger.info(f"🎁 Promo command від {user.id}")
    
    promo_text = (
        "🎁 *Активні промокоди*\n\n"
        "Введіть промокод при оформленні замовлення:\n\n"
        "🔥 *FIRST* - 20% на перше замовлення\n"
        "🍕 *PIZZA15* - 15% на піцу\n"
        "🎉 *WEEKEND* - 10% у вихідні\n\n"
        "💡 Промокод можна ввести на етапі оформлення замовлення."
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 Замовити зі знижкою", callback_data="v2_show_menu")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        promo_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# КОМАНДА /cancel (Скасування дії)
# ============================================================================

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скасувати поточну дію"""
    user = update.effective_user
    logger.info(f"❌ Cancel command від {user.id}")
    
    try:
        from app.utils.session import update_user_session
        update_user_session(user.id, {'state': 'idle'})
    except ImportError:
        pass
    
    keyboard = [
        [InlineKeyboardButton("🏠 На головну", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "❌ *Скасовано*\n\n"
        "Поточну дію скасовано. Що бажаєте зробити?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# РЕЄСТРАЦІЯ КОМАНД
# ============================================================================

def register_command_handlers(application):
    """
    Реєстрація всіх command handlers
    
    Args:
        application: Telegram Application instance
    """
    logger.info("📝 Registering command handlers...")
    
    # Основні команди
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("cart", cart_command))
    application.add_handler(CommandHandler("order", order_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Додаткові команди
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CommandHandler("orders", orders_command))
    application.add_handler(CommandHandler("promo", promo_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    logger.info("✅ Command handlers registered")