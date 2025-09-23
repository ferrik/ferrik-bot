import os
import json
import logging
import gspread
from google.oauth2 import service_account
from datetime import datetime, timedelta
import base64

logger = logging.getLogger("ferrik.sheets")

GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "").strip()
CREDS_JSON = os.environ.get("CREDS_JSON")  # JSON як строка
CREDS_B64 = os.environ.get("CREDS_B64")    # Base64 закодований JSON
SERVICE_ACCOUNT_KEY_PATH = os.environ.get("SERVICE_ACCOUNT_KEY_PATH", "").strip()

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

gc = None
spreadsheet = None

# Простий кеш меню
_menu_cache = []
_menu_cache_time = None
CACHE_TTL = int(os.environ.get("MENU_CACHE_TTL_SECONDS", "900"))  # 15 min

def init_gspread_client():
    """Ініціалізація клієнта Google Sheets"""
    global gc, spreadsheet
    
    if gc and spreadsheet:
        return True

    try:
        creds = None
        
        # Пробуємо різні способи отримання credentials
        
        # 1) CREDS_B64 - Base64 закодований JSON
        if CREDS_B64:
            try:
                logger.info("Using CREDS_B64 from env")
                decoded_creds = base64.b64decode(CREDS_B64).decode('utf-8')
                
                # Збереження у тимчасовий файл для Render
                temp_path = "/tmp/creds.json"
                with open(temp_path, 'w') as f:
                    f.write(decoded_creds)
                    
                info = json.loads(decoded_creds)
                creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPE)
                logger.info("Successfully loaded credentials from CREDS_B64")
                
            except Exception as e:
                logger.error(f"Error decoding CREDS_B64: {e}")
        
        # 2) CREDS_JSON - прямий JSON як строка
        elif CREDS_JSON:
            try:
                logger.info("Using CREDS_JSON from env")
                info = json.loads(CREDS_JSON)
                creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPE)
                logger.info("Successfully loaded credentials from CREDS_JSON")
            except Exception as e:
                logger.error(f"Error parsing CREDS_JSON: {e}")
        
        # 3) Файл SERVICE_ACCOUNT_KEY_PATH
        elif SERVICE_ACCOUNT_KEY_PATH and os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
            try:
                logger.info(f"Using service account file: {SERVICE_ACCOUNT_KEY_PATH}")
                creds = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_KEY_PATH, scopes=SCOPE
                )
                logger.info("Successfully loaded credentials from file")
            except Exception as e:
                logger.error(f"Error loading credentials from file: {e}")
        
        if not creds:
            logger.error("No valid Google credentials found. Set CREDS_B64, CREDS_JSON or SERVICE_ACCOUNT_KEY_PATH.")
            return False

        # Авторизація та підключення до таблиці
        gc = gspread.authorize(creds)
        
        if not GOOGLE_SHEET_ID:
            logger.error("GOOGLE_SHEET_ID not set.")
            return False
            
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
        logger.info(f"Connected to Google Sheet: {GOOGLE_SHEET_ID}")
        return True
        
    except Exception as e:
        logger.exception(f"init_gspread_client error: {e}")
        return False

def test_gspread_connection():
    """Тестує підключення до Google Sheets"""
    try:
        if not init_gspread_client():
            logger.error("Cannot test connection - initialization failed")
            return False
            
        # Пробуємо отримати список worksheets
        worksheets = spreadsheet.worksheets()
        worksheet_names = [ws.title for ws in worksheets]
        logger.info(f"Available worksheets: {worksheet_names}")
        
        # Перевіряємо наявність необхідних вкладок
        required_sheets = ["Меню", "Замовлення", "Конфіг"]
        missing_sheets = [sheet for sheet in required_sheets if sheet not in worksheet_names]
        
        if missing_sheets:
            logger.warning(f"Missing required worksheets: {missing_sheets}")
            return False
        
        logger.info("Google Sheets connection test successful")
        return True
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

def get_menu_from_sheet(force=False):
    """
    Повертає список позицій меню з Google Sheets
    Використовує кешування для продуктивності
    """
    global _menu_cache, _menu_cache_time
    
    try:
        if not init_gspread_client():
            logger.error("Cannot connect to Google Sheets")
            return []

        # Перевіряємо кеш
        now = datetime.utcnow()
        if not force and _menu_cache and _menu_cache_time:
            cache_age = (now - _menu_cache_time).total_seconds()
            if cache_age < CACHE_TTL:
                logger.debug(f"Using cached menu (age: {cache_age:.1f}s)")
                return _menu_cache

        # Завантажуємо меню з Google Sheets
        ws = spreadsheet.worksheet("Меню")
        records = ws.get_all_records()
        
        processed = []
        for r in records:
            # Очищуємо та нормалізуємо дані
            item_id = str(r.get("ID", "")).strip()
            if not item_id:
                continue
                
            # Назва страви (можливі варіанти колонок)
            name = (
                r.get("Страви") or 
                r.get("Назва Страви") or 
                r.get("Назва") or 
                ""
            ).strip()
            
            if not name:
                logger.warning(f"Item {item_id} has no name, skipping")
                continue
            
            # Ціна
            price_raw = r.get("Ціна", 0)
            try:
                if isinstance(price_raw, str):
                    price = float(price_raw.strip().replace(",", ".").replace(" ", ""))
                else:
                    price = float(price_raw)
            except (ValueError, TypeError):
                logger.warning(f"Invalid price for item {item_id}: {price_raw}")
                price = 0.0
            
            # Категорія
            category = str(r.get("Категорія", "Інше")).strip()
            
            # Активний статус
            active_raw = str(r.get("Активний", "Так")).strip().lower()
            active = active_raw in ("так", "yes", "true", "1", "активний")
            
            processed.append({
                "ID": item_id,
                "name": name,
                "price": price,
                "category": category,
                "description": str(r.get("Опис", "")).strip(),
                "photo": str(r.get("Фото URL", "")).strip(),
                "restaurant": str(r.get("Ресторан", "")).strip(),
                "cooking_time": str(r.get("Час_приготування", "")).strip(),
                "delivery_time": str(r.get("Час Доставки (хв)", "")).strip(),
                "allergens": str(r.get("Аллергени", "")).strip(),
                "rating": str(r.get("Рейтинг", "")).strip(),
                "active": active
            })
        
        # Фільтруємо тільки активні позиції
        _menu_cache = [item for item in processed if item.get("active")]
        _menu_cache_time = now
        
        logger.info(f"Menu loaded: {len(_menu_cache)} active items from {len(processed)} total")
        return _menu_cache
        
    except gspread.exceptions.WorksheetNotFound:
        logger.error("Worksheet 'Меню' not found in the spreadsheet.")
        return []
    except Exception as e:
        logger.exception(f"get_menu_from_sheet error: {e}")
        return []

def update_menu_cache(force=False):
    """Оновлює кеш меню"""
    return get_menu_from_sheet(force=force)

def get_item_by_id(item_id):
    """Отримує конкретну позицію меню за ID"""
    try:
        menu_items = get_menu_from_sheet()
        
        for item in menu_items:
            if str(item.get("ID")) == str(item_id):
                return item
                
        logger.warning(f"Item with ID {item_id} not found in menu")
        return None
        
    except Exception as e:
        logger.error(f"Error getting item by ID {item_id}: {e}")
        return None

def get_categories():
    """Отримує список всіх категорій меню"""
    try:
        menu_items = get_menu_from_sheet()
        categories = set()
        
        for item in menu_items:
            if item.get("active"):
                categories.add(item.get("category", "Інше"))
                
        return sorted(list(categories))
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return []

def get_items_by_category(category):
    """Отримує всі позиції меню з конкретної категорії"""
    try:
        menu_items = get_menu_from_sheet()
        
        return [
            item for item in menu_items 
            if item.get("category") == category and item.get("active")
        ]
        
    except Exception as e:
        logger.error(f"Error getting items for category {category}: {e}")
        return []

def save_order_to_sheets(order_data):
    """Зберігає замовлення в Google Sheets"""
    try:
        if not init_gspread_client():
            logger.error("Cannot connect to Google Sheets to save order")
            return False
            
        ws = spreadsheet.worksheet("Замовлення")
        
        # Генеруємо ID замовлення
        now = datetime.now()
        order_id = f"ORD-{now.strftime('%Y%m%d%H%M%S')}-{order_data.get('chat_id', '0')}"
        
        # Підготовка даних для запису
        row_data = [
            order_id,                                    # ID Замовлення
            str(order_data.get('chat_id', '')),         # Telegram User ID
            now.strftime('%Y-%m-%d %H:%M:%S'),          # Час Замовлення
            json.dumps(order_data.get('items', []), ensure_ascii=False),  # Товари (JSON)
            str(order_data.get('total', 0)),            # Загальна Сума
            order_data.get('address', ''),              # Адреса
            order_data.get('phone', ''),                # Телефон
            order_data.get('payment_method', ''),       # Спосіб Оплати
            'Нове',                                     # Статус
            'Telegram Bot',                             # Канал
            str(order_data.get('delivery_cost', 0)),    # Вартість доставки
            str(order_data.get('total_with_delivery', order_data.get('total', 0))),  # Загальна сума з доставкою
            order_data.get('delivery_type', 'Доставка'),# Тип доставки
            order_data.get('delivery_time', ''),        # Час доставки
            'Система',                                  # Оператор
            order_data.get('notes', '')                 # Примітки
        ]
        
        # Додаємо рядок до таблиці
        ws.append_row(row_data)
        
        logger.info(f"Order {order_id} saved successfully")
        return order_id
        
    except Exception as e:
        logger.error(f"Error saving order: {e}")
        return None

def get_config():
    """Отримує конфігурацію з Google Sheets"""
    try:
        if not init_gspread_client():
            logger.error("Cannot connect to Google Sheets to get config")
            return {}
            
        ws = spreadsheet.worksheet("Конфіг")
        records = ws.get_all_records()
        
        config = {}
        for record in records:
            key = record.get("Ключ", "").strip()
            value = record.get("Значення", "").strip()
            if key:
                config[key] = value
                
        logger.debug(f"Config loaded: {config}")
        return config
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return {}

def get_config_value(key, default=None):
    """Отримує конкретне значення з конфігурації"""
    try:
        config = get_config()
        return config.get(key, default)
    except Exception as e:
        logger.error(f"Error getting config value {key}: {e}")
        return default

def is_restaurant_open():
    """Перевіряє чи відкритий ресторан на основі конфігурації"""
    try:
        config = get_config()
        open_time = config.get("Година відкриття", "10:00")
        close_time = config.get("Година закриття", "22:00")
        
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        return open_time <= current_time <= close_time
        
    except Exception as e:
        logger.error(f"Error checking restaurant hours: {e}")
        # За замовчуванням вважаємо відкритим
        return True

def get_min_delivery_amount():
    """Отримує мінімальну суму для доставки"""
    try:
        return float(get_config_value("Мінімальна сума доставки", "200"))
    except:
        return 200.0

def update_order_status(order_id, status, operator=None):
    """Оновлює статус замовлення"""
    try:
        if not init_gspread_client():
            return False
            
        ws = spreadsheet.worksheet("Замовлення")
        
        # Знаходимо рядок з замовленням
        orders = ws.get_all_records()
        for i, order in enumerate(orders, start=2):  # +2 бо рахунок з 1 + заголовки
            if order.get("ID Замовлення") == order_id:
                # Оновлюємо статус
                ws.update_cell(i, 9, status)  # Колонка "Статус"
                
                # Якщо передано оператора, оновлюємо і його
                if operator:
                    ws.update_cell(i, 15, operator)  # Колонка "Оператор"
                    
                logger.info(f"Order {order_id} status updated to {status}")
                return True
                
        logger.warning(f"Order {order_id} not found for status update")
        return False
        
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        return False

def get_menu_stats():
    """Отримує статистику меню"""
    try:
        menu_items = get_menu_from_sheet(force=True)
        
        categories = {}
        total_items = len(menu_items)
        active_items = 0
        
        for item in menu_items:
            category = item.get("category", "Інше")
            if category not in categories:
                categories[category] = {"total": 0, "active": 0}
                
            categories[category]["total"] += 1
            
            if item.get("active"):
                categories[category]["active"] += 1
                active_items += 1
        
        return {
            "total_items": total_items,
            "active_items": active_items,
            "categories": categories,
            "cache_age": (datetime.utcnow() - _menu_cache_time).total_seconds() if _menu_cache_time else None
        }
        
    except Exception as e:
        logger.error(f"Error getting menu stats: {e}")
        return {"total_items": 0, "active_items": 0, "categories": {}}

# Додаткові функції для сумісності зі старим кодом
def update_menu_cache(force=False):
    """Оновлює кеш меню - аліас для get_menu_from_sheet"""
    return get_menu_from_sheet(force=force)

def test_gspread_connection():
    """Тестує підключення до Google Sheets"""
    try:
        if not init_gspread_client():
            logger.error("Cannot test connection - initialization failed")
            return False
            
        worksheets = spreadsheet.worksheets()
        worksheet_names = [ws.title for ws in worksheets]
        logger.info(f"Available worksheets: {worksheet_names}")
        
        required_sheets = ["Меню", "Замовлення", "Конфіг"]
        missing_sheets = [sheet for sheet in required_sheets if sheet not in worksheet_names]
        
        if missing_sheets:
            logger.warning(f"Missing required worksheets: {missing_sheets}")
            return False
        
        logger.info("Google Sheets connection test successful")
        return True
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
