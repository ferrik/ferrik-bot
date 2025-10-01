"""
Модуль для обробки розмов з користувачем
Використовує промпти з prompts.py та AI для інтелектуальної взаємодії
"""

import logging
from datetime import datetime
from prompts import (
    get_greeting, get_system_prompt, get_text, get_menu_buttons,
    detect_language, build_recommendation_prompt, TIME_OF_DAY_SUGGESTIONS
)
from services.gemini import get_ai_response
from services.sheets import get_menu_from_sheet, search_menu_items
from models.user import get_state, set_state, get_cart

logger = logging.getLogger('ferrik')


def get_time_of_day():
    """Визначає частину доби"""
    hour = datetime.now().hour
    if 6 <= hour < 11:
        return 'morning'
    elif 11 <= hour < 16:
        return 'lunch'
    elif 16 <= hour < 21:
        return 'evening'
    else:
        return 'night'


def get_user_language(user_id):
    """Отримує мову користувача (зберігається в стані)"""
    state, data = get_state(user_id)
    if data and 'language' in data:
        return data['language']
    return 'ua'  # За замовчуванням українська


def set_user_language(user_id, lang):
    """Встановлює мову користувача"""
    state, data = get_state(user_id)
    if not data:
        data = {}
    data['language'] = lang
    set_state(user_id, state, data)


def handle_start_command(chat_id, user):
    """Обробник команди /start з підтримкою мов"""
    from services.telegram import send_message
    
    try:
        # Визначаємо мову з імені користувача або за замовчуванням
        lang = get_user_language(chat_id)
        
        # Отримуємо привітання
        greeting = get_greeting(lang)
        
        # Отримуємо час доби для персоналізації
        time_of_day = get_time_of_day()
        time_greeting = TIME_OF_DAY_SUGGESTIONS.get(lang, {}).get(time_of_day, {}).get('greeting', '')
        
        if time_greeting:
            greeting = f"{time_greeting}\n\n{greeting}"
        
        # Створюємо клавіатуру
        buttons = get_menu_buttons(lang)
        keyboard = {
            "keyboard": [
                [{"text": buttons['menu']}, {"text": buttons['recommendation']}],
                [{"text": buttons['cart']}, {"text": buttons['order_status']}],
                [{"text": buttons['help']}]
            ],
            "resize_keyboard": True
        }
        
        send_message(chat_id, greeting, keyboard)
        set_state(chat_id, 'normal')
        
        logger.info(f"Start command handled for {chat_id} in {lang}")
        
    except Exception as e:
        logger.error(f"Error in handle_start_command: {e}", exc_info=True)


def handle_menu_command(chat_id, user):
    """Показує меню з категоріями"""
    from services.telegram import send_message
    
    try:
        lang = get_user_language(chat_id)
        menu = get_menu_from_sheet()
        
        if not menu:
            send_message(chat_id, get_text('menu_empty', lang))
            return
        
        # Групуємо за категоріями
        categories = {}
        for item in menu:
            cat = item.get('Категорія', 'Інше')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        # Формуємо повідомлення
        menu_text = "🍽 <b>Меню:</b>\n\n" if lang == 'ua' else "🍽 <b>Menu:</b>\n\n"
        
        for category, items in sorted(categories.items()):
            menu_text += f"<b>{category}</b>\n"
            for item in items[:10]:  # Макс 10 на категорію
                name = item.get('Страви', 'N/A')
                price = item.get('Ціна', 0)
                menu_text += f"• {name} - {price} грн\n"
            menu_text += "\n"
        
        # Додаємо підказку
        hint = "Напишіть назву страви щоб дізнатися більше" if lang == 'ua' else "Type dish name to learn more"
        menu_text += f"\n💡 {hint}"
        
        send_message(chat_id, menu_text)
        
    except Exception as e:
        logger.error(f"Error in handle_menu_command: {e}", exc_info=True)
        send_message(chat_id, get_text('error', get_user_language(chat_id)))


def handle_recommendation_request(chat_id, user, query=None):
    """Обробляє запит на рекомендацію"""
    from services.telegram import send_message
    
    try:
        lang = get_user_language(chat_id)
        
        # Якщо немає конкретного запиту - запитуємо
        if not query:
            question = get_text('cuisine_type', lang) if lang == 'ua' else USER_QUESTIONS['en']['cuisine_type']
            send_message(chat_id, question)
            set_state(chat_id, 'awaiting_recommendation_details')
            return
        
        # Отримуємо меню
        menu = get_menu_from_sheet()
        if not menu:
            send_message(chat_id, get_text('menu_empty', lang))
            return
        
        # Відправляємо індикатор обробки
        send_message(chat_id, get_text('processing', lang))
        
        # Будуємо промпт для AI
        user_preferences = {
            'query': query,
            'people': 1,  # За замовчуванням
            'time_of_day': get_time_of_day()
        }
        
        prompt = build_recommendation_prompt(user_preferences, menu, lang)
        
        # Отримуємо рекомендацію від AI
        recommendation = get_ai_response(prompt, {
            'first_name': user.get('first_name', ''),
            'username': user.get('username', '')
        })
        
        send_message(chat_id, recommendation)
        set_state(chat_id, 'normal')
        
    except Exception as e:
        logger.error(f"Error in handle_recommendation_request: {e}", exc_info=True)
        send_message(chat_id, get_text('error', get_user_language(chat_id)))


def handle_cart_command(chat_id, user):
    """Показує кошик"""
    from handlers.cart import show_cart
    
    try:
        show_cart(chat_id)
    except Exception as e:
        logger.error(f"Error in handle_cart_command: {e}", exc_info=True)


def handle_search_query(chat_id, text, user):
    """Обробляє пошук страв"""
    from services.telegram import send_message
    
    try:
        lang = get_user_language(chat_id)
        
        # Шукаємо в меню
        results = search_menu_items(text)
        
        if not results:
            # Якщо не знайдено - використовуємо AI
            handle_ai_conversation(chat_id, text, user)
            return
        
        # Показуємо результати
        response = "🔍 <b>Знайдено:</b>\n\n" if lang == 'ua' else "🔍 <b>Found:</b>\n\n"
        
        for item in results[:5]:
            name = item.get('Страви', 'N/A')
            desc = item.get('Опис', '')
            price = item.get('Ціна', 0)
            
            response += f"<b>{name}</b>\n"
            if desc:
                response += f"📝 {desc}\n"
            response += f"💰 {price} грн\n\n"
        
        # Додаємо кнопки для додавання в кошик
        keyboard = {
            "inline_keyboard": [
                [{"text": f"➕ {results[i].get('Страви')}", 
                  "callback_data": f"add_{results[i].get('ID')}"} ]
                for i in range(min(3, len(results)))
            ]
        }
        
        send_message(chat_id, response, keyboard)
        
    except Exception as e:
        logger.error(f"Error in handle_search_query: {e}", exc_info=True)


def handle_ai_conversation(chat_id, text, user):
    """Обробляє вільну розмову через AI"""
    from services.telegram import send_message
    
    try:
        lang = get_user_language(chat_id)
        
        # Визначаємо мову з тексту
        detected_lang = detect_language(text)
        if detected_lang != lang:
            set_user_language(chat_id, detected_lang)
            lang = detected_lang
        
        # Отримуємо системний промпт
        system_prompt = get_system_prompt(lang)
        
        # Отримуємо меню для контексту
        menu = get_menu_from_sheet()
        menu_context = ""
        if menu:
            menu_context = "\n\nДОСТУПНЕ МЕНЮ:\n" + "\n".join([
                f"- {item.get('Страви')}: {item.get('Ціна')} грн"
                for item in menu[:20]
            ])
        
        # Формуємо повний промпт
        full_prompt = f"{system_prompt}{menu_context}\n\nКористувач: {text}\n\nТвоя відповідь:"
        
        # Отримуємо відповідь
        user_context = {
            'first_name': user.get('first_name', ''),
            'username': user.get('username', '')
        }
        
        response = get_ai_response(full_prompt, user_context)
        
        send_message(chat_id, response)
        
    except Exception as e:
        logger.error(f"Error in handle_ai_conversation: {e}", exc_info=True)
        send_message(chat_id, get_text('error', get_user_language(chat_id)))


def handle_button_press(chat_id, button_text, user):
    """Обробляє натискання кнопок"""
    from services.telegram import send_message
    
    try:
        lang = get_user_language(chat_id)
        buttons = get_menu_buttons(lang)
        
        if button_text == buttons['menu']:
            handle_menu_command(chat_id, user)
        elif button_text == buttons['recommendation']:
            handle_recommendation_request(chat_id, user)
        elif button_text == buttons['cart']:
            handle_cart_command(chat_id, user)
        elif button_text == buttons['order_status']:
            handle_order_status(chat_id, user)
        elif button_text == buttons['help']:
            handle_help_command(chat_id, user)
        else:
            # Невідома кнопка - обробляємо як текст
            handle_search_query(chat_id, button_text, user)
            
    except Exception as e:
        logger.error(f"Error in handle_button_press: {e}", exc_info=True)


def handle_order_status(chat_id, user):
    """Показує статус замовлень"""
    from services.telegram import send_message
    
    lang = get_user_language(chat_id)
    # TODO: Реалізувати отримання замовлень користувача
    message = "У вас поки немає активних замовлень" if lang == 'ua' else "You don't have any active orders yet"
    send_message(
