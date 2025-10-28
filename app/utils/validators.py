"""
🛡️ Валідатори та парсери даних
Оновлена версія з розширеним функціоналом
"""
import re
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# Парсинг цін та кількості
# ============================================================================

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


def calculate_total_price(items: List[Dict[str, Any]]) -> float:
    """Розрахунок загальної вартості замовлення"""
    total = 0.0
    for item in items:
        price = safe_parse_price(item.get('price', 0))
        quantity = safe_parse_quantity(item.get('quantity', 1))
        total += price * quantity
    return round(total, 2)


# ============================================================================
# Валідація телефонів
# ============================================================================

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
    
    if len(clean) == 9:  # без 0 на початку
        return True  # 501234567
    
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


def format_phone_display(phone: str) -> str:
    """Форматування телефону для відображення: +380 (50) 123-45-67"""
    normalized = normalize_phone(phone)
    if not normalized:
        return phone
    
    # +380501234567 -> +380 (50) 123-45-67
    if len(normalized) == 13:
        return f"{normalized[:4]} ({normalized[4:6]}) {normalized[6:9]}-{normalized[9:11]}-{normalized[11:]}"
    
    return normalized


# ============================================================================
# Валідація адреси
# ============================================================================

def validate_address(address: str) -> bool:
    """Перевірка адреси доставки"""
    if not address or len(address.strip()) < 10:
        return False
    
    # Має містити хоча б одну цифру (номер будинку)
    if not re.search(r'\d', address):
        return False
    
    return True


def parse_address(address: str) -> Dict[str, str]:
    """
    Парсинг адреси на компоненти
    
    Приклад: "вул. Хрещатик, 1, кв. 5" ->
    {
        'street': 'вул. Хрещатик',
        'building': '1',
        'apartment': '5',
        'full': 'вул. Хрещатик, 1, кв. 5'
    }
    """
    result = {
        'street': '',
        'building': '',
        'apartment': '',
        'full': address.strip()
    }
    
    if not address:
        return result
    
    # Спроба знайти квартиру
    apt_match = re.search(r'кв\.?\s*(\d+)', address, re.IGNORECASE)
    if apt_match:
        result['apartment'] = apt_match.group(1)
    
    # Спроба знайти номер будинку
    building_match = re.search(r',\s*(\d+[а-яА-Я]?)\s*[,.]?', address)
    if building_match:
        result['building'] = building_match.group(1)
    
    # Вулиця - все до першої коми або цифри
    street_match = re.match(r'^([^,]+?)(?=\s*,|\s*\d)', address)
    if street_match:
        result['street'] = street_match.group(1).strip()
    
    return result


# ============================================================================
# Очищення введення
# ============================================================================

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


def validate_text_length(text: str, min_len: int = 1, max_len: int = 500) -> bool:
    """Перевірка довжини тексту"""
    if not text:
        return min_len == 0
    
    length = len(text.strip())
    return min_len <= length <= max_len


# ============================================================================
# Валідація даних товару
# ============================================================================

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


def validate_order_data(order: dict) -> tuple[bool, Optional[str]]:
    """
    Валідація даних замовлення
    
    Returns:
        (is_valid, error_message)
    """
    # Перевірка обов'язкових полів
    if not order.get('items') or len(order['items']) == 0:
        return False, "❌ Замовлення не містить товарів"
    
    if not order.get('phone'):
        return False, "❌ Не вказано номер телефону"
    
    if not validate_phone(order['phone']):
        return False, "❌ Некоректний формат телефону"
    
    if not order.get('address'):
        return False, "❌ Не вказано адресу доставки"
    
    if not validate_address(order['address']):
        return False, "❌ Некоректна адреса доставки (має бути мінімум 10 символів та містити номер будинку)"
    
    # Перевірка товарів
    for item in order['items']:
        if not validate_item_data(item):
            return False, f"❌ Некоректні дані товару: {item.get('name', 'Unknown')}"
    
    # Перевірка загальної суми
    total = calculate_total_price(order['items'])
    if total <= 0:
        return False, "❌ Загальна сума замовлення повинна бути більше 0"
    
    return True, None


# ============================================================================
# Валідація email
# ============================================================================

def validate_email(email: str) -> bool:
    """Проста валідація email"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# ============================================================================
# Валідація дати та часу
# ============================================================================

def validate_delivery_time(time_str: str) -> bool:
    """
    Валідація часу доставки
    
    Формати: "14:30", "09:00"
    """
    if not time_str:
        return False
    
    pattern = r'^([01]\d|2[0-3]):([0-5]\d)$'
    return bool(re.match(pattern, time_str))


def parse_delivery_time(time_str: str) -> Optional[tuple[int, int]]:
    """
    Парсинг часу доставки
    
    Returns: (hour, minute) or None
    """
    if not validate_delivery_time(time_str):
        return None
    
    hour, minute = map(int, time_str.split(':'))
    return (hour, minute)


# ============================================================================
# Helpers для форматування
# ============================================================================

def format_price(price: float, currency: str = "грн") -> str:
    """Форматування ціни для відображення"""
    return f"{price:.2f} {currency}"


def format_order_summary(order: dict) -> str:
    """Форматування замовлення для відображення"""
    lines = ["📦 Ваше замовлення:\n"]
    
    for idx, item in enumerate(order.get('items', []), 1):
        name = item.get('name', 'Unknown')
        price = safe_parse_price(item.get('price', 0))
        quantity = safe_parse_quantity(item.get('quantity', 1))
        total = price * quantity
        
        lines.append(f"{idx}. {name}")
        lines.append(f"   {quantity} × {format_price(price)} = {format_price(total)}\n")
    
    total = calculate_total_price(order['items'])
    lines.append(f"\n💰 Всього: {format_price(total)}")
    
    if order.get('phone'):
        lines.append(f"\n📱 Телефон: {format_phone_display(order['phone'])}")
    
    if order.get('address'):
        lines.append(f"📍 Адреса: {order['address']}")
    
    if order.get('comment'):
        lines.append(f"💬 Коментар: {order['comment']}")
    
    return "\n".join(lines)


# ============================================================================
# Тестування (для розробки)
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTING VALIDATORS")
    print("=" * 60)
    
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
    
    print("\n💰 Testing prices:")
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
    
    print("\n📱 Testing phones:")
    for phone, expected in test_phones:
        result = validate_phone(phone)
        normalized = normalize_phone(phone)
        formatted = format_phone_display(phone) if normalized else "N/A"
        status = "✅" if result == expected else "❌"
        print(f"{status} {phone}")
        print(f"   Valid: {result}, Normalized: {normalized}, Formatted: {formatted}")
    
    # Тест адреси
    test_addresses = [
        "вул. Хрещатик, 1, кв. 5",
        "Дарвіна 10а",
        "проспект Миру 150"
    ]
    
    print("\n📍 Testing addresses:")
    for addr in test_addresses:
        is_valid = validate_address(addr)
        parsed = parse_address(addr)
        print(f"{'✅' if is_valid else '❌'} {addr}")
        print(f"   Parsed: {parsed}")
    
    # Тест замовлення
    test_order = {
        'items': [
            {'id': '1', 'name': 'Піца Маргарита', 'price': '120 грн', 'quantity': 2},
            {'id': '2', 'name': 'Coca-Cola', 'price': '30', 'quantity': 1}
        ],
        'phone': '0501234567',
        'address': 'вул. Хрещатик, 1, кв. 5',
        'comment': 'Додзвоніться за 10 хв'
    }
    
    print("\n📦 Testing order:")
    is_valid, error = validate_order_data(test_order)
    print(f"{'✅' if is_valid else '❌'} Order validation: {error if error else 'OK'}")
    print(f"\nOrder summary:\n{format_order_summary(test_order)}")
    
    print("\n" + "=" * 60)
