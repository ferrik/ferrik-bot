"""
Google Sheets Service
Робота з Google Sheets API для меню та замовлень

Виправлення:
- Decimal замість float для цін
- Нормалізація полів через field_mapping
- Кращa обробка помилок
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
from utils.price_handler import price_to_sheets_format, parse_price
from config import normalize_menu_list, create_legacy_compatible_item

logger = logging.getLogger(__name__)

# Google Sheets API setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Кеш для service
_sheets_service = None


def get_sheets_service():
    """
    Отримує або створює Google Sheets service
    
    Returns:
        Google Sheets API service
    """
    global _sheets_service
    
    if _sheets_service is not None:
        return _sheets_service
    
    try:
        # Парсимо credentials з JSON
        if config.GOOGLE_CREDENTIALS_JSON:
            creds_dict = json.loads(config.GOOGLE_CREDENTIALS_JSON)
        else:
            raise ValueError("Google credentials not configured")
        
        # Створюємо credentials
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )
        
        # Створюємо service
        _sheets_service = build('sheets', 'v4', credentials=credentials)
        
        logger.info("✅ Google Sheets service initialized")
        return _sheets_service
        
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets service: {e}")
        raise


def get_menu_from_sheet() -> List[Dict[str, Any]]:
    """
    Отримує меню з Google Sheets
    
    ВИПРАВЛЕННЯ:
    - Нормалізація полів через field_mapping
    - Legacy compatibility
    - Кращa обробка помилок
    
    Returns:
        List of menu items з нормалізованими полями
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Читаємо заголовки (перший рядок)
        headers_result = sheet.values().get(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range='Menu!A1:Z1'
        ).execute()
        
        headers = headers_result.get('values', [[]])[0]
        
        if not headers:
            logger.error("No headers found in menu sheet")
            return []
        
        # Читаємо дані (з другого рядка)
        result = sheet.values().get(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range='Menu!A2:Z1000'
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.warning("No data found in menu sheet")
            return []
        
        # Конвертуємо в list of dicts
        raw_menu = []
        for row in values:
            # Доповнюємо пусті комірки
            if len(row) < len(headers):
                row = row + [''] * (len(headers) - len(row))
            
            # Створюємо dict
            item = dict(zip(headers, row))
            
            # Пропускаємо порожні рядки
            if not any(item.values()):
                continue
            
            raw_menu.append(item)
        
        logger.info(f"Loaded {len(raw_menu)} raw items from sheet")
        
        # КРИТИЧНО: Нормалізуємо поля
        normalized_menu = normalize_menu_list(raw_menu)
        
        # BACKWARD COMPATIBILITY: Додаємо legacy ключі
        compatible_menu = [create_legacy_compatible_item(item) for item in normalized_menu]
        
        logger.info(f"✅ Menu normalized: {len(compatible_menu)} items")
        return compatible_menu
        
    except HttpError as e:
        logger.error(f"HTTP error loading menu: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to load menu from sheets: {e}")
        return []


def save_order_to_sheets(order_id: str, cart: Dict, contact_info: Dict) -> bool:
    """
    Зберігає замовлення в Google Sheets
    
    КРИТИЧНЕ ВИПРАВЛЕННЯ:
    - Decimal замість float (БЕЗ ВТРАТИ ТОЧНОСТІ!)
    - Правильне форматування для Sheets
    - Кращa обробка помилок
    
    Args:
        order_id: ID замовлення
        cart: Словник {item: quantity}
        contact_info: Контактна інформація
    
    Returns:
        True якщо успішно, False якщо помилка
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Готуємо rows для запису
        rows_to_add = []
        
        for item, quantity in cart.items():
            # Конвертуємо item (може бути dict або frozenset)
            if isinstance(item, dict):
                item_dict = item
            else:
                try:
                    item_dict = dict(item)
                except (TypeError, ValueError):
                    logger.error(f"Cannot convert item to dict: {type(item)}")
                    continue
            
            # Отримуємо поля (підтримка обох форматів)
            item_name = item_dict.get('Назва Страви') or item_dict.get('name', 'N/A')
            item_category = item_dict.get('Категорія') or item_dict.get('category', 'N/A')
            price_value = item_dict.get('Ціна') or item_dict.get('price', 0)
            
            # ⚠️ КРИТИЧНО: Використовуємо price_to_sheets_format
            # ❌ НЕ РОБИТИ: float(str(price))  ← Втрата точності!
            # ✅ ПРАВИЛЬНО: price_to_sheets_format(price)
            price_formatted = price_to_sheets_format(price_value)
            
            # Розраховуємо total для рядка
            unit_price = parse_price(price_value)
            from decimal import Decimal
            item_total = unit_price * Decimal(str(quantity))
            total_formatted = price_to_sheets_format(item_total)
            
            # Формуємо row
            row = [
                str(order_id),                               # A: Order ID
                timestamp,                                   # B: Timestamp
                item_name,                                   # C: Item Name
                item_category,                               # D: Category
                int(quantity),                               # E: Quantity (int)
                price_formatted,                             # F: Unit Price (STRING!)
                total_formatted,                             # G: Total (STRING!)
                contact_info.get('phone', 'N/A'),           # H: Phone
                contact_info.get('address', 'N/A'),         # I: Address
                contact_info.get('name', 'N/A'),            # J: Customer Name
            ]
            
            rows_to_add.append(row)
        
        if not rows_to_add:
            logger.warning(f"No rows to add for order {order_id}")
            return False
        
        # Записуємо в Sheets
        body = {
            'values': rows_to_add
        }
        
        result = sheet.values().append(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range='Orders!A:J',  # Adjust if your sheet has different name/columns
            valueInputOption='RAW',  # ВАЖЛИВО: RAW щоб зберегти string format
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        updated_cells = result.get('updates', {}).get('updatedCells', 0)
        logger.info(f"✅ Order {order_id} saved to sheets: {updated_cells} cells updated")
        
        return True
        
    except HttpError as e:
        logger.error(f"HTTP error saving order {order_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to save order {order_id} to sheets: {e}")
        # НЕ кидаємо exception - це не критично якщо Sheets failed
        return False


def get_orders_from_sheet(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Отримує останні замовлення з Sheets
    
    Args:
        limit: Максимальна кількість замовлень
    
    Returns:
        List of orders
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Читаємо заголовки
        headers_result = sheet.values().get(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range='Orders!A1:J1'
        ).execute()
        
        headers = headers_result.get('values', [[]])[0]
        
        if not headers:
            logger.warning("No headers in Orders sheet")
            return []
        
        # Читаємо дані
        result = sheet.values().get(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range=f'Orders!A2:J{limit + 1}'
        ).execute()
        
        values = result.get('values', [])
        
        # Конвертуємо в list of dicts
        orders = []
        for row in values:
            if len(row) < len(headers):
                row = row + [''] * (len(headers) - len(row))
            
            order = dict(zip(headers, row))
            orders.append(order)
        
        logger.info(f"Loaded {len(orders)} orders from sheet")
        return orders
        
    except Exception as e:
        logger.error(f"Failed to load orders: {e}")
        return []


def update_menu_item(item_id: str, updates: Dict[str, Any]) -> bool:
    """
    Оновлює товар в меню
    
    Args:
        item_id: ID товару
        updates: Словник з полями для оновлення
    
    Returns:
        True якщо успішно
    """
    try:
        # TODO: Реалізувати якщо потрібна функція редагування
        logger.warning("update_menu_item not implemented yet")
        return False
        
    except Exception as e:
        logger.error(f"Failed to update menu item {item_id}: {e}")
        return False


def add_menu_item(item: Dict[str, Any]) -> bool:
    """
    Додає новий товар в меню
    
    Args:
        item: Словник з даними товару
    
    Returns:
        True якщо успішно
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Формуємо row (відповідно до структури вашої таблиці)
        row = [
            item.get('ID', ''),
            item.get('Назва Страви', ''),
            item.get('Категорія', ''),
            price_to_sheets_format(item.get('Ціна', 0)),
            item.get('Опис', ''),
            item.get('Доступно', 'Так'),
        ]
        
        body = {'values': [row]}
        
        result = sheet.values().append(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range='Menu!A:F',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logger.info(f"✅ Menu item added: {item.get('Назва Страви')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add menu item: {e}")
        return False


def test_sheets_connection() -> bool:
    """
    Тестує з'єднання з Google Sheets
    
    Returns:
        True якщо з'єднання OK
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Пробуємо прочитати назву таблиці
        result = sheet.get(spreadsheetId=config.GOOGLE_SHEET_ID).execute()
        title = result.get('properties', {}).get('title', 'Unknown')
        
        logger.info(f"✅ Sheets connection OK. Connected to: '{title}'")
        return True
        
    except Exception as e:
        logger.error(f"❌ Sheets connection failed: {e}")
        return False


def get_sheet_info() -> Dict[str, Any]:
    """
    Отримує інформацію про таблицю
    
    Returns:
        Dict з метаданими таблиці
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        result = sheet.get(spreadsheetId=config.GOOGLE_SHEET_ID).execute()
        
        info = {
            'title': result.get('properties', {}).get('title'),
            'sheets': [s['properties']['title'] for s in result.get('sheets', [])],
            'url': f"https://docs.google.com/spreadsheets/d/{config.GOOGLE_SHEET_ID}"
        }
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get sheet info: {e}")
        return {}


# ============================================================================
# HELPER ФУНКЦІЇ
# ============================================================================

def validate_menu_item(item: Dict[str, Any]) -> tuple:
    """
    Валідує що item містить всі необхідні поля
    
    Args:
        item: Словник товару
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    required_fields = ['Назва Страви', 'Ціна', 'Категорія']
    
    for field in required_fields:
        if field not in item or not item[field]:
            return False, f"Missing required field: {field}"
    
    # Перевірка що ціна валідна
    from utils.price_handler import validate_price
    is_valid, error = validate_price(item['Ціна'])
    if not is_valid:
        return False, f"Invalid price: {error}"
    
    return True, ""


def format_price_for_display(price_value: Any) -> str:
    """
    Форматує ціну для відображення
    
    Args:
        price_value: Ціна
    
    Returns:
        Відформатована строка з валютою
    """
    from utils.price_handler import format_price
    return format_price(price_value)


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    'get_sheets_service',
    'get_menu_from_sheet',
    'save_order_to_sheets',
    'get_orders_from_sheet',
    'update_menu_item',
    'add_menu_item',
    'test_sheets_connection',
    'get_sheet_info',
    'validate_menu_item',
]