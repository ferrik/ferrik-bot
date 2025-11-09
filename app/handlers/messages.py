"""
🔧 ДОДАЙ ЦЕЙ КОД В САМИЙ КІНЕЦЬ ФАЙЛУ app/handlers/messages.py
(після всіх інших функцій)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Імпорти (перевір, що вони є на початку файлу)
try:
    from app.utils.validators import validate_phone, normalize_phone
    from app.utils.cart_manager import get_user_cart, get_cart_total
    from app.utils.session import get_user_session, update_user_session
    from app.utils.warm_greetings import get_user_stats
except ImportError as e:
    logging.warning(f"⚠️ Some imports not available: {e}")

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS (якщо їх немає у файлі)
# ============================================================================

def sanitize_input(text: str) -> str:
    """Очищення введення користувача"""
    if not text:
        return ""
    # Видалення зайвих пробілів
    text = text.strip()
    # Обмеження довжини
    if len(text) > 500:
        text = text[:500]
    return text


def detect_intent(text: str) -> str:
    """
    Визначення наміру користувача
    
    Returns:
        'menu' | 'cart' | 'checkout' | 'recommendation' | 'unknown'
    """
    text_lower = text.lower()
    
    # Меню
    menu_keywords = ['меню', 'menu', 'показ', 'що є', 'catalog', 'каталог']
    if any(keyword in text_lower for keyword in menu_keywords):
        return 'menu'
    
    # Кошик
    cart_keywords = ['кошик', 'корзин', 'cart', 'basket']
    if any(keyword in text_lower for keyword in cart_keywords):
        return 'cart'
    
    # Оформлення
    checkout_keywords = ['замовити', 'оформити', 'купити', 'order', 'checkout']
    if any(keyword in text_lower for keyword in checkout_keywords):
        return 'checkout'
    
    # Рекомендації
    recommendation_keywords = ['хочу', 'порадь', 'підкажи', 'рекоменд', 'що взяти']
    if any(keyword in text_lower for keyword in recommendation_keywords):
        return 'recommendation'
    
    return 'unknown'


def detect_mood(text: str) -> str:
    """Визначення настрою користувача"""
    text_lower = text.lower()
    
    positive_keywords = ['супер', 'класно', 'дякую', 'чудово', '👍', '❤️', '😊']
    negative_keywords = ['погано', 'не подобається', 'не хочу', '👎', '😞']
    
    if any(keyword in text_lower for keyword in positive_keywords):
        return 'positive'
    elif any(keyword in text_lower for keyword in negative_keywords):
        return 'negative'
    
    return 'neutral'


# ============================================================================
# PLACEHOLDER HANDLERS (якщо функцій немає, використовуються заглушки)
# ============================================================================

async def handle_recommendation(update, context, text, mood, stats):
    """Обробка запиту рекомендацій"""
    await update.message.reply_text(
        "🤔 Шукаю для вас щось смачненьке!\n\n"
        "💡 Спробуйте команду /menu_v2 для перегляду всіх страв."
    )


async def handle_menu_request(update, context):
    """Обробка запиту меню"""
    keyboard = [
        [InlineKeyboardButton("📋 Відкрити меню", callback_data="v2_show_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 Натисніть кнопку нижче, щоб відкрити меню:",
        reply_markup=reply_markup
    )


async def handle_cart_request(update, context):
    """Обробка запиту кошика"""
    user_id = update.effective_user.id
    
    try:
        cart = get_user_cart(user_id)
        
        if not cart:
            await update.message.reply_text(
                "🛒 Ваш кошик порожній!\n\n"
                "Додайте щось смачненьке через /menu_v2"
            )
            return
        
        # Формуємо текст кошика
        items_text = "\n".join([
            f"{i+1}. {item.get('name', 'Товар')} x{item.get('quantity', 1)} = {item.get('price', 0) * item.get('quantity', 1)} грн"
            for i, item in enumerate(cart)
        ])
        
        total = get_cart_total(user_id)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Оформити", callback_data="checkout_start"),
                InlineKeyboardButton("🗑️ Очистити", callback_data="cart_clear")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🛒 *Ваш кошик:*\n\n{items_text}\n\n💰 *Всього: {total} грн*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Cart error: {e}")
        await update.message.reply_text("❌ Помилка при отриманні кошика")


async def handle_checkout_request(update, context):
    """Обробка запиту оформлення замовлення"""
    user_id = update.effective_user.id
    
    try:
        cart = get_user_cart(user_id)
        
        if not cart:
            await update.message.reply_text(
                "❌ Кошик порожній! Додайте товари через /menu_v2"
            )
            return
        
        # Запускаємо процес оформлення
        update_user_session(user_id, {'state': 'awaiting_phone'})
        
        await update.message.reply_text(
            "📱 Для оформлення замовлення введіть ваш номер телефону:\n\n"
            "Формат: +380XXXXXXXXX або 0XXXXXXXXX",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Checkout error: {e}")
        await update.message.reply_text("❌ Помилка при оформленні")


# ============================================================================
# ГОЛОВНИЙ HANDLER ДЛЯ ТЕКСТОВИХ ПОВІДОМЛЕНЬ
# ============================================================================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Головний обробник текстових повідомлень
    Викликається для всіх текстів (крім команд)
    
    Підтримує:
    - Багатокрокові діалоги (телефон, адреса, промокод)
    - Визначення намірів (меню, кошик, checkout)
    - AI рекомендації через Gemini
    """
    user = update.effective_user
    text = update.message.text
    
    logger.info(f"💬 Message from {user.id}: {text[:50]}...")
    
    # Очистити введення від шкідливих символів
    text = sanitize_input(text)
    
    # Отримати сесію та статистику користувача
    try:
        session = get_user_session(user.id)
        stats = get_user_stats(user.id)
    except Exception as e:
        logger.warning(f"⚠️ Session/stats error: {e}")
        session = {'state': 'idle'}
        stats = {}
    
    current_state = session.get('state', 'idle')
    
    # ========================================================================
    # ОБРОБКА БАГАТОКРОКОВИХ ДІАЛОГІВ
    # ========================================================================
    
    # СТАН: очікуємо телефон для замовлення
    if current_state == 'awaiting_phone':
        if validate_phone(text):
            normalized = normalize_phone(text)
            update_user_session(user.id, {
                'phone': normalized,
                'state': 'awaiting_address'
            })
            
            await update.message.reply_text(
                "✅ Телефон збережено!\n\n"
                "📍 Тепер введіть адресу доставки:\n"
                "_(наприклад: вул. Хрещатик, 12, кв. 5)_",
                parse_mode='Markdown'
            )
            return
        else:
            await update.message.reply_text(
                "❌ Невірний формат телефону!\n\n"
                "Спробуйте ще раз:\n"
                "✅ +380501234567\n"
                "✅ 0501234567\n"
                "✅ 050 123 45 67",
                parse_mode='Markdown'
            )
            return
    
    # СТАН: очікуємо адресу доставки
    if current_state == 'awaiting_address':
        if len(text) >= 10 and any(c.isdigit() for c in text):
            update_user_session(user.id, {
                'address': text,
                'state': 'confirming_order'
            })
            
            # Показуємо підсумок замовлення
            try:
                cart = get_user_cart(user.id)
                if cart:
                    phone = session.get('phone', 'Не вказано')
                    
                    # Формуємо текст замовлення
                    items_text = "\n".join([
                        f"{i+1}. {item.get('name', 'Товар')} x{item.get('quantity', 1)} = {item.get('price', 0) * item.get('quantity', 1)} грн"
                        for i, item in enumerate(cart)
                    ])
                    
                    total = get_cart_total(user.id)
                    delivery_cost = 50  # TODO: динамічна ціна доставки
                    final_total = total + delivery_cost
                    
                    summary = (
                        "📋 *Підсумок замовлення:*\n\n"
                        f"{items_text}\n\n"
                        f"💰 Сума: {total} грн\n"
                        f"🚚 Доставка: {delivery_cost} грн\n"
                        f"*Разом: {final_total} грн*\n\n"
                        f"📞 Телефон: {phone}\n"
                        f"📍 Адреса: {text}\n"
                    )
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Підтвердити", callback_data="confirm_order"),
                            InlineKeyboardButton("✏️ Змінити", callback_data="edit_order"),
                        ],
                        [
                            InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order"),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"{summary}\n💬 Все правильно?",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "❌ Кошик порожній! Спершу додайте товари через /menu_v2"
                    )
            except Exception as e:
                logger.error(f"❌ Order summary error: {e}")
                await update.message.reply_text("❌ Помилка при формуванні замовлення")
            return
        else:
            await update.message.reply_text(
                "❌ Адреса занадто коротка або не містить номера будинку! 😕\n\n"
                "Повинна бути мінімум 10 символів.\n\n"
                "Приклад: _вул. Хрещатик, 12, кв. 5_",
                parse_mode='Markdown'
            )
            return
    
    # СТАН: очікуємо промокод
    if current_state == 'awaiting_promocode':
        sheets_service = context.bot_data.get('sheets_service')
        if sheets_service:
            try:
                promo_data = sheets_service.validate_promocode(text)
                if promo_data:
                    update_user_session(user.id, {
                        'promocode': text,
                        'discount': promo_data.get('discount_percent', 0),
                        'state': 'idle'
                    })
                    
                    await update.message.reply_text(
                        f"🎉 Промокод *{text}* застосовано!\n\n"
                        f"Знижка: *{promo_data.get('discount_percent', 0)}%* ⭐\n\n"
                        "Продовжуйте оформлення замовлення!",
                        parse_mode='Markdown'
                    )
                    return
            except Exception as e:
                logger.error(f"❌ Promocode validation error: {e}")
        
        await update.message.reply_text(
            "❌ Промокод невірний або закінчився! 😔\n\n"
            "Спробуйте інший або продовжуйте без промокоду.",
            parse_mode='Markdown'
        )
        return
    
    # ========================================================================
    # НОРМАЛЬНИЙ РЕЖИМ: аналізуємо намір користувача
    # ========================================================================
    
    # Визначаємо намір та настрій
    intent = detect_intent(text)
    mood = detect_mood(text)
    
    logger.info(f"🎯 Detected intent: {intent}, mood: {mood}")
    
    # Обробляємо на основі наміру
    if intent == 'recommendation':
        await handle_recommendation(update, context, text, mood, stats)
    
    elif intent == 'menu':
        await handle_menu_request(update, context)
    
    elif intent == 'cart':
        await handle_cart_request(update, context)
    
    elif intent == 'checkout':
        await handle_checkout_request(update, context)
    
    else:
        # За замовчуванням - показати підказку з можливостями
        keyboard = [
            [
                InlineKeyboardButton("📋 Меню", callback_data="v2_show_menu"),
                InlineKeyboardButton("🛒 Кошик", callback_data="v2_view_cart"),
            ],
            [
                InlineKeyboardButton("🎲 Здивуй мене!", callback_data="surprise_me"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "💡 Не зовсім зрозумів 🤔\n\n"
            "Спробуй:\n"
            "• /menu_v2 — переглянути меню\n"
            "• /cart — мій кошик\n"
            "• Або натисни кнопку нижче:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )