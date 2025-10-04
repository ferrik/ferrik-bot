import os
import gspread
from google.oauth2.service_account import Credentials
import logging
import json
from datetime import datetime

logger = logging.getLogger("hubsy_sheets")

_sheets_client = None
_menu_cache = []
_cache_timestamp = None

def init_gspread_client():
    """Ініціалізація Google Sheets"""
    global _sheets_client
    
    if _sheets_client:
        return _sheets_client
    
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not creds_json:
            logger.error("❌ GOOGLE_CREDENTIALS_JSON not set")
            return None
        
        creds_dict = json.loads(creds_json)
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        _sheets_client = gspread.authorize(creds)
        
        logger.info("✅ Google Sheets initialized")
        return _sheets_client
        
    except Exception as e:
        logger.error(f"❌ Sheets init error: {e}", exc_info=True)
        return None

def get_menu_from_sheet(force_reload=False):
    """Отримати меню з кешем"""
    global _menu_cache, _cache_timestamp
    
    # Кеш на 5 хвилин
    if not force_reload and _menu_cache and _cache_timestamp:
        age = (datetime.now() - _cache_timestamp).total_seconds()
        if age < 300:
            logger.info(f"📦 Using cache ({len(_menu_cache)} items)")
            return _menu_cache
    
    try:
        client = init_gspread_client()
        if not client:
            logger.warning("⚠️ No client")
            return _menu_cache
        
        sheet_id = os.environ.get("GOOGLE_SHEET_ID") or os.environ.get("SPREADSHEET_ID")
        if not sheet_id:
            logger.error("❌ SHEET_ID not set")
            return _menu_cache
        
        # Відкриваємо аркуш "Меню"
        spreadsheet = client.open_by_key(sheet_id)
        menu_sheet = spreadsheet.worksheet("Меню")
        
        # Отримуємо всі записи
        raw_menu = menu_sheet.get_all_records()
        
        # Адаптуємо структуру під ваші колонки
        menu = []
        for item in raw_menu:
            # Перевіряємо чи активна страва
            active = str(item.get('Активний', '')).lower()
            if active not in ['так', 'yes', 'true', '1']:
                continue  # Пропускаємо неактивні
            
            # Конвертуємо під стандартну структуру
            adapted_item = {
                'ID': item.get('ID', ''),
                'Назва Страви': item.get('Страви', ''),  # ← КЛЮЧОВА ЗМІНА
                'Категорія': item.get('Категорія', ''),
                'Ціна': item.get('Ціна', 0),
                'Опис': item.get('Опис', ''),
                'Вага': '',  # У вас немає цієї колонки
                'Ресторан': item.get('Ресторан', ''),
                'Час Доставки': item.get('Час Доставки (хв)', ''),
                'Фото': item.get('Фото URL', ''),
                'Рейтинг': item.get('Рейтинг', ''),
                'Аллергени': item.get('Аллергени', '')
            }
            
            # Додаємо тільки якщо є назва страви
            if adapted_item['Назва Страви']:
                menu.append(adapted_item)
        
        _menu_cache = menu
        _cache_timestamp = datetime.now()
        
        logger.info(f"✅ Menu loaded: {len(menu)} items")
        return menu
        
    except gspread.exceptions.WorksheetNotFound:
        logger.error("❌ Worksheet 'Меню' not found")
        return _menu_cache
    except Exception as e:
        logger.error(f"❌ Menu loading error: {e}", exc_info=True)
        return _menu_cache

def save_order_to_sheets(chat_id, cart):
    """Зберегти замовлення"""
    try:
        client = init_gspread_client()
        if not client:
            logger.error("❌ Cannot save: no client")
            return False
        
        sheet_id = os.environ.get("GOOGLE_SHEET_ID") or os.environ.get("SPREADSHEET_ID")
        spreadsheet = client.open_by_key(sheet_id)
        
        # Відкриваємо аркуш "Замовлення"
        try:
            orders_sheet = spreadsheet.worksheet("Замовлення")
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("⚠️ 'Замовлення' not found, creating...")
            orders_sheet = spreadsheet.add_worksheet(title="Замовлення", rows="100", cols="15")
            # Додаємо заголовки як у вашій таблиці
            orders_sheet.append_row([
                "ID Замовлення", "Telegram User ID", "Час Замовлення", 
                "Товари (JSON)", "Загальна Сума", "Адреса", "Телефон",
                "Спосіб Оплати", "Статус", "Канал", "Вартість доставки",
                "Загальна сума", "Тип доставки", "Час доставки/самовивозу",
                "Оператор", "Примітки"
            ])
        
        # Формуємо дані замовлення
        order_items = []
        total = 0
        
        for item in cart:
            name = item.get('Назва Страви', '')
            item_id = item.get('ID', '')
            price = float(str(item.get('Ціна', 0)).replace(',', '.'))
            
            order_items.append({
                "id": item_id,
                "name": name,
                "price": price,
                "qty": 1
            })
            total += price
        
        # ID замовлення
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        order_id = f"ORD-{timestamp}-{chat_id}"
        
        # Час замовлення
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # JSON товарів
        items_json = json.dumps(order_items, ensure_ascii=False)
        
        # Рядок для таблиці
        order_data = [
            order_id,
            str(chat_id),
            order_time,
            items_json,
            f"{total:.2f}",
            "",  # Адреса (додайте якщо потрібно)
            "",  # Телефон
            "Готівка при отриманні",
            "Нове",
            "Telegram Bot",
            "0.0",
            "",
            "",
            "",
            "",
            ""
        ]
        
        orders_sheet.append_row(order_data)
        logger.info(f"✅ Order saved: {order_id}, {total:.2f} грн")
        return True
        
    except Exception as e:
        logger.error(f"❌ Save order error: {e}", exc_info=True)
        return False

def is_sheets_connected():
    """Перевірка підключення"""
    try:
        client = init_gspread_client()
        return client is not None
    except:
        return False

def search_menu_items(query):
    """Пошук страв"""
    try:
        menu = get_menu_from_sheet()
        query_lower = query.lower()
        
        results = []
        for item in menu:
            name = item.get('Назва Страви', '').lower()
            category = item.get('Категорія', '').lower()
            description = item.get('Опис', '').lower()
            
            if query_lower in name or query_lower in category or query_lower in description:
                results.append(item)
        
        logger.info(f"🔍 Search '{query}': {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"❌ Search error: {e}", exc_info=True)
        return []

def reload_menu():
    """Примусове перезавантаження"""
    logger.info("🔄 Force reload...")
    return get_menu_from_sheet(force_reload=True)