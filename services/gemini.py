import os
import logging
import google.generativeai as genai

logger = logging.getLogger("ferrik")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def get_gemini_recommendation(query):
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, cannot provide AI recommendation.")
        return "Вибачте, рекомендації AI тимчасово недоступні. 😔"

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Дай коротку рекомендацію страви на основі запиту: {query}")
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "Вибачте, сталася помилка при отриманні рекомендації. 😔"
