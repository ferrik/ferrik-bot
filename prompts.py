"""
Модуль з промптами та повідомленнями для FoodBot
Підтримує українську (UA) та англійську (EN) мови
"""

# ============= ПРИВІТАННЯ =============

GREETING = {
    'ua': """👋 Привіт!

Я <b>FoodBot</b> – твій помічник для замовлення їжі в Тернополі.

Хочеш подивитись меню чи отримати рекомендацію?""",
    
    'en': """👋 Hi!

I'm <b>FoodBot</b> – your food delivery assistant in Ternopil.

Do you want to see the menu or get a recommendation?"""
}


# ============= МЕНЮ КОМАНД =============

MENU_BUTTONS = {
    'ua': {
        'menu': '📖 Меню',
        'recommendation': '⭐ Рекомендація',
        'cart': '🛒 Корзина',
        'order_status': '🚚 Статус замовлення',
        'help': 'ℹ️ Допомога'
    },
    'en': {
        'menu': '📖 Menu',
        'recommendation': '⭐ Recommendation',
        'cart': '🛒 Cart',
        'order_status': '🚚 Order status',
        'help': 'ℹ️ Help'
    }
}


# ============= ЗАПИТАННЯ ДО КОРИСТУВАЧА =============

USER_QUESTIONS = {
    'ua': {
        'cuisine_type': 'Які страви ви хочете: українська кухня, піца чи щось легке?',
        'choose_or_recommend': 'Хочете обрати самостійно чи отримати пораду від мене?',
        'how_many_people': 'Скільки людей буде замовляти?',
        'budget': 'Який ваш бюджет на замовлення?',
        'delivery_or_pickup': 'Доставка чи самовивіз?',
        'delivery_time': 'На який час замовити?'
    },
    'en': {
        'cuisine_type': 'What type of food would you like: Ukrainian cuisine, pizza, or something light?',
        'choose_or_recommend': 'Would you like to choose yourself or get my recommendation?',
        'how_many_people': 'How many people are ordering?',
        'budget': 'What is your budget for the order?',
        'delivery_or_pickup': 'Delivery or pickup?',
        'delivery_time': 'What time would you like to order?'
    }
}


# ============= СИСТЕМНИЙ ПРОМПТ ДЛЯ GPT =============

SYSTEM_PROMPT = {
    'ua': """Ти FoodBot – асистент для доставки їжі в Тернополі.

ОСНОВНІ ПРАВИЛА:
• Завжди пиши українською мовою
• Тон – дружній + інформативний
• Основна мета – допомогти швидко знайти та замовити страву
• Будь стислим, але корисним

РЕКОМЕНДАЦІЇ:
• Коли користувач просить рекомендацію – обирай страви на основі:
  - Популярності
  - Типу кухні
  - Часу доби (сніданок/обід/вечеря)
  - Бюджету якщо вказано

УТОЧНЕННЯ:
• Якщо користувач вагається – став уточнюючі запитання:
  - Кількість людей
  - Тип кухні
  - Бюджет
  - Дієтичні обмеження

ОБМЕЖЕННЯ:
• НІКОЛИ не вигадуй ресторанів чи страв, яких нема в базі
• Якщо даних нема, відповідай: "На жаль, цієї страви зараз немає"
• Не обіцяй того, що не можеш виконати

ЗАВЕРШЕННЯ:
• У кінці кожної взаємодії пропонуй наступну дію:
  - "Подивитися меню"
  - "Отримати пораду"
  - "Перейти в корзину"

ПРИКЛАДИ ГАРНОЇ ВЗАЄМОДІЇ:
Користувач: "Щось легке на вечерю"
Ти: "Маю кілька варіантів легких страв:
🥗 Салат Цезар (120 грн)
🍲 Крем-суп з броколі (95 грн)
🍝 Паста Примавера (140 грн)

Що обираємо?"

Користувач: "Порадь піцу для компанії"
Ти: "Для компанії раджу великі піци:
🍕 Чотири сири (32см) - 280 грн
🍕 М'ясна (32см) - 320 грн
🍕 Маргарита (32см) - 240 грн

Скільки вас буде?"
""",

    'en': """You are FoodBot – a food delivery assistant in Ternopil.

CORE RULES:
• Always write in English
• Tone – friendly + informative
• Main goal – help quickly find and order food
• Be concise but helpful

RECOMMENDATIONS:
• When user asks for recommendation – choose dishes based on:
  - Popularity
  - Cuisine type
  - Time of day (breakfast/lunch/dinner)
  - Budget if specified

CLARIFICATIONS:
• If user hesitates – ask clarifying questions:
  - Number of people
  - Cuisine type
  - Budget
  - Dietary restrictions

LIMITATIONS:
• NEVER invent restaurants or dishes not in database
• If no data available, respond: "Sorry, this dish is currently unavailable"
• Don't promise what you can't deliver

CLOSING:
• At the end of each interaction suggest next action:
  - "View menu"
  - "Get recommendation"
  - "Go to cart"

EXAMPLES OF GOOD INTERACTION:
User: "Something light for dinner"
You: "I have several light options:
🥗 Caesar Salad (120 UAH)
🍲 Broccoli Cream Soup (95 UAH)
🍝 Primavera Pasta (140 UAH)

What would you like?"

User: "Recommend pizza for a group"
You: "For a group I recommend large pizzas:
🍕 Four Cheeses (32cm) - 280 UAH
🍕 Meat Lovers (32cm) - 320 UAH
🍕 Margherita (32cm) - 240 UAH

How many people?"
"""
}


# ============= ВІДПОВІДІ НА ТИПОВІ СИТУАЦІЇ =============

RESPONSES = {
    'ua': {
        'menu_empty': 'На жаль, меню зараз недоступне. Спробуйте пізніше або зв\'яжіться з підтримкою.',
        'item_not_found': 'На жаль, цієї страви зараз немає в меню.',
        'cart_empty': 'Ваш кошик порожній. Додайте щось смачне з меню! 😊',
        'order_placed': '✅ Замовлення прийнято! Очікуйте дзвінка від оператора.',
        'error': 'Виникла помилка. Спробуйте ще раз або зв\'яжіться з підтримкою.',
        'outside_hours': 'Нажаль, ми зараз не працюємо. Графік роботи: {open_hour} - {close_hour}',
        'min_order': 'Мінімальна сума замовлення: {amount} грн',
        'added_to_cart': '✅ Додано до кошика',
        'removed_from_cart': '🗑️ Видалено з кошика',
        'ask_phone': 'Будь ласка, вкажіть ваш номер телефону:\n<code>+380XXXXXXXXX</code>',
        'ask_address': 'Вкажіть адресу доставки:\n<i>наприклад: вул. Руська, 12, кв. 5</i>',
        'no_delivery': '😔 На жаль, доставка за цією адресою неможлива.\nЗона доставки: центр Тернополя (до 7 км)',
        'processing': '⏳ Обробляємо ваш запит...',
    },
    'en': {
        'menu_empty': 'Sorry, menu is currently unavailable. Try later or contact support.',
        'item_not_found': 'Sorry, this dish is not available right now.',
        'cart_empty': 'Your cart is empty. Add something delicious from the menu! 😊',
        'order_placed': '✅ Order placed! Wait for operator call.',
        'error': 'An error occurred. Try again or contact support.',
        'outside_hours': 'Sorry, we are closed now. Working hours: {open_hour} - {close_hour}',
        'min_order': 'Minimum order amount: {amount} UAH',
        'added_to_cart': '✅ Added to cart',
        'removed_from_cart': '🗑️ Removed from cart',
        'ask_phone': 'Please provide your phone number:\n<code>+380XXXXXXXXX</code>',
        'ask_address': 'Provide delivery address:\n<i>e.g.: 12 Ruska St, apt. 5</i>',
        'no_delivery': '😔 Sorry, delivery to this address is not available.\nDelivery zone: Ternopil center (up to 7 km)',
        'processing': '⏳ Processing your request...',
    }
}


# ============= ПРОМПТИ ДЛЯ АДМІНІСТРАТОРІВ =============

ADMIN_COMMANDS = {
    'ua': {
        'add_dish': 'Додати страву: [назва], [опис], [ціна], [категорія], [ресторан]',
        'edit_price': 'Змінити ціну на [нова ціна] для [страва]',
        'toggle_active': 'Активувати/Деактивувати [страва]',
        'stats': 'Показати топ-5 страв за останній тиждень',
        'update_status': 'Оновити статус замовлення №{order_id} → [Прийнято/Готується/Доставляється/Виконано]',
        'daily_report': 'Щоденний звіт',
        'orders_pending': 'Нові замовлення'
    },
    'en': {
        'add_dish': 'Add dish: [name], [description], [price], [category], [restaurant]',
        'edit_price': 'Change price to [new price] for [dish]',
        'toggle_active': 'Activate/Deactivate [dish]',
        'stats': 'Show top 5 dishes from last week',
        'update_status': 'Update order status №{order_id} → [Accepted/Cooking/Delivering/Completed]',
        'daily_report': 'Daily report',
        'orders_pending': 'Pending orders'
    }
}


# ============= СТАТУСИ ЗАМОВЛЕНЬ =============

ORDER_STATUSES = {
    'ua': {
        'new': 'Нове',
        'accepted': 'Прийнято',
        'cooking': 'Готується',
        'ready': 'Готове',
        'delivering': 'Доставляється',
        'completed': 'Виконано',
        'cancelled': 'Скасовано'
    },
    'en': {
        'new': 'New',
        'accepted': 'Accepted',
        'cooking': 'Cooking',
        'ready': 'Ready',
        'delivering': 'Delivering',
        'completed': 'Completed',
        'cancelled': 'Cancelled'
    }
}


# ============= ФУНКЦІЇ ДОПОМОГИ =============

def get_text(key, lang='ua', **kwargs):
    """Отримує текст за ключем та мовою з підстановкою параметрів"""
    try:
        text = RESPONSES[lang].get(key, RESPONSES['ua'].get(key, ''))
        if kwargs:
            text = text.format(**kwargs)
        return text
    except Exception:
        return RESPONSES['ua'].get(key, '')


def get_greeting(lang='ua'):
    """Отримує привітання"""
    return GREETING.get(lang, GREETING['ua'])


def get_system_prompt(lang='ua'):
    """Отримує системний промпт для GPT"""
    return SYSTEM_PROMPT.get(lang, SYSTEM_PROMPT['ua'])


def get_menu_buttons(lang='ua'):
    """Отримує кнопки меню"""
    return MENU_BUTTONS.get(lang, MENU_BUTTONS['ua'])


def detect_language(text):
    """Визначає мову тексту (простий спосіб)"""
    # Перевіряємо на наявність кириличних символів
    cyrillic = any(char in 'абвгдеєжзиіїйклмнопрстуфхцчшщьюя' for char in text.lower())
    return 'ua' if cyrillic else 'en'


def build_recommendation_prompt(user_preferences, menu_items, lang='ua'):
    """Будує промпт для рекомендації страв"""
    
    system = get_system_prompt(lang)
    
    # Формуємо список страв
    menu_text = "\n".join([
        f"- {item.get('Страви')}: {item.get('Опис', '')} ({item.get('Ціна')} грн, {item.get('Категорія', '')})"
        for item in menu_items[:30]
    ])
    
    user_query = user_preferences.get('query', '')
    people_count = user_preferences.get('people', 1)
    budget = user_preferences.get('budget', None)
    
    prompt = f"""{system}

ДОСТУПНІ СТРАВИ:
{menu_text}

ЗАПИТ КОРИСТУВАЧА: "{user_query}"
КІЛЬКІСТЬ ЛЮДЕЙ: {people_count}
"""
    
    if budget:
        prompt += f"БЮДЖЕТ: {budget} грн\n"
    
    prompt += "\nДай рекомендацію (2-4 страви) з поясненням чому саме ці."
    
    return prompt


# ============= ПРИКЛАДИ ДІАЛОГІВ =============

SAMPLE_DIALOGS = {
    'ua': [
        {
            'user': 'Привіт',
            'bot': get_greeting('ua'),
            'description': 'Стандартне привітання'
        },
        {
            'user': 'Хочу щось на обід',
            'bot': 'На обід раджу:\n🍲 Борщ з пампушками (85 грн)\n🍖 Котлета по-київськи (120 грн)\n🥗 Салат Грецький (75 грн)\n\nЩо обираємо?',
            'description': 'Рекомендація на обід'
        },
        {
            'user': 'Додай борщ до корзини',
            'bot': '✅ Борщ з пампушками додано до кошика (85 грн)\n\nЩе щось додати?',
            'description': 'Додавання до кошика'
        },
        {
            'user': 'Оформити замовлення',
            'bot': 'Будь ласка, вкажіть ваш номер телефону:\n+380XXXXXXXXX',
            'description': 'Початок оформлення'
        }
    ]
}


# ============= ЧАСИ ДОБИ ДЛЯ РЕКОМЕНДАЦІЙ =============

TIME_OF_DAY_SUGGESTIONS = {
    'ua': {
        'morning': {  # 6:00 - 11:00
            'greeting': 'Доброго ранку! ☀️',
            'suggestions': ['сніданок', 'каша', 'омлет', 'млинці', 'кава']
        },
        'lunch': {  # 11:00 - 16:00
            'greeting': 'Доброго дня! 🌤️',
            'suggestions': ['обід', 'суп', 'гарячі страви', 'бізнес-ланч']
        },
        'evening': {  # 16:00 - 21:00
            'greeting': 'Доброго вечора! 🌆',
            'suggestions': ['вечеря', 'піца', 'суші', 'стейк']
        },
        'night': {  # 21:00 - 6:00
            'greeting': 'Добраніч! 🌙',
            'suggestions': ['легкі страви', 'салати', 'закуски']
        }
    }
}
