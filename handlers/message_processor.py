import logging
from concurrent.futures import ThreadPoolExecutor
from services.gemini import analyze_user_request_with_gemini, format_ai_response
from services.sheets import get_menu_from_sheet
from services.telegram import tg_send_message
from handlers.cart import add_item_to_cart, show_cart
from handlers.budget import handle_budget_input, show_price_ranges
from models.user import get_state, set_state, add_chat_history

logger = logging.getLogger("ferrik.processor")

# Thread pool для асинхронної обробки
EXECUTOR = ThreadPoolExecutor(max_workers=3)

def process_text_message(chat_id, text, user_info=None):
    """Обробляє текстові повідомлення користувача"""
    try:
        # Додаємо до історії
        add_chat_history(chat_id, text, is_user=True)
        
        user_state = get_state(chat_id)
        
        # Обробляємо стани
        if user_state and user_state != "normal":
            return handle_state_input(chat_id, text, user_state)
        
        # Команди
        if text.startswith('/'):
            return handle_commands(chat_id, text, user_info)
        
        # Кнопки головного меню
        if text in get_main_menu_buttons():
            return handle_main_menu_button(chat_id, text)
        
        # Використовуємо AI для аналізу
        EXECUTOR.submit(process_with_ai, chat_id, text)
        return True
        
    except Exception as e:
        logger.error(f"Error processing text message for {chat_id}: {e}")
        tg_send_message(chat_id, "Вибачте, сталася помилка при обробці повідомлення.")
        return False

def process_with_ai(chat_id, text):
    """Асинхронна обробка за допомогою AI"""
    try:
        # Отримуємо меню для AI
        menu_items = get_menu_from_sheet()
        
        # Аналізуємо запит
        ai_result = analyze_user_request_with_gemini(text, menu_items)
        
        if not ai_result:
            fallback_search(chat_id, text, menu_items)
            return
        
        action = ai_result.get("action")
        
        if action == "add_to_cart":
            handle_ai_add_to_cart(chat_id, ai_result)
        elif action == "question":
            handle_ai_question(chat_id, ai_result)
        elif action == "search":
            handle_ai_search(chat_id, ai_result, menu_items)
        else:
            handle_ai_error(chat_id, ai_result)
        
        # Додаємо відповідь AI до історії
        reply = ai_result.get("reply", "")
        if reply:
            add_chat_history(chat_id, reply, is_user=False)
            
    except Exception as e:
        logger.error(f"Error in AI processing for {chat_id}: {e}")
        fallback_search(chat_id, text, get_menu_from_sheet())

def handle_ai_add_to_cart(chat_id, ai_result):
    """Обробляє додавання товарів до кошика через AI"""
    try:
        items_to_add = ai_result.get("items", [])
        reply = ai_result.get("reply", "Додаю до кошика...")
        
        # Відправляємо підтвердження
        tg_send_message(chat_id, reply)
        
        # Додаємо товари
        added_count = 0
        for item_data in items_to_add:
            item_id = item_data.get("id")
            quantity = item_data.get("quantity", 1)
            
            for _ in range(quantity):
                if add_item_to_cart(chat_id, item_id, quantity=1):
                    added_count += 1
        
        # Показуємо кошик якщо щось додано
        if added_count > 0:
            show_cart(chat_id)
        else:
            tg_send_message(chat_id, "Не вдалося додати товари. Перевірте наявність в меню.")
            
    except Exception as e:
        logger.error(f"Error handling AI add to cart: {e}")
        tg_send_message(chat_id, "Помилка при додаванні до кошика.")

def handle_ai_question(chat_id, ai_result):
    """Обробляє питання/поради від AI"""
    reply = ai_result.get("reply", "")
    formatted_reply = format_ai_response(ai_result)
    
    # Додаємо швидкі дії якщо це рекомендація
    keyboard = None
    if any(word in reply.lower() for word in ["рекомендую", "пораджу", "спробуйте"]):
        keyboard = {
            "inline_keyboard": [
                [{"text": "🍽️ Переглянути меню", "callback_data": "show_menu"}],
                [{"text": "💰 Підібрати за бюджетом", "callback_data": "budget_search"}]
            ]
        }
    
    tg_send_message(chat_id, formatted_reply, reply_markup=keyboard)

def handle_ai_search(chat_id, ai_result, menu_items):
    """Обробляє пошукові запити від AI"""
    query = ai_result.get("query", "").lower()
    reply = ai_result.get("reply", "Шукаю...")
    
    # Відправляємо повідомлення про пошук
    tg_send_message(chat_id, reply)
    
    # Виконуємо пошук
    found_items = [
        item for item in menu_items
        if item.get('active', True) and (
            query in item.get('name', '').lower() or
            query in item.get('category', '').lower() or
            query in item.get('description', '').lower()
        )
    ]
    
    if found_items:
        show_search_results(chat_id, found_items, query)
    else:
        suggest_alternatives(chat_id, query, menu_items)

def handle_ai_error(chat_id, ai_result):
    """Обробляє помилки AI"""
    reply = ai_result.get("reply", "Не зрозумів запит.")
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🍽️ Показати меню", "callback_data": "show_menu"}],
            [{"text": "💰 Пошук за бюджетом", "callback_data": "budget_search"}],
            [{"text": "