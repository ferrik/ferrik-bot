"""
🤖 GEMINI SERVICE - Google AI Integration
Повний файл, готовий до використання на GitHub
"""
import json
import logging
import time
from typing import List, Dict, Any, Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Сервіс для роботи з Google Gemini AI
    
    Функціонал:
    - Обробка природних запитів користувачів
    - Розпізнавання наміру (замовлення/меню/інше)
    - Рекомендації товарів
    - Пошук по меню
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Ініціалізація Gemini сервісу
        
        Args:
            api_key: API ключ від Google AI Studio
            model_name: Назва моделі (gemini-1.5-flash рекомендована)
        """
        self.api_key = api_key
        self.model_name = model_name
        self.model = None
        self.last_request_time = {}  # Для rate limiting
        
        logger.info(f"🤖 Initializing Gemini Service: {model_name}")
        
        if not api_key:
            logger.error("❌ GEMINI_API_KEY not provided!")
            raise ValueError("GEMINI_API_KEY is required")
        
        self._initialize()
    
    def _initialize(self):
        """Ініціалізація API"""
        try:
            if not genai:
                logger.error("❌ google-generativeai not installed!")
                raise ImportError("google-generativeai is required")
            
            # Налаштування API
            genai.configure(api_key=self.api_key)
            
            # Створення моделі
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 1000,
                    'top_p': 0.95,
                    'top_k': 40,
                }
            )
            
            logger.info(f"✅ Gemini initialized: {self.model_name}")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            raise
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    
    def _check_rate_limit(self, user_id: int, max_requests: int = 5, 
                         time_window: int = 60) -> tuple[bool, Optional[int]]:
        """
        Перевірка rate limiting
        
        Args:
            user_id: ID користувача
            max_requests: Максимум запитів
            time_window: Часовий період (секунди)
        
        Returns:
            (allowed: bool, wait_seconds: Optional[int])
        """
        now = time.time()
        
        if user_id not in self.last_request_time:
            self.last_request_time[user_id] = []
        
        # Видалити старі запити за межами часового вікна
        self.last_request_time[user_id] = [
            req_time for req_time in self.last_request_time[user_id]
            if now - req_time < time_window
        ]
        
        # Перевірити ліміт
        if len(self.last_request_time[user_id]) < max_requests:
            self.last_request_time[user_id].append(now)
            return True, None
        
        # Розрахувати час очікування
        oldest = self.last_request_time[user_id][0]
        wait_time = int(time_window - (now - oldest)) + 1
        
        return False, max(0, wait_time)
    
    # ========================================================================
    # ОБРОБКА ЗАМОВЛЕНЬ
    # ========================================================================
    
    def process_order_request(
        self,
        user_id: int,
        user_message: str,
        menu_items: List[Dict[str, Any]],
        user_cart: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обробити запит користувача через AI
        
        Args:
            user_id: ID користувача
            user_message: Повідомлення користувача
            menu_items: Доступні товари
            user_cart: Поточний кошик користувача
        
        Returns:
            {
                'action': 'add_to_cart' | 'show_menu' | 'recommend' | 'info',
                'items': [...],  # Знайдені товари
                'message': 'Відповідь користувачу',
                'success': True/False
            }
        """
        
        # 1️⃣ ПЕРЕВІРКА RATE LIMITING
        allowed, wait_time = self._check_rate_limit(user_id)
        
        if not allowed:
            logger.warning(f"⏱️ Rate limit hit for user {user_id}, wait {wait_time}s")
            return {
                'action': 'error',
                'message': f"⏱️ Задто багато запитів! Чекайте {wait_time} сек",
                'success': False
            }
        
        # 2️⃣ ПОБУДОВА ПРОМПТУ
        prompt = self._build_order_prompt(user_message, menu_items, user_cart)
        
        try:
            # 3️⃣ ЗАПИТ ДО GEMINI
            logger.info(f"🤖 Sending AI request for user {user_id}")
            response = self.model.generate_content(prompt)
            
            # 4️⃣ ПАРСИНГ ВІДПОВІДІ
            result = self._parse_ai_response(response.text, menu_items)
            
            logger.info(f"✅ AI response received: action={result.get('action')}")
            return result
        
        except Exception as e:
            logger.error(f"❌ Gemini API error: {e}")
            return {
                'action': 'error',
                'message': "❌ Помилка AI обробки. Спробуйте пізніше",
                'success': False
            }
    
    def _build_order_prompt(
        self,
        user_message: str,
        menu_items: List[Dict[str, Any]],
        user_cart: List[Dict[str, Any]] = None
    ) -> str:
        """Побудова промпту для AI"""
        
        # Форматування меню
        menu_text = "ДОСТУПНЕ МЕНЮ:\n"
        for item in menu_items[:20]:  # Обмежуємо для краї токенів
            name = item.get('name', 'Unknown')
            category = item.get('category', 'Other')
            price = item.get('price', 0)
            menu_text += f"- {name} ({category}) - {price} грн\n"
        
        # Форматування кошика (якщо є)
        cart_text = "ПОТОЧНИЙ КОШИК:\n"
        if user_cart:
            for item in user_cart:
                name = item.get('name', 'Unknown')
                qty = item.get('quantity', 1)
                cart_text += f"- {name} x{qty}\n"
        else:
            cart_text += "Порожній\n"
        
        # ОСНОВНИЙ ПРОМПТ
        prompt = f"""🤖 Ти - асистент замовлення їжі у ресторані FerrikFoot.

{menu_text}

{cart_text}

ЗАПИТ КОРИСТУВАЧА: "{user_message}"

ТВОЇ ІНСТРУКЦІЇ:
1. Проаналізуй запит
2. Визнач намір:
   - "add_to_cart" - якщо користувач хоче замовити
   - "show_menu" - якщо хоче побачити меню
   - "recommend" - якщо хоче рекомендацію
   - "info" - для інших питань
3. Знайди товари з меню (якщо необхідно)
4. Відповідай дружелюбно та коротко українською

⚠️ ОБОВ'ЯЗКОВО ВІДПОВІДАЙ У ФОРМАТІ JSON:
{{
    "action": "add_to_cart" або "show_menu" або "recommend" або "info",
    "items": [
        {{"id": "товару_айді", "name": "Назва", "price": 120, "quantity": 1}}
    ],
    "message": "Твоя відповідь українською"
}}

ПРАВИЛА:
✓ Шукай товари за частковими назвами
✓ Якщо не знайдеш - порекомендуй схожі
✓ Завжди будь ввічливим
✓ ВІДПОВІДАЙ ТІЛЬКИ JSON БЕЗ ДОДАТКОВОГО ТЕКСТУ!
"""
        
        return prompt
    
    def _parse_ai_response(
        self,
        ai_text: str,
        menu_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Парсинг JSON відповіді від AI"""
        
        try:
            # Очищення від markdown
            clean_text = ai_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.startswith('```'):
                clean_text = clean_text[3:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            
            clean_text = clean_text.strip()
            
            # Парсинг JSON
            result = json.loads(clean_text)
            
            # ВАЛІДАЦІЯ ТОВАРІВ
            if result.get('action') == 'add_to_cart' and result.get('items'):
                validated_items = []
                
                for item in result['items']:
                    item_id = item.get('id')
                    item_name = item.get('name', '').lower()
                    
                    # Шукаємо товар в меню
                    found_item = None
                    for menu_item in menu_items:
                        if (str(menu_item.get('id')) == str(item_id) or 
                            menu_item.get('name', '').lower() == item_name or
                            item_name in menu_item.get('name', '').lower()):
                            found_item = menu_item
                            break
                    
                    if found_item:
                        validated_items.append({
                            'id': found_item['id'],
                            'name': found_item['name'],
                            'price': found_item.get('price', 0),
                            'quantity': int(item.get('quantity', 1))
                        })
                
                result['items'] = validated_items
            
            # Перевірка обов'язкових полів
            if 'action' not in result:
                result['action'] = 'info'
            if 'message' not in result:
                result['message'] = 'Виконано'
            if 'items' not in result:
                result['items'] = []
            
            result['success'] = True
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse AI JSON: {e}\nText: {ai_text[:200]}")
            
            return {
                'action': 'info',
                'message': ai_text if len(ai_text) < 500 else 'Спробуйте /menu для перегляду меню',
                'items': [],
                'success': False
            }
        
        except Exception as e:
            logger.error(f"❌ Error parsing AI response: {e}")
            return {
                'action': 'error',
                'message': '❌ Помилка обробки. Спробуйте пізніше',
                'items': [],
                'success': False
            }
    
    # ========================================================================
    # ПОШУК ТА РЕКОМЕНДАЦІЇ
    # ========================================================================
    
    def search_items(
        self,
        query: str,
        menu_items: List[Dict[str, Any]],
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Пошук товарів за запитом
        
        Args:
            query: Пошуковий запит
            menu_items: Меню для пошуку
            max_results: Макс результатів
        
        Returns:
            Список знайдених товарів
        """
        
        query_lower = query.lower()
        results = []
        
        for item in menu_items:
            name = item.get('name', '').lower()
            category = item.get('category', '').lower()
            description = item.get('description', '').lower()
            
            # Просте збігання
            if (query_lower in name or 
                query_lower in category or 
                query_lower in description):
                results.append(item)
        
        return results[:max_results]
    
    def get_recommendations(
        self,
        user_mood: Optional[str] = None,
        menu_items: List[Dict[str, Any]] = None,
        max_recommendations: int = 3
    ) -> Dict[str, Any]:
        """
        Отримати рекомендації на основі настрою
        
        Args:
            user_mood: Настрій користувача (happy, sad, busy, lazy)
            menu_items: Меню для рекомендацій
            max_recommendations: Кількість рекомендацій
        
        Returns:
            Рекомендації з повідомленням
        """
        
        mood_prompts = {
            'happy': "рекомендуй яскраві, святкові страви",
            'sad': "рекомендуй комфортну, теплу їжу",
            'busy': "рекомендуй швидкі, легкі страви",
            'lazy': "рекомендуй готові, легкі блюда",
        }
        
        prompt_end = mood_prompts.get(user_mood, "рекомендуй популярні страви")
        
        if not menu_items:
            return {
                'success': False,
                'message': 'Меню недоступне',
                'items': []
            }
        
        try:
            prompt = f"""Ти асистент ресторану. {prompt_end}

Меню:
{self._format_menu_for_prompt(menu_items[:15])}

Рекомендуй {max_recommendations} страви в форматі JSON:
{{
    "items": [
        {{"id": "1", "name": "Назва", "reason": "Коротка причина"}}
    ],
    "message": "Привітання з рекомендаціями"
}}
"""
            
            response = self.model.generate_content(prompt)
            result = json.loads(response.text.strip('```json\n').strip('```'))
            
            # Валідація
            validated = []
            for rec in result.get('items', []):
                for item in menu_items:
                    if str(item.get('id')) == str(rec.get('id')):
                        validated.append(item)
                        break
            
            return {
                'success': True,
                'message': result.get('message', 'Ось мої рекомендації'),
                'items': validated[:max_recommendations]
            }
        
        except Exception as e:
            logger.error(f"❌ Recommendations error: {e}")
            return {
                'success': False,
                'message': 'Помилка при отриманні рекомендацій',
                'items': []
            }
    
    def _format_menu_for_prompt(self, menu_items: List[Dict[str, Any]]) -> str:
        """Форматування меню для промпту"""
        text = ""
        for item in menu_items:
            name = item.get('name', '')
            price = item.get('price', 0)
            category = item.get('category', '')
            text += f"- {name} ({category}) - {price} грн\n"
        return text
    
    # ========================================================================
    # УТИЛІТИ
    # ========================================================================
    
    def test_connection(self) -> bool:
        """Тест підключення до Gemini API"""
        try:
            response = self.model.generate_content("Скажи 'OK' якщо ти працюєш")
            logger.info(f"✅ Gemini API test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Gemini API test failed: {e}")
            return False
    
    def generate_response(self, prompt: str) -> str:
        """
        Генерація загальної відповіді
        
        Args:
            prompt: Промпт для AI
        
        Returns:
            Відповідь від AI
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return "Вибачте, виникла помилка при генерації відповіді."


# ============================================================================
# ТЕСТУВАННЯ (для розробки)
# ============================================================================

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ GEMINI_API_KEY not set in .env")
        exit(1)
    
    print("=" * 60)
    print("🧪 TESTING GEMINI SERVICE")
    print("=" * 60)
    
    # Ініціалізація
    service = GeminiService(api_key)
    
    # Тестовий меню
    menu = [
        {'id': '1', 'name': 'Піца Маргарита', 'category': 'Pizza', 'price': 120},
        {'id': '2', 'name': 'Піца Пепероні', 'category': 'Pizza', 'price': 150},
        {'id': '3', 'name': 'Цезар', 'category': 'Salad', 'price': 80},
        {'id': '4', 'name': 'Cola', 'category': 'Drink', 'price': 30},
    ]
    
    # Тест 1: Connection
    print("\n1️⃣ Testing connection...")
    if service.test_connection():
        print("✅ Connection OK")
    else:
        print("❌ Connection failed")
    
    # Тест 2: Order processing
    print("\n2️⃣ Testing order processing...")
    result = service.process_order_request(
        user_id=123,
        user_message="Хочу піцу Маргарита",
        menu_items=menu
    )
    print(f"Action: {result.get('action')}")
    print(f"Message: {result.get('message')}")
    print(f"Items: {len(result.get('items', []))} found")
    
    # Тест 3: Search
    print("\n3️⃣ Testing search...")
    search_result = service.search_items("піца", menu)
    print(f"Found {len(search_result)} items")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
