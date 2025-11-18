"""
🏪 RESTAURANT SELECTOR - Вибір ресторану з рейтингом
FerrikBot v3.3 - Новий UX
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

logger = logging.getLogger(__name__)


async def select_restaurant_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показати список ресторанів з рейтингом та часом доставки
    
    Формат:
    🍕 FerrikPizza — 4.8⭐
    ⏱ Доставка: 25–35 хв
    💬 Хіт: Пепероні
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    logger.info(f"🏪 Restaurant selection by {user.first_name}")
    
    # Отримуємо список ресторанів
    restaurants = get_restaurants(context)
    
    if not restaurants:
        await query.edit_message_text(
            "😔 На жаль, зараз немає доступних ресторанів.\n\n"
            "Спробуй пізніше!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")]
            ])
        )
        return
    
    # Формуємо повідомлення
    message = "🏪 **Обери ресторан:**\n\n"
    
    keyboard = []
    
    for idx, rest in enumerate(restaurants, 1):
        rest_id = rest.get('id', rest.get('ID', ''))
        name = rest.get('name', rest.get("Ім'я_партнера", 'Ресторан'))
        emoji = rest.get('emoji', '🍴')
        rating = rest.get('rating', rest.get('Рейтинг', 4.5))
        delivery_time = rest.get('delivery_time', rest.get('Час_доставки', '25–35'))
        hit_dish = rest.get('hit_dish', rest.get('Хіт_страва', ''))
        
        # Форматуємо блок ресторану
        message += f"{idx}. {emoji} **{name}** — {rating}⭐\n"
        message += f"   ⏱ Доставка: {delivery_time} хв\n"
        
        if hit_dish:
            message += f"   💬 Хіт: {hit_dish}\n"
        
        message += "\n"
        
        # Кнопка вибору ресторану
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {name}",
                callback_data=f"v2_restaurant_{rest_id}"
            )
        ])
    
    # Навігація
    keyboard.append([
        InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
    ])
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def get_restaurants(context: ContextTypes.DEFAULT_TYPE) -> list:
    """
    Отримати список ресторанів
    
    Джерела:
    1. Google Sheets (таблиця Партнери)
    2. Дефолтний список (якщо Sheets не підключено)
    """
    sheets_service = context.bot_data.get('sheets_service')
    
    if sheets_service and sheets_service.is_connected():
        try:
            # Спробувати отримати з Sheets
            restaurants = sheets_service.get_active_restaurants()
            if restaurants:
                return restaurants
        except Exception as e:
            logger.warning(f"Could not fetch restaurants from Sheets: {e}")
    
    # Дефолтні ресторани (для демо)
    return [
        {
            'id': 'P001',
            'name': 'FerrikPizza',
            'emoji': '🍕',
            'rating': 4.8,
            'delivery_time': '25–35',
            'hit_dish': 'Пепероні',
            'categories': ['Піца', 'Салати', 'Напої']
        },
        {
            'id': 'P002',
            'name': 'BurgerHub',
            'emoji': '🍔',
            'rating': 4.6,
            'delivery_time': '20–30',
            'hit_dish': 'Класичний бургер',
            'categories': ['Бургери', 'Закуски', 'Напої']
        },
        {
            'id': 'P003',
            'name': 'SushiPro',
            'emoji': '🍣',
            'rating': 4.9,
            'delivery_time': '30–40',
            'hit_dish': 'Філадельфія Лайт',
            'categories': ['Суші', 'Роли', 'Напої']
        }
    ]


async def restaurant_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Після вибору ресторану → показуємо категорії
    
    Flow: Ресторан → Категорії → Товари
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    restaurant_id = query.data.replace("v2_restaurant_", "")
    
    logger.info(f"🏪 Restaurant {restaurant_id} selected by {user.first_name}")
    
    # Зберігаємо вибраний ресторан
    context.user_data['selected_restaurant'] = restaurant_id
    
    # Отримуємо інфо про ресторан
    restaurant = get_restaurant_by_id(restaurant_id, context)
    
    if not restaurant:
        await query.answer("❌ Ресторан не знайдено", show_alert=True)
        return
    
    # Показуємо категорії ресторану
    await show_restaurant_categories(query, context, restaurant)


def get_restaurant_by_id(restaurant_id: str, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Отримати ресторан по ID"""
    restaurants = get_restaurants(context)
    
    for rest in restaurants:
        if rest.get('id') == restaurant_id or rest.get('ID') == restaurant_id:
            return rest
    
    return None


async def show_restaurant_categories(query, context, restaurant: dict):
    """Показати категорії вибраного ресторану"""
    rest_name = restaurant.get('name', 'Ресторан')
    rest_emoji = restaurant.get('emoji', '🍴')
    categories = restaurant.get('categories', [])
    
    # Якщо категорії не вказані - отримуємо всі категорії з меню цього ресторану
    if not categories:
        sheets_service = context.bot_data.get('sheets_service')
        if sheets_service and sheets_service.is_connected():
            try:
                categories = sheets_service.get_restaurant_categories(restaurant.get('id'))
            except:
                pass
    
    # Дефолтні якщо немає
    if not categories:
        categories = ['Піца', 'Салати', 'Напої', 'Закуски']
    
    # Формуємо повідомлення
    message = f"{rest_emoji} **{rest_name}**\n\nОбери категорію:"
    
    # Клавіатура з категоріями (по 2 в рядку)
    keyboard = []
    
    for i in range(0, len(categories), 2):
        row = []
        for cat in categories[i:i+2]:
            emoji = get_emoji_for_category(cat)
            row.append(InlineKeyboardButton(
                f"{emoji} {cat}",
                callback_data=f"v2_rest_cat_{restaurant.get('id')}_{cat}"
            ))
        keyboard.append(row)
    
    # Навігація
    keyboard.append([
        InlineKeyboardButton("◀️ Заклади", callback_data="v2_select_restaurant"),
        InlineKeyboardButton("🛒 Кошик", callback_data="v2_view_cart")
    ])
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def get_emoji_for_category(category: str) -> str:
    """Отримати емоджі для категорії"""
    emoji_map = {
        'Піца': '🍕',
        'Бургери': '🍔',
        'Салати': '🥗',
        'Суші': '🍣',
        'Роли': '🍣',
        'Кава': '☕',
        'Десерти': '🍰',
        'Напої': '🥤',
        'Закуски': '🍟',
    }
    return emoji_map.get(category, '🍴')


async def restaurant_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показати товари категорії в вибраному ресторані
    
    callback_data format: v2_rest_cat_P001_Піца
    """
    query = update.callback_query
    await query.answer()
    
    # Парсимо callback data
    parts = query.data.replace("v2_rest_cat_", "").split("_", 1)
    restaurant_id = parts[0]
    category = parts[1] if len(parts) > 1 else ""
    
    logger.info(f"📋 Category {category} in restaurant {restaurant_id}")
    
    # Отримуємо товари
    items = get_restaurant_category_items(restaurant_id, category, context)
    
    if not items:
        await query.answer("😔 Товарів немає", show_alert=True)
        return
    
    # Показуємо товари
    await show_items_list(query, context, restaurant_id, category, items)


def get_restaurant_category_items(restaurant_id: str, category: str, context) -> list:
    """Отримати товари ресторану за категорією"""
    sheets_service = context.bot_data.get('sheets_service')
    
    if sheets_service and sheets_service.is_connected():
        try:
            items = sheets_service.get_menu_by_restaurant_and_category(
                restaurant_id, 
                category
            )
            if items:
                return items
        except Exception as e:
            logger.error(f"Error fetching items: {e}")
    
    # Sample для демо
    return get_sample_restaurant_items(restaurant_id, category)


def get_sample_restaurant_items(restaurant_id: str, category: str) -> list:
    """Sample товари для демо"""
    samples = {
        'P001': {  # FerrikPizza
            'Піца': [
                {'id': 1, 'name': 'Маргарита', 'price': 180, 'desc': 'Томати, моцарела, базилік'},
                {'id': 2, 'name': 'Пепероні', 'price': 200, 'desc': 'Гостра ковбаска'},
            ],
            'Салати': [
                {'id': 10, 'name': 'Цезар', 'price': 120, 'desc': 'Курка, пармезан'},
                {'id': 11, 'name': 'Грецький', 'price': 110, 'desc': 'Фета, оливки'},
            ],
        },
        'P002': {  # BurgerHub
            'Бургери': [
                {'id': 5, 'name': 'Класичний', 'price': 150, 'desc': 'Яловичина, томат'},
                {'id': 6, 'name': 'Чізбургер', 'price': 170, 'desc': 'З подвійним сиром'},
            ],
        },
    }
    
    return samples.get(restaurant_id, {}).get(category, [])


async def show_items_list(query, context, restaurant_id: str, category: str, items: list):
    """Показати список товарів"""
    emoji = get_emoji_for_category(category)
    message = f"{emoji} **{category.upper()}**\n\n"
    
    keyboard = []
    
    for idx, item in enumerate(items[:10], 1):
        item_id = item.get('id', item.get('ID', 0))
        name = item.get('name', item.get('Страви', 'Товар'))
        price = item.get('price', item.get('Ціна', 0))
        desc = item.get('desc', item.get('Опис', ''))
        
        message += f"{idx}. **{name}** — {price} грн\n"
        if desc:
            message += f"   _{desc}_\n"
        message += "\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"➕ {name} ({price} грн)",
                callback_data=f"v2_add_{item_id}"
            )
        ])
    
    # Навігація
    keyboard.append([
        InlineKeyboardButton("◀️ Категорії", callback_data=f"v2_restaurant_{restaurant_id}"),
        InlineKeyboardButton("🛒 Кошик", callback_data="v2_view_cart")
    ])
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================================
# РЕЄСТРАЦІЯ HANDLERS
# ============================================================================

def register_restaurant_selector_handlers(application):
    """
    Реєструє restaurant selector handlers
    
    Використання в main.py:
    ───────────────────────────
    from app.handlers.restaurant_selector import register_restaurant_selector_handlers
    
    register_restaurant_selector_handlers(app)
    """
    
    application.add_handler(CallbackQueryHandler(
        select_restaurant_callback,
        pattern="^v2_select_restaurant$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        restaurant_selected_callback,
        pattern="^v2_restaurant_P"
    ))
    
    application.add_handler(CallbackQueryHandler(
        restaurant_category_callback,
        pattern="^v2_rest_cat_"
    ))
    
    logger.info("✅ Restaurant selector handlers registered")


__all__ = ['register_restaurant_selector_handlers']
