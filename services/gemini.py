"""
Google Gemini AI service для отримання рекомендацій
"""

import google.generativeai as genai
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Налаштування Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_gemini_recommendation(prompt):
    """
    Отримання рекомендації від Gemini API
    
    Args:
        prompt (str): Текст запиту для AI
        
    Returns:
        str: Відповідь від AI або повідомлення про помилку
    """
    try:
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not configured")
            return "Сервіс рекомендацій тимчасово недоступний"
        
        # Створюємо модель
        model = genai.GenerativeModel('gemini-pro')
        
        # Налаштування генерації
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        # Генеруємо відповідь
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        if response.text:
            logger.info("Successfully got Gemini recommendation")
            return response.text.strip()
        else:
            logger.error("Empty response from Gemini")
            return "На жаль, не вдалося отримати рекомендацію"
            
    except Exception as e:
        logger.error(f"Error in get_gemini_recommendation: {e}")
        return "Виникла помилка при отриманні рекомендацій"

def test_gemini_connection():
    """
    Тестування з'єднання з Gemini API
    
    Returns:
        bool: True якщо з'єднання успішне, False інакше
    """
    try:
        test_prompt = "Відповідь одним словом: OK"
        response = get_gemini_recommendation(test_prompt)
        
        if response and "недоступний" not in response and "помилка" not in response.lower():
            logger.info("Gemini API connection test passed")
            return True
        else:
            logger.warning("Gemini API connection test failed")
            return False
            
    except Exception as e:
        logger.error(f"Gemini connection test error: {e}")
        return False
