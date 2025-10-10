"""
Швидкі тести для перевірки що все працює після встановлення

Запуск: python tests/test_quick.py
"""
import sys
from decimal import Decimal

def test_imports():
    """Тест 1: Перевірка що всі модулі імпортуються"""
    print("Тест 1: Імпорти...")
    
    try:
        from utils.html_formatter import escape_field, validate_telegram_html
        print("  ✅ html_formatter імпортовано")
    except ImportError as e:
        print(f"  ❌ html_formatter: {e}")
        return False
    
    try:
        from utils.price_handler import parse_price, format_price
        print("  ✅ price_handler імпортовано")
    except ImportError as e:
        print(f"  ❌ price_handler: {e}")
        return False
    
    try:
        from config import normalize_menu_item, MenuField
        print("  ✅ field_mapping імпортовано")
    except ImportError as e:
        print(f"  ❌ field_mapping: {e}")
        return False
    
    return True


def test_xss_protection():
    """Тест 2: XSS захист"""
    print("\nТест 2: XSS Protection...")
    
    from utils.html_formatter import escape_field, validate_telegram_html
    
    # Тест escape
    dangerous = '<script>alert("xss")</script>'
    escaped = escape_field(dangerous)
    
    if '<script>' in escaped:
        print(f"  ❌ XSS не заблоковано: {escaped}")
        return False
    print(f"  ✅ XSS заблоковано: {escaped[:50]}...")
    
    # Тест validation
    safe_html = "<b>Safe text</b>"
    dangerous_html = '<script>alert(1)</script>'
    
    if not validate_telegram_html(safe_html):
        print("  ❌ Безпечний HTML відхилено")
        return False
    
    if validate_telegram_html(dangerous_html):
        print("  ❌ Небезпечний HTML прийнято")
        return False
    
    print("  ✅ Validation працює правильно")
    return True


def test_decimal_precision():
    """Тест 3: Decimal точність"""
    print("\nТест 3: Decimal Precision...")
    
    from utils.price_handler import parse_price
    
    # Класична проблема float
    result = parse_price("0.1") + parse_price("0.2")
    expected = Decimal("0.3")
    
    if result != expected:
        print(f"  ❌ Decimal неточний: {result} != {expected}")
        return False
    
    print(f"  ✅ 0.1 + 0.2 = {result} (точно!)")
    
    # Тест parse різних форматів
    test_cases = [
        ("120", Decimal("120.00")),
        ("120.50", Decimal("120.50")),
        ("120,50", Decimal("120.50")),  # Європейський формат
        ("120 грн", Decimal("120.00")),
    ]
    
    for input_val, expected_val in test_cases:
        result = parse_price(input_val)
        if result != expected_val:
            print(f"  ❌ parse_price('{input_val}') = {result}, очікувалось {expected_val}")
            return False
    
    print("  ✅ Парсинг всіх форматів працює")
    return True


def test_field_mapping():
    """Тест 4: Field Mapping"""
    print("\nТест 4: Field Mapping...")
    
    from config import normalize_menu_item, get_field_value, MenuField
    
    # Тест нормалізації
    raw_item = {
        'Страви': 'Борщ',  # Sheets формат
        'Ціна': '120',
        'Категорія': 'Супи'
    }
    
    normalized = normalize_menu_item(raw_item)
    
    # Перевірка internal ключів
    if normalized.get('name') != 'Борщ':
        print(f"  ❌ Нормалізація не спрацювала: {normalized}")
        return False
    
    print(f"  ✅ Нормалізація: {raw_item} → {normalized}")
    
    # Тест get_field_value
    value = get_field_value(normalized, MenuField.NAME)
    if value != 'Борщ':
        print(f"  ❌ get_field_value повернув {value}")
        return False
    
    print("  ✅ get_field_value працює")
    return True


def test_cart_calculation():
    """Тест 5: Розрахунок корзини"""
    print("\nТест 5: Cart Calculation...")
    
    from utils.price_handler import calculate_cart_total
    
    # Створюємо тестову корзину
    cart = {
        frozenset({'Ціна': '120.50', 'name': 'Item1'}.items()): 2,
        frozenset({'Ціна': '99.99', 'name': 'Item2'}.items()): 1,
    }
    
    total = calculate_cart_total(cart)
    expected = Decimal('340.99')  # 120.50*2 + 99.99
    
    if total != expected:
        print(f"  ❌ Розрахунок неправильний: {total} != {expected}")
        return False
    
    print(f"  ✅ Total: {total} (правильно!)")
    return True


def test_sheets_format():
    """Тест 6: Формат для Sheets"""
    print("\nТест 6: Sheets Format...")
    
    from utils.price_handler import price_to_sheets_format
    
    test_cases = [
        (Decimal("120.50"), "120.50"),
        ("99", "99.00"),
        (150.123, "150.12"),  # Округлення
    ]
    
    for input_val, expected in test_cases:
        result = price_to_sheets_format(input_val)
        if result != expected:
            print(f"  ❌ {input_val} → {result}, очікувалось {expected}")
            return False
        if not isinstance(result, str):
            print(f"  ❌ Результат не string: {type(result)}")
            return False
    
    print("  ✅ Всі формати Sheets правильні")
    return True


def run_all_tests():
    """Запускає всі тести"""
    print("=" * 60)
    print("ШВИДКА ПЕРЕВІРКА ПІСЛЯ ВСТАНОВЛЕННЯ")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_xss_protection,
        test_decimal_precision,
        test_field_mapping,
        test_cart_calculation,
        test_sheets_format,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ EXCEPTION: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТИ: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 ВСІ ТЕСТИ ПРОЙШЛИ! Можна починати міграцію.")
        return 0
    else:
        print("⚠️  Є проблеми. Перевірте помилки вище.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
```

---

## 📄 10. Швидкий setup script `setup.sh`

```bash
#!/bin/bash
# Швидкий setup для нових модулів

echo "🚀 Starting setup..."

# Створити структуру
echo "📁 Creating directories..."
mkdir -p utils config state tests

# Створити __init__ файли
echo "📝 Creating __init__.py files..."
touch utils/__init__.py
touch config/__init__.py
touch state/__init__.py
touch tests/__init__.py

# Перевірка Python
echo "🐍 Checking Python version..."
python --version

# Встановлення залежностей
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Копіювати .env.example якщо .env не існує
if [ ! -f .env ]; then
    echo "⚙️  Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  ВАЖЛИВО: Відредагуйте .env файл з вашими credentials!"
else
    echo "✅ .env already exists"
fi

# Запустити тести
echo "🧪 Running tests..."
python tests/test_quick.py

echo ""
echo "=" 
echo "✅ Setup complete!"
echo "=" 
echo ""
echo "Next steps:"
echo "1. Відредагуйте .env файл"
echo "2. Скопіюйте код з артефактів у відповідні файли"
echo "3. Запустіть: python tests/test_quick.py"
echo "4. Якщо тести OK - почніть міграцію main.py"
```

Зробіть executable:
```bash
chmod +x setup.sh
```

---

## 🎯 ІНСТРУКЦІЯ ПО КОПІЮВАННЮ

### Крок 1: Створити структуру (в терміналі)

```bash
# Перейти в корінь проекту
cd /path/to/your/bot/project

# Запустити setup
bash setup.sh

# АБО вручну:
mkdir -p utils config state tests
touch utils/__init__.py config/__init__.py state/__init__.py tests/__init__.py
```

### Крок 2: Скопіювати файли

Відкрийте кожен артефакт і **повністю скопіюйте** код:

1. **`full_html_formatter`** → копіювати в `utils/html_formatter.py`
2. **`full_price_handler`** → копіювати в `utils/price_handler.py`
3. **`full_field_mapping`** → копіювати в `config/field_mapping.py`
4. **`full_quick_test`** → копіювати в `tests/test_quick.py`
5. `.env.example` → скопіювати текст вище
6. `requirements.txt` → додати рядки з вище
7. `.gitignore` → додати рядки з вище

### Крок 3: Перевірка

```bash
# Встановити залежності
pip install -r requirements.txt

# Запустити тести
python tests/test_quick.py

# Очікується вивід:
# ✅ Всі тести пройшли
```

### Крок 4: Налаштувати .env

```bash
# Скопіювати приклад
cp .env.example .env

# Відредагувати (вставити свої credentials)
nano .env
# або
vim .env
```

---

## ✅ CHECKLIST

Після копіювання всіх файлів перевірте:

- [ ] `utils/html_formatter.py` існує і містить код
- [ ] `utils/price_handler.py` існує і містить код
- [ ] `config/field_mapping.py` існує і містить код
- [ ] `tests/test_quick.py` існує і містить код
- [ ] `.env.example` створено
- [ ] `.gitignore` оновлено
- [ ] `requirements.txt` оновлено
- [ ] `python tests/test_quick.py` виконується без помилок

---

**Далі що?** Після успішного проходження тестів переходьте до модифікації `main.py` та `services/sheets.py`. Хочете щоб я надав **повні версії цих файлів зі змінами**?