"""
🎁 SURPRISE ME - AI-КЕРОВАНИЙ СЮРПРИЗ З КОМБО ТА ЗНИЖКАМИ
"""

import random
from typing import List, Dict, Any
from app.utils.validators import calculate_total_price

class SurpriseMe:
    """AI-сюрприз для користувачів"""
    
    DISCOUNT_RANGES = {
        'standard': (10, 15),    # 10-15%
        'vip': (15, 20),         # 15-20%
        'loyal': (20, 30),       # 20-30% для 50+ замовлень
    }
    
    SURPRISE_MESSAGES = [
        "🎁 Я для тебе щось спеціальне вибрав! 😋",
        "🎲 Почувай мою енергію! Ось мій вибір 🔮",
        "✨ Это мой personal pick для тебя! 👨‍🍳",
        "🌟 Вирішив здивувати тебе! 🎉",
        "💫 Мої улюбленці для тебе! 🤩",
    ]
    
    COMBO_STRUCTURES = [
        # 2 основні + 1 напиток
        {'main': 2, 'drink': 1, 'desc': 'Дуо + напій'},
        # 1 основне + 1 салат + 1 десерт
        {'main': 1, 'salad': 1, 'dessert': 1, 'desc': 'Комбо обід'},
        # 3 закуски для компанії
        {'appetizer': 3, 'desc': 'Для компанії'},
        # 1 основне + 2 напиткі
        {'main': 1, 'drink': 2, 'desc': 'Для вечірки'},
    ]
    
    @staticmethod
    def generate_surprise(
        menu_items: List[Dict[str, Any]],
        user_order_count: int,
        user_favorites: List[str] = None
    ) -> Dict[str, Any]:
        """
        Генерація сюрпризу
        
        Args:
            menu_items: Список товарів з меню
            user_order_count: Кількість замовлень користувача
            user_favorites: Улюблені товари користувача
        
        Returns:
            Dict з сюрпризом:
            {
                'items': [item1, item2, ...],
                'discount': 15,
                'total_original': 350.0,
                'total_discounted': 297.5,
                'saved': 52.5,
                'message': 'Повідомлення',
                'combo_name': 'Назва комбо'
            }
        """
        
        if not menu_items or len(menu_items) < 3:
            return None
        
        # Визначаємо рівень знижки
        if user_order_count >= 50:
            discount_range = SurpriseMe.DISCOUNT_RANGES['loyal']
        elif user_order_count >= 10:
            discount_range = SurpriseMe.DISCOUNT_RANGES['vip']
        else:
            discount_range = SurpriseMe.DISCOUNT_RANGES['standard']
        
        discount = random.randint(*discount_range)
        
        # Категоризуємо товари
        categories = {
            'main': [],
            'salad': [],
            'dessert': [],
            'drink': [],
            'appetizer': [],
        }
        
        for item in menu_items:
            cat = item.get('category', '').lower()
            
            if any(x in cat for x in ['піца', 'бургер', 'main', 'основне']):
                categories['main'].append(item)
            elif any(x in cat for x in ['салат', 'salad']):
                categories['salad'].append(item)
            elif any(x in cat for x in ['десерт', 'dessert', 'торт', 'кейк']):
                categories['dessert'].append(item)
            elif any(x in cat for x in ['напій', 'drink', 'coffee', 'сік']):
                categories['drink'].append(item)
            elif any(x in cat for x in ['закуска', 'appetizer', 'starter']):
                categories['appetizer'].append(item)
        
        # Вибираємо структуру комбо
        combo_structure = random.choice(SurpriseMe.COMBO_STRUCTURES)
        
        # Формуємо комбо
        surprise_items = []
        for category, count in combo_structure.items():
            if category != 'desc':
                if category in categories and len(categories[category]) > 0:
                    items = random.sample(
                        categories[category],
                        min(count, len(categories[category]))
                    )
                    surprise_items.extend(items)
        
        # Якщо не вистачає - додаємо з усіх
        if len(surprise_items) < 2:
            remaining = random.sample(menu_items, min(2, len(menu_items)))
            surprise_items.extend(remaining)
        
        # Розраховуємо вартість
        total_original = calculate_total_price([{'price': item['price'], 'quantity': 1} for item in surprise_items])
        total_discounted = total_original * (1 - discount / 100)
        saved = total_original - total_discounted
        
        return {
            'items': surprise_items[:3],  # Максимум 3 товари
            'discount': discount,
            'total_original': round(total_original, 2),
            'total_discounted': round(total_discounted, 2),
            'saved': round(saved, 2),
            'message': random.choice(SurpriseMe.SURPRISE_MESSAGES),
            'combo_name': combo_structure['desc']
        }
    
    @staticmethod
    def format_surprise_message(surprise: Dict[str, Any]) -> str:
        """Форматування сюрпризу в красиву mensaje"""
        
        items_text = "\n".join([
            f"🔹 {item['name']} — {item['price']} грн"
            for item in surprise['items']
        ])
        
        message = f"""🎁 **СЮРПРИЗ ВІД ФЕРИКА!** 🎁

{surprise['message']}

**КОМБО:** {surprise['combo_name']}

{items_text}

💰 **Звичайна вартість:** {surprise['total_original']} грн
🎯 **Зі знижкою {surprise['discount']}%:** {surprise['total_discounted']} грн
💚 **Ви заощадили:** {surprise['saved']} грн

✨ Це ж фантастично! 🚀"""
        
        return message
    
    @staticmethod
    def apply_surprise_to_cart(surprise: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Перетворення сюрпризу в товари для кошика"""
        items_for_cart = []
        
        for item in surprise['items']:
            items_for_cart.append({
                'id': item['id'],
                'name': item['name'],
                'price': item['price'],
                'quantity': 1,
                'category': item.get('category', ''),
                'from_surprise': True,
                'discount_applied': surprise['discount']
            })
        
        return items_for_cart


# ============================================================================
# ТЕСТ
# ============================================================================

if __name__ == "__main__":
    print("🎁 Testing Surprise Me:\n")
    
    # Тестові дані
    menu = [
        {'id': '1', 'name': 'Піца Маргарита', 'category': 'Pizza', 'price': 120},
        {'id': '2', 'name': 'Піца Пепероні', 'category': 'Pizza', 'price': 150},
        {'id': '3', 'name': 'Цезар', 'category': 'Salad', 'price': 80},
        {'id': '4', 'name': 'Чорна Форест', 'category': 'Dessert', 'price': 90},
        {'id': '5', 'name': 'Cola', 'category': 'Drink', 'price': 30},
        {'id': '6', 'name': 'Каша', 'category': 'Main', 'price': 95},
    ]
    
    # Генеруємо сюрприз
    surprise = SurpriseMe.generate_surprise(menu, user_order_count=15)
    
    print("1️⃣ Сюрприз для користувача (15 замовлень):")
    print(SurpriseMe.format_surprise_message(surprise))
    
    print("\n2️⃣ Товари для кошика:")
    cart_items = SurpriseMe.apply_surprise_to_cart(surprise)
    for item in cart_items:
        print(f"  - {item['name']} ({item['discount_applied']}% знижка)")
