"""
🎭 Система рекомендацій на основі настрою користувача
"""
from typing import List, Dict, Optional
from datetime import datetime
import random
import logging

logger = logging.getLogger(__name__)


class MoodRecommender:
    """AI-рекомендатор страв на основі настрою"""
    
    # Характеристики настроїв
    MOOD_PROFILES = {
        'happy': {
            'name': 'Щасливий(а)',
            'emoji': '😊',
            'keywords': ['легкі', 'яскраві', 'святкові', 'соковиті'],
            'categories': ['салати', 'піца', 'десерти'],
            'avoid_categories': ['супи'],
            'preferences': {
                'light': 0.7,
                'colorful': 0.8,
                'sweet': 0.6
            }
        },
        'calm': {
            'name': 'Спокійний(а)',
            'emoji': '😌',
            'keywords': ['теплі', 'комфортні', 'традиційні'],
            'categories': ['супи', 'паста', 'ризотто'],
            'avoid_categories': ['бургери', 'фастфуд'],
            'preferences': {
                'warm': 0.9,
                'comfort': 0.8,
                'traditional': 0.7
            }
        },
        'energetic': {
            'name': 'Енергійний(а)',
            'emoji': '💪',
            'keywords': ['білкові', 'поживні', 'м\'ясні'],
            'categories': ['гриль', 'стейки', 'бургери', 'боули'],
            'avoid_categories': ['десерти'],
            'preferences': {
                'protein': 0.9,
                'hearty': 0.8,
                'substantial': 0.7
            }
        },
        'romantic': {
            'name': 'Романтичний(а)',
            'emoji': '🤗',
            'keywords': ['вишукані', 'ніжні', 'делікатні'],
            'categories': ['паста', 'морепродукти', 'десерти'],
            'avoid_categories': ['фастфуд', 'бургери'],
            'preferences': {
                'elegant': 0.9,
                'delicate': 0.8,
                'refined': 0.7
            }
        },
        'hungry': {
            'name': 'Голодний(а)',
            'emoji': '😋',
            'keywords': ['швидкі', 'ситні', 'великі порції'],
            'categories': ['бургери', 'піца', 'стейки', 'паста'],
            'avoid_categories': [],
            'preferences': {
                'fast': 0.9,
                'filling': 1.0,
                'large': 0.8
            }
        },
        'surprise': {
            'name': 'Здивуй мене',
            'emoji': '🎲',
            'keywords': ['цікаві', 'незвичайні', 'нові'],
            'categories': [],  # Вибираємо випадково
            'avoid_categories': [],
            'preferences': {
                'unique': 0.9,
                'new': 1.0,
                'experimental': 0.8
            }
        }
    }
    
    @staticmethod
    def get_time_based_suggestions() -> Dict:
        """Рекомендації на основі часу доби"""
        hour = datetime.now().hour
        
        if 6 <= hour < 11:
            return {
                'period': 'morning',
                'emoji': '🌅',
                'message': 'Доброго ранку! Як щодо смачного сніданку?',
                'categories': ['сніданки', 'кава', 'випічка'],
                'boost_items': ['омлет', 'сирники', 'круасан', 'каша']
            }
        elif 11 <= hour < 15:
            return {
                'period': 'lunch',
                'emoji': '☀️',
                'message': 'Час обіду! Що б з\'їсти?',
                'categories': ['супи', 'салати', 'основні страви', 'бізнес-ланчі'],
                'boost_items': ['суп', 'салат', 'другі страви']
            }
        elif 15 <= hour < 18:
            return {
                'period': 'afternoon',
                'emoji': '🍵',
                'message': 'Післяобідній перекус? Маємо ідеї!',
                'categories': ['десерти', 'напої', 'закуски'],
                'boost_items': ['кава', 'тістечко', 'круасан']
            }
        elif 18 <= hour < 23:
            return {
                'period': 'dinner',
                'emoji': '🌆',
                'message': 'Час вечері! Щось особливе сьогодні?',
                'categories': ['піца', 'паста', 'стейки', 'морепродукти'],
                'boost_items': ['піца', 'стейк', 'паста', 'ризотто']
            }
        else:
            return {
                'period': 'night',
                'emoji': '🌙',
                'message': 'Пізній перекус? Є швидкі варіанти!',
                'categories': ['закуски', 'напої', 'десерти'],
                'boost_items': ['сендвіч', 'салат', 'десерт']
            }
    
    @staticmethod
    def calculate_item_score(item: Dict, mood: str, time_suggestions: Dict) -> float:
        """
        Розраховує score для товару на основі настрою та часу
        """
        score = 0.0
        
        mood_profile = MoodRecommender.MOOD_PROFILES.get(mood, {})
        
        # Базовий score - рейтинг товару
        rating = float(item.get('rating', item.get('Рейтинг', 3.0)))
        score += rating * 2  # Максимум +10 балів
        
        # Бонус за категорію
        category = item.get('category', item.get('Категорія', '')).lower()
        preferred_cats = [c.lower() for c in mood_profile.get('categories', [])]
        avoid_cats = [c.lower() for c in mood_profile.get('avoid_categories', [])]
        
        for pref_cat in preferred_cats:
            if pref_cat in category:
                score += 5.0
                break
        
        for avoid_cat in avoid_cats:
            if avoid_cat in category:
                score -= 3.0
                break
        
        # Бонус за час доби
        time_categories = [c.lower() for c in time_suggestions.get('categories', [])]
        for time_cat in time_categories:
            if time_cat in category:
                score += 3.0
                break
        
        # Бонус за ключові слова в назві/описі
        name = item.get('name', item.get('Страви', '')).lower()
        description = item.get('description', item.get('Опис', '')).lower()
        text = f"{name} {description}"
        
        for keyword in mood_profile.get('keywords', []):
            if keyword in text:
                score += 2.0
        
        # Бонус за швидкість приготування (для голодних)
        if mood == 'hungry':
            cook_time = int(item.get('cook_time', item.get('Час_приготування', 30)))
            if cook_time <= 20:
                score += 4.0
            elif cook_time <= 30:
                score += 2.0
        
        # Випадковість для "surprise me"
        if mood == 'surprise':
            score += random.uniform(0, 5)
        
        return max(0, score)
    
    @staticmethod
    def recommend(items: List[Dict], mood: str, limit: int = 3, user_history: List[str] = None) -> List[Dict]:
        """
        Генерує рекомендації на основі настрою
        
        Args:
            items: Список доступних товарів
            mood: Настрій користувача
            limit: Кількість рекомендацій
            user_history: Історія замовлень (ID товарів)
        
        Returns:
            Список рекомендованих товарів з scores
        """
        if not items:
            logger.warning("No items available for recommendations")
            return []
        
        time_suggestions = MoodRecommender.get_time_based_suggestions()
        user_history = user_history or []
        
        # Розраховуємо score для кожного товару
        scored_items = []
        for item in items:
            # Перевіряємо, чи активний товар
            is_active = item.get('active', item.get('Активний', True))
            if not is_active:
                continue
            
            score = MoodRecommender.calculate_item_score(item, mood, time_suggestions)
            
            # Бонус для нових товарів (які користувач ще не замовляв)
            item_id = str(item.get('id', item.get('ID', '')))
            if item_id not in user_history:
                score += 1.0
            
            scored_items.append({
                'item': item,
                'score': score
            })
        
        # Сортуємо за score
        scored_items.sort(key=lambda x: x['score'], reverse=True)
        
        # Повертаємо топ N
        recommendations = [
            {
                **si['item'],
                'recommendation_score': si['score']
            }
            for si in scored_items[:limit]
        ]
        
        return recommendations
    
    @staticmethod
    def format_recommendations(recommendations: List[Dict], mood: str) -> str:
        """Форматує рекомендації в текст"""
        mood_profile = MoodRecommender.MOOD_PROFILES.get(mood, {})
        mood_name = mood_profile.get('name', 'Настрій')
        mood_emoji = mood_profile.get('emoji', '😊')
        
        time_suggestions = MoodRecommender.get_time_based_suggestions()
        
        result = f"{mood_emoji} **Рекомендації для настрою: {mood_name}**\n"
        result += f"{time_suggestions['emoji']} _{time_suggestions['message']}_\n\n"
        
        if not recommendations:
            result += "😔 На жаль, зараз немає доступних страв. Спробуйте пізніше!\n"
            return result
        
        result += "🎯 Я підібрав(ла) для тебе:\n\n"
        
        for i, item in enumerate(recommendations, 1):
            name = item.get('name', item.get('Страви', 'Невідомо'))
            price = item.get('price', item.get('Ціна', 0))
            rating = item.get('rating', item.get('Рейтинг', 0))
            description = item.get('description', item.get('Опис', ''))
            
            # Обрізаємо опис
            if description and len(description) > 60:
                description = description[:60] + "..."
            
            result += f"**{i}. {name}**\n"
            if description:
                result += f"   _{description}_\n"
            result += f"   💰 {price} грн"
            if rating:
                result += f" | ⭐ {rating}/5"
            result += "\n\n"
        
        result += "💡 Натисни на страву, щоб додати в кошик!"
        
        return result
    
    @staticmethod
    def create_recommendation_keyboard(recommendations: List[Dict]) -> Dict:
        """Створює клавіатуру з рекомендаціями"""
        keyboard = {'inline_keyboard': []}
        
        for item in recommendations:
            item_id = item.get('id', item.get('ID'))
            name = item.get('name', item.get('Страви', 'Товар'))[:30]
            
            keyboard['inline_keyboard'].append([
                {'text': f"➕ {name}", 'callback_data': f"add_{item_id}"}
            ])
        
        # Додаткові опції
        keyboard['inline_keyboard'].append([
            {'text': '🎲 Інші варіанти', 'callback_data': 'recommend_again'},
            {'text': '📋 Все меню', 'callback_data': 'menu'}
        ])
        
        return keyboard


# ============================================================================
# Тестування
# ============================================================================
if __name__ == "__main__":
    # Тестові дані
    sample_items = [
        {
            'id': 1,
            'name': 'Крем-суп з броколі',
            'category': 'Супи',
            'description': 'Ніжний крем-суп з свіжої броколі',
            'price': 95,
            'rating': 4.7,
            'cook_time': 15
        },
        {
            'id': 2,
            'name': 'Стейк Рібай',
            'category': 'Гриль',
            'description': 'Соковитий яловичий стейк',
            'price': 450,
            'rating': 4.9,
            'cook_time': 25
        },
        {
            'id': 3,
            'name': 'Піца "Маргарита"',
            'category': 'Піца',
            'description': 'Класична італійська піца',
            'price': 180,
            'rating': 4.8,
            'cook_time': 20
        }
    ]
    
    print("=== Тестування рекомендацій ===\n")
    
    for mood in ['calm', 'energetic', 'hungry']:
        print(f"\n{'='*50}")
        print(f"НАСТРІЙ: {mood.upper()}")
        print('='*50)
        
        recommendations = MoodRecommender.recommend(sample_items, mood, limit=2)
        print(MoodRecommender.format_recommendations(recommendations, mood))
