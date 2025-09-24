import os
import logging
import json
import google.generativeai as genai

logger = logging.getLogger("ferrik.gemini")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Ініціалізуємо Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API Key configured successfully.")
else:
    logger.warning("Gemini API Key not found. AI features will be disabled.")

# Системний промпт для Ukrainian food bot
SYSTEM_PROMPT = """
Ти — дружній український асистент для Telegram food-бота FerrikFootBot. 

Твої завдання:
- Допомагати з вибором страв і підбором по бюджету
- Аналізувати запити користувачів і визначати їхні наміри
- Давати корисні поради про їжу
- Відповідати українською мовою

Правила:
- Пиши українською, простими реченнями
- Додавай емодзі, але не переборщуй
- Відповідай стисло та по суті
- Пропонуй 2-4 варіанти при пораді
- Використовуй тільки страви з переданого меню
- Не вигадуй ціни чи наявність товарів
- Повертай результат у форматі JSON
"""

def analyze_user_request_with_gemini(user_text, menu_items):
    """
    Аналізує запит користувача за допомогою Gemini AI
    Повертає JSON з дією та рекомендаціями
    """
    if not GEMINI_API_KEY:
        logger.warning("Gemini API not configured, returning fallback response.")
        return {
            "action": "question",
            "reply": "Вибачте, AI-рекомендації тимчасово недоступні. Скористайтеся меню для вибору страв."
        }

    try:
        # Підготовка даних меню для промпту
        menu_for_prompt = "\n".join([
            f"ID: {item.get('ID')}, Назва: {item.get('name')}, Ціна: {item.get('price'):.2f}, Категорія: {item.get('category')}"
            for item in menu_items if item.get('active', True)
        ])

        # Формуємо повний промпт
        full_prompt = f"""
{SYSTEM_PROMPT}

Проаналізуй запит користувача і поверни результат у форматі JSON.

Запит користувача: "{user_text}"

Доступне меню:
---
{menu_for_prompt}
---

Твоє завдання - визначити намір користувача і повернути ОДНУ з дій у JSON:

1. "add_to_cart": якщо користувач хоче додати щось у кошик
   Формат: {{"action": "add_to_cart", "items": [{{"id": "ID_товару", "quantity": кількість}}], "reply": "текст підтвердження"}}

2. "question": якщо це прохання поради, пошук за бюджетом, загальне питання
   Формат: {{"action": "question", "reply": "детальна відповідь з рекомендаціями"}}

3. "search": якщо користувач шукає конкретну страву або категорію
   Формат: {{"action": "search", "query": "пошуковий запит", "reply": "пояснення пошуку"}}

4. "error": якщо запит незрозумілий
   Формат: {{"action": "error", "reply": "вибачення та пропозиція допомоги"}}

Приклади:

# Замовлення
Запит: "дві піци маргарита"
JSON: {{"action": "add_to_cart", "items": [{{"id": "PZ001", "quantity": 2}}], "reply": "Додаю 2 піци Маргарита до кошика!"}}

# Порада за бюджетом  
Запит: "що можна взяти на 300 грн?"
JSON: {{"action": "question", "reply": "На 300 грн рекомендую: Піцу Маргарита (150 грн) + салат Цезар (130 грн) = 280 грн. Залишиться ще 20 грн на напій!"}}

# Пошук
Запит: "є суші?"
JSON: {{"action": "search", "query": "суші", "reply": "Шукаю суші в нашому меню..."}}

# Загальне питання
Запит: "що найсмачніше?"
JSON: {{"action": "question", "reply": "За рейтингом найпопулярніші: Філадельфія (4.8/5) та Пепероні (4.7/5). Що більше до вподоби - суші чи піца?"}}

Тепер проаналізуй запит: "{user_text}" і поверни ТІЛЬКИ JSON без додаткового тексту.
"""

        # Викликаємо Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=400,
            temperature=0.7,
            response_mime_type="application/json"
        )
        
        response = model.generate_content(full_prompt, generation_config=generation_config)
        
        # Очищуємо та парсимо відповідь
        cleaned_response = response.text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
        
        logger.info(f"Gemini response: {cleaned_response}")
        return json.loads(cleaned_response)
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
        return {
            "action": "error", 
            "reply": "Вибачте, сталася помилка при обробці запиту. Спробуйте переформулювати."
        }
    except Exception as e:
        logger.error(f"Gemini request failed: {e}")
        return {
            "action": "question",
            "reply": "Не зовсім зрозумів ваш запит. Можете обрати категорію з меню або уточнити, що саме шукаєте?"
        }

def get_budget_recommendations(budget, menu_items):
    """Отримує рекомендації за бюджетом користувача"""
    try:
        budget_float = float(str(budget).replace(',', '.'))
        
        suitable_items = [
            item for item in menu_items 
            if item.get('active', True) and item.get('price', 0) <= budget_float
        ]
        
        if not suitable_items:
            return f"На жаль, немає страв у бюджеті до {budget_float:.0f} грн. Наша найдешевша позиція коштує {min(item.get('price', 999) for item in menu_items if item.get('active')):.0f} грн."
        
        # Сортуємо за рейтингом та ціною
        suitable_items.sort(key=lambda x: (-float(x.get('rating', 0)), x.get('price', 0)))
        
        recommendations = []
        for item in suitable_items[:5]:  # Топ 5
            recommendations.append(
                f"• {item.get('name')} - {item.get('price'):.0f} грн"
                + (f" ⭐{item.get('rating')}" if item.get('rating') else "")
            )
        
        return f"У вашому бюджеті {budget_float:.0f} грн знайшов {len(suitable_items)} варіантів:\n\n" + "\n".join(recommendations)
        
    except (ValueError, TypeError):
        return "Будь ласка, вкажіть бюджет числом (наприклад: 200)."

def get_category_recommendations(category, menu_items):
    """Отримує рекомендації за категорією"""
    category_items = [
        item for item in menu_items 
        if item.get('active', True) and 
        category.lower() in item.get('category', '').lower()
    ]
    
    if not category_items:
        available_categories = list(set(item.get('category') for item in menu_items if item.get('active')))
        return f"Категорія '{category}' не знайдена. Доступні категорії: {', '.join(available_categories)}"
    
    # Топ-3 за рейтингом
    category_items.sort(key=lambda x: -float(x.get('rating', 0)))
    
    recommendations = []
    for item in category_items[:3]:
        recommendations.append(
            f"🔹 {item.get('name')} - {item.get('price'):.0f} грн"
            + (f" ⭐{item.get('rating')}" if item.get('rating') else "")
            + (f"\n   {item.get('description')[:50]}..." if item.get('description') else "")
        )
    
    return f"Найкращі позиції в категорії '{category}':\n\n" + "\n\n".join(recommendations)

def get_gemini_recommendation(query):
    """Базова функція для отримання рекомендацій (для сумісності)"""
    simple_response = analyze_user_request_with_gemini(query, [])
    return simple_response.get("reply", "Вибачте, не можу обробити запит.")

def format_ai_response(ai_result):
    """Форматує відповідь AI для відправки користувачу"""
    if not ai_result:
        return "Вибачте, сталася помилка при обробці запиту."
    
    action = ai_result.get("action")
    reply = ai_result.get("reply", "")
    
    # Додаємо контекстну інформацію залежно від дії
    if action == "add_to_cart":
        return f"🛒 {reply}"
    elif action == "question":
        return f"💡 {reply}"
    elif action == "search":
        return f"🔍 {reply}"
    elif action == "error":
        return f"❓ {reply}"
    else:
        return reply