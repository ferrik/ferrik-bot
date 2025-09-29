import logging
import os
from services.sheets import get_menu_from_sheet

logger = logging.getLogger("ferrik")
logging.basicConfig(level=logging.INFO)

try:
    import google.generativeai as genai
except ImportError:
    logger.warning("Google Generative AI module not found. AI recommendations will be disabled.")
    genai = None

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-1.5-flash")
ENABLE_AI_RECOMMENDATIONS = os.environ.get("ENABLE_AI_RECOMMENDATIONS", "true").lower() == "true"

def init_gemini_client():
    """Ініціалізація клієнта Gemini."""
    if not genai or not ENABLE_AI_RECOMMENDATIONS:
        logger.warning("Gemini client initialization skipped: genai module or ENABLE_AI_RECOMMENDATIONS not set")
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logger.info(f"Gemini client initialized. Using model: {GEMINI_MODEL_NAME}")
        return model
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        return None

def get_gemini_recommendation(user_input: str, chat_history: list):
    """Отримує рекомендацію від Gemini на основі вводу користувача та історії чату."""
    if not ENABLE_AI_RECOMMENDATIONS:
        logger.info("AI recommendations are disabled")
        return "Рекомендації AI відключені. Будь ласка, виберіть категорію з меню."

    gemini_client = init_gemini_client()
    if not gemini_client:
        logger.error("Cannot generate recommendation: Gemini client not initialized")
        return "Вибачте, рекомендації AI недоступні. Спробуйте ще раз пізніше."

    try:
        # Отримуємо меню з Google Sheets
        menu = get_menu_from_sheet()
        if not menu:
            logger.warning("No menu items available for recommendation")
            # Промпт для порожнього меню
            prompt = f"""
            Ви - дружній помічник у ресторані FerrikFootBot, який допомагає клієнтам вибрати смачну їжу. 
            На жаль, меню зараз недоступне, але ви можете запропонувати популярні категорії страв.

            Історія чату (останні 5 повідомлень):
            { "\n".join([f"{msg['role']}: {msg['text']}" for msg in chat_history[-5:]]) }

            Запит користувача: {user_input}

            Запропонуйте 1-2 популярні категорії страв (наприклад, піца, бургери, суші) або загальну рекомендацію, яка відповідає запиту.
            Відповідь має бути короткою (1-2 речення), українською мовою, у дружньому та апетитному стилі ресторану.
            Наприклад: "Як щодо соковитого бургера чи хрусткої піци? 🍔🍕"
            """
        else:
            # Формуємо список страв для Gemini
            menu_items = [f"{item['name']} ({item['category']}, {item['price']} грн): {item['description']}" for item in menu.values()]
            menu_text = "\n".join(menu_items)

            # Формуємо історію чату для контексту
            history_text = "\n".join([f"{msg['role']}: {msg['text']}" for msg in chat_history[-5:]])

            prompt = f"""
            Ви - дружній помічник у ресторані FerrikFootBot, який допомагає клієнтам вибрати смачну їжу з меню.
            Ваша мета - запропонувати одну страву або категорію, яка відповідає запиту користувача, у неформальному, апетитному стилі.

            Доступне меню:
            {menu_text}

            Історія чату (останні 5 повідомлень):
            {history_text}

            Запит користувача: {user_input}

            Запропонуйте одну страву або категорію з меню, яка найкраще відповідає запиту.
            Якщо запит нечіткий (наприклад, "Що поїсти?"), виберіть популярну страву чи категорію (наприклад, піцу чи бургери).
            Якщо користувач згадує алергени (наприклад, "без глютену"), врахуйте це, використовуючи поле алергенів із меню.
            Відповідь має бути короткою (1-2 речення), українською мовою, у дружньому та апетитному стилі ресторану.
            Наприклад: "Спробуй нашу Маргариту – класична піца з томатами та моцарелою! 🍕"
            """
        
        response = gemini_client.generate_content(prompt)
        recommendation = response.text.strip()

        logger.info(f"Generated recommendation for user input '{user_input}': {recommendation}")
        return recommendation
    except Exception as e:
        logger.error(f"Error in get_gemini_recommendation: {str(e)}")
        return "Вибачте, виникла помилка при генерації рекомендації. Спробуйте ще раз."