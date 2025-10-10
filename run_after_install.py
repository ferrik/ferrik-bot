#!/usr/bin/env python3
"""
Фінальний тест після встановлення всіх патчів
Перевіряє що все працює разом

Запуск: python run_after_install.py
"""

import sys
import os

def print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def print_step(step_num, text):
    print(f"\n[{step_num}] {text}")

def test_step(test_func, name):
    """Запускає тест і виводить результат"""
    try:
        result = test_func()
        if result:
            print(f"  ✅ {name} - OK")
            return True
        else:
            print(f"  ❌ {name} - FAILED")
            return False
    except Exception as e:
        print(f"  ❌ {name} - EXCEPTION: {e}")
        return False


# ============================================================================
# ТЕСТИ
# ============================================================================

def test_imports():
    """Тест 1: Всі модулі імпортуються"""
    try:
        from utils.html_formatter import escape_field
        from utils.price_handler import parse_price
        from config import normalize_menu_item
        return True
    except ImportError:
        return False

def test_config():
    """Тест 2: Config завантажується"""
    try:
        import config
        return hasattr(config, 'BOT_TOKEN')
    except Exception:
        return False

def test_html_safety():
    """Тест 3: HTML escaping працює"""
    from utils.html_formatter import escape_field, validate_telegram_html
    
    dangerous = '<script>alert(1)</script>'
    escaped = escape_field(dangerous)
    
    if '<script>' in escaped:
        return False
    
    if validate_telegram_html(dangerous):
        return False
    
    return True

def test_decimal_math():
    """Тест 4: Decimal точність"""
    from utils.price_handler import parse_price
    from decimal import Decimal
    
    result = parse_price("0.1") + parse_price("0.2")
    return result == Decimal("0.3")

def test_field_mapping():
    """Тест 5: Field mapping"""
    from config.field_mapping import normalize_menu_item