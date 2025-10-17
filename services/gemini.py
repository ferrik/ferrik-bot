"""
Gemini AI Service
Інтеграція з Google Gemini API для AI пошуку

Виправлення:
- Санітизація user input
- Кращa обробка помилок
- Fallback механізм
"""

import logging
import requests
from typing import List, Dict, Any, Optional

import config
from utils.html_formatter import sanitize_user_input

logger = logging.getLogger(__name__)

# Gemini API endpoint
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

def get_ai_response(query: str, menu: List[Dict[str, Any]]) -> Optional[str]:
    """
    Отримує відповідь від Gemini AI
    
    Args:
        query: Запит користувача
        menu: Список товарів меню
    
    Returns:
        Відповідь AI або None
    """
    if not config.GEMINI_API_KEY:
        logger.warning("Gemini API key not configured")
        return None
    
    # Санітизація запиту
    clean_query = sanitize_user_input(query)
    
    if not clean_query:
        return None
    
    try:
        # Формуємо prompt
        menu_text = "\n".join([
            f"- {item.get('Назва Страви', 'N/A')}: {item.get('Опис', 'Без опису')}"
            for item in menu[:50]  # Обмежуємо кількість для context
        ])
        
        prompt = f"""Ти асистент ресторану. Допоможи клієнту знайти страву з меню.

Меню:
{menu_text}

Запит клієнта: {clean_query}

Дай коротку відповідь (2-3 речення) та порекомендуй конкретні страви з меню."""
        
        # API request
        headers = {
            'Content-Type': 'application/json',
        }
        
        payload = {
            'contents': [{
                'parts': [{'text': prompt}]
            }]
        }
        
        response = requests.post(
            f"{GEMINI_API_URL}?key={config.GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Парсимо відповідь
        if 'candidates' in result and len(result['candidates']) > 0:
            text = result['candidates'][0]['content']['parts'][0]['text']
            return text
        
        return None
        
    except requests.exceptions.Timeout:
        logger.error("Gemini API timeout")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in AI response: {e}")
        return None


def search_menu(query: str, menu: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Пошук страв в меню за допомогою AI або fallback до простого пошуку
    
    Args:
        query: Пошуковий запит
        menu: Список товарів
    
    Returns:
        List відфільтрованих items
    """
    # Санітизація
    clean_query = sanitize_user_input(query).lower()
    
    if not clean_query:
        return []
    
    results = []
    
    # Спочатку пробуємо простий пошук (завжди працює)
    for item in menu:
        name = (item.get('Назва Страви', '') or '').lower()
        description = (item.get('Опис', '') or '').lower()
        category = (item.get('Категорія', '') or '').lower()
        
        if (clean_query in name or 
            clean_query in description or 
            clean_query in category):
            results.append(item)
    
    # Якщо знайдено через простий пошук - повертаємо
    if results:
        logger.info(f"Simple search found {len(results)} items for '{query}'")
        return results
    
    # Якщо нічого не знайдено - пробуємо AI (якщо доступний)
    if config.GEMINI_API_KEY:
        try:
            logger.info(f"Trying AI search for '{query}'")
            ai_response = get_ai_response(query, menu)
            
            if ai_response:
                # AI повертає текст з рекомендаціями
                # Пробуємо витягти назви страв з відповіді
                results = extract_items_from_ai_response(ai_response, menu)
                
                if results:
                    logger.info(f"AI search found {len(results)} items")
                    return results
        except Exception as e:
            logger.error(f"AI search failed: {e}")
    
    # Якщо все не спрацювало - повертаємо порожній список
    logger.info(f"No results found for '{query}'")
    return []


def extract_items_from_ai_response(ai_text: str, menu: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Витягує items з AI відповіді
    
    Args:
        ai_text: Текст відповіді AI
        menu: Повне меню
    
    Returns:
        List знайдених items
    """
    results = []
    ai_text_lower = ai_text.lower()
    
    # Шукаємо згадки страв з меню в AI відповіді
    for item in menu:
        name = (item.get('Назва Страви', '') or '').lower()
        
        if name and name in ai_text_lower:
            results.append(item)
    
    return results


def get_ai_recommendation(user_preferences: Dict[str, Any], menu: List[Dict[str, Any]]) -> Optional[str]:
    """
    Отримує AI рекомендації на основі вподобань користувача
    
    Args:
        user_preferences: Словник з вподобаннями (вегетаріанство, алергії, etc)
        menu: Список товарів
    
    Returns:
        Текст рекомендації
    """
    if not config.GEMINI_API_KEY:
        return None
    
    try:
        # Формуємо промпт з вподобаннями
        prefs_text = ", ".join([f"{k}: {v}" for k, v in user_preferences.items()])
        
        menu_text = "\n".join([
            f"- {item.get('Назва Страви')}: {item.get('Опис', 'Без опису')}"
            for item in menu[:30]
        ])
        
        prompt = f"""Ти дієтолог ресторану. Допоможи клієнту вибрати страву.

Вподобання клієнта: {prefs_text}

Меню:
{menu_text}

Порекомендуй 2-3 страви які найкраще підходять клієнту та коротко поясни чому."""
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            'contents': [{
                'parts': [{'text': prompt}]
            }]
        }
        
        response = requests.post(
            f"{GEMINI_API_URL}?key={config.GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and len(result['candidates']) > 0:
            return result['candidates'][0]['content']['parts'][0]['text']
        
        return None
        
    except Exception as e:
        logger.error(f"AI recommendation failed: {e}")
        return None


def test_gemini_connection() -> bool:
    """
    Тестує з'єднання з Gemini API
    
    Returns:
        True якщо API доступний
    """
    if not config.GEMINI_API_KEY:
        logger.warning("Gemini API key not configured")
        return False
    
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {
            'contents': [{
                'parts': [{'text': 'Test connection'}]
            }]
        }
        
        response = requests.post(
            f"{GEMINI_API_URL}?key={config.GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("✅ Gemini API connection OK")
            return True
        else:
            logger.error(f"❌ Gemini API returned {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Gemini API connection failed: {e}")
        return False


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    'get_ai_response',
    'search_menu',
    'get_ai_recommendation',
    'test_gemini_connection',
]
