"""
🎨 Форматування меню для красивого відображення
"""
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MenuFormatter:
    """Форматує меню для відображення в Telegram"""
    
    # Емодзі для категорій
    CATEGORY_EMOJI = {
        'піца': '🍕',
        'pizza': '🍕',
        'бургер': '🍔',
        'burger': '🍔',
        'суп': '🍜',
        'soup': '🍜',
        'салат': '🥗',
        'salad': '🥗',
        'десерт': '🍰',
        'dessert': '🍰',
        'напій': '🥤',
        'drink': '🥤',
        'кава': '☕',
        'coffee': '☕',
        'суші': '🍱',
        'sushi': '🍱',
        'паста': '🍝',
        'pasta': '🍝',
        'сніданок': '🍳',
        'breakfast': '🍳',
        'гриль': '🥩',
        'grill': '🥩'
    }
    
    # Емодзі для особливостей
    FEATURE_EMOJI = {
        'vegetarian': '🌱',
        'vegan': '🥬',
        'spicy': '🌶️',
        'new': '🆕',
        'hot': '🔥',
        'popular': '⭐',
        'chef_choice': '👨‍🍳',
        'discount': '💰',
        'fast': '⚡'
    }
    
    @staticmethod
    def get_category_emoji(category: str) -> str:
        """Повертає емодзі для категорії"""
        category_lower = category.lower()
        for key, emoji in MenuFormatter.CATEGORY_EMOJI.items():
            if key in category_lower:
                return emoji
        return '🍽️'  # Default
    
    @staticmethod
    def format_price(price: float) -> str:
        """Форматує ціну красиво"""
        if price == int(price):
            return f"{int(price)} грн"
        return f"{price:.2f} грн"
    
    @staticmethod
    def format_item_card(item: Dict) -> str:
        """
        Форматує одну позицію меню як карточку
        
        Приклад:
        🍕 **Піца "Маргарита"**
        _Класична піца з моцарелою та томатами_
        
        💰 180 грн | ⏱️ 25 хв | ⭐ 4.8/5.0
        🌱 Вегетаріанська | 🔥 Популярна
        """
        # Базова інформація
        name = item.get('name', 'Без назви')
        category = item.get('category', '')
        description = item.get('description', '')
        price = item.get('price', 0)
        
        # Додаткова інформація
        cook_time = item.get('cook_time', item.get('Час_приготування', 0))
        rating = item.get('rating', item.get('Рейтинг', 0))
        allergens = item.get('allergens', item.get('Аллергени', ''))
        
        # Емодзі категорії
        emoji = MenuFormatter.get_category_emoji(category)
        
        # Формуємо карточку
        card = f"{emoji} **{name}**\n"
        
        if description:
            # Обмежуємо опис до 100 символів
            desc = description[:100] + "..." if len(description) > 100 else description
            card += f"_{desc}_\n"
        
        card += "\n"
        
        # Основна інформація в один рядок
        info_parts = [f"💰 {MenuFormatter.format_price(price)}"]
        
        if cook_time:
            info_parts.append(f"⏱️ {cook_time} хв")
        
        if rating:
            info_parts.append(f"⭐ {rating}/5.0")
        
        card += " | ".join(info_parts)
        
        # Теги та особливості
        tags = []
        
        if allergens:
            allergen_list = [a.strip() for a in str(allergens).split(',')]
            for allergen in allergen_list[:2]:  # Максимум 2 алергени
                if allergen.lower() in ['молоко', 'глютен', 'горіхи']:
                    tags.append(f"⚠️ {allergen}")
        
        # Додаємо популярність
        if rating and float(rating) >= 4.5:
            tags.append("🔥 Хіт")
        
        if tags:
            card += "\n" + " | ".join(tags)
        
        return card
    
    @staticmethod
    def format_menu_category(category: str, items: List[Dict], page: int = 1, per_page: int = 5) -> str:
        """
        Форматує категорію меню з пагінацією
        """
        emoji = MenuFormatter.get_category_emoji(category)
        
        # Заголовок
        result = f"{emoji} **{category.upper()}**\n"
        result += "=" * 40 + "\n\n"
        
        # Пагінація
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_items = items[start_idx:end_idx]
        
        total_pages = (len(items) + per_page - 1) // per_page
        
        if not page_items:
            result += "😔 На жаль, страв у цій категорії наразі немає.\n"
            return result
        
        # Відображаємо товари
        for i, item in enumerate(page_items, start=start_idx + 1):
            result += f"**{i}.** " + MenuFormatter.format_item_card(item)
            result += "\n\n" + "-" * 40 + "\n\n"
        
        # Інформація про пагінацію
        if total_pages > 1:
            result += f"📄 Сторінка {page} з {total_pages}\n"
        
        return result
    
    @staticmethod
    def format_cart(cart_items: List[Dict], total: float) -> str:
        """
        Форматує кошик покупок
        
        🛒 **Твій кошик**
        
        1. 🍕 Піца "Маргарита" x2 — 360 грн
        2. 🥤 Coca-Cola 0.5л x1 — 35 грн
        
        ━━━━━━━━━━━━━━━━━━━━━
        💰 **Разом: 395 грн**
        """
        if not cart_items:
            return (
                "🛒 **Твій кошик порожній**\n\n"
                "Додай щось смачненьке з меню! 😋"
            )
        
        result = "🛒 **Твій кошик**\n\n"
        
        for i, item in enumerate(cart_items, 1):
            name = item.get('name', 'Невідомо')
            qty = item.get('quantity', 1)
            price = item.get('price', 0)
            subtotal = price * qty
            
            # Емодзі для категорії
            category = item.get('category', '')
            emoji = MenuFormatter.get_category_emoji(category)
            
            result += f"{i}. {emoji} {name} x{qty} — {MenuFormatter.format_price(subtotal)}\n"
        
        result += "\n" + "━" * 30 + "\n"
        result += f"💰 **Разом: {MenuFormatter.format_price(total)}**\n"
        
        return result
    
    @staticmethod
    def format_order_confirmation(order_data: Dict) -> str:
        """
        Форматує підтвердження замовлення
        """
        order_number = order_data.get('order_number', 'N/A')
        items = order_data.get('items', [])
        total = order_data.get('total', 0)
        phone = order_data.get('phone', '')
        address = order_data.get('address', '')
        delivery_time = order_data.get('delivery_time', '45-60 хв')
        
        result = "✅ **Замовлення прийнято!**\n\n"
        result += f"📋 Номер замовлення: `#{order_number}`\n\n"
        
        result += "🛍️ **Ваше замовлення:**\n"
        for item in items:
            name = item.get('name', 'Невідомо')
            qty = item.get('quantity', 1)
            result += f"• {name} x{qty}\n"
        
        result += f"\n💰 **Сума: {MenuFormatter.format_price(total)}**\n\n"
        
        result += "📍 **Доставка:**\n"
        result += f"• Адреса: {address}\n"
        result += f"• Телефон: {phone}\n"
        result += f"• Очікуваний час: {delivery_time}\n\n"
        
        result += "🚚 Відстежити статус замовлення: /track\n"
        result += "💬 Зв'язатись з підтримкою: /support\n\n"
        
        result += "🙏 Дякуємо за замовлення! Смачного! 😋"
        
        return result
    
    @staticmethod
    def create_menu_keyboard(items: List[Dict], page: int = 1, per_page: int = 5) -> Dict:
        """Створює клавіатуру для меню"""
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_items = items[start_idx:end_idx]
        
        total_pages = (len(items) + per_page - 1) // per_page
        
        keyboard = {'inline_keyboard': []}
        
        # Кнопки товарів (по 2 в рядку)
        for i in range(0, len(page_items), 2):
            row = []
            for j in range(i, min(i + 2, len(page_items))):
                item = page_items[j]
                item_id = item.get('id', j)
                name = item.get('name', 'Товар')[:20]  # Обмеження
                
                row.append({
                    'text': f"{name}",
                    'callback_data': f"item_{item_id}"
                })
            keyboard['inline_keyboard'].append(row)
        
        # Навігація
        if total_pages > 1:
            nav_row = []
            if page > 1:
                nav_row.append({'text': '◀️ Назад', 'callback_data': f'page_{page-1}'})
            nav_row.append({'text': f'{page}/{total_pages}', 'callback_data': 'noop'})
            if page < total_pages:
                nav_row.append({'text': 'Вперед ▶️', 'callback_data': f'page_{page+1}'})
            keyboard['inline_keyboard'].append(nav_row)
        
        # Кнопки дій
        keyboard['inline_keyboard'].append([
            {'text': '🛒 Кошик', 'callback_data': 'view_cart'},
            {'text': '🏠 Головна', 'callback_data': 'main_menu'}
        ])
        
        return keyboard


# ============================================================================
# Тестування
# ============================================================================
if __name__ == "__main__":
    # Приклад товару
    sample_item = {
        'id': 1,
        'name': 'Піца "Маргарита"',
        'category': 'Піца',
        'description': 'Класична італійська піца з моцарелою, свіжими томатами та базиліком',
        'price': 180,
        'cook_time': 25,
        'rating': 4.8,
        'allergens': 'Глютен, Молоко'
    }
    
    print("=== Карточка товару ===")
    print(MenuFormatter.format_item_card(sample_item))
    
    print("\n\n=== Кошик ===")
    cart_items = [
        {'name': 'Піца "Маргарита"', 'category': 'Піца', 'quantity': 2, 'price': 180},
        {'name': 'Coca-Cola 0.5л', 'category': 'Напої', 'quantity': 1, 'price': 35}
    ]
    print(MenuFormatter.format_cart(cart_items, 395))
    
    print("\n\n=== Підтвердження замовлення ===")
    order = {
        'order_number': '1234',
        'items': cart_items,
        'total': 395,
        'phone': '+380501234567',
        'address': 'вул. Шевченка, 15, кв. 10',
        'delivery_time': '45-60 хв'
    }
    print(MenuFormatter.format_order_confirmation(order))
