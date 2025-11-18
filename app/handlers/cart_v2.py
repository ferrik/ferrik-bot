"""
🛒 CART V2 - Кошик з upsell та покращеним UX
FerrikBot v3.3 - Новий UX
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.utils.cart_manager import (
    get_user_cart,
    get_cart_total,
    is_cart_empty,
    add_to_cart,
    remove_from_cart,
    clear_user_cart
)

logger = logging.getLogger(__name__)


async def cart_v2_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cart_v2 - новий стиль"""
    user = update.effective_user
    await show_cart_v2(update.message, user.id, context)


async def cart_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback для кошика"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    await show_cart_v2(query.message, user.id, context, edit=True)


async def show_cart_v2(message, user_id: int, context, edit: bool = False):
    """
    Показати кошик з новим UX
    
    Особливості:
    - Деталізований підсумок
    - Вартість доставки
    - Upsell пропозиції
    - Емоційний тон
    """
    
    if is_cart_empty(user_id):
        text = (
            "🛒 **Твій кошик порожній**\n\n"
            "Обери щось смачне з меню! 😋"
        )
        
        keyboard = [
            [InlineKeyboardButton("🍕 До меню", callback_data="v2_back_to_start")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if edit:
            await message.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        return
    
    # Отримуємо товари з кошика
    cart = get_user_cart(user_id)
    total = get_cart_total(user_id)
    
    # Розраховуємо доставку
    delivery_cost = calculate_delivery(total)
    final_total = total + delivery_cost
    
    # Формуємо повідомлення
    text = "🛒 **Твій кошик:**\n\n"
    
    # Список товарів
    for idx, item in enumerate(cart, 1):
        name = item.get('name', 'Товар')
        price = item.get('price', 0)
        qty = item.get('quantity', 1)
        subtotal = price * qty
        
        text += f"{idx}. {name} ×{qty} — {subtotal} грн\n"
    
    text += "\n" + "─" * 25 + "\n"
    
    # Підсумок
    text += f"💰 Разом: **{total} грн**\n"
    text += f"🚚 Доставка: **{delivery_cost} грн**\n"
    
    if delivery_cost == 0:
        text += "   _🎉 Безкоштовна від 300 грн!_\n"
    elif total >= 250:
        left = 300 - total
        text += f"   _💡 Ще {left} грн до безкоштовної!_\n"
    
    text += f"\n📦 **До оплати: {final_total} грн**\n"
    
    # Upsell пропозиції
    upsell_items = get_upsell_suggestions(cart, context)
    
    if upsell_items:
        text += "\n" + "─" * 25 + "\n"
        text += "👇 **До замовлення часто додають:**\n\n"
        
        for item in upsell_items[:2]:
            name = item.get('name', 'Товар')
            price = item.get('price', 0)
            text += f"• {name} — {price} грн\n"
        
        text += "\n_Додати щось? 🙂_"
    
    # Клавіатура
    keyboard = []
    
    # Основні дії
    keyboard.append([
        InlineKeyboardButton("🧾 Оформити замовлення", callback_data="v2_checkout")
    ])
    
    keyboard.append([
        InlineKeyboardButton("➕ Додати ще", callback_data="v2_back_to_start"),
        InlineKeyboardButton("🗑 Очистити", callback_data="v2_clear_cart")
    ])
    
    # Upsell кнопки
    if upsell_items:
        for item in upsell_items[:2]:
            item_id = item.get('id', 0)
            name = item.get('name', 'Товар')
            price = item.get('price', 0)
            
            keyboard.append([
                InlineKeyboardButton(
                    f"➕ {name} ({price} грн)",
                    callback_data=f"v2_add_{item_id}"
                )
            ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ Назад", callback_data="v2_back_to_start")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if edit:
        await message.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)


def calculate_delivery(total: float) -> int:
    """
    Розрахувати вартість доставки
    
    Правила:
    - від 300 грн: безкоштовно
    - менше 300: 50 грн
    """
    if total >= 300:
        return 0
    return 50


def get_upsell_suggestions(cart: list, context) -> list:
    """
    Отримати upsell пропозиції
    
    Логіка:
    1. Аналізуємо що в кошику
    2. Шукаємо популярні комбінації
    3. Пропонуємо топ-2 товари
    
    Приклад:
    - Якщо є піца → пропонуємо Cola, Garlic bread
    - Якщо є бургер → пропонуємо Fries, Milkshake
    """
    
    # Визначаємо категорії товарів у кошику
    categories_in_cart = set()
    for item in cart:
        cat = item.get('category', '')
        if cat:
            categories_in_cart.add(cat.lower())
    
    # Словник upsell пропозицій
    upsell_map = {
        'pizza': [
            {'id': 20, 'name': 'Coca-Cola 0.5л', 'price': 40, 'category': 'drinks'},
            {'id': 30, 'name': 'Часниковий хліб', 'price': 50, 'category': 'snacks'},
        ],
        'піца': [
            {'id': 20, 'name': 'Coca-Cola 0.5л', 'price': 40, 'category': 'drinks'},
            {'id': 30, 'name': 'Часниковий хліб', 'price': 50, 'category': 'snacks'},
        ],
        'burgers': [
            {'id': 31, 'name': 'Картопля фрі', 'price': 60, 'category': 'snacks'},
            {'id': 32, 'name': 'Молочний коктейль', 'price': 70, 'category': 'drinks'},
        ],
        'бургери': [
            {'id': 31, 'name': 'Картопля фрі', 'price': 60, 'category': 'snacks'},
            {'id': 32, 'name': 'Молочний коктейль', 'price': 70, 'category': 'drinks'},
        ],
    }
    
    # Збираємо пропозиції
    suggestions = []
    
    for cat in categories_in_cart:
        if cat in upsell_map:
            suggestions.extend(upsell_map[cat])
    
    # Якщо немає категорій - пропонуємо популярні напої
    if not suggestions:
        suggestions = [
            {'id': 20, 'name': 'Coca-Cola 0.5л', 'price': 40, 'category': 'drinks'},
            {'id': 21, 'name': 'Sprite 0.5л', 'price': 40, 'category': 'drinks'},
        ]
    
    # Фільтруємо товари які вже є в кошику
    cart_ids = {item.get('id') for item in cart}
    suggestions = [s for s in suggestions if s.get('id') not in cart_ids]
    
    return suggestions[:2]


async def clear_cart_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистити кошик"""
    query = update.callback_query
    await query.answer("🗑️ Кошик очищено")
    
    user_id = query.from_user.id
    clear_user_cart(user_id)
    
    await show_cart_v2(query.message, user_id, context, edit=True)


async def add_item_v2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Додати товар в кошик (v2)"""
    query = update.callback_query
    
    user_id = query.from_user.id
    item_id = int(query.data.replace("v2_add_", ""))
    
    # Отримуємо товар
    item = get_item_by_id(item_id, context)
    
    if not item:
        await query.answer("❌ Товар не знайдено", show_alert=True)
        return
    
    # Додаємо в кошик
    cart_item = {
        'id': item.get('id'),
        'name': item.get('name'),
        'price': item.get('price'),
        'category': item.get('category', ''),
        'restaurant': item.get('restaurant', ''),
        'quantity': 1
    }
    
    add_to_cart(user_id, cart_item)
    
    await query.answer(f"✅ {item.get('name')} додано!", show_alert=False)
    
    logger.info(f"✅ Item {item_id} added to cart by user {user_id}")


def get_item_by_id(item_id: int, context) -> dict:
    """Отримати товар по ID"""
    sheets_service = context.bot_data.get('sheets_service')
    
    if sheets_service and sheets_service.is_connected():
        try:
            item = sheets_service.get_item_by_id(item_id)
            if item:
                return item
        except:
            pass
    
    # Sample для демо
    sample_items = {
        1: {'id': 1, 'name': 'Маргарита', 'price': 180, 'category': 'pizza'},
        2: {'id': 2, 'name': 'Пепероні', 'price': 200, 'category': 'pizza'},
        5: {'id': 5, 'name': 'Класичний', 'price': 150, 'category': 'burgers'},
        6: {'id': 6, 'name': 'Чізбургер', 'price': 170, 'category': 'burgers'},
        20: {'id': 20, 'name': 'Coca-Cola 0.5л', 'price': 40, 'category': 'drinks'},
        21: {'id': 21, 'name': 'Sprite 0.5л', 'price': 40, 'category': 'drinks'},
        30: {'id': 30, 'name': 'Часниковий хліб', 'price': 50, 'category': 'snacks'},
        31: {'id': 31, 'name': 'Картопля фрі', 'price': 60, 'category': 'snacks'},
        32: {'id': 32, 'name': 'Молочний коктейль', 'price': 70, 'category': 'drinks'},
    }
    
    return sample_items.get(item_id)


# ============================================================================
# РЕЄСТРАЦІЯ HANDLERS
# ============================================================================

def register_cart_v2_handlers(application):
    """
    Реєструє cart v2 handlers
    
    Використання в main.py:
    ───────────────────────────
    from app.handlers.cart_v2 import register_cart_v2_handlers
    
    register_cart_v2_handlers(app)
    """
    
    # Команда
    application.add_handler(CommandHandler("cart_v2", cart_v2_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(
        cart_v2_callback,
        pattern="^v2_view_cart$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        clear_cart_v2_callback,
        pattern="^v2_clear_cart$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        add_item_v2_callback,
        pattern="^v2_add_"
    ))
    
    logger.info("✅ Cart v2 handlers registered")


__all__ = ['register_cart_v2_handlers']
