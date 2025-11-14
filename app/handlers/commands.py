"""
Command Handlers - Handle bot commands
FerrikBot v3.2
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Import utilities
from app.utils.cart_manager import (
    get_cart_summary,
    format_cart_message,
    clear_user_cart,
    is_cart_empty
)
from app.utils.warm_greetings import (
    get_greeting_for_user,
    get_surprise_message,
    format_user_profile,
    update_user_stats
)
from app.services.sheets_service import sheets_service

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command - Welcome message
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    
    logger.info(f"👤 /start from {username or first_name} (ID: {user_id})")
    
    try:
        # Get personalized greeting
        greeting = get_greeting_for_user(user_id, username, first_name)
        
        # Check for surprise message
        surprise = get_surprise_message(user_id)
        
        # Build message
        message = greeting + "\n\n"
        
        if surprise:
            message += f"{surprise}\n\n"
        
        message += (
            "🍕 <b>FerrikBot</b> - твій помічник у замовленні їжі\n\n"
            "📋 <b>Доступні команди:</b>\n"
            "▪️ /menu - Переглянути меню\n"
            "▪️ /cart - Кошик\n"
            "▪️ /order - Оформити замовлення\n"
            "▪️ /profile - Мій профіль\n"
            "▪️ /help - Допомога\n\n"
            "Обирай команду або просто напиши що хочеш замовити! 😊"
        )
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("🍕 Меню", callback_data="menu"),
                InlineKeyboardButton("🛒 Кошик", callback_data="cart")
            ],
            [
                InlineKeyboardButton("👤 Профіль", callback_data="profile"),
                InlineKeyboardButton("❓ Допомога", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Error in /start: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Виникла помилка. Спробуйте ще раз або напишіть /help"
        )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /menu command - Show menu
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user = update.effective_user
    logger.info(f"👤 /menu from {user.username or user.first_name}")
    
    try:
        # TODO: Load menu from Google Sheets
        # For now, show sample menu
        
        message = (
            "🍕 <b>Меню FerrikBot</b>\n\n"
            "<b>🍕 Піца:</b>\n"
            "▪️ Маргарита - 180 грн\n"
            "▪️ Пепероні - 200 грн\n"
            "▪️ 4 Сири - 220 грн\n"
            "▪️ М'ясна - 240 грн\n\n"
            "<b>🍔 Бургери:</b>\n"
            "▪️ Класичний - 150 грн\n"
            "▪️ Чізбургер - 170 грн\n"
            "▪️ Бекон бургер - 190 грн\n\n"
            "<b>🍟 Закуски:</b>\n"
            "▪️ Картопля фрі - 60 грн\n"
            "▪️ Нагетси - 80 грн\n"
            "▪️ Крильця - 120 грн\n\n"
            "<b>🥤 Напої:</b>\n"
            "▪️ Coca-Cola - 40 грн\n"
            "▪️ Sprite - 40 грн\n"
            "▪️ Сік - 50 грн\n\n"
            "Для замовлення натисни на кнопку нижче або напиши назву страви!"
        )
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("🍕 Піца", callback_data="category_pizza"),
                InlineKeyboardButton("🍔 Бургери", callback_data="category_burgers")
            ],
            [
                InlineKeyboardButton("🍟 Закуски", callback_data="category_snacks"),
                InlineKeyboardButton("🥤 Напої", callback_data="category_drinks")
            ],
            [
                InlineKeyboardButton("🛒 Кошик", callback_data="cart"),
                InlineKeyboardButton("◀️ Назад", callback_data="start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Error in /menu: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Не вдалося завантажити меню. Спробуйте ще раз."
        )


async def cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /cart command - Show shopping cart
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user = update.effective_user
    user_id = user.id
    logger.info(f"👤 /cart from {user.username or user.first_name}")
    
    try:
        # Get cart summary
        summary = get_cart_summary(user_id)
        
        if summary['is_empty']:
            message = (
                "🛒 <b>Ваш кошик порожній</b>\n\n"
                "Використайте /menu щоб додати товари 🍕"
            )
            keyboard = [
                [InlineKeyboardButton("🍕 Меню", callback_data="menu")]
            ]
        else:
            # Format cart message
            message = format_cart_message(user_id)
            
            # Create keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Оформити замовлення", callback_data="checkout"),
                ],
                [
                    InlineKeyboardButton("🍕 Додати ще", callback_data="menu"),
                    InlineKeyboardButton("🗑️ Очистити", callback_data="cart_clear")
                ]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Error in /cart: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Не вдалося відкрити кошик. Спробуйте ще раз."
        )


async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /order command - Start checkout process
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user = update.effective_user
    user_id = user.id
    logger.info(f"👤 /order from {user.username or user.first_name}")
    
    try:
        # Check if cart is empty
        if is_cart_empty(user_id):
            await update.message.reply_text(
                "⚠️ Ваш кошик порожній!\n\n"
                "Додайте товари через /menu перед оформленням замовлення.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🍕 Меню", callback_data="menu")]
                ])
            )
            return
        
        # Get cart summary
        summary = get_cart_summary(user_id)
        
        message = (
            "📦 <b>Оформлення замовлення</b>\n\n"
            f"{format_cart_message(user_id)}\n\n"
            "Для оформлення замовлення:\n"
            "1️⃣ Натисни кнопку 'Продовжити'\n"
            "2️⃣ Введи свій номер телефону\n"
            "3️⃣ Введи адресу доставки\n"
            "4️⃣ Підтверди замовлення\n\n"
            "💳 Оплата при отриманні"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Продовжити", callback_data="order_phone")],
            [InlineKeyboardButton("◀️ Назад до кошика", callback_data="cart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Error in /order: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Не вдалося оформити замовлення. Спробуйте ще раз."
        )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /profile command - Show user profile
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user = update.effective_user
    user_id = user.id
    username = user.username
    logger.info(f"👤 /profile from {username or user.first_name}")
    
    try:
        # Format profile
        message = format_user_profile(user_id, username)
        
        keyboard = [
            [
                InlineKeyboardButton("🛒 Кошик", callback_data="cart"),
                InlineKeyboardButton("🍕 Меню", callback_data="menu")
            ],
            [
                InlineKeyboardButton("◀️ Назад", callback_data="start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Error in /profile: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Не вдалося завантажити профіль. Спробуйте ще раз."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command - Show help message
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user = update.effective_user
    logger.info(f"👤 /help from {user.username or user.first_name}")
    
    try:
        message = (
            "❓ <b>Допомога FerrikBot</b>\n\n"
            "<b>📋 Команди:</b>\n"
            "▪️ /start - Головне меню\n"
            "▪️ /menu - Переглянути меню\n"
            "▪️ /cart - Відкрити кошик\n"
            "▪️ /order - Оформити замовлення\n"
            "▪️ /profile - Мій профіль\n"
            "▪️ /help - Ця довідка\n\n"
            "<b>🎯 Як замовити:</b>\n"
            "1. Відкрий /menu\n"
            "2. Вибери страви\n"
            "3. Перевір /cart\n"
            "4. Оформи /order\n\n"
            "<b>💎 Система лояльності:</b>\n"
            "▪️ Bronze (0-4 замовлення) - 5% знижка\n"
            "▪️ Silver (5-9 замовлень) - 15% знижка\n"
            "▪️ Gold (10-24 замовлення) - 20% знижка\n"
            "▪️ Platinum (25-49 замовлень) - 25% знижка\n"
            "▪️ Diamond (50+ замовлень) - 30% знижка\n\n"
            "<b>📞 Підтримка:</b>\n"
            "Є питання? Напиши нам: @support\n\n"
            "🍕 Смачного!"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🍕 Меню", callback_data="menu"),
                InlineKeyboardButton("🛒 Кошик", callback_data="cart")
            ],
            [
                InlineKeyboardButton("◀️ Назад", callback_data="start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Error in /help: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Не вдалося завантажити довідку."
        )


# Export all command handlers
__all__ = [
    'start',
    'menu',
    'cart',
    'order',
    'profile',
    'help_command'
]
