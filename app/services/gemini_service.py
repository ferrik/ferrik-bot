"""
🤖 Сервіс для роботи з Gemini AI
"""
import json
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from app.utils.validators import safe_parse_price, safe_parse_quantity

logger = logging.getLogger(__name__)


class GeminiService:
    """Сервіс для роботи з Gemini AI"""
    
    def __init__(self, config):
        """
        Ініціалізація сервісу
        
        Args:
            config: GeminiConfig з API key та налаштуваннями
        """
        self.config = config
        self.model = None
        
        self._initialize()
    
    def _initialize(self):
        """Ініціалізація Gemini API"""
        try:
            # Налаштування API
            genai.configure(api_key=self.config.api_key)
            
            # Створюємо модель
            self.model = genai.GenerativeModel(
                model_name=self.config.model_name,
                generation_config={
                    'temperature': self.config.temperature,
                    'max_output_tokens': self.config.max_tokens,
                }
            )
            
            logger.info(f"✅ Gemini AI initialized: {self.config.model_name}")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini AI: {e}")
            raise
    
    # ========================================================================
    # Обробка замовлень
    # ========================================================================
    
    def process_order_request(
        self,
        user_message: str,
        menu_items: List[Dict[str, Any]],
        user_cart: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Обробити запит користувача через AI
        
        Args:
            user_message: Повідомлення користувача
            menu_items: Доступні товари з меню
            user_cart: Поточний кошик користувача
        
        Returns:
            dict: {
                'action': 'add_to_cart' | 'show_menu' | 'checkout' | 'info',
                'items': [...],
                'message': 'Відповідь для користувача'
            }
        """
        try:
            # Формуємо промпт
            prompt = self._build_order_prompt(user_message, menu_items, user_cart)
            
            # Відправляємо запит до AI
            response = self.model.generate_content(prompt)
            
            # Парсимо відповідь
            result = self._parse_ai_response(response.text, menu_items)
            
            logger.info(f"🤖 AI processed request: action={result.get('action')}")
            return result
        
        except Exception as e:
            logger.error(f"❌ Error processing AI request: {e}")
            return {
                'action': 'info',
                'message': 'Вибачте, виникла помилка. Спробуйте використати команди /menu або /help'
            }
    
    def _build_order_prompt(
        self,
        user_message: str,
        menu_items: List[Dict[str, Any]],
        user_cart: List[Dict[str, Any]]
    ) -> str:
        """Побудова промпту для AI"""
        
        # Форматуємо меню
        menu_text = "ДОСТУПНЕ МЕНЮ:\n"
        for item in menu_items:
            menu_text += f"- {item['name']} ({item['category']}) - {item['price']} грн"
            if item.get('description'):
                menu_text += f" | {item['description']}"
            menu_text += "\n"
        
        # Форматуємо кошик
        cart_text = "ПОТОЧНИЙ КОШИК:\n"
        if user_cart:
            for item in user_cart:
                cart_text += f"- {item['name']} x{item.get('quantity', 1)}\n"
        else:
            cart_text += "Порожній\n"
        
        prompt = f"""Ти - асистент для замовлення їжі в ресторані FerrikFoot.

{menu_text}

{cart_text}

ПОВІДОМЛЕННЯ КОРИСТУВАЧА: "{user_message}"

ТВОЄ ЗАВДАННЯ:
1. Проаналізувати запит користувача
2. Визначити намір (додати товар, переглянути меню, оформити замовлення, тощо)
3. Знайти відповідні товари з меню (якщо користувач хоче щось замовити)
4. Відповісти у форматі JSON

ФОРМАТ ВІДПОВІДІ (ОБОВ'ЯЗКОВО JSON):
{{
    "action": "add_to_cart" або "show_menu" або "checkout" або "info",
    "items": [
        {{"id": "ID_товару", "name": "Назва", "price": ціна, "quantity": кількість}}
    ],
    "message": "Дружня відповідь українською"
}}

ПРАВИЛА:
- action="add_to_cart" - якщо користувач хоче замовити конкретні страви
- action="show_menu" - якщо користувач хоче побачити меню
- action="checkout" - якщо користувач хоче оформити замовлення
- action="info" - для загальних питань
- Шукай товари за частковими збігами назв
- Якщо товар не знайдено, пропонуй схожі
- Завжди будь ввічливим та допомагай

ВІДПОВІДАЙ ТІЛЬКИ В ФОРМАТІ JSON, БЕЗ ДОДАТКОВОГО ТЕКСТУ!"""
        
        return prompt
    
    def _parse_ai_response(
        self,
        ai_text: str,
        menu_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Парсинг відповіді AI"""
        
        try:
            # Очищуємо відповідь від markdown
            clean_text = ai_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.startswith('```'):
                clean_text = clean_text[3:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Парсимо JSON
            result = json.loads(clean_text)
            
            # Валідація та доповнення даних товарів
            if result.get('action') == 'add_to_cart' and result.get('items'):
                validated_items = []
                
                for item in result['items']:
                    # Шукаємо товар в меню
                    menu_item = None
                    item_id = item.get('id')
                    item_name = item.get('name', '').lower()
                    
                    for menu in menu_items:
                        if (str(menu['id']) == str(item_id) or 
                            menu['name'].lower() == item_name):
                            menu_item = menu
                            break
                    
                    if menu_item:
                        validated_items.append({
                            'id': menu_item['id'],
                            'name': menu_item['name'],
                            'price': menu_item['price'],
                            'quantity': safe_parse_quantity(item.get('quantity', 1))
                        })
                
                result['items'] = validated_items
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse AI JSON: {e}\nText: {ai_text}")
            
            # Fallback відповідь
            return {
                'action': 'info',
                'message': ai_text if len(ai_text) < 500 else 'Не зрозумів запит. Спробуйте /menu або /help'
            }
    
    # ========================================================================
    # Допоміжні методи
    # ========================================================================
    
    def generate_response(self, prompt: str) -> str:
        """
        Генерація загальної відповіді
        
        Args:
            prompt: Промпт для AI
        
        Returns:
            str: Відповідь AI
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return "Вибачте, виникла помилка при генерації відповіді."
    
    def suggest_items(
        self,
        query: str,
        menu_items: List[Dict[str, Any]],
        max_suggestions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Підказати товари на основі запиту
        
        Args:
            query: Пошуковий запит
            menu_items: Доступні товари
            max_suggestions: Максимальна кількість підказок
        
        Returns:
            list: Рекомендовані товари
        """
        try:
            menu_text = "\n".join([
                f"{item['name']} - {item['category']} - {item['price']} грн"
                for item in menu_items
            ])
            
            prompt = f"""З наступного меню:

{menu_text}

Запит користувача: "{query}"

Порекомендуй {max_suggestions} найбільш підходящих товарів.
Відповідай у форматі JSON:
{{
    "suggestions": [
        {{"id": "...", "name": "...", "reason": "..."}}
    ]
}}"""
            
            response = self.model.generate_content(prompt)
            result = json.loads(response.text.strip('```json\n').strip('```'))
            
            # Знаходимо повні дані товарів
            suggestions = []
            for sugg in result.get('suggestions', []):
                for item in menu_items:
                    if item['id'] == sugg['id'] or item['name'] == sugg['name']:
                        suggestions.append(item)
                        break
            
            return suggestions[:max_suggestions]
        
        except Exception as e:
            logger.error(f"❌ Error suggesting items: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Тест підключення до Gemini API"""
        try:
            response = self.model.generate_content("Привіт! Скажи 'OK' якщо ти працюєш.")
            logger.info(f"✅ Gemini test successful: {response.text[:50]}")
            return True
        except Exception as e:
            logger.error(f"❌ Gemini test failed: {e}")
            return False


# ============================================================================
# Debugging
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTING GEMINI SERVICE")
    print("=" * 60)
    
    print("\nThis module requires proper configuration to test.")
    print("Use it within the application context.")
