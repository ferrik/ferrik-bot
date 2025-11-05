"""
Gemini AI Integration
Інтеграція з Google Gemini для розумного пошуку та рекомендацій
"""
import logging
from typing import List, Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

# Перевірка наявності Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    
    if config.GEMINI_API_KEY:
        genai.configure(api_key=config.GEMINI_API_KEY)
        logger.info("✅ Gemini AI configured")
    else:
        logger.warning("⚠️ GEMINI_API_KEY not set")
        GEMINI_AVAILABLE = False
        
except ImportError:
    logger.error("❌ google-generativeai not installed")
    GEMINI_AVAILABLE = False


def search_menu(query: str, menu_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Розумний пошук у меню через AI
    
    Args:
        query: Запит користувача (напр. "щось солодке", "м'ясне")
        menu_data: Список страв з меню
    
    Returns:
        list: Знайдені страви
    """
    if not GEMINI_AVAILABLE or not menu_data:
        # Fallback: простий пошук по назві
        return simple_search(query, menu_data)
    
    try:
        # Формуємо промпт для AI
        menu_text = "\n".join([
            f"{i+1}. {item.get('Страви', item.get('Назва Страви', 'N/A'))} - "
            f"{item.get('Опис', '')} ({item.get('Ціна', 0)} грн)"
            for i, item in enumerate(menu_data[:30])  # Лімітуємо 30 страв
        ])
        
        prompt = f"""Ти асистент для пошуку страв у ресторані.

МЕНЮ:
{menu_text}

ЗАПИТ: "{query}"

Знайди 3-5 страв з меню, які найбільше підходять під запит.
Відповідай ТІЛЬКИ номерами страв через кому (наприклад: 1, 5, 12).
Якщо нічого не підходить, відповідай: НІЧОГО"""
        
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        
        # Парсинг відповіді
        answer = response.text.strip()
        
        if "НІЧОГО" in answer.upper():
            return []
        
        # Витягуємо номери
        indices = []
        for part in answer.split(','):
            try:
                idx = int(part.strip()) - 1  # -1 бо AI рахує з 1
                if 0 <= idx < len(menu_data):
                    indices.append(idx)
            except ValueError:
                continue
        
        # Повертаємо знайдені страви
        results = [menu_data[i] for i in indices[:5]]  # Максимум 5
        
        logger.info(f"✅ AI search: '{query}' → {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"❌ AI search failed: {e}")
        return simple_search(query, menu_data)


def simple_search(query: str, menu_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Простий пошук по назві (fallback)
    
    Args:
        query: Запит користувача
        menu_data: Список страв
    
    Returns:
        list: Знайдені страви
    """
    query_lower = query.lower()
    results = []
    
    for item in menu_data:
        name = item.get('Страви', item.get('Назва Страви', '')).lower()
        description = item.get('Опис', '').lower()
        category = item.get('Категорія', '').lower()
        
        if (query_lower in name or 
            query_lower in description or 
            query_lower in category):
            results.append(item)
    
    logger.info(f"✅ Simple search: '{query}' → {len(results)} results")
    return results[:5]  # Максимум 5


def get_ai_response(query: str, menu_data: List[Dict[str, Any]]) -> Optional[str]:
    """
    Отримати AI коментар/пораду
    
    Args:
        query: Запит користувача
        menu_data: Список страв
    
    Returns:
        str: Відповідь AI або None
    """
    if not GEMINI_AVAILABLE:
        return None
    
    try:
        # Формуємо контекст
        menu_categories = set()
        for item in menu_data:
            cat = item.get('Категорія', 'Інше')
            menu_categories.add(cat)
        
        categories_text = ", ".join(menu_categories)
        
        prompt = f"""Ти дружній асистент ресторану в Тернополі.

ДОСТУПНІ КАТЕГОРІЇ: {categories_text}

ЗАПИТ КОРИСТУВАЧА: "{query}"

Дай коротку (2-3 речення) пораду або коментар українською мовою.
Будь дружнім та корисним. Використовуй емодзі 😊"""
        
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        
        answer = response.text.strip()
        logger.info(f"✅ AI response generated")
        
        return answer
        
    except Exception as e:
        logger.error(f"❌ AI response failed: {e}")
        return None


def get_recommendation(
    user_preferences: Dict[str, Any],
    menu_data: List[Dict[str, Any]],
    count: int = 3
) -> List[Dict[str, Any]]:
    """
    Отримати персональні рекомендації
    
    Args:
        user_preferences: Уподобання користувача
        menu_data: Список страв
        count: Кількість рекомендацій
    
    Returns:
        list: Рекомендовані страви
    """
    if not GEMINI_AVAILABLE or not menu_data:
        # Fallback: повертаємо популярні
        return menu_data[:count]
    
    try:
        # Формуємо промпт
        menu_text = "\n".join([
            f"{i+1}. {item.get('Страви', 'N/A')} - "
            f"{item.get('Опис', '')} ({item.get('Ціна', 0)} грн, "
            f"{item.get('Категорія', 'Інше')})"
            for i, item in enumerate(menu_data[:30])
        ])
        
        people = user_preferences.get('people', 1)
        budget = user_preferences.get('budget', 'не вказано')
        cuisine = user_preferences.get('cuisine', 'будь-яка')
        
        prompt = f"""Ти асистент ресторану. Порадь страви з меню.

МЕНЮ:
{menu_text}

ПОБАЖАННЯ:
- Кількість людей: {people}
- Бюджет: {budget}
- Кухня: {cuisine}

Порадь {count} страви з меню які найбільше підходять.
Відповідай ТІЛЬКИ номерами через кому (наприклад: 1, 5, 12)."""
        
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        
        answer = response.text.strip()
        
        # Парсинг номерів
        indices = []
        for part in answer.split(','):
            try:
                idx = int(part.strip()) - 1
                if 0 <= idx < len(menu_data):
                    indices.append(idx)
            except ValueError:
                continue
        
        results = [menu_data[i] for i in indices[:count]]
        
        if not results:
            # Fallback
            results = menu_data[:count]
        
        logger.info(f"✅ Recommendations: {len(results)} items")
        return results
        
    except Exception as e:
        logger.error(f"❌ Recommendations failed: {e}")
        return menu_data[:count]


def test_gemini_connection() -> bool:
    """
    Тест підключення до Gemini
    
    Returns:
        bool: True якщо працює
    """
    if not GEMINI_AVAILABLE:
        logger.warning("⚠️ Gemini not available")
        return False
    
    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = model.generate_content("Скажи 'OK' якщо працює")
        
        answer = response.text.strip()
        logger.info(f"✅ Gemini test: {answer}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Gemini test failed: {e}")
        return False


# Тестування при імпорті
if __name__ == "__main__":
    print("🧪 Testing Gemini service...")
    if test_gemini_connection():
        print("✅ Gemini connection OK")
    else:
        print("❌ Gemini connection FAILED")
