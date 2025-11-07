"""
💬 Обробник текстових повідомлень з AI
Персоналізовані рекомендації та розуміння намірів
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.utils.session import (
    get_user_session,
    update_user_session,
    get_user_cart,
    add_to_cart,
    get_user_stats,
)
from app.utils.validators import sanitize_input, validate_phone, normalize_phone
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# ============================================================================
# ПЕРСОНАЛІЗОВАНІ ВІДПОВІДІ
# ============================================================================

MOOD_SUGGESTIONS = {
    'sad': {
        'emoji': '😢',
        'message': 'Я бачу, що ти в сумному настрої... 💔',
        'categories': ['comfort food', 'desserts', 'warm drinks'],
        'discount': 15,
    },
    'happy': {
        'emoji': '😊',
        'message': 'Чудово! Святкуємо? 🎉',
        'categories': ['pizza', 'sushi', 'celebrations'],
        'discount': 10,
    },
    'busy': {
        'emoji': '⚡',
        'message': 'Я бачу, ти спішиш... ⏰',
        'categories': ['fast food', 'quick meals'],
        'discount': 5,
    },
    'lazy': {
        'emoji': '😴',
        'message': 'Ліниво готувати? Я розумію! 😴',
        'categories': ['ready-to-eat', 'comfort food'],
        'discount': 0,
    },
}

INTENT_KEYWORDS = {
    'menu': ['меню', 'что есть', 'каталог', 'список', 'показать', 'меню'],
    'recommendation': ['порадь', 'что заказать', 'совет', 'рекомендуй', 'что попробовать'],
    'cart': ['корзина', 'кошик', 'что я заказал', 'мой заказ'],
    'checkout': ['оформить', 'заказать', 'отправить', 'доставить'],
    'mood': ['грустно', 'весело', 'спешу', 'лениво', 'холодно', 'жарко'],
}


async def handle_ai_order(update, context, text):
    user = update.effective_user
    
    # ОТРИМУЄМО GEMINI SERVICE
    gemini = context.bot_data.get('gemini_service')
    
    # ОБРОБЛЯЄМО З RATE LIMITING
    result = gemini.process_order_request(
        user_id=user.id,
        text=text,
        menu_items=[...]
    )
    
    # ЯК ЩО РЕЙТ ЛІМІТ?
    if result.get('action') == 'error':
        await update.message.reply_text(
            result['message'],
            parse_mode='Markdown'
        )
        return
    
    # Звичайна обробка
    # ...
    
    # ========================================================================
    # ОБРОБКА РІЗНИХ СТАНІВ
    # ========================================================================
    
    current_state = session.get('state', 'idle')
    
    # СТАН: очікуємо телефон
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
                "_(наприклад: вул. Руська, 12, кв. 5)_",
                parse_mode='Markdown'
            )
            return
        else:
            await update.message.reply_text(
                "❌ Невірний формат телефону!\n\n"
                "Спробуйте ще раз:\n"
                "✅ +380501234567\n"
                "✅ 0501234567",
                parse_mode='Markdown'
            )
            return
    
    # СТАН: очікуємо адресу
    if current_state == 'awaiting_address':
        if len(text) >= 10 and any(c.isdigit() for c in text):
            update_user_session(user.id, {
                'address': text,
                'state': 'confirming_order'
            })
            
            # Показуємо підсумок
            cart = get_user_cart(user.id)
            if cart:
                order_data = {
                    'items': cart,
                    'phone': session.get('phone'),
                    'address': text,
                }
                
                summary = format_order_summary(order_data)
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Підтвердити", callback_data="confirm_order"),
                        InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"{summary}\n\n💬 Все правильно?",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            return
        else:
            await update.message.reply_text(
                "❌ Адреса занадто коротка! 😕\n\n"
                "Повинна бути мінімум 10 символів та мати номер будинку.\n\n"
                "_(наприклад: вул. Руська, 12, кв. 5)_",
                parse_mode='Markdown'
            )
            return
    
    # СТАН: очікуємо промокод
    if current_state == 'awaiting_promocode':
        sheets_service = context.bot_data.get('sheets_service')
        if sheets_service:
            promo_data = sheets_service.validate_promocode(text)
            if promo_data:
                update_user_session(user.id, {
                    'promocode': text,
                    'state': 'idle'
                })
                
                await update.message.reply_text(
                    f"🎉 Промокод **{text}** застосовано!\n\n"
                    f"Знижка: **{promo_data['discount_percent']}%** ⭐",
                    parse_mode='Markdown'
                )
                return
            else:
                await update.message.reply_text(
                    "❌ Промокод невірний або закінчився! 😔",
                    parse_mode='Markdown'
                )
                return
    
    # ========================================================================
    # НОРМАЛЬНИЙ РЕЖИМ: аналізуємо намір користувача
    # ========================================================================
    
    # Визначаємо намір
    intent = detect_intent(text)
    mood = detect_mood(text)
    
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
        # За замовчуванням - спробуємо додати товар до кошика через AI
        await handle_ai_order(update, context, text)


def detect_intent(text: str) -> str:
    """Визначити намір користувача"""
    text_lower = text.lower()
    
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            return intent
    
    return 'order'  # За замовчуванням - спроба замовлення


def detect_mood(text: str) -> str:
    """Визначити настрій користувача"""
    text_lower = text.lower()
    
    mood_keywords = {
        'sad': ['грустно', 'сумно', 'погано', 'плохо', 'дипресія'],
        'happy': ['весело', 'класно', 'клево', 'круто', 'супер', 'радісно'],
        'busy': ['спішу', 'поспешаю', 'швидко', 'срочно', 'нету времени'],
        'lazy': ['ленивый', 'ліниво', 'не хочу готувати', 'не хочу готовить'],
    }
    
    for mood, keywords in mood_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return mood
    
    return None


async def handle_recommendation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    mood: str,
    stats: dict
):
    """Обробка запиту на рекомендацію"""
    gemini_service = context.bot_data.get('gemini_service')
    sheets_service = context.bot_data.get('sheets_service')
    
    if not gemini_service or not sheets_service:
        await update.message.reply_text("❌ Сервіс недоступний")
        return
    
    # Формуємо персоналізований запит
    menu_items = sheets_service.get_menu()
    
    # Додаємо контекст настрою
    mood_context = ""
    if mood and mood in MOOD_SUGGESTIONS:
        mood_info = MOOD_SUGGESTIONS[mood]
        mood_context = f"\nНастрій користувача: {mood_info['message']}"
    
    # Додаємо контекст улюблених страв
    favorites_context = ""
    if stats['favorite_item']:
        favorites_context = f"\nУлюблена страва користувача: {stats['favorite_item']}"
    
    # Запит до AI
    prompt = f"""Користувач запросив рекомендацію: "{text}"
{mood_context}
{favorites_context}

Порекомендуй 2-3 найбільш підходящі страви з меню.
Будь дружелюбний, використовуй емодзі та поясни чому саме ці страви."""
    
    response = await gemini_service.generate_response(prompt)
    
    keyboard = [
        [InlineKeyboardButton("📋 Переглянути меню", callback_data="show_menu")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        response,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_menu_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка запиту меню"""
    sheets_service = context.bot_data.get('sheets_service')
    
    if not sheets_service:
        await update.message.reply_text("❌ Сервіс недоступний")
        return
    
    menu_items = sheets_service.get_menu()
    
    if not menu_items:
        await update.message.reply_text("😔 Меню наразі порожнє")
        return
    
    # Групуємо за категоріями
    categories = {}
    for item in menu_items:
        cat = item.get('category', 'Інше')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    # Формуємо повідомлення
    message_parts = ["📋 **МЕНЮ**\n"]
    
    for category, items in categories.items():
        message_parts.append(f"\n**{category}**")
        for item in items[:5]:  # Обмежуємо 5 на категорію
            name = item.get('name', '')
            price = item.get('price', 0)
            rating = item.get('rating', 0)
            stars = "⭐" * int(rating) if rating > 0 else ""
            
            message_parts.append(f"🔹 {name} — {price} грн {stars}")
    
    message_parts.append("\n💬 Напишіть назву страви щоб додати до кошика!")
    
    menu_text = "\n".join(message_parts)
    
    keyboard = [
        [InlineKeyboardButton("🛒 Мій кошик", callback_data="show_cart")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if len(menu_text) > 4000:
        chunks = [menu_text[i:i+4000] for i in range(0, len(menu_text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
        await update.message.reply_text(
            "📍 Виберіть товар:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            menu_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def handle_cart_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка запиту кошика"""
    user = update.effective_user
    cart = get_user_cart(user.id)
    
    if not cart or len(cart) == 0:
        keyboard = [[InlineKeyboardButton("📋 Меню", callback_data="show_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🛒 Ваш кошик порожній! 😔\n\n"
            "Додайте щось смачне з меню! 🍕",
            reply_markup=reply_markup
        )
        return
    
    # Формуємо кошик
    order_data = {'items': cart}
    summary = format_order_summary(order_data)
    
    keyboard = [
        [InlineKeyboardButton("🎁 Промокод", callback_data="enter_promocode")],
        [InlineKeyboardButton("✅ Оформити", callback_data="checkout")],
        [InlineKeyboardButton("🗑️ Очистити", callback_data="clear_cart")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        summary,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_checkout_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка запиту оформлення"""
    user = update.effective_user
    cart = get_user_cart(user.id)
    
    if not cart or len(cart) == 0:
        await update.message.reply_text(
            "🛒 Кошик порожній! Нема чого замовляти 😔"
        )
        return
    
    update_user_session(user.id, {'state': 'awaiting_phone'})
    
    await update.message.reply_text(
        "📱 Введіть ваш номер телефону:\n"
        "_(наприклад: +380501234567 або 0501234567)_",
        parse_mode='Markdown'
    )


async def handle_ai_order(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Обробка замовлення через AI"""
    user = update.effective_user
    gemini_service = context.bot_data.get('gemini_service')
    sheets_service = context.bot_data.get('sheets_service')
    
    if not gemini_service or not sheets_service:
        await update.message.reply_text("❌ Сервіс недоступний")
        return
    
    # Отримуємо меню
    menu_items = sheets_service.get_menu()
    cart = get_user_cart(user.id)
    
    # Обробляємо через AI
    ai_result = await gemini_service.process_order_request(
        text,
        menu_items,
        cart
    )
    
    # Відповідаємо користувачу
    if ai_result.get('action') == 'add_to_cart':
        # Додаємо товари до кошика
        items_added = []
        for item in ai_result.get('items', []):
            add_to_cart(user.id, item)
            items_added.append(f"✅ {item['name']}")
        
        response_text = "\n".join(items_added)
        response_text += "\n\n🛒 Додано до кошика!"
        response_text += "\n\nЩе щось додати чи оформити? 😋"
    
    else:
        response_text = ai_result.get('message', 'Не зрозумів запит 😕')
    
    keyboard = [
        [
            InlineKeyboardButton("🛒 Мій кошик", callback_data="show_cart"),
            InlineKeyboardButton("📋 Меню", callback_data="show_menu"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        response_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================================
# Допоміжні функції
# ============================================================================

def format_order_summary(order: dict) -> str:
    """Форматування замовлення"""
    lines = ["📦 **Ваше замовлення:**\n"]
    
    for idx, item in enumerate(order.get('items', []), 1):
        name = item.get('name', 'Unknown')
        price = item.get('price', 0)
        qty = item.get('quantity', 1)
        total = price * qty
        
        lines.append(f"{idx}. {name}")
        lines.append(f"   {qty} × {price} грн = **{total} грн**\n")
    
    total = sum(
        item.get('price', 0) * item.get('quantity', 1)
        for item in order.get('items', [])
    )
    
    lines.append(f"\n💰 **Всього: {total} грн**")
    
    if order.get('phone'):
        lines.append(f"\n📱 **Телефон:** {order['phone']}")
    
    if order.get('address'):
        lines.append(f"📍 **Адреса:** {order['address']}")
    
    return "\n".join(lines)
