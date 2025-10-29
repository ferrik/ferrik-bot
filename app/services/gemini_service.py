"""
🤖 GEMINI SERVICE - з Rate Limiting
"""
import logging
from app.utils.rate_limiter import ai_rate_limiter

logger = logging.getLogger(__name__)

class GeminiService:
    def process_order_request(self, user_id: int, text: str, menu_items):
        """
        ОНОВЛЕНО: з Rate Limiting
        """
        # ПЕРЕВІРКА RATE LIMIT
        if not ai_rate_limiter.is_allowed(user_id):
            wait_time = ai_rate_limiter.get_wait_time(user_id)
            return {
                'action': 'error',
                'message': f"⏱️ Задто багато запитів! Чекайте {wait_time} сек"
            }
        
        # Звичайна обробка
        try:
            # ... існуючий код ...
            response = self.model.generate_content(prompt)
            return self._parse_ai_response(response.text, menu_items)
        
        except Exception as e:
            logger.error(f"❌ AI error: {e}")
            return {
                'action': 'error',
                'message': 'Помилка AI обробки'
            }
