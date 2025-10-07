"""
Безпечний HTML форматер для Telegram Bot API
Виправляє проблему з XSS та некоректним escaping

ВИКОРИСТАННЯ:
    from utils.html_formatter import format_item_safe, escape_field
"""
import html
import re
from typing import Dict, Any

# Дозволені Telegram HTML теги (без атрибутів)
ALLOWED_TAGS = {'b', 'i', 'code', 'pre', 's', 'u', 'a', 'tg-spoiler'}


def escape_field(value: Any) -> str:
    """
    Безпечно ескейпить одне поле (назва, опис, ціна)
    
    Args:
        value: Значення для ескейпу (str, int, float, Decimal)
    
    Returns:
        Escaped string безпечний для вставки в HTML
    """
    if value is None:
        return ""
    return html.escape(str(value))


def format_item_safe(item: Dict[str, Any]) -> str:
    """
    Форматує елемент меню з безпечним HTML
    
    Args:
        item: Словник з полями Назва Страви, Опис, Ціна, Категорія
    
    Returns:
        HTML-відформатований текст з правильним escaping
    """
    name = escape_field(item.get('Назва Страви', 'Без назви'))
    category = escape_field(item.get('Категорія', 'Без категорії'))
    price = escape_field(item.get('Ціна', '0'))
    description = escape_field(item.get('Опис', ''))
    
    # Складаємо HTML з вже escaped даних
    result = f"<b>{name}</b>\n"
    result += f"<i>Категорія:</i> {category}\n"
    
    if description:
        result += f"{description}\n"
    
    result += f"<b>Ціна:</b> {price} грн"
    
    return result


def format_cart_item_safe(item: Dict[str, Any], quantity: int) -> str:
    """
    Форматує товар у корзині з безпечним HTML
    """
    name = escape_field(item.get('Назва Страви', 'Невідомий товар'))
    price = escape_field(item.get('Ціна', '0'))
    
    return f"<b>{name}</b> x{quantity} = {price} грн"


def validate_telegram_html(text: str) -> bool:
    """
    Перевіряє, чи містить текст тільки дозволені Telegram теги
    
    Args:
        text: HTML текст для перевірки
    
    Returns:
        True якщо текст безпечний, False якщо містить недозволені теги
    """
    # Знаходимо всі теги
    tag_pattern = r'</?(\w+)(?:\s[^>]*)?>'
    tags = re.findall(tag_pattern, text)
    
    # Перевіряємо, чи всі теги дозволені
    for tag in tags:
        if tag.lower() not in ALLOWED_TAGS:
            return False
    
    # Перевіряємо наявність атрибутів (крім href для <a>)
    dangerous_pattern = r'<(?!a\s+href=)[^>]+\s+\w+='
    if re.search(dangerous_pattern, text):
        return False
    
    return True


def sanitize_user_input(text: str) -> str:
    """
    Очищує user input від HTML тегів (для пошуку, номерів телефону)
    
    Args:
        text: Текст від користувача
    
    Returns:
        Текст без HTML тегів
    """
    # Видаляємо всі HTML теги
    clean = re.sub(r'<[^>]+>', '', text)
    # Видаляємо зайві пробіли
    clean = ' '.join(clean.split())
    return clean.strip()