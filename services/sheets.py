import os
import logging
import gspread
from google.oauth2.service_account import Credentials
import json

logger = logging.getLogger('ferrik')

# Конфігурація
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')  # JSON як string

# Глобальні змінні
_gc = None
_worksheet = None

def init_gspread_client():
    """
    Ініціалізує клієнт Google Sheets
    """
    global _gc, _worksheet
    
    try:
        if not GOOGLE_CREDENTIALS:
            logger.error("❌ GOOGLE_CREDENTIALS не знайдено в змінних середовища")
            return False
            
        if not SPREADSHEET_ID:
            logger.error("❌ SPREADSHEET_ID не знайдено в змінних середовища")
            return False
        
        # Парсимо JSON credentials
        try:
            creds_dict = json.loads(GOOGLE_CREDENTIALS)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Помилка парсингу GOOGLE_CREDENTIALS: {e}")
            return False
        
        # Налаштування scope для Google Sheets API
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Створюємо credentials
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        # Авторизуємось в gspread
        _gc = gspread.authorize(credentials)
        
        # Відкриваємо таблицю
        try:
            wb = _gc.open_by_key(SPREADSHEET_ID)
            _worksheet = wb.sheet1  # Перший аркуш
            logger.info(f"✅ Google Sheets підключено: {wb.title}")
            return True
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 403:
                logger.error(f"❌ Немає доступу до таблиці. Надайте доступ для: {creds_dict.get('client_email')}")
            else:
                logger.error(f"❌ API помилка: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації Google Sheets: {e}", exc_info=True)
        return False


def get_worksheet():
    """Повертає worksheet або None"""
    return _worksheet


def is_sheets_connected():
    """Перевіряє, чи підключено Google Sheets"""
    return _worksheet is not None


def add_order(user_data: dict):
    """
    Додає замовлення в Google Sheets
    """
    if not _worksheet:
        logger.warning("⚠️ Google Sheets не підключено, замовлення не збережено")
        return False
    
    try:
        # Приклад структури даних для запису
        row = [
            user_data.get('timestamp', ''),
            user_data.get('user_id', ''),
            user_data.get('username', ''),
            user_data.get('order', ''),
            user_data.get('status', 'pending')
        ]
        
        _worksheet.append_row(row)
        logger.info(f"✅ Замовлення додано в Google Sheets для користувача {user_data.get('username')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Помилка при додаванні замовлення: {e}", exc_info=True)
        return False


def get_menu():
    """
    Отримує меню з Google Sheets
    Припускаємо, що меню знаходиться на другому аркуші
    """
    if not _gc:
        return None
    
    try:
        wb = _gc.open_by_key(SPREADSHEET_ID)
        menu_sheet = wb.worksheet("Меню")  # Або sheet1, залежно від структури
        
        # Отримуємо всі записи
        records = menu_sheet.get_all_records()
        logger.info(f"✅ Отримано меню: {len(records)} позицій")
        return records
        
    except Exception as e:
        logger.error(f"❌ Помилка при отриманні меню: {e}", exc_info=True)
        return None