"""
Google Sheets Integration
Робота з Google Sheets як базою даних
"""
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import config

logger = logging.getLogger(__name__)

# Перевірка наявності gspread
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    logger.error("❌ gspread not installed")
    GSPREAD_AVAILABLE = False

# Глобальний клієнт
_sheet_client = None
_menu_cache = []
_menu_cache_time = None
CACHE_TTL = 300  # 5 хвилин


def get_sheet_client():
    """
    Отримати клієнт Google Sheets
    
    Returns:
        gspread.Client або None
    """
    global _sheet_client
    
    if _sheet_client:
        return _sheet_client
    
    if not GSPREAD_AVAILABLE:
        logger.error("❌ gspread not available")
        return None
    
    if not config.GOOGLE_SHEET_ID:
        logger.error("❌ GOOGLE_SHEET_ID not set")
        return None
    
    if not config.GOOGLE_CREDENTIALS:
        logger.error("❌ GOOGLE_CREDENTIALS not set")
        return None
    
    try:
        # Парсинг credentials з JSON string
        creds_dict = json.loads(config.GOOGLE_CREDENTIALS)
        
        # Налаштування OAuth2
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=scopes
        )
        
        _sheet_client = gspread.authorize(credentials)
        logger.info("✅ Google Sheets client authorized")
        
        return _sheet_client
        
    except Exception as e:
        logger.error(f"❌ Failed to authorize Google Sheets: {e}")
        return None


def get_menu_from_sheet() -> List[Dict[str, Any]]:
    """
    Завантажити меню з Google Sheets
    
    Returns:
        list: Список страв
    """
    global _menu_cache, _menu_cache_time
    
    # Перевірка кешу
    if _menu_cache and _menu_cache_time:
        age = (datetime.now() - _menu_cache_time).total_seconds()
        if age < CACHE_TTL:
            logger.info(f"✅ Menu from cache ({len(_menu_cache)} items)")
            return _menu_cache
    
    # Завантаження з Sheets
    client = get_sheet_client()
    if not client:
        logger.error("❌ Cannot get sheet client")
        return []
    
    try:
        # Відкриваємо таблицю
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        
        # Аркуш "Меню"
        menu_sheet = sheet.worksheet(config.SHEET_NAMES.get('menu', 'Меню'))
        
        # Отримати всі дані
        records = menu_sheet.get_all_records()
        
        # Фільтрація активних
        active_items = []
        for item in records:
            is_active = str(item.get('Активний', 'TRUE')).upper()
            
            if is_active in ['TRUE', 'ТАК', '1', 'YES']:
                active_items.append(item)
        
        # Оновлення кешу
        _menu_cache = active_items
        _menu_cache_time = datetime.now()
        
        logger.info(f"✅ Menu loaded: {len(active_items)} items")
        return active_items
        
    except Exception as e:
        logger.error(f"❌ Failed to load menu: {e}")
        return _menu_cache  # Повертаємо старий кеш


def save_order_to_sheet(order_data: Dict[str, Any]) -> bool:
    """
    Зберегти замовлення в Google Sheets
    
    Args:
        order_data: Дані замовлення
    
    Returns:
        bool: True якщо успішно
    """
    client = get_sheet_client()
    if not client:
        return False
    
    try:
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        orders_sheet = sheet.worksheet(config.SHEET_NAMES.get('orders', 'Замовлення'))
        
        # Формування рядка
        row = [
            order_data.get('order_id', ''),
            order_data.get('user_id', ''),
            order_data.get('username', ''),
            order_data.get('timestamp', datetime.now().isoformat()),
            json.dumps(order_data.get('items', []), ensure_ascii=False),
            order_data.get('total', 0),
            order_data.get('status', 'new'),
            order_data.get('phone', ''),
            order_data.get('address', ''),
            order_data.get('notes', '')
        ]
        
        # Додавання рядка
        orders_sheet.append_row(row)
        
        logger.info(f"✅ Order saved: {order_data.get('order_id')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save order: {e}")
        return False


def get_orders_by_status(status: str = 'new') -> List[Dict[str, Any]]:
    """
    Отримати замовлення за статусом
    
    Args:
        status: Статус замовлення
    
    Returns:
        list: Список замовлень
    """
    client = get_sheet_client()
    if not client:
        return []
    
    try:
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        orders_sheet = sheet.worksheet(config.SHEET_NAMES.get('orders', 'Замовлення'))
        
        records = orders_sheet.get_all_records()
        
        # Фільтрація по статусу
        filtered = [
            order for order in records 
            if order.get('status', '').lower() == status.lower()
        ]
        
        logger.info(f"✅ Found {len(filtered)} orders with status '{status}'")
        return filtered
        
    except Exception as e:
        logger.error(f"❌ Failed to get orders: {e}")
        return []


def update_order_status(order_id: str, new_status: str) -> bool:
    """
    Оновити статус замовлення
    
    Args:
        order_id: ID замовлення
        new_status: Новий статус
    
    Returns:
        bool: True якщо успішно
    """
    client = get_sheet_client()
    if not client:
        return False
    
    try:
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        orders_sheet = sheet.worksheet(config.SHEET_NAMES.get('orders', 'Замовлення'))
        
        # Знайти рядок
        cell = orders_sheet.find(order_id)
        
        if not cell:
            logger.warning(f"⚠️ Order not found: {order_id}")
            return False
        
        # Оновити статус (колонка G = 7)
        orders_sheet.update_cell(cell.row, 7, new_status)
        
        logger.info(f"✅ Order {order_id} status updated to '{new_status}'")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update order status: {e}")
        return False


def get_partners() -> List[Dict[str, Any]]:
    """
    Отримати список партнерів
    
    Returns:
        list: Список партнерів
    """
    client = get_sheet_client()
    if not client:
        return []
    
    try:
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        partners_sheet = sheet.worksheet(config.SHEET_NAMES.get('partners', 'Партнери'))
        
        records = partners_sheet.get_all_records()
        
        logger.info(f"✅ Loaded {len(records)} partners")
        return records
        
    except Exception as e:
        logger.error(f"❌ Failed to load partners: {e}")
        return []


def test_sheets_connection() -> bool:
    """
    Тест підключення до Google Sheets
    
    Returns:
        bool: True якщо працює
    """
    client = get_sheet_client()
    if not client:
        return False
    
    try:
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        title = sheet.title
        
        logger.info(f"✅ Connected to sheet: {title}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False


def invalidate_menu_cache():
    """Інвалідувати кеш меню (примусове оновлення)"""
    global _menu_cache_time
    _menu_cache_time = None
    logger.info("🔄 Menu cache invalidated")


# Тестування при імпорті
if __name__ == "__main__":
    print("🧪 Testing Google Sheets service...")
    if test_sheets_connection():
        print("✅ Sheets connection OK")
        
        # Тест завантаження меню
        menu = get_menu_from_sheet()
        print(f"✅ Menu loaded: {len(menu)} items")
    else:
        print("❌ Sheets connection FAILED")
