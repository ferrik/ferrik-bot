"""
🛡️ Валідатори та парсери даних
"""
import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

def safe_parse_price(value: Any) -> float:
    """
    Безпечно парсить ціну з будь-якого формату
    
    Приклади:
        "30 грн" -> 30.0
        "45,5" -> 45.5
        "120.50 грн" -> 120.5
        None -> 0.0
        "" -> 0.0
        "invalid" -> 0.0
    """
    if value is None or value == '':
        return 0.0
    
    try:
        # Конвертуємо в рядок та очищуємо
        clean = str(value).strip()
        
        # Видаляємо текст (грн, uah, тощо)
        clean = re.sub(r'[^\d.,\-]', '', clean)
        
        # Заміна коми на крапку
        clean = clean.replace(',', '.')
        
        # Якщо порожній рядок після очищення
        if not clean or clean == '.':
            return 0.0
        
        # Конвертуємо в float
        result = float(clean)
        
        # Перевірка на адекватність (захист від помилок)
        if result < 0:
            logger.warning(f"⚠️ Negative price detected: {value} -> {result}")
            return 0.0
        
        if result > 1000000:  # 1 млн - максимальна ціна
            logger.warning(f"⚠️ Unrealistic price: {value} -> {result}")
            return 0.0
            
        return result
        
    except (ValueError, TypeError) as e:
        logger.warning(f"❌ Invalid price format: {value} -> {e}")
        return 0.0


def safe_parse_quantity(value: Any) -> int:
    """Безпечно парсить кількість"""
    if value is None or value == '':
        return 0
    
    try:
        qty = int(float(str(value)))
        return max(0, min(qty, 999))  # 0-999
    except (ValueError, TypeError):
        logger.warning(f"❌ Invalid quantity: {value}")
        return 0


def validate_phone(phone: str) -> bool:
    """
    Перевірка українського номера телефону
    
    Формати:
        +380501234567
        0501234567
        380501234567
    """
    if not phone:
        return False
    
    # Видаляємо всі нецифрові символи
    clean = re.sub(r'\D', '', phone)
    
    # Перевірка формату
    if len(clean) == 10 and clean.startswith('0'):
        return True  # 0501234567
    
    if len(clean) == 12 and clean.startswith('380'):
        return True  # 380501234567
    
    return False


def normalize_phone(phone: str) -> Optional[str]:
    """Нормалізація телефону до формату +380XXXXXXXXX"""
    if not phone:
        return None
    
    clean = re.sub(r'\D', '', phone)
    
    if len(clean) == 10 and clean.startswith('0'):
        return f"+38{clean}"
    
    if len(clean) == 12 and clean.startswith('380'):
        return f"+{clean}"
    
    if len(clean) == 9:  # без 0 на початку
        return f"+380{clean}"
    
    return None


def validate_address(address: str) -> bool:
    """Перевірка адреси доставки"""
    if not address or len(address.strip()) < 10:
        return False
    
    # Має містити хоча б одну цифру (номер будинку)
    if not re.search(r'\d', address):
        return False
    
    return True


def sanitize_input(text: str, max_length: int = 500) -> str:
    """Очищення введення користувача від небезпечних символів"""
    if not text:
        return ""
    
    # Обмеження довжини
    text = text[:max_length]
    
    # Видалення HTML тегів (базовий захист)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Видалення керуючих символів
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text.strip()


def validate_item_data(item: dict) -> bool:
    """
    Перевірка коректності даних товару з Google Sheets
    
    Required fields: id, name, price
    """
    required_fields = ['id', 'name', 'price']
    
    for field in required_fields:
        if field not in item or not item[field]:
            logger.error(f"❌ Missing required field '{field}' in item: {item}")
            return False
    
    # Перевірка ціни
    price = safe_parse_price(item['price'])
    if price <= 0:
        logger.error(f"❌ Invalid price for item: {item}")
        return False
    
    return True


# ============================================================================
# Тестування (для розробки)
# ============================================================================
if __name__ == "__main__":
    # Тести цін
    test_prices = [
        ("30 грн", 30.0),
        ("45,5", 45.5),
        ("120.50 грн", 120.5),
        (None, 0.0),
        ("", 0.0),
        ("invalid", 0.0),
        ("-50", 0.0),
        ("1000000000", 0.0)
    ]
    
    print("🧪 Testing prices:")
    for input_val, expected in test_prices:
        result = safe_parse_price(input_val)
        status = "✅" if result == expected else "❌"
        print(f"{status} {input_val} -> {result} (expected {expected})")
    
    # Тести телефонів
    test_phones = [
        ("+380501234567", True),
        ("0501234567", True),
        ("380501234567", True),
        ("501234567", True),
        ("123", False),
        ("", False)
    ]
    
    print("\n🧪 Testing phones:")
    for phone, expected in test_phones:
        result = validate_phone(phone)
        normalized = normalize_phone(phone)
        status = "✅" if result == expected else "❌"
        print(f"{status} {phone} -> valid={result}, normalized={normalized}")
