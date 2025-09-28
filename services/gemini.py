import os
import logging
import json
import google.generativeai as genai  # Виправлено імпорт
from config import GEMINI_API_KEY, GEMINI_MODEL_NAME, ENABLE_AI_RECOMMENDATIONS, ERROR_MESSAGES
from services.sheets import get_menu_from_sheet 

logger = logging.getLogger("ferrik")
client = None

# --- Configuration for System Instruction ---
SYSTEM_INSTRUCTION = (
    "Ти є чат-ботом для кафе. Твоє ім'я FerrikFootBot. "
    "Твоя головна мета — допомагати клієнтам, надаючи інформацію про меню та відповідаючи на їхні запитання. "
    "Дотримуйся наступних інструкцій:\n"
    "1. Завжди відповідай українською мовою.\n"
    "2. Відповідай дружньо, доброзичливо та інформативно.\n"
    "3. Усі відповіді мають ґрунтуватися виключно на наданому МЕНЮ.\n"
    "4. Якщо не знаєш відповіді — чесно повідомляй.\n"
    "5. Якщо питання «не по темі» — відповідай: \"Вибачте, я можу допомогти лише з питаннями щодо нашого меню. Чим можу вас почастувати?\"\n"
    "6. Використовуй історію розмови для персоналізації.\n"
    "7. Якщо клієнт щось обрав, можеш порадити додаткову страву чи напій.\n"
    "8. Виділяй **назви страв** і **ціни** для кращої читабельності.\n"
    "9. Якщо клієнт просить категорію (наприклад, десерти, напої), показуй лише відповідні страви з меню."
)

def init_gemini_client():
    """Ініціалізація клієнта Gemini API."""
    global client
    if not ENABLE_AI_RECOMMENDATIONS:
        logger.warning("AI recommendations disabled")
        return False
        
    if client is None and GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)  # Налаштування API ключа
            client = genai  # Використовуємо модуль як клієнт
            logger.info(f"✅ Gemini client initialized. Using model: {GEMINI_MODEL_NAME}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client or model '{GEMINI_MODEL_NAME}': {e}")
            return False
    
    return client is not None

def get_gemini_recommendation(user_prompt: str, chat_history: list = None) -> str:
    """
    Надсилає запит до Gemini API для отримання рекомендації або відповіді,
    використовуючи актуальне меню та історію чату.
    
    :param user_prompt: Запит користувача.
    :param chat_history: Історія розмови (список об'єктів {role: str, text: str}).
    :return: Сгенерований текст або повідомлення про помилку.
    """
    if not ENABLE_AI_RECOMMENDATIONS or not init_gemini_client():
        return ERROR_MESSAGES['ai_unavailable']

    try:
        # 1. Отримуємо актуальне меню 
        menu_items = get_menu_from_sheet(force=False)
        menu_cache_json = json.dumps(menu_items, ensure_ascii=False, indent=2)

        # 2. Формуємо історію розмови
        chat_history_str = ""
        if chat_history:
            chat_history_str = "\n".join([f"{h.get('role', 'User')}: {h.get('text', '')}" for h in chat_history])

        # 3. Формуємо фінальний промпт для моделі
        full_prompt = (
            f"Контекст:\nОсь наше актуальне меню у форматі JSON. Використовуй цю інформацію для відповідей:\n{menu_cache_json}\n\n"
            f"Це історія нашої розмови (від найстарішого до найновішого):\n{chat_history_str}\n\n"
            f"Запит клієнта: {user_prompt}"
        )
        
        # Налаштування генерації
        model = client.GenerativeModel(
            model_name=GEMINI_MODEL_NAME,
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        # Виклик API
        response = model.generate_content(
            contents=full_prompt,
            generation_config={
                "temperature": 0.7
            }
        )

        return response.text

    except Exception as e:
        logger.error(f"❌ Error in get_gemini_recommendation: {e}")
        return ERROR_MESSAGES['ai_unavailable']