"""
🍕 MENU HANDLER - Гібридний інтерфейс з розмовним UX
Натискай на текст → отримуй результат, без зайвих меню
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

# ============================================================================
# MOCK DATA (потім замінити на Google Sheets)
# ============================================================================

CATEGORIES = {
    "pizza": {
        "name": "Піца",
        "emoji": "🍕",
        "description": "Італійська класика на тонкому тісті",
        "products": [
            {
                "id": 1,
                "name": "Маргарита",
                "price": 180,
                "description": "Томати, базилік, моцарела",
                "time": "25 хв",
                "popular": True
            },
            {
                "id": 2,
                "name": "Пепероні",
                "price": 220,
                "description": "Салямі, моцарела, томатний соус",
                "time": "25 хв",
                "popular": True
            },
            {
                "id": 3,
                "name": "4 сири",
                "price": 250,
                "description": "Моцарела, пармезан, дор блю, чеддер",
                "time": "30 хв",
                "special": True  # Страва дня
            },
            {
                "id": 4,
                "name": "Гавайська",
                "price": 210,
                "description": "Курка, ананаси, моцарела",
                "time": "25 хв"
            }
        ]
    },
    "burgers": {
        "name": "Бургери",
        "emoji": "🍔",
        "description": "Соковиті бургери з свіжими інгредієнтами",
        "products": [
            {
                "id": 5,
                "name": "Бургер Класик",
                "price": 150,
                "description": "Яловичина, салат, помідор, сир чеддер",
                "time": "15 хв",
                "popular": True
            },
            {
                "id": 6,
                "name": "Чікен Бургер",
                "price": 140,
                "description": "Курячий котлет, соус BBQ, огірок",
                "time": "15 хв"
            },
            {
                "id": 7,
                "name": "Вегетаріанський",
                "price": 130,
                "description": "Соєвий котлет, овочі, хумус",
                "time": "12 хв"
            }
        ]
    },
    "mexican": {
        "name": "Мексиканська кухня",
        "emoji": "🌮",
        "description": "Гострі страви з Мексики",
        "products": [
            {
                "id": 8,
                "name": "Тако Мексиканське",
                "price": 120,
                "description": "Яловичина, боби, сальса, сметана",
                "time": "10 хв"
            },
            {
                "id": 9,
                "name": "Бурріто з куркою",
                "price": 140,
                "description": "Курка, рис, боби, гуакамоле",
                "time": "12 хв"
            }
        ]
    },
    "salads": {
        "name": "Салати",
        "emoji": "🥗",
        "description": "Свіжі овочеві салати",
        "products": [
            {
                "id": 10,
                "name": "Цезар з куркою",
                "price": 140,
                "description": "Курка, айсберг, пармезан, крутони",
                "time": "8 хв"
            },
            {
                "id": 11,
                "name": "Грецький",
                "price": 120,
                "description": "Фета, томати, огірки, оливки",
                "time": "7 хв"
            }
        ]
    },
    "drinks": {
        "name": "Напої",
        "emoji": "☕",
        "description": "Освіжаючі напої",
        "products": [
            {
                "id": 12,
                "name": "Кола 0.5л",
                "price": 30,
                "description": "Освіжаючий газований напій",
                "time": "0 хв"
            },
            {
                "id": 13,
                "name": "Сік апельсиновий",
                "price": 40,
                "description": "Свіжовичавлений 0.3л",
                "time": "0 хв"
            }
        ]
    },
    "desserts": {
        "name": "Десерти",
        "emoji": "🍰",
        "description": "Солодке до кави",
        "products": [
            {
                "id": 14,
                "name": "Тірамісу",
                "price": 90,
                "description": "Класичний італійський десерт",
                "time": "0 хв"
            }
        ]
    }
}

# Спеціальна пропозиція (страва дня)
DAILY_SPECIAL = {
    "product_id": 3,  # 4 сири
    "discount": 20,
    "emoji": "🔥"
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_product_by_id(product_id):
    """Знайти продукт за ID"""
    for cat_data in CATEGORIES.values():
        for product in cat_data["products"]:
            if product["id"] == product_id:
                return product
    return None


def get_special_offer():
    """Отримати страву дня з розрахованою ціною"""
    product = get_product_by_id(DAILY_SPECIAL["product_id"])
    if not product:
        return None
    
    original_price = product["price"]
    discount = DAILY_SPECIAL["discount"]
    discounted_price = original_price * (1 - discount / 100)
    
    return {
        **product,
        "original_price": original_price,
        "discounted_price": int(discounted_price),
        "discount": discount
    }


def format_cart(cart):
    """Форматувати кошик для відображення"""
    if not cart or not cart.get('items'):
        return "🛒 Кошик порожній"
    
    text = "🛒 *Твій кошик:*\n\n"
    
    for item in cart['items']:
        text += f"• {item['name']} x{item['quantity']} — {item['price'] * item['quantity']} грн\n"
    
    text += f"\n💵 *Разом: {cart['total']} грн*"
    
    return text


def get_quick_access_keyboard():
    """Швидкі кнопки (завжди доступні)"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 Кошик", callback_data="view_cart"),
            InlineKeyboardButton("📋 Меню", callback_data="main_menu"),
            InlineKeyboardButton("💰 Акції", callback_data="special_offer")
        ]
    ])


# ============================================================================
# КОМАНДА /start - Головне меню
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Головне меню з категоріями та швидким доступом
    """
    user = update.effective_user
    logger.info(f"🏠 /start від користувача {user.id}")
    
    # Перевірити, чи є історія замовлень (для персоналізації)
    has_orders = context.user_data.get('orders_count', 0) > 0
    
    # Привітання
    if has_orders:
        greeting = f"Привіт знову, {user.first_name}! 👋"
    else:
        greeting = f"🍴 Привіт, {user.first_name}! Я — Ferrik, твій персональний помічник зі смаку 🤖✨"
    
    # Страва дня
    special = get_special_offer()
    special_text = ""
    if special:
        special_text = (
            f"\n🔥 *Страва дня:* {special['name']} (-{special['discount']}%) "
            f"— ~~{special['original_price']}~~ *{special['discounted_price']} грн*\n"
        )
    
    # Категорії (по 3 в рядку)
    categories_text = "\n"
    cat_list = list(CATEGORIES.items())
    for i in range(0, len(cat_list), 3):
        row = cat_list[i:i+3]
        categories_text += " | ".join([f"{cat['emoji']} {cat['name']}" for _, cat in row]) + "\n"
    
    message_text = (
        f"{greeting}"
        f"{special_text}"
        f"{categories_text}"
        f"\n💡 _Натисни на категорію або просто напиши, що хочеш їсти!_"
    )
    
    # Клавіатура з категоріями
    keyboard = []
    
    # Страва дня (якщо є)
    if special:
        keyboard.append([
            InlineKeyboardButton("🔥 Страва дня", callback_data="special_offer")
        ])
    
    # Категорії (по 2 в рядку)
    cat_buttons = [
        InlineKeyboardButton(
            f"{cat_data['emoji']} {cat_data['name']}",
            callback_data=f"category_{cat_id}"
        )
        for cat_id, cat_data in CATEGORIES.items()
    ]
    
    for i in range(0, len(cat_buttons), 2):
        keyboard.append(cat_buttons[i:i+2])
    
    # Швидкий доступ
    keyboard.append([
        InlineKeyboardButton("🛒 Кошик", callback_data="view_cart"),
        InlineKeyboardButton("💰 Акції", callback_data="special_offer"),
        InlineKeyboardButton("📦 Історія", callback_data="order_history")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Головне меню (повернутися)
# ============================================================================

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повернутися до головного меню"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    has_orders = context.user_data.get('orders_count', 0) > 0
    
    if has_orders:
        greeting = f"📋 Головне меню:"
    else:
        greeting = "📋 *Меню FerrikBot*"
    
    special = get_special_offer()
    special_text = ""
    if special:
        special_text = (
            f"\n🔥 *Страва дня:* {special['name']} "
            f"— *{special['discounted_price']} грн* (-{special['discount']}%)\n"
        )
    
    categories_text = "\n"
    cat_list = list(CATEGORIES.items())
    for i in range(0, len(cat_list), 3):
        row = cat_list[i:i+3]
        categories_text += " | ".join([f"{cat['emoji']} {cat['name']}" for _, cat in row]) + "\n"
    
    message_text = (
        f"{greeting}"
        f"{special_text}"
        f"{categories_text}"
        f"\n💡 _Обери категорію або напиши, що хочеш!_"
    )
    
    keyboard = []
    
    if special:
        keyboard.append([
            InlineKeyboardButton("🔥 Страва дня", callback_data="special_offer")
        ])
    
    cat_buttons = [
        InlineKeyboardButton(
            f"{cat_data['emoji']} {cat_data['name']}",
            callback_data=f"category_{cat_id}"
        )
        for cat_id, cat_data in CATEGORIES.items()
    ]
    
    for i in range(0, len(cat_buttons), 2):
        keyboard.append(cat_buttons[i:i+2])
    
    keyboard.append([
        InlineKeyboardButton("🛒 Кошик", callback_data="view_cart"),
        InlineKeyboardButton("💰 Акції", callback_data="special_offer"),
        InlineKeyboardButton("📦 Історія", callback_data="order_history")
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

async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показати всі товари в категорії (натискай на текст!)
    """
    query = update.callback_query
    await query.answer()
    
    category_id = query.data.replace("category_", "")
    
    if category_id not in CATEGORIES:
        await query.answer("❌ Категорія не знайдена", show_alert=True)
        return
    
    category = CATEGORIES[category_id]
    
    # Зберегти поточну категорію в контексті (для breadcrumbs)
    context.user_data['current_category'] = category_id
    
    # Breadcrumbs
    breadcrumbs = f"🏠 Головна > {category['emoji']} {category['name']}"
    
    # Заголовок
    message_text = (
        f"{breadcrumbs}\n\n"
        f"{category['emoji']} *{category['name'].upper()}*\n"
        f"_{category['description']}_\n\n"
    )
    
    # Список товарів (натискай на текст!)
    for idx, product in enumerate(category["products"], 1):
        special_mark = ""
        price_text = f"{product['price']} грн"
        
        # Якщо страва дня
        if product.get('special'):
            special = get_special_offer()
            if special and special['id'] == product['id']:
                special_mark = " 🔥"
                price_text = f"~~{product['price']}~~ *{special['discounted_price']} грн*"
        
        # Якщо популярна
        if product.get('popular'):
            special_mark += " ⭐"
        
        message_text += (
            f"{idx}. *{product['name']}*{special_mark} — {price_text}\n"
            f"   _{product['description']}_\n"
            f"   ⏱️ {product['time']}\n\n"
        )
    
    message_text += "━━━━━━━━━━━━━━━━━━━━\n"
    message_text += "_Натисни на назву страви або напиши номер (1, 2, 3...)_"
    
    # Клавіатура: кожен товар = кнопка
    keyboard = []
    
    for idx, product in enumerate(category["products"], 1):
        price = product['price']
        
        # Якщо страва дня - показати знижену ціну
        if product.get('special'):
            special = get_special_offer()
            if special and special['id'] == product['id']:
                price = special['discounted_price']
        
        keyboard.append([
            InlineKeyboardButton(
                f"{idx}. {product['name']} — {price} грн",
                callback_data=f"add_to_cart_{product['id']}"
            )
        ])
    
    # Навігація
    keyboard.append([
        InlineKeyboardButton("◀️ Назад", callback_data="main_menu"),
        InlineKeyboardButton("🛒 Кошик", callback_data="view_cart")
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

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Додати товар в кошик"""
    query = update.callback_query
    
    product_id = int(query.data.replace("add_to_cart_", ""))
    product = get_product_by_id(product_id)
    
    if not product:
        await query.answer("❌ Товар не знайдено", show_alert=True)
        return
    
    # Перевірити знижку (якщо страва дня)
    price = product['price']
    if product.get('special'):
        special = get_special_offer()
        if special and special['id'] == product_id:
            price = special['discounted_price']
    
    # Ініціалізувати кошик
    if 'cart' not in context.user_data:
        context.user_data['cart'] = {'items': [], 'total': 0}
    
    cart = context.user_data['cart']
    
    # Перевірити, чи товар вже в кошику
    existing_item = next((item for item in cart['items'] if item['id'] == product_id), None)
    
    if existing_item:
        existing_item['quantity'] += 1
        await query.answer(f"➕ {product['name']} +1")
    else:
        cart['items'].append({
            'id': product_id,
            'name': product['name'],
            'price': price,
            'quantity': 1
        })
        await query.answer(f"✅ {product['name']} додано!")
    
    # Оновити загальну суму
    cart['total'] = sum(item['price'] * item['quantity'] for item in cart['items'])
    
    logger.info(f"✅ {product['name']} додано в кошик користувача {query.from_user.id}")
    
    # Показати повідомлення
    cart_summary = format_cart(cart)
    
    # Breadcrumbs
    current_cat = context.user_data.get('current_category')
    breadcrumbs = "🏠 Головна"
    if current_cat and current_cat in CATEGORIES:
        breadcrumbs += f" > {CATEGORIES[current_cat]['emoji']} {CATEGORIES[current_cat]['name']}"
    
    message_text = (
        f"{breadcrumbs}\n\n"
        f"✅ *{product['name']}* додано в кошик!\n\n"
        f"{cart_summary}\n\n"
        f"Що далі?"
    )
    
    # Кнопки швидкого вибору
    keyboard = []
    
    # Продовжити в поточній категорії
    if current_cat:
        keyboard.append([
            InlineKeyboardButton(
                f"📋 Більше з категорії {CATEGORIES[current_cat]['name']}",
                callback_data=f"category_{current_cat}"
            )
        ])
    
    # Інші категорії
    other_cats = [
        InlineKeyboardButton(
            f"{cat_data['emoji']} {cat_data['name']}",
            callback_data=f"category_{cat_id}"
        )
        for cat_id, cat_data in list(CATEGORIES.items())[:3]
        if cat_id != current_cat
    ]
    
    for i in range(0, len(other_cats), 2):
        keyboard.append(other_cats[i:i+2])
    
    # Оформити замовлення
    keyboard.append([
        InlineKeyboardButton("✅ Оформити замовлення", callback_data="checkout")
    ])
    
    # Швидкий доступ
    keyboard.append([
        InlineKeyboardButton("🛒 Кошик", callback_data="view_cart"),
        InlineKeyboardButton("📋 Меню", callback_data="main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Страва дня (спеціальна пропозиція)
# ============================================================================

async def show_special_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати страву дня зі знижкою"""
    query = update.callback_query
    await query.answer()
    
    special = get_special_offer()
    
    if not special:
        await query.edit_message_text("❌ Спеціальна пропозиція недоступна")
        return
    
    message_text = (
        f"🔥 *СТРАВА ДНЯ* 🔥\n\n"
        f"*{special['name']}*\n"
        f"{special['description']}\n"
        f"⏱️ Приготування: {special['time']}\n\n"
        f"💰 Ціна: ~~{special['original_price']} грн~~ → *{special['discounted_price']} грн*\n"
        f"🎁 Знижка {special['discount']}%!\n\n"
        f"Встигни замовити! 🔥"
    )
    
    keyboard = [
        [InlineKeyboardButton(
            f"🛒 Додати за {special['discounted_price']} грн",
            callback_data=f"add_to_cart_{special['id']}"
        )],
        [InlineKeyboardButton("◀️ Назад до меню", callback_data="main_menu")]
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

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати вміст кошика"""
    query = update.callback_query
    await query.answer()
    
    cart = context.user_data.get('cart', {'items': [], 'total': 0})
    
    if not cart['items']:
        message_text = (
            "🛒 *Кошик порожній*\n\n"
            "Обери щось смачне з меню! 😋"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 Перейти до меню", callback_data="main_menu")]
        ]
    else:
        message_text = "🛒 *Твій кошик:*\n\n"
        
        for item in cart['items']:
            total_price = item['price'] * item['quantity']
            message_text += f"• {item['name']} x{item['quantity']} — {total_price} грн\n"
        
        message_text += f"\n💵 *Разом: {cart['total']} грн*\n\n"
        message_text += "Готовий оформити замовлення?"
        
        keyboard = []
        
        # Кнопки видалення товарів
        for item in cart['items']:
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ Видалити {item['name']}",
                    callback_data=f"remove_from_cart_{item['id']}"
                )
            ])
        
        # Оформити
        keyboard.append([
            InlineKeyboardButton("✅ Оформити замовлення", callback_data="checkout")
        ])
        
        # Навігація
        keyboard.append([
            InlineKeyboardButton("📋 Продовжити покупки", callback_data="main_menu")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Видалити з кошика
# ============================================================================

async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Видалити товар з кошика"""
    query = update.callback_query
    
    product_id = int(query.data.replace("remove_from_cart_", ""))
    
    cart = context.user_data.get('cart', {'items': [], 'total': 0})
    
    # Знайти та видалити товар
    cart['items'] = [item for item in cart['items'] if item['id'] != product_id]
    
    # Оновити загальну суму
    cart['total'] = sum(item['price'] * item['quantity'] for item in cart['items'])
    
    await query.answer("🗑️ Товар видалено")
    
    # Показати оновлений кошик
    await view_cart(update, context)


# ============================================================================
# CALLBACK: Історія замовлень (placeholder)
# ============================================================================

async def order_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати історію замовлень"""
    query = update.callback_query
    await query.answer()
    
    # TODO: Реалізувати читання з Google Sheets
    message_text = (
        "📦 *Історія замовлень*\n\n"
        "У тебе поки немає замовлень.\n"
        "Зроби перше замовлення! 🎉"
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 Перейти до меню", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


# ============================================================================
# CALLBACK: Оформлення замовлення (placeholder)
# ============================================================================

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Почати оформлення замовлення"""
    query = update.callback_query
    await query.answer()
    
    cart = context.user_data.get('cart', {'items': [], 'total': 0})
    
    if not cart['items']:
        await query.answer("🛒 Кошик порожній!", show_alert=True)
        return
    
    # TODO: Реалізувати ConversationHandler для замовлення
    message_text = (
        "✅ *Оформлення замовлення*\n\n"
        "Функція в розробці! 🚧\n\n"
        "Скоро ти зможеш:\n"
        "• Вказати адресу доставки\n"
        "• Обрати спосіб оплати\n"
        "• Отримати номер замовлення\n\n"
        "Поки що можеш переглянути кошик 😊"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Повернутися до кошика", callback_data="view_cart")],
        [InlineKeyboardButton("📋 Головне меню", callback_data="main_menu")]
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

def register_menu_handlers(application):
    """
    Реєструє всі handlers для гібридного меню
    """
    # Команди
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", start_command))  # /menu = /start
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(show_category, pattern="^category_"))
    application.add_handler(CallbackQueryHandler(add_to_cart, pattern="^add_to_cart_"))
    application.add_handler(CallbackQueryHandler(show_special_offer, pattern="^special_offer$"))
    application.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    application.add_handler(CallbackQueryHandler(remove_from_cart, pattern="^remove_from_cart_"))
    application.add_handler(CallbackQueryHandler(order_history, pattern="^order_history$"))
    application.add_handler(CallbackQueryHandler(checkout, pattern="^checkout$"))
    
    logger.info("✅ Hybrid menu handlers registered")
