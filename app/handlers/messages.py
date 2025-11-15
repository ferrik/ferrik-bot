"""
Text Message Handlers - Handle text messages
FerrikBot v3.2
"""

import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.utils.cart_manager import clear_user_cart, get_cart_summary
from app.utils.warm_greetings import update_user_stats

logger = logging.getLogger(__name__)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle all text messages (non-commands)
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user = update.effective_user
    user_id = user.id
    text = update.message.text
    
    logger.info(f"💬 Message from {user.username or user.first_name}: {text[:50]}")
    
    try:
        # Check if we're waiting for specific input
        user_data = context.user_data
        
        # Phone number input
        if user_data.get('awaiting_phone'):
            await handle_phone_input(update, context, text)
            return
        
        # Address input
        if user_data.get('awaiting_address'):
            await handle_address_input(update, context, text)
            return
        
        # Promo code input
        if user_data.get('awaiting_promo'):
            await handle_promo_input(update, context, text)
            return
        
        # Default: search in menu or show help
        await handle_general_message(update, context, text)
    
    except Exception as e:
        logger.error(f"❌ Error handling message: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Виникла помилка. Спробуйте ще раз або використайте /help"
        )


async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle phone number input"""
    user_id = update.effective_user.id
    
    # Validate phone number
    phone_pattern = r'^\+?380\d{9}$'
    clean_phone = re.sub(r'[\s\-\(\)]', '', text)
    
    if not re.match(phone_pattern, clean_phone):
        await update.message.reply_text(
            "⚠️ Невірний формат номера телефону.\n\n"
            "Введіть номер у форматі: +380XXXXXXXXX\n"
            "Наприклад: +380501234567"
        )
        return
    
    # Save phone
    context.user_data['phone'] = clean_phone
    context.user_data['awaiting_phone'] = False
    context.user_data['awaiting_address'] = True
    
    await update.message.reply_text(
        f"✅ Номер телефону збережено: {clean_phone}\n\n"
        "Тепер введіть адресу доставки:\n"
        "Наприклад: вул. Шевченка 15, кв. 42"
    )


async def handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle address input with confirmation"""
    user_id = update.effective_user.id
    
    # Validate address (basic check)
    if len(text) < 10:
        await update.message.reply_text(
            "⚠️ Адреса занадто коротка.\n\n"
            "Введіть повну адресу:\n"
            "вулиця, номер будинку, квартира\n"
            "Наприклад: вул. Шевченка 15, кв. 42"
        )
        return
    
    # Save address
    context.user_data['address'] = text
    context.user_data['awaiting_address'] = False
    
    # Get all order data
    summary = get_cart_summary(user_id)
    phone = context.user_data.get('phone')
    
    # Calculate costs
    delivery_cost = 0 if summary['total'] >= 300 else 50
    total_with_delivery = summary['total'] + delivery_cost
    
    # Get restaurant info
    restaurant_name = "Ресторан"
    if summary['items']:
        first_item = summary['items'][0]
        restaurant_name = first_item.get('restaurant', 'Ресторан')
    
    # Format order confirmation message
    message = (
        "📋 <b>ПІДТВЕРДЖЕННЯ ЗАМОВЛЕННЯ</b>\n\n"
        f"🏪 <b>Заклад:</b> {restaurant_name}\n\n"
    )
    
    # Add items
    message += "🛒 <b>Ваше замовлення:</b>\n"
    for item in summary['items']:
        name = item['name']
        price = item['price']
        quantity = item.get('quantity', 1)
        subtotal = price * quantity
        message += f"▪️ {name} × {quantity} = {subtotal} грн\n"
    
    message += "\n━━━━━━━━━━━━━━━━\n"
    message += f"💰 Сума товарів: <b>{summary['total']} грн</b>\n"
    message += f"🚚 Доставка: <b>{delivery_cost} грн</b>\n"
    
    if delivery_cost == 0:
        message += "<i>(Безкоштовна від 300 грн)</i>\n"
    
    message += f"\n💵 <b>РАЗОМ: {total_with_delivery} грн</b>\n\n"
    
    # Delivery details
    message += "📦 <b>Деталі доставки:</b>\n"
    message += f"📞 Телефон: {phone}\n"
    message += f"📍 Адреса: {text}\n"
    message += "💳 Оплата: Готівка при отриманні\n"
    message += "⏱ Час доставки: 30-45 хв\n\n"
    
    message += "❓ Підтвердити замовлення?"
    
    # Confirmation buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ ПІДТВЕРДИТИ ЗАМОВЛЕННЯ", callback_data="confirm_order")
        ],
        [
            InlineKeyboardButton("✏️ Змінити телефон", callback_data="change_phone"),
            InlineKeyboardButton("✏️ Змінити адресу", callback_data="change_address")
        ],
        [
            InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order")
        ]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle promo code input"""
    promo_code = text.strip().upper()
    
    # Sample promo codes (should come from database)
    valid_promos = {
        'FIRST20': {'discount': 20, 'description': 'Знижка 20% на перше замовлення'},
        'WELCOME': {'discount': 15, 'description': 'Вітальна знижка 15%'},
        'LOYAL5': {'discount': 15, 'description': 'Знижка за 5 замовлень'},
        'LOYAL10': {'discount': 20, 'description': 'Знижка за 10 замовлень'}
    }
    
    if promo_code in valid_promos:
        promo = valid_promos[promo_code]
        context.user_data['promo_code'] = promo_code
        context.user_data['promo_discount'] = promo['discount']
        context.user_data['awaiting_promo'] = False
        
        await update.message.reply_text(
            f"✅ Промокод '{promo_code}' активовано!\n\n"
            f"{promo['description']}\n"
            f"💰 Знижка: {promo['discount']}%"
        )
    else:
        await update.message.reply_text(
            f"❌ Промокод '{promo_code}' не знайдено.\n\n"
            "Спробуйте інший або продовжіть без промокоду."
        )


async def handle_general_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle general messages - search or help"""
    text_lower = text.lower()
    
    # Greetings
    greetings = ['привіт', 'здрастуй', 'вітаю', 'добрий день', 'hello', 'hi']
    if any(greeting in text_lower for greeting in greetings):
        await update.message.reply_text(
            "👋 Привіт! Я FerrikBot.\n\n"
            "Використовуй /menu щоб переглянути меню або /help для довідки.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🍕 Меню", callback_data="menu"),
                    InlineKeyboardButton("❓ Допомога", callback_data="help")
                ]
            ])
        )
        return
    
    # Menu keywords
    menu_keywords = ['меню', 'menu', 'їжа', 'замовити', 'піца', 'бургер']
    if any(keyword in text_lower for keyword in menu_keywords):
        await update.message.reply_text(
            "🍕 Відкриваю меню...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🍕 Меню", callback_data="menu")]
            ])
        )
        return
    
    # Cart keywords
    cart_keywords = ['кошик', 'корзина', 'cart', 'basket']
    if any(keyword in text_lower for keyword in cart_keywords):
        await update.message.reply_text(
            "🛒 Відкриваю кошик...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Кошик", callback_data="cart")]
            ])
        )
        return
    
    # Help keywords
    help_keywords = ['допомога', 'help', 'довідка', 'як', 'що робити']
    if any(keyword in text_lower for keyword in help_keywords):
        await update.message.reply_text(
            "❓ Відкриваю довідку...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ Допомога", callback_data="help")]
            ])
        )
        return
    
    # Default response
    await update.message.reply_text(
        "🤔 Не впевнений що ти маєш на увазі.\n\n"
        "Спробуй:\n"
        "▪️ /menu - Переглянути меню\n"
        "▪️ /cart - Відкрити кошик\n"
        "▪️ /help - Довідка",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🍕 Меню", callback_data="menu"),
                InlineKeyboardButton("🛒 Кошик", callback_data="cart")
            ],
            [
                InlineKeyboardButton("❓ Допомога", callback_data="help")
            ]
        ])
    )


# Export
__all__ = ['handle_text_message']