"""
🔍 Інтелектуальний пошук по меню з NLP
"""
import re
from typing import List, Dict, Set
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class MenuSearch:
    """Інтелектуальний пошук по меню"""
    
    # Словник синонімів та альтернативних назв
    SYNONYMS = {
        'піца': ['pizza', 'піца', 'піцца'],
        'бургер': ['burger', 'гамбургер', 'чізбургер'],
        'салат': ['salad', 'овочі', 'зелень'],
        'суп': ['soup', 'юшка', 'бульйон'],
        'десерт': ['dessert', 'солодке', 'тістечко', 'торт'],
        'напій': ['drink', 'beverage', 'сік', 'компот'],
        'кава': ['coffee', 'еспресо', 'капучіно', 'латте'],
        'м\'ясо': ['meat', 'яловичина', 'свинина', 'курка', 'курячий'],
        'риба': ['fish', 'форель', 'лосось', 'тунець'],
        'вегетаріанський': ['vegetarian', 'vegan', 'без м\'яса', 'овочевий'],
        'гострий': ['spicy', 'hot', 'перчений'],
        'сир': ['cheese', 'чіз', 'сирний'],
        'томат': ['tomato', 'помідор', 'томатний'],
        'гриби': ['mushroom', 'печериці', 'грибний']
    }
    
    # Стоп-слова (ігноруються при пошуку)
    STOP_WORDS = {
        'з', 'із', 'на', 'в', 'у', 'та', 'і', 'або', 'без', 'під',
        'the', 'with', 'and', 'or', 'in', 'on'
    }
    
    # Ключові слова для фільтрів
    FILTER_KEYWORDS = {
        'vegetarian': ['вегетаріанський', 'без м\'яса', 'овочевий', 'vegetarian', 'vegan'],
        'spicy': ['гострий', 'пекучий', 'spicy', 'hot'],
        'cheap': ['дешевий', 'недорогий', 'бюджетний', 'економ'],
        'expensive': ['дорогий', 'преміум', 'елітний'],
        'fast': ['швидкий', 'швидко', 'fast', 'quick'],
        'new': ['новий', 'нове', 'новинка', 'new']
    }
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Нормалізує текст для пошуку"""
        # Нижній регістр
        text = text.lower().strip()
        
        # Видалення зайвих пробілів
        text = re.sub(r'\s+', ' ', text)
        
        # Видалення спецсимволів (залишаємо букви, цифри, пробіли)
        text = re.sub(r'[^\w\s\'-]', '', text, flags=re.UNICODE)
        
        return text
    
    @staticmethod
    def extract_keywords(query: str) -> Set[str]:
        """Витягує ключові слова з запиту"""
        normalized = MenuSearch.normalize_text(query)
        words = normalized.split()
        
        # Видаляємо стоп-слова
        keywords = {word for word in words if word not in MenuSearch.STOP_WORDS}
        
        # Додаємо синоніми
        expanded_keywords = set(keywords)
        for keyword in keywords:
            for main_word, synonyms in MenuSearch.SYNONYMS.items():
                if keyword in synonyms:
                    expanded_keywords.add(main_word)
                    expanded_keywords.update(synonyms)
        
        return expanded_keywords
    
    @staticmethod
    def extract_filters(query: str) -> Dict[str, bool]:
        """Витягує фільтри з запиту"""
        normalized = MenuSearch.normalize_text(query)
        filters = {}
        
        for filter_name, keywords in MenuSearch.FILTER_KEYWORDS.items():
            for keyword in keywords:
                if keyword in normalized:
                    filters[filter_name] = True
                    break
        
        return filters
    
    @staticmethod
    def calculate_relevance(item: Dict, keywords: Set[str], filters: Dict) -> float:
        """
        Розраховує релевантність товару до пошукового запиту
        
        Returns:
            float: Score від 0 до 100
        """
        score = 0.0
        
        # Підготовка тексту товару
        name = MenuSearch.normalize_text(item.get('name', item.get('Страви', '')))
        description = MenuSearch.normalize_text(item.get('description', item.get('Опис', '')))
        category = MenuSearch.normalize_text(item.get('category', item.get('Категорія', '')))
        allergens = MenuSearch.normalize_text(item.get('allergens', item.get('Аллергени', '')))
        
        full_text = f"{name} {description} {category}"
        
        # Перевірка кожного ключового слова
        for keyword in keywords:
            # Точний збіг в назві (найвищий пріоритет)
            if keyword in name:
                score += 30.0
            
            # Збіг в категорії
            elif keyword in category:
                score += 20.0
            
            # Збіг в описі
            elif keyword in description:
                score += 15.0
            
            # Часткове співпадання (fuzzy match)
            else:
                # Перевіряємо схожість з назвою
                ratio = SequenceMatcher(None, keyword, name).ratio()
                if ratio > 0.6:
                    score += 10.0 * ratio
        
        # Перевірка фільтрів
        if filters:
            filter_match_count = 0
            
            # Вегетаріанське
            if filters.get('vegetarian'):
                if any(word in full_text for word in ['вегетаріанський', 'овочевий', 'салат']):
                    score += 10.0
                    filter_match_count += 1
                elif any(word in full_text for word in ['м\'ясо', 'курка', 'свинина']):
                    score -= 20.0  # Штраф за невідповідність
            
            # Гостре
            if filters.get('spicy'):
                if any(word in full_text for word in ['гострий', 'перець', 'чілі']):
                    score += 10.0
                    filter_match_count += 1
            
            # Швидке приготування
            if filters.get('fast'):
                cook_time = int(item.get('cook_time', item.get('Час_приготування', 30)))
                if cook_time <= 20:
                    score += 10.0
                    filter_match_count += 1
            
            # Ціна
            price = float(item.get('price', item.get('Ціна', 0)))
            if filters.get('cheap') and price <= 150:
                score += 10.0
                filter_match_count += 1
            elif filters.get('expensive') and price >= 300:
                score += 10.0
                filter_match_count += 1
        
        # Бонус за рейтинг
        rating = float(item.get('rating', item.get('Рейтинг', 0)))
        if rating >= 4.5:
            score += 5.0
        
        return min(100.0, score)
    
    @staticmethod
    def search(query: str, items: List[Dict], limit: int = 10) -> List[Dict]:
        """
        Виконує інтелектуальний пошук
        
        Args:
            query: Пошуковий запит
            items: Список товарів
            limit: Максимальна кількість результатів
        
        Returns:
            Список найбільш релевантних товарів
        """
        if not query or not items:
            return []
        
        # Витягуємо ключові слова та фільтри
        keywords = MenuSearch.extract_keywords(query)
        filters = MenuSearch.extract_filters(query)
        
        logger.info(f"Search query: {query}")
        logger.info(f"Keywords: {keywords}")
        logger.info(f"Filters: {filters}")
        
        # Розраховуємо релевантність для кожного товару
        scored_items = []
        for item in items:
            # Перевіряємо, чи активний товар
            is_active = item.get('active', item.get('Активний', True))
            if not is_active:
                continue
            
            score = MenuSearch.calculate_relevance(item, keywords, filters)
            
            if score > 0:
                scored_items.append({
                    'item': item,
                    'score': score
                })
        
        # Сортуємо за релевантністю
        scored_items.sort(key=lambda x: x['score'], reverse=True)
        
        # Повертаємо топ N
        results = [si['item'] for si in scored_items[:limit]]
        
        logger.info(f"Found {len(results)} results")
        
        return results
    
    @staticmethod
    def format_search_results(results: List[Dict], query: str) -> str:
        """Форматує результати пошуку"""
        if not results:
            return (
                f"🔍 Результати пошуку: \"{query}\"\n\n"
                f"😔 Нічого не знайдено.\n\n"
                f"💡 Спробуй:\n"
                f"• Інші ключові слова\n"
                f"• Переглянути все меню: /menu\n"
                f"• Підібрати страву за настроєм: /recommend"
            )
        
        result_text = f"🔍 **Результати пошуку:** \"{query}\"\n\n"
        result_text += f"Знайдено: **{len(results)}** позицій\n\n"
        
        from menu_formatter import MenuFormatter
        
        for i, item in enumerate(results[:5], 1):  # Показуємо перші 5
            result_text += f"**{i}.** "
            result_text += MenuFormatter.format_item_card(item)
            result_text += "\n\n" + "-" * 40 + "\n\n"
        
        if len(results) > 5:
            result_text += f"_...та ще {len(results) - 5} варіантів_\n"
        
        return result_text
    
    @staticmethod
    def create_search_keyboard(results: List[Dict]) -> Dict:
        """Створює клавіатуру з результатами пошуку"""
        keyboard = {'inline_keyboard': []}
        
        for item in results[:5]:
            item_id = item.get('id', item.get('ID'))
            name = item.get('name', item.get('Страви', ''))[:30]
            
            keyboard['inline_keyboard'].append([
                {'text': f"👁️ {name}", 'callback_data': f"item_{item_id}"},
                {'text': '➕', 'callback_data': f"add_{item_id}"}
            ])
        
        keyboard['inline_keyboard'].append([
            {'text': '🔄 Новий пошук', 'callback_data': 'search_menu'},
            {'text': '📋 Все меню', 'callback_data': 'menu'}
        ])
        
        return keyboard
    
    @staticmethod
    def get_search_suggestions() -> List[str]:
        """Повертає популярні пошукові запити"""
        return [
            "піца з грибами",
            "щось вегетаріанське",
            "гострий суп",
            "десерт без глютену",
            "швидкий перекус",
            "м'ясна страва",
            "легкий салат",
            "каву з десертом"
        ]


# ============================================================================
# Допоміжні функції
# ============================================================================

def handle_search(user_id: int, query: str, telegram_api, sheets_api):
    """Обробляє пошуковий запит"""
    # Отримуємо меню
    menu_items = sheets_api.get_menu()
    
    if not menu_items:
        telegram_api.send_message(
            user_id,
            "😔 На жаль, зараз меню недоступне. Спробуй пізніше!"
        )
        return
    
    # Виконуємо пошук
    results = MenuSearch.search(query, menu_items, limit=10)
    
    # Форматуємо та відправляємо результати
    result_text = MenuSearch.format_search_results(results, query)
    result_keyboard = MenuSearch.create_search_keyboard(results)
    
    telegram_api.send_message(user_id, result_text, reply_markup=result_keyboard)


# ============================================================================
# Тестування
# ============================================================================
if __name__ == "__main__":
    # Тестові дані
    test_items = [
        {
            'id': 1,
            'name': 'Піца "Маргарита"',
            'category': 'Піца',
            'description': 'Класична італійська піца з моцарелою та томатами',
            'price': 180,
            'rating': 4.8,
            'cook_time': 20
        },
        {
            'id': 2,
            'name': 'Салат "Цезар"',
            'category': 'Салати',
            'description': 'Свіжий салат з куркою, пармезаном та соусом',
            'price': 150,
            'rating': 4.6,
            'cook_time': 10
        },
        {
            'id': 3,
            'name': 'Овочевий суп',
            'category': 'Супи',
            'description': 'Легкий вегетаріанський суп з сезонних овочів',
            'price': 95,
            'rating': 4.5,
            'cook_time': 15
        },
        {
            'id': 4,
            'name': 'Бургер з грибами',
            'category': 'Бургери',
            'description': 'Соковитий бургер з печерицями та сиром',
            'price': 165,
            'rating': 4.7,
            'cook_time': 18
        }
    ]
    
    # Тестові запити
    test_queries = [
        "піца з сиром",
        "щось вегетаріанське",
        "швидкий перекус",
        "бургер",
        "салат без м'яса"
    ]
    
    print("=== Тестування пошуку ===\n")
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Запит: {query}")
        print('='*50)
        
        results = MenuSearch.search(query, test_items, limit=3)
        print(MenuSearch.format_search_results(results, query))
