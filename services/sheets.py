"""
Google Sheets Service
Робота з Google Sheets API для меню та замовлень
"""

import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
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
        # ВИПРАВЛЕННЯ: Использувати GOOGLE_CREDENTIALS замість GOOGLE_CREDENTIALS_JSON
        creds_json = config.GOOGLE_CREDENTIALS or os.getenv('GOOGLE_CREDENTIALS', '')
        
        if not creds_json:
            raise ValueError("❌ GOOGLE_CREDENTIALS not configured in environment")
        
        # Парсимо JSON
        creds_dict = json.loads(creds_json)
        
        # Створюємо credentials
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )
        
        # Створюємо service
        _sheets_service = build('sheets', 'v4', credentials=credentials)
        
        logger.info("✅ Google Sheets service initialized successfully")
        return _sheets_service
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse GOOGLE_CREDENTIALS JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to initialize Google Sheets service: {e}")
        raise


def get_menu_from_sheet() -> List[Dict[str, Any]]:
    """
    Отримує меню з Google Sheets
    
    Читає з листа "Меню" і нормалізує поля
    
    Returns:
        List of menu items з нормалізованими полями
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Читаємо заголовки (перший рядок) - листа називається "Меню"
        headers_result = sheet.values().get(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range='Меню!A1:L1'  # ВИПРАВЛЕННЯ: Українське ім'я листа
        ).execute()
        
        headers = headers_result.get('values', [[]])[0]
        
        if not headers:
            logger.error("❌ No headers found in 'Меню' sheet")
            return []
        
        logger.info(f"📋 Headers found: {headers}")
        
        # Читаємо дані (з другого рядка)
        result = sheet.values().get(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range='Меню!A2:L1000'
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.warning("⚠️  No data found in 'Меню' sheet")
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
        
        logger.info(f"📊 Loaded {len(raw_menu)} raw items from sheet")
        
        # КРИТИЧНО: Нормалізуємо поля через config.normalize_menu_list
        # Замість normalize_menu_list(raw_menu):
normalized_menu = []
for item in raw_menu:
    # Перевіряємо чи активний
    if item.get('Активний', '').lower() in ['так', 'yes', 'true', '1']:
        # Конвертуємо ціну
        try:
            item['Ціна'] = float(item.get('Ціна', 0))
        except:
            item['Ціна'] = 0
        
        normalized_menu.append(item)

logger.info(f"✅ Menu normalized: {len(normalized_menu)} items")
return normalized_menu
        
        logger.info(f"✅ Menu normalized: {len(normalized_menu)} items")
        return normalized_menu
        
    except HttpError as e:
        logger.error(f"❌ HTTP error loading menu: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Failed to load menu from sheets: {e}", exc_info=True)
        return []


def save_order_to_sheets(order_id: str, user_id: int, cart: Dict, contact_info: Dict) -> bool:
    """
    Зберігає замовлення в Google Sheets
    
    Args:
        order_id: ID замовлення
        user_id: Telegram user ID
        cart: Словник {item_name: quantity}
        contact_info: Контактна інформація {phone, address, name}
    
    Returns:
        True якщо успішно, False якщо помилка
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Конвертуємо cart в JSON
        cart_json = json.dumps(cart)
        
        # Розраховуємо суму
        total_amount = sum(
            float(item.get('price', 0)) * int(qty)
            for item, qty in cart.items()
        )
        
        # Готуємо row для запису
        row = [
            str(order_id),                                  # A: ID_замовлення
            str(user_id),                                   # B: Telegram User ID
            timestamp,                                      # C: Час_замовлення
            cart_json,                                      # D: Товари (JSON)
            round(total_amount, 2),                        # E: Загальна_сума
            contact_info.get('address', 'N/A'),           # F: Адреса
            contact_info.get('phone', 'N/A'),             # G: Телефон
            'card',                                         # H: Спосіб_оплати
            'pending',                                      # I: Статус
        ]
        
        body = {'values': [row]}
        
        result = sheet.values().append(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range='Замовлення!A:I',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        updated_cells = result.get('updates', {}).get('updatedCells', 0)
        logger.info(f"✅ Order {order_id} saved to sheets: {updated_cells} cells updated")
        
        return True
        
    except HttpError as e:
        logger.error(f"❌ HTTP error saving order {order_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to save order {order_id} to sheets: {e}", exc_info=True)
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
            range='Замовлення!A1:I1'
        ).execute()
        
        headers = headers_result.get('values', [[]])[0]
        
        if not headers:
            logger.warning("⚠️  No headers in 'Замовлення' sheet")
            return []
        
        # Читаємо дані
        result = sheet.values().get(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range=f'Замовлення!A2:I{limit + 1}'
        ).execute()
        
        values = result.get('values', [])
        
        # Конвертуємо в list of dicts
        orders = []
        for row in values:
            if len(row) < len(headers):
                row = row + [''] * (len(headers) - len(row))
            
            order = dict(zip(headers, row))
            orders.append(order)
        
        logger.info(f"📊 Loaded {len(orders)} orders from sheet")
        return orders
        
    except Exception as e:
        logger.error(f"❌ Failed to load orders: {e}")
        return []


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
        
        sheets_list = [s['properties']['title'] for s in result.get('sheets', [])]
        
        info = {
            'title': result.get('properties', {}).get('title'),
            'sheets': sheets_list,
            'url': f"https://docs.google.com/spreadsheets/d/{config.GOOGLE_SHEET_ID}"
        }
        
        logger.info(f"📋 Sheet info: {info}")
        
        return info
        
    except Exception as e:
        logger.error(f"❌ Failed to get sheet info: {e}")
        return {}


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    'get_sheets_service',
    'get_menu_from_sheet',
    'save_order_to_sheets',
    'get_orders_from_sheet',
    'test_sheets_connection',
    'get_sheet_info',
]
