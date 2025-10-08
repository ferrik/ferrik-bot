"""
Field mapping для зворотної сумісності та нормалізації даних.
"""

def normalize_menu_item(item):
    """
    Нормалізує елемент меню. Наразі просто повертає item,
    але може бути розширено в майбутньому.
    """
    return item

def get_field_value(item, field, default=None):
    """
    Безпечно отримує значення з елемента меню, підтримуючи
    як рядкові ключі, так і enum-поля.
    """
    # Якщо field - це enum, отримуємо його значення (value)
    if hasattr(field, 'value'):
        field = field.value
    return item.get(field, default)

def create_legacy_compatible_item(item):
    """
    Створює об'єкт, сумісний зі старою логікою.
    Наразі повертає item без змін.
    """
    return item

class MenuField:
    """
    Константи для полів меню, щоб уникнути помилок
    при наборі тексту (magic strings).
    """
    NAME = "Назва Страви"
    CATEGORY = "Категорія"
    PRICE = "Ціна"
    DESCRIPTION = "Опис"

