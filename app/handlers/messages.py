"""
💬 Обробники текстових повідомлень
FerrikBot v3.2 - ВИПРАВЛЕНА ВЕРСІЯ (підтримка редагування профілю)
"""
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.utils.cart_manager import clear_user_cart, get_cart_summary
from app.utils.warm_greetings import update_user_stats
from app.handlers.callbacks import show_order_confirmation

logger = logging.getLogger(__name__)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    user = update.effective_user
    user_id = user.id
    text = update.message.text
    
    logger.info(f"💬 Message from {user.username or user.first_name}: {text[:50]}")
    
    try:
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
        
        # Default: show help
        await handle_general_message(update, context, text)
    
    except Exception as e:
        logger.error(f"❌ Error handling message: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Виникла помилка. Спробуйте ще раз або використайте /help"
        )


async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle phone number input - ПОКРАЩЕНО"""
    user_id = update.effective_user.id
    
    # Validate phone
    phone_pattern = r'^\+?380\d{9}$'
    clean_phone = re.sub(r'[\s\-\(\)]', '', text)
    
    # Додаємо +380 якщо користувач ввів без коду країни
    if clean_phone.startswith('0') and len(clean_phone) == 10:
        clean_phone = '+38' + clean_phone
    elif clean_phone.startswith('380') and len(clean_phone) == 12:
        clean_phone = '+' + clean_phone
    
    if not re.match(phone_pattern, clean_phone):
        await update.message.reply_text(
            "⚠️ Невірний формат номера телефону.\n\n"
            "Введіть номер у форматі:\n"
            "▪️ +380XXXXXXXXX\n"
            "▪️ 380XXXXXXXXX\n"
            "▪️ 0XXXXXXXXX\n\n"
            "Наприклад: +380501234567 або 0501234567"
        )
        return
    
    # Save phone
    context.user_data['phone'] = clean_phone
    context.user_data['awaiting_phone'] = False
    
    # Перевіряємо чи це редагування профілю чи оформлення замовлення
    if context.user_data.get('editing_profile'):
        context.user_data['editing_profile'] = False
        
        await update.message.reply_text(
            f"✅ Номер телефону оновлено: {clean_phone}\n\n"
            "Дані збережено у вашому профілі!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 До профілю", callback_data="profile")],
                [InlineKeyboardButton("🍕 До меню", callback_data="menu")]
            ])
        )
    else:
        # Оформлення замовлення - запитуємо адресу
        context.user_data['awaiting_address'] = True
        
        await update.message.reply_text(
            f"✅ Номер телефону збережено: {clean_phone}\n\n"
            "Тепер введіть адресу доставки:\n"
            "Наприклад: вул. Шевченка 15, кв. 42"
        )


async def handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle address input - ПОКРАЩЕНО"""
    user_id = update.effective_user.id
    
    # Validate address
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
    
    # Перевіряємо чи це редагування профілю чи оформлення замовлення
    if context.user_data.get('editing_profile'):
        context.user_data['editing_profile'] = False
        
        await update.message.reply_text(
            f"✅ Адресу оновлено:\n{text}\n\n"
            "Дані збережено у вашому профілі!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 До профілю", callback_data="profile")],
                [InlineKeyboardButton("🍕 До меню", callback_data="menu")]
            ])
        )
    else:
        # Оформлення замовлення - показуємо підтвердження
        phone = context.user_data.get('phone')
        
        # Використовуємо функцію з callbacks.py
        # Створюємо mock query object
        class MockQuery:
            def __init__(self, message, user):
                self.message = message
                self.from_user = user
            
            async def edit_message_text(self, text, **kwargs):
                await self.message.reply_text(text, **kwargs)
        
        mock_query = MockQuery(update.message, update.effective_user)
        await show_order_confirmation(mock_query, context, phone, text)


async def handle_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle promo code"""
    promo_code = text.strip().upper()
    
    # Sample promos
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
    """Handle general messages"""
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
    
    # Profile keywords - ДОДАНО
    profile_keywords = ['профіль', 'profile', 'мої дані', 'my profile']
    if any(keyword in text_lower for keyword in profile_keywords):
        await update.message.reply_text(
            "👤 Відкриваю профіль...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 Профіль", callback_data="profile")]
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
    
    # Default
    await update.message.reply_text(
        "🤔 Не впевнений що ти маєш на увазі.\n\n"
        "Спробуй:\n"
        "▪️ /menu - Переглянути меню\n"
        "▪️ /cart - Відкрити кошик\n"
        "▪️ /profile - Мій профіль\n"
        "▪️ /help - Довідка",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🍕 Меню", callback_data="menu"),
                InlineKeyboardButton("🛒 Кошик", callback_data="cart")
            ],
            [
                InlineKeyboardButton("👤 Профіль", callback_data="profile"),
                InlineKeyboardButton("❓ Допомога", callback_data="help")
            ]
        ])
    )


__all__ = ['handle_text_message']
