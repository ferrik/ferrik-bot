"""
🤖 AI Recommender - Персональні рекомендації
"""
import random
from datetime import datetime
from typing import List, Dict

class AIRecommender:
    """Розумні рекомендації на основі історії та контексту"""
    
    def __init__(self, db, sheets):
        self.db = db
        self.sheets = sheets
    
    def get_recommendations(self, user_id: int, context: str = 'general') -> List[Dict]:
        """
        Отримати персональні рекомендації
        
        context: 'morning', 'lunch', 'dinner', 'late_night', 'general'
        """
        # Отримуємо історію
        orders = self.db.get_user_orders(user_id)
        menu = self.sheets.get_menu_items()
        
        # Аналізуємо вподобання
        favorite_categories = self._analyze_preferences(orders)
        
        # Фільтруємо по часу доби
        menu = self._filter_by_time(menu, context)
        
        # Сортуємо по релевантності
        recommended = self._score_items(menu, favorite_categories)
        
        return recommended[:5]  # Топ-5
    
    def _analyze_preferences(self, orders: List) -> Dict:
        """Аналіз вподобань користувача"""
        categories = {}
        
        for order in orders:
            # Парсимо items_json
            items = order.get('items_json', [])
            if isinstance(items, str):
                import json
                items = json.loads(items)
            
            for item in items:
                cat = item.get('category', 'Інше')
                categories[cat] = categories.get(cat, 0) + 1
        
        return categories
    
    def _filter_by_time(self, menu: List, context: str) -> List:
        """Фільтрація по часу доби"""
        hour = datetime.now().hour
        
        if context == 'morning' or 6 <= hour < 11:
            # Сніданки
            keywords = ['сніданок', 'каша', 'омлет', 'панкейк']
        elif context == 'lunch' or 11 <= hour < 16:
            # Обіди
            keywords = ['суп', 'салат', 'комбо', 'ланч']
        elif context == 'dinner' or 16 <= hour < 22:
            # Вечері
            keywords = ['піца', 'бургер', 'паста', 'стейк']
        else:
            # Пізня вечеря
            keywords = ['закуска', 'десерт', 'напій']
        
        # Фільтруємо
        filtered = []
        for item in menu:
            name = item.get('Страви', '').lower()
            desc = item.get('Опис', '').lower()
            
            if any(kw in name or kw in desc for kw in keywords):
                filtered.append(item)
        
        return filtered if filtered else menu  # Якщо нічого не знайшли - все меню
    
    def _score_items(self, menu: List, preferences: Dict) -> List:
        """Оцінка релевантності страв"""
        scored = []
        
        for item in menu:
            score = 0
            
            # Бонус за улюблену категорію
            cat = item.get('Категорія', '')
            if cat in preferences:
                score += preferences[cat] * 10
            
            # Бонус за рейтинг
            rating = item.get('Рейтинг', 0)
            if rating:
                score += float(rating) * 5
            
            # Бонус за популярність (випадково для демо)
            score += random.randint(0, 20)
            
            scored.append((item, score))
        
        # Сортуємо
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [item for item, score in scored]
    
    def get_mood_recommendations(self, mood: str) -> List[Dict]:
        """Рекомендації по настрою"""
        menu = self.sheets.get_menu_items()
        
        mood_map = {
            'happy': ['десерт', 'піца', 'бургер'],  # Веселе
            'hungry': ['комбо', 'стейк', 'бургер'],  # Голодний
            'lazy': ['піца', 'доставка', 'готове'],  # Лінивий
            'romantic': ['паста', 'вино', 'десерт'],  # Романтичний
            'healthy': ['салат', 'суп', 'рис']  # Здорове
        }
        
        keywords = mood_map.get(mood, [])
        
        filtered = []
        for item in menu:
            name = item.get('Страви', '').lower()
            desc = item.get('Опис', '').lower()
            
            if any(kw in name or kw in desc for kw in keywords):
                filtered.append(item)
        
        return filtered[:5]
    
    def search_by_query(self, query: str) -> List[Dict]:
        """Пошук по запиту (NLP-подібний)"""
        menu = self.sheets.get_menu_items()
        query = query.lower()
        
        # Ключові слова
        keywords = query.split()
        
        results = []
        for item in menu:
            name = item.get('Страви', '').lower()
            desc = item.get('Опис', '').lower()
            tags = item.get('Аллергени', '').lower()
            
            # Шукаємо збіги
            matches = sum(
                1 for kw in keywords 
                if kw in name or kw in desc or kw in tags
            )
            
            if matches > 0:
                results.append((item, matches))
        
        # Сортуємо по релевантності
        results.sort(key=lambda x: x[1], reverse=True)
        
        return [item for item, score in results[:10]] 