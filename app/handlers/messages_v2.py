"""
💬 MESSAGE HANDLER V2 - Обробка телефону/адреси
FerrikBot v3.3 - Новий UX
"""
import logging
import re
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)


async def handle_contact_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка Request Contact (швидкий спосіб)
    
    Telegram автоматично надсилає номер телефону
    """
    user = update.effective_user
    contact = update.message.contact
    
    if contact and contact.user_id == user.id:
        phone = contact.phone_number
        
        # Нормалізуємо формат
        if not phone.startswith('+'):
            phone = '+' + phone
        
        logger.info(f"📱 Contact received from {user.first_name}: {phone}")
        
        # Зберігаємо телефон
        context.user_data['phone'] = phone
        context.user_data['awaiting_phone_v2'] = False
        
        # Переходимо до запиту адреси
        from app.handlers.checkout_v2 import request_address_v2
        await request_address_v2(update.message, context)


async def handle_text_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка текстових повідомлень для v2
    
    Контексти:
    - awaiting_phone_v2: очікуємо телефон
    - awaiting_address_v2: очікуємо адресу
    """
    user = update.effective_user
    text = update.message.text
    
    # Перевірка на скасування
    if text == "❌ Скасувати":
        context.user_data.pop('awaiting_phone_v2', None)
        context.user_data.pop('awaiting_address_v2', None)
        
        await update.message.reply_text(
            "❌ Оформлення скасовано",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Очікуємо телефон
    if context.user_data.get('awaiting_phone_v2'):
        await handle_phone_input_v2(update, context, text)
        return
    
    # Очікуємо адресу
    if context.user_data.get('awaiting_address_v2'):
        await handle_address_input_v2(update, context, text)
        return


async def handle_phone_input_v2(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """
    Обробка телефону (введеного вручну)
    
    Підтримувані формати:
    - +380501234567
    - 380501234567
    - 0501234567
    """
    user = update.effective_user
    
    # Очищуємо від пробілів, дефісів, дужок
    clean_phone = re.sub(r'[\s\-\(\)]', '', text)
    
    # Нормалізуємо формат
    if clean_phone.startswith('0') and len(clean_phone) == 10:
        clean_phone = '+38' + clean_phone
    elif clean_phone.startswith('380') and len(clean_phone) == 12:
        clean_phone = '+' + clean_phone
    elif not clean_phone.startswith('+'):
        clean_phone = '+' + clean_phone
    
    # Валідація українського номера
    phone_pattern = r'^\+380\d{9}$'
    
    if not re.match(phone_pattern, clean_phone):
        await update.message.reply_text(
            "⚠️ Невірний формат номера телефону.\n\n"
            "Введи номер у форматі:\n"
            "▪️ +380501234567\n"
            "▪️ 0501234567\n\n"
            "Або натисни кнопку \"📲 Надіслати телефон\""
        )
        return
    
    logger.info(f"📱 Phone entered manually by {user.first_name}: {clean_phone}")
    
    # Зберігаємо телефон
    context.user_data['phone'] = clean_phone
    context.user_data['awaiting_phone_v2'] = False
    
    # Переходимо до запиту адреси
    from app.handlers.checkout_v2 import request_address_v2
    await request_address_v2(update.message, context)


async def handle_address_input_v2(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """
    Обробка адреси
    
    Валідація:
    - Мінімум 10 символів
    - Має містити цифру (номер будинку)
    """
    user = update.effective_user
    
    # Валідація
    if len(text) < 10:
        await update.message.reply_text(
            "⚠️ Адреса занадто коротка.\n\n"
            "Введи повну адресу:\n"
            "_вул. Шевченка 12, кв. 45_",
            parse_mode='Markdown'
        )
        return
    
    # Перевірка на номер будинку
    if not re.search(r'\d', text):
        await update.message.reply_text(
            "⚠️ Вкажи номер будинку.\n\n"
            "Приклад: _вул. Шевченка 12, кв. 45_",
            parse_mode='Markdown'
        )
        return
    
    logger.info(f"📍 Address entered by {user.first_name}: {text}")
    
    # Зберігаємо адресу
    context.user_data['address'] = text
    context.user_data['awaiting_address_v2'] = False
    
    # Показуємо підтвердження
    phone = context.user_data.get('phone')
    
    # Створюємо mock query для show_order_confirmation_v2
    class MockQuery:
        def __init__(self, message, user):
            self.message = message
            self.from_user = user
        
        async def answer(self, text="", show_alert=False):
            pass
        
        async def edit_message_text(self, text, **kwargs):
            # Видаляємо keyboard перед показом підтвердження
            await self.message.reply_text(
                "Оформлення...",
                reply_markup=ReplyKeyboardRemove()
            )
            await self.message.reply_text(text, **kwargs)
    
    mock_query = MockQuery(update.message, user)
    
    from app.handlers.checkout_v2 import show_order_confirmation_v2
    await show_order_confirmation_v2(mock_query, context, phone, text)


# ============================================================================
# РЕЄСТРАЦІЯ HANDLERS
# ============================================================================

def register_messages_v2_handlers(application):
    """
    Реєструє message v2 handlers
    
    Використання в main.py:
    ───────────────────────────
    from app.handlers.messages_v2 import register_messages_v2_handlers
    
    register_messages_v2_handlers(app)
    """
    
    # Contact handler (пріоритет вище!)
    application.add_handler(MessageHandler(
        filters.CONTACT,
        handle_contact_v2
    ))
    
    # Text handler (для телефону/адреси)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_v2
    ))
    
    logger.info("✅ Messages v2 handlers registered")


__all__ = ['register_messages_v2_handlers']
