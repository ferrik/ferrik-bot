import os
import logging
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
from datetime import datetime
from config import SPREADSHEET_ID, GOOGLE_CREDENTIALS_JSON, CREDS_B64

logger = logging.getLogger('ferrik')

# Глобальні змінні
_gc = None
_workbook = None
_menu_sheet = None
_orders_sheet = None
_config_sheet = None
spreadsheet = None  # Для сумісності з admin_panel

# Кеш меню
_menu_cache = {}
_cache_timestamp = None
CACHE_TTL = 3600  # 1 година

def init_gspread_client():
    """Ініціалізує клієнт Google Sheets"""
    global _gc, _workbook, _menu_sheet, _orders_sheet, _config_sheet, spreadsheet
    
    try:
        # Спробуємо використати CREDS_B64
        if CREDS_B64:
            logger.info("Using CREDS_B64 from env")
            credentials_data = base64.b64decode(CREDS_B64).decode('utf-8')
            credentials_dict = json.loads(credentials_data)
            logger.info("CREDS_B64 decoded successfully")
        elif GOOGLE_CREDENTIALS_JSON:
            logger.info("Using GOOGLE_CREDENTIALS_JSON from env")
            credentials_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        else:
            logger.error("❌ No credentials found")
            return False
        
        # Налаштування scope для Google Sheets API
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Створюємо credentials
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
        
        # Авторизуємось в gspread
        _gc = gspread.authorize(credentials)
        
        # Відкриваємо таблицю
        try:
            _workbook = _gc.open_by_key(SPREADSHEET_ID)
            spreadsheet = _workbook  # Для admin_panel
            
            # Підключаємося до аркушів
            _menu_sheet = _workbook.worksheet("Меню")
            _orders_sheet = _workbook.worksheet("Замовлення")
            _config_sheet = _workbook.worksheet("Конфіг")
            
            logger.info(f"✅ Google Sheets підключено: {_workbook.title}")
            return True
            
        except gspread.exceptions.WorksheetNotFound as e:
            logger.error(f"❌ Не знайдено аркуш: {e}")
            return False
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 403:
                logger.error(f"❌ Немає доступу до таблиці. Надайте доступ для: {credentials_dict.get('client_email')}")
            else:
                logger.error(f"❌ API помилка: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації Google Sheets: {e}", exc_info=True)
        return False


def is_sheets_connected():
    """Перевіряє, чи підключено Google Sheets"""
    return _workbook is not None


def get_menu_from_sheet(force=False):
    """
    Отримує меню з Google Sheets (з кешуванням)
    ВАЖЛИВО: Ця функція має назву БЕЗ "s" для сумісності з gemini.py
    """
    global _menu_cache, _cache_timestamp
    
    # Перевіряємо кеш
    if not force and _menu_cache and _cache_timestamp:
        cache_age = (datetime.now() - _cache_timestamp).total_seconds()
        if cache_age < CACHE_TTL:
            logger.info(f"Використовується кеш меню (вік: {cache_age:.0f}с)")
            return _menu_cache
    
    if not _menu_sheet:
        logger.warning("⚠️ Menu sheet не підключено")
        return []
    
    try:
        # Отримуємо всі записи
        records = _menu_sheet.get_all_records()
        
        # Конвертуємо в правильний формат
        menu_items = []
        for record in records:
            # Перевіряємо активність
            is_active = str(record.get('Активний', '')).lower() in ['true', '1', 'так', 'yes', 'TRUE']
            
            if is_active:
                menu_items.append({
                    'ID': record.get('ID', ''),
                    'Категорія': record.get('Категорія', ''),
                    'Страви': record.get('Страви', ''),  # ← Правильна назва колонки!
                    'name': record.get('Страви', ''),  # Додатково для сумісності
                    'Опис': record.get('Опис', ''),
                    'description': record.get('Опис', ''),
                    'Ціна': float(record.get('Ціна', 0)),
                    'price': float(record.get('Ціна', 0)),
                    'Ресторан': record.get('Ресторан', ''),
                    'Час Доставки (хв)': record.get('Час Доставки (хв)', ''),
                    'Фото URL': record.get('Фото URL', ''),
                    'photo': record.get('Фото URL', ''),
                    'Активний': True,
                    'active': True,
                    'Час_приготування': record.get('Час_приготування', ''),
                    'Аллергени': record.get('Аллергени', ''),
                    'Рейтинг': record.get('Рейтинг', ''),
                    'rating': record.get('Рейтинг', '')
                })
        
        # Оновлюємо кеш
        _menu_cache = menu_items
        _cache_timestamp = datetime.now()
        
        logger.info(f"✅ Меню завантажено: {len(menu_items)} активних позицій з {len(records)} загальних")
        return menu_items
        
    except Exception as e:
        logger.error(f"❌ Помилка при отриманні меню: {e}", exc_info=True)
        return _menu_cache if _menu_cache else []


def get_menu():
    """Alias для get_menu_from_sheet (для зворотної сумісності)"""
    return get_menu_from_sheet()


def get_item_by_id(item_id):
    """Отримує страву за ID"""
    try:
        menu = get_menu_from_sheet()
        for item in menu:
            if str(item.get('ID')) == str(item_id):
                return item
        return None
    except Exception as e:
        logger.error(f"❌ Помилка пошуку страви {item_id}: {e}")
        return None


def save_order_to_sheets(order_data):
    """
    Зберігає замовлення в Google Sheets
    Повертає ID замовлення або False
    """
    if not _orders_sheet:
        logger.warning("⚠️ Orders sheet не підключено")
        return False
    
    try:
        # Генеруємо ID замовлення
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{order_data.get('chat_id', '0')}"
        
        # Формуємо рядок для запису
        row = [
            order_id,                                           # ID Замовлення
            order_data.get('chat_id', ''),                     # Telegram User ID
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),      # Час Замовлення
            json.dumps(order_data.get('items', []), ensure_ascii=False),  # Товари (JSON)
            order_data.get('total', 0),                        # Загальна Сума
            order_data.get('address', ''),                     # Адреса
            order_data.get('phone', ''),                       # Телефон
            order_data.get('payment_method', 'Готівка'),      # Спосіб Оплати
            'Нове',                                            # Статус
            'Telegram',                                        # Канал
            order_data.get('delivery_cost', 0),                # Вартість доставки
            order_data.get('total_with_delivery', 0),          # Загальна сума
            order_data.get('delivery_type', 'Доставка'),      # Тип доставки
            order_data.get('delivery_time', ''),               # Час доставки/самовивозу
            '',                                                # Оператор
            order_data.get('notes', '')                        # Примітки
        ]
        
        _orders_sheet.append_row(row)
        logger.info(f"✅ Замовлення {order_id} збережено в Google Sheets")
        return order_id
        
    except Exception as e:
        logger.error(f"❌ Помилка збереження замовлення: {e}", exc_info=True)
        return False


def get_config(key, default=None):
    """Отримує значення конфігурації"""
    if not _config_sheet:
        logger.warning(f"⚠️ Config sheet не підключено")
        return default
    
    try:
        records = _config_sheet.get_all_records()
        for record in records:
            if record.get('Ключ') == key:
                return record.get('Значення', default)
        return default
    except Exception as e:
        logger.error(f"❌ Помилка отримання конфігу {key}: {e}")
        return default


def get_working_hours():
    """Отримує години роботи"""
    open_hour = get_config('OPEN_HOUR', '09:00')
    close_hour = get_config('CLOSE_HOUR', '22:00')
    return open_hour, close_hour


def get_min_delivery_amount():
    """Отримує мінімальну суму доставки"""
    return float(get_config('MIN_DELIVERY_AMOUNT', 200))


def get_menu_by_category():
    """Повертає меню згруповане по категоріях"""
    menu = get_menu_from_sheet()
    categorized = {}
    
    for item in menu:
        category = item.get('Категорія', 'Інше')
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(item)
    
    return categorized


def search_menu_items(query):
    """Шукає страви в меню"""
    menu = get_menu_from_sheet()
    query_lower = query.lower()
    results = []
    
    for item in menu:
        name = str(item.get('Страви', '')).lower()
        description = str(item.get('Опис', '')).lower()
        category = str(item.get('Категорія', '')).lower()
        
        if query_lower in name or query_lower in description or query_lower in category:
            results.append(item)
    
    logger.info(f"🔍 Пошук '{query}': знайдено {len(results)} позицій")
    return results


def get_menu_stats():
    """Отримує статистику меню"""
    try:
        menu = get_menu_from_sheet()
        all_records = _menu_sheet.get_all_records() if _menu_sheet else []
        
        categories = {}
        for record in all_records:
            cat = record.get('Категорія', 'Інше')
            is_active = str(record.get('Активний', '')).lower() in ['true', '1', 'так', 'yes']
            
            if cat not in categories:
                categories[cat] = {'active': 0, 'total': 0}
            
            categories[cat]['total'] += 1
            if is_active:
                categories[cat]['active'] += 1
        
        cache_age = 0
        if _cache_timestamp:
            cache_age = (datetime.now() - _cache_timestamp).total_seconds()
        
        return {
            'total_items': len(all_records),
            'active_items': len(menu),
            'categories': categories,
            'cache_age': cache_age
        }
    except Exception as e:
        logger.error(f"❌ Помилка статистики меню: {e}")
        return {}


# Для зворотної сумісності зі старим кодом
def init_sheets():
    """Alias для init_gspread_client"""
    return init_gspread_client()


def get_menu_from_sheets():
    """Alias для get_menu_from_sheet (з "s" на кінці)"""
    return get_menu_from_sheet()