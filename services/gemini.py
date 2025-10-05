import os
import logging
import google.generativeai as genai

logger = logging.getLogger("gemini_service")

_gemini_client = None
_model = None

def init_gemini_client():
    """Ініціалізація Gemini AI"""
    global _gemini_client, _model
    
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("❌ GEMINI_API_KEY not set")
            return None
        
        genai.configure(api_key=api_key)
        
        # Використовуємо безкоштовну модель
        model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.0-flash-exp")
        
        _model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 500,
            }
        )
        
        logger.info(f"✅ Gemini initialized: {model_name}")
        return _model
        
    except Exception as e:
        logger.error(f"❌ Gemini init error: {e}", exc_info=True)
        return None

def is_gemini_connected():
    """Перевірка підключення"""
    return _model is not None

def get_ai_response(prompt, max_retries=2):
    """Отримати відповідь від AI"""
    global _model
    
    if not _model:
        _model = init_gemini_client()
        if not _model:
            raise RuntimeError("Gemini not available")
    
    for attempt in range(max_retries):
        try:
            # Системний промпт для контексту
            system_prompt = """Ти - помічник ресторану Hubsy. 
Твоя мета: допомогти користувачу обрати страви.
Відповідай коротко (2-3 речення), дружньо, українською мовою.
Будь конкретним та корисним."""
            
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            response = _model.generate_content(full_prompt)
            
            if not response or not response.text:
                logger.warning(f"Empty response on attempt {attempt + 1}")
                continue
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"❌ AI error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                continue
            raise
    
    raise RuntimeError("AI failed after retries")

def analyze_user_query(query, menu_context):
    """Аналіз запиту користувача для пошуку"""
    prompt = f"""Проаналізуй запит користувача: "{query}"

Контекст меню: {menu_context}

Визнач:
1. Чи це запит про категорію їжі (піца, суші, десерти тощо)?
2. Чи це запит про конкретну страву?
3. Чи це запит про характеристики (солодке, м'ясне, вегетаріанське)?

Поверни ТІЛЬКИ одне слово - назву категорії або страви."""
    
    return get_ai_response(prompt)

def generate_recommendation(user_preferences=None, menu_items=None):
    """Генерація персональної рекомендації"""
    context = ""
    
    if user_preferences:
        context += f"Користувач часто замовляє: {user_preferences}. "
    
    if menu_items:
        context += f"Доступні страви: {', '.join(menu_items[:10])}. "
    
    prompt = f"""{context}

Порекомендуй 2-3 найкращі страви для користувача.
Поясни чому саме ці страви підійдуть.
Будь дружнім та переконливим."""
    
    return get_ai_response(prompt)

def chat_with_user(user_message, conversation_history=None):
    """Діалог з користувачем"""
    context = ""
    
    if conversation_history:
        context = "Попередні повідомлення:\n"
        for msg in conversation_history[-3:]:  # Останні 3
            context += f"- {msg}\n"
    
    prompt = f"""{context}

Користувач пише: "{user_message}"

Відповідь як помічник ресторану (коротко, дружньо):"""
    
    return get_ai_response(prompt)