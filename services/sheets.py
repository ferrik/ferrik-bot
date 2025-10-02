import os
import gspread
from google.oauth2.service_account import Credentials
import logging
import json
from datetime import datetime

logger = logging.getLogger("hubsy_sheets")

# Глобальний кеш
_sheets_client = None
_menu_cache = []
_cache_timestamp = None

def init_gspread_client():
    """Ініціалізація Google Sheets клієнта"""
    global _sheets_client
    
    if _sheets_client:
        return _sheets_client
    
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not creds_json:
            logger.error("❌ GOOGLE_CREDENTIALS_JSON is not set")
            return None
        
        creds_dict = json.loads(creds_json)
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        _sheets_client = gspread.authorize(creds)
        
        logger.info("✅ Google Sheets client initialized")
        return _sheets_client
        
    except Exception as e:
        logger.error(f"❌ Error initializing Google Sheets: {str(e)}", exc_info=True)
        return None

def get_menu_from_sheet(force_reload=False):
    """Отримати меню з кешем"""
    global _menu_cache, _cache_timestamp
    
    # Повертаємо кеш якщо актуальний (5 хвилин)
    if not force_reload and _menu_cache and _cache_timestamp:
        age = (datetime.now() - _cache_timestamp).total_seconds()
        if age < 300:  # 5 хвилин
            logger.info(f"📦 Using cached menu ({len(_menu_cache)} items)")
            return _menu_cache
    
    try:
        client = init_gspread_client()
        if not client:
            logger.warning("⚠️ No client, returning cached menu")
            return _menu_cache
        
        sheet_id = os.environ.get("GOOGLE_SHEET_ID") or os.environ.get("SPREADSHEET_ID")
        if not sheet_id:
            logger.error("❌ GOOGLE_SHEET_ID not set")
            return _menu_cache
        
        sheet = client.open_by_key(sheet_id).sheet1
        menu = sheet.get_all_records()
        
        # Фільтруємо порожні рядки
        menu = [item for item in menu if item.get("Назва Страви")]
        
        _menu_cache = menu
        _cache_timestamp = datetime.now()
        
        logger.info(f"✅ Menu loaded: {len(menu)} items")
        return menu
        
    except Exception as e:
        logger.error(f"❌ Error loading menu: {str(e)}", exc_info=True)
        return _menu_cache  # Повертаємо старий кеш

def save_order_to_sheets(chat_id, cart):
    """Зберегти замовлення в Google Sheets"""
    try:
        client = init_gspread_client()
        if not client:
            logger.error("❌ Cannot save order: no client")
            return False
        
        sheet_id = os.environ.get("GOOGLE_SHEET_ID") or os.environ.get("SPREADSHEET_ID")
        spreadsheet = client.open_by_key(sheet_id)
        
        # Спроба отримати або створити аркуш Orders
        try:
            orders_sheet = spreadsheet.worksheet("Orders")
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("⚠️ Orders sheet not found, creating...")
            orders_sheet = spreadsheet.add_worksheet(title="Orders", rows="100", cols="10")
            # Додаємо заголовки
            orders_sheet.append_row([
                "Chat ID", "Дата", "Замовлення", "Сума", "Статус"
            ])
        
        # Формуємо дані замовлення
        order_items = []
        total = 0
        
        for item in cart:
            name = item.get("Назва Страви", "")
            price = item.get("Ціна", 0)
            
            try:
                price_float = float(str(price).replace(",", "."))
                total += price_float
            except:
                pass
            
            order_items.append(name)
        
        order_text = ", ".join(order_items)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        order_data = [
            str(chat_id),
            timestamp,
            order_text,
            f"{total:.2f}",
            "Нове"
        ]
        
        orders_sheet.append_row(order_data)
        logger.info(f"✅ Order saved for {chat_id}: {total:.2f} грн")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving order: {str(e)}", exc_info=True)
        return False

def is_sheets_connected():
    """Перевірка підключення до Sheets"""
    try:
        client = init_gspread_client()
        return client is not None
    except:
        return False

def search_menu_items(query):
    """Пошук страв у меню"""
    try:
        menu = get_menu_from_sheet()
        query_lower = query.lower()
        
        results = []
        for item in menu:
            name = item.get("Назва Страви", "").lower()
            category = item.get("Категорія", "").lower()
            description = item.get("Опис", "").lower()
            
            if query_lower in name or query_lower in category or query_lower in description:
                results.append(item)
        
        logger.info(f"🔍 Search '{query}': {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error searching menu: {str(e)}", exc_info=True)
        return []

def get_item_by_id(item_id):
    """Отримати страву за ID"""
    menu = get_menu_from_sheet()
    for item in menu:
        if str(item.get("ID", "")) == str(item_id):
            return item
    return None

def reload_menu():
    """Примусове перезавантаження меню"""
    logger.info("🔄 Force reloading menu...")
    return get_menu_from_sheet(force_reload=True)