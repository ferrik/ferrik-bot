import requests
import json
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

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
        
        # URL для Gemini API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        
        # Заголовки запиту
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Тіло запиту
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        # Відправка запиту
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            # Перевірка на наявність відповіді
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    text = candidate['content']['parts'][0].get('text', '')
                    if text:
                        logger.info("Successfully got Gemini recommendation")
                        return text.strip()
            
            logger.error(f"Unexpected Gemini response structure: {result}")
            return "На жаль, не вдалося отримати рекомендацію"
            
        else:
            logger.error(f"Gemini API error {response.status_code}: {response.text}")
            return "Сервіс рекомендацій тимчасово недоступний"
            
    except requests.exceptions.Timeout:
        logger.error("Gemini API timeout")
        return "Час очікування відповіді минув, спробуйте пізніше"
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API request error: {e}")
        return "Помилка з'єднання з сервісом рекомендацій"
        
    except Exception as e:
        logger.error(f"Unexpected error in get_gemini_recommendation: {e}")
        return "Виникла несподівана помилка"

def test_gemini_connection():
    """
    Тестування з'єднання з Gemini API
    
    Returns:
        bool: True якщо з'єднання успішне, False інакше
    """
    try:
        test_prompt = "Привіт! Це тест. Відповідь одним словом: OK"
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