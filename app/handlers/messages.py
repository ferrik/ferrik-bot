"""
Text Message Handlers - Minimal version
FerrikBot v3.2
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle all text messages (non-commands)
    Minimal version for quick deployment
    """
    user = update.effective_user
    text = update.message.text
    
    logger.info(f"💬 Message from {user.username or user.first_name}: {text[:50]}")
    
    try:
        text_lower = text.lower()
        
        # Greetings
        if any(word in text_lower for word in ['привіт', 'hello', 'hi', 'здрастуй']):
            await update.message.reply_text(
                "👋 Привіт! Я FerrikBot.\n\n"
                "Використовуй /menu щоб переглянути меню!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🍕 Меню", callback_data="menu")]
                ])
            )
            return
        
        # Menu
        if any(word in text_lower for word in ['меню', 'menu', 'їжа']):
            await update.message.reply_text(
                "🍕 Відкриваю меню...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🍕 Меню", callback_data="menu")]
                ])
            )
            return
        
        # Cart
        if any(word in text_lower for word in ['кошик', 'cart', 'корзина']):
            await update.message.reply_text(
                "🛒 Відкриваю кошик...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Кошик", callback_data="cart")]
                ])
            )
            return
        
        # Help
        if any(word in text_lower for word in ['допомога', 'help', 'довідка']):
            await update.message.reply_text(
                "❓ Відкриваю довідку...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❓ Допомога", callback_data="help")]
                ])
            )
            return
        
        # Default
        await update.message.reply_text(
            "🤔 Не зрозумів...\n\n"
            "Спробуй:\n"
            "▪️ /menu - Меню\n"
            "▪️ /cart - Кошик\n"
            "▪️ /help - Допомога",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🍕 Меню", callback_data="menu"),
                    InlineKeyboardButton("🛒 Кошик", callback_data="cart")
                ]
            ])
        )
        
    except Exception as e:
        logger.error(f"❌ Error handling message: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Виникла помилка. Спробуй /help"
        )


__all__ = ['handle_text_message']
