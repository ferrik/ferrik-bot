"""
Централізована система мапінгу полів між Google Sheets та внутрішнім представленням
Вирішує проблему неузгодженості ключів між модулями

Автор: Claude AI
Дата: 2025-10-07
"""
from typing import Dict, List, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MenuField(str, Enum):
    """
    Стандартизовані назви полів меню (internal representation)
    Ці назви використовуються скрізь у коді
    """
    ID = "id"
    NAME = "name"
    CATEGORY = "category"
    PRICE = "price"
    DESCRIPTION = "description"
    AVAILABLE = "available"
    IMAGE_URL = "image_url"


# Мапінг колонок Google Sheets → internal fields
SHEETS_TO_INTERNAL = {
    'ID': MenuField.ID,
    'Страви': MenuField.NAME,  # Назва колонки в Google Sheets
    'Назва Страви': MenuField.NAME,  # Альтернативна назва
    'Категорія': MenuField.CATEGORY,
    'Ціна': MenuField.PRICE,
    'Опис': MenuField.DESCRIPTION,
    'Доступно': MenuField.AVAILABLE,
    'Зображення': MenuField.IMAGE_URL,
}

# Зворотній мапінг для запису назад у Sheets
INTERNAL_TO_SHEETS = {
    MenuField.ID: 'ID',
    MenuField.NAME: 'Назва Страви',
    MenuField.CATEGORY: 'Категорія',
    MenuField.PRICE: 'Ціна',
    MenuField.DESCRIPTION: 'Опис',
    MenuField.AVAILABLE: 'Доступно',
    MenuField.IMAGE_URL: 'Зображення',
}


def normalize_menu_item(raw_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Нормалізує item з Google Sheets до стандартного формату
    
    Args:
        raw_item: Сирий словник з Google Sheets (різні назви колонок)
    
    Returns:
        Нормалізований словник з стандартними полями MenuField
    
    Example:
        >>> raw = {'Страви': 'Борщ', 'Ціна': '120'}
        >>> normalized = normalize_menu_item(raw)
        >>> normalized['name']
        'Борщ'
    """
    normalized = {}
    
    for sheets_key, value in raw_item.items():
        # Знаходимо відповідне internal поле
        internal_field = SHEETS_TO_INTERNAL.get(sheets_key)
        
        if internal_field:
            normalized[internal_field.value] = value
        else:
            # Невідомий ключ - зберігаємо як є (для сумісності)
            logger.debug(f"Unknown field in raw_item: {sheets_key}")
            normalized[sheets_key] = value
    
    # Забезпечуємо наявність обов'язкових полів
    normalized.setdefault(MenuField.ID.value, None)
    normalized.setdefault(MenuField.NAME.value, "Без назви")
    normalized.setdefault(MenuField.CATEGORY.value, "Інше")
    normalized.setdefault(MenuField.PRICE.value, "0")
    normalized.setdefault(MenuField.DESCRIPTION.value, "")
    normalized.setdefault(MenuField.AVAILABLE.value, True)
    
    return normalized


def denormalize_menu_item(internal_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Конвертує internal формат назад у формат Google Sheets
    
    Args:
        internal_item: Словник з internal полями
    
    Returns:
        Словник з назвами колонок Google Sheets
    
    Example:
        >>> internal = {'name': 'Борщ', 'price': '120'}
        >>> sheets = denormalize_menu_item(internal)
        >>> sheets['Назва Страви']
        'Борщ'
    """
    sheets_item = {}
    
    for internal_key, value in internal_item.items():
        # Знаходимо відповідну назву колонки Sheets
        try:
            field = MenuField(internal_key)
            sheets_key = INTERNAL_TO_SHEETS.get(field)
            if sheets_key:
                sheets_item[sheets_key] = value
            else:
                sheets_item[internal_key] = value
        except ValueError:
            # Невідоме поле - зберігаємо як є
            sheets_item[internal_key] = value
    
    return sheets_item


def normalize_menu_list(raw_menu: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Нормалізує весь список меню з Google Sheets
    
    Args:
        raw_menu: Список сирих items з Sheets
    
    Returns:
        Список нормалізованих items
    """
    return [normalize_menu_item(item) for item in raw_menu]


def get_field_value(item: Dict[str, Any], field: MenuField, default: Any = None) -> Any:
    """
    Безпечно отримує значення поля з item (підтримує обидва формати)
    
    Спочатку шукає internal назву, потім legacy, потім Sheets назву
    
    Args:
        item: Menu item (normalized або raw)
        field: Поле для отримання
        default: Дефолтне значення
    
    Returns:
        Значення поля або default
    
    Example:
        >>> item = {'name': 'Борщ', 'Назва Страви': 'Борщ legacy'}
        >>> get_field_value(item, MenuField.NAME)
        'Борщ'  # Пріоритет internal назві
    """
    # Спробувати internal назву
    value = item.get(field.value)
    if value is not None:
        return value
    
    # Спробувати Sheets назву
    sheets_name = INTERNAL_TO_SHEETS.get(field)
    if sheets_name:
        value = item.get(sheets_name)
        if value is not None:
            return value
    
    # Спробувати всі можливі Sheets варіанти
    for sheets_key, internal_field in SHEETS_TO_INTERNAL.items():
        if internal_field == field:
            value = item.get(sheets_key)
            if value is not None:
                return value
    
    return default


def create_legacy_compatible_item(internal_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Створює item з обома форматами ключів для зворотної сумісності
    
    Використовувати під час міграції, щоб старий код продовжував працювати
    
    Args:
        internal_item: Словник з internal полями
    
    Returns:
        Словник з обома форматами ключів
    
    Example:
        >>> internal = {'name': 'Борщ', 'price': '120'}
        >>> compatible = create_legacy_compatible_item(internal)
        >>> compatible['name']  # Новий формат
        'Борщ'
        >>> compatible['Назва Страви']  # Старий формат
        'Борщ'
    """
    result = internal_item.copy()
    
    # Додаємо legacy ключі
    if MenuField.NAME.value in internal_item:
        result["Назва Страви"] = internal_item[MenuField.NAME.value]
    if MenuField.CATEGORY.value in internal_item:
        result["Категорія"] = internal_item[MenuField.CATEGORY.value]
    if MenuField.PRICE.value in internal_item:
        result["Ціна"] = internal_item[MenuField.PRICE.value]
    if MenuField.DESCRIPTION.value in internal_item:
        result["Опис"] = internal_item[MenuField.DESCRIPTION.value]
    if MenuField.ID.value in internal_item:
        result["ID"] = internal_item[MenuField.ID.value]
    
    return result


# Для backward compatibility - константи для старого коду
KEY_NAME = "Назва Страви"
KEY_CATEGORY = "Категорія"
KEY_PRICE = "Ціна"
KEY_DESCRIPTION = "Опис"
KEY_ID = "ID"


if __name__ == "__main__":
    # Тести для перевірки
    print("=" * 60)
    print("ТЕСТ FIELD MAPPING")
    print("=" * 60)
    
    # Тест 1: Нормалізація
    print("\n1. Нормалізація з Sheets формату:")
    raw_item = {
        'ID': '123',
        'Страви': 'Борщ український',
        'Категорія': 'Супи',
        'Ціна': '120',
    }
    normalized = normalize_menu_item(raw_item)
    print(f"   Raw: {raw_item}")
    print(f"   Normalized: {normalized}")
    
    # Тест 2: Денормалізація
    print("\n2. Денормалізація назад у Sheets:")
    sheets_format = denormalize_menu_item(normalized)
    print(f"   Back to Sheets: {sheets_format}")
    
    # Тест 3: Безпечне отримання
    print("\n3. Безпечне отримання значення:")
    name = get_field_value(normalized, MenuField.NAME)
    print(f"   Name: {name}")
    
    # Тест 4: Legacy сумісність
    print("\n4. Legacy-compatible формат:")
    compatible = create_legacy_compatible_item(normalized)
    print(f"   Має 'name': {'name' in compatible}")
    print(f"   Має 'Назва Страви': {'Назва Страви' in compatible}")
    print(f"   Обидва рівні: {compatible.get('name') == compatible.get('Назва Страви')}")
    
    print("\n" + "=" * 60)
    print("✅ ВСІ ТЕСТИ ПРОЙШЛИ")
    print("=" * 60)
