"""
Система обробки цін з Decimal для фінансової точності

ВИКОРИСТАННЯ:
    from utils.price_handler import parse_price, format_price, calculate_cart_total
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Any
import re

# Точність для грошових операцій (2 десяткові знаки)
PRICE_PRECISION = Decimal('0.01')


def parse_price(value: Any) -> Decimal:
    """
    Безпечно конвертує будь-яке значення в Decimal ціну
    
    Args:
        value: Ціна (str, int, float, Decimal)
    
    Returns:
        Decimal ціна з правильною точністю
    
    Raises:
        ValueError: якщо value не може бути сконвертовано в ціну
    """
    if isinstance(value, Decimal):
        return value.quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)
    
    if value is None or value == '':
        return Decimal('0.00')
    
    # Конвертуємо в string для безпечної обробки
    price_str = str(value).strip()
    
    # Видаляємо currency symbols та пробіли
    price_str = re.sub(r'[^\d.,-]', '', price_str)
    
    # Замінюємо кому на крапку (європейський формат)
    price_str = price_str.replace(',', '.')
    
    # Видаляємо множинні крапки (залишаємо тільки останню)
    parts = price_str.split('.')
    if len(parts) > 2:
        price_str = ''.join(parts[:-1]) + '.' + parts[-1]
    
    if not price_str or price_str == '.':
        return Decimal('0.00')
    
    try:
        price = Decimal(price_str)
        return price.quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)
    except InvalidOperation as e:
        raise ValueError(f"Неможливо конвертувати '{value}' в ціну: {e}")


def format_price(price: Union[Decimal, str, float, int], 
                 currency: str = "грн",
                 include_currency: bool = True) -> str:
    """
    Форматує ціну для відображення
    
    Args:
        price: Ціна для форматування
        currency: Символ валюти
        include_currency: Чи додавати валюту
    
    Returns:
        Відформатована ціна як string
    """
    decimal_price = parse_price(price)
    
    # Форматуємо з двома десятковими знаками
    formatted = f"{decimal_price:.2f}"
    
    if include_currency:
        return f"{formatted} {currency}"
    return formatted


def calculate_cart_total(cart: dict) -> Decimal:
    """
    Розраховує загальну суму корзини з точністю Decimal
    
    Args:
        cart: Словник {item_dict: quantity}
    
    Returns:
        Загальна сума як Decimal
    """
    total = Decimal('0.00')
    
    for item, quantity in cart.items():
        # item може бути словником або frozen dict
        if isinstance(item, dict):
            price_value = item.get('Ціна') or item.get('price', 0)
        else:
            # Якщо frozen dict або інший тип
            try:
                price_value = dict(item).get('Ціна') or dict(item).get('price', 0)
            except (TypeError, ValueError):
                price_value = 0
        
        item_price = parse_price(price_value)
        item_total = item_price * Decimal(str(quantity))
        total += item_total
    
    return total.quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)


def price_to_sheets_format(price: Union[Decimal, str, float, int]) -> str:
    """
    Конвертує ціну для збереження в Google Sheets
    
    Args:
        price: Ціна для конвертації
    
    Returns:
        String з двома десятковими знаками (без валюти)
    """
    decimal_price = parse_price(price)
    # Повертаємо просто число без валюти для Sheets
    return f"{decimal_price:.2f}"