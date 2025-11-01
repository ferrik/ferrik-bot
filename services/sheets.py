"""
📊 Google Sheets Service
Інтеграція з Google Sheets для меню та замовлень
"""
import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)

class SheetsService:
    """Сервіс для роботи з Google Sheets"""
    
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Ініціалізація Google Sheets клієнта"""
        try:
            # Отримуємо credentials з environment
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            sheets_id = os.getenv('GOOGLE_SHEETS_ID')
            
            if not creds_json or not sheets_id:
                logger.warning("⚠️ Google Sheets credentials not configured")
                return
            
            # Парсимо JSON credentials
            if isinstance(creds_json, str):
                creds_dict = json.loads(creds_json)
            else:
                creds_dict = creds_json
            
            # Scope для доступу
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Створюємо credentials
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                creds_dict, 
                scope
            )
            
            # Авторизуємось
            self.client = gspread.authorize(credentials)
            
            # Відкриваємо таблицю
            self.spreadsheet = self.client.open_by_key(sheets_id)
            
            logger.info("✅ Google Sheets connected successfully")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in GOOGLE_CREDENTIALS_JSON: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets: {e}")
    
    def get_menu_items(self) -> List[Dict]:
        """
        Отримати меню з Google Sheets
        
        Очікувана структура листа "Меню":
        ID | Категорія | Страви | Опис | Ціна | Ресторан | Час Доставки | Фото URL | Активний
        """
        try:
            if not self.spreadsheet:
                logger.warning("⚠️ Google Sheets not initialized, returning empty menu")
                return self._get_demo_menu()
            
            # Отримуємо лист "Меню"
            worksheet = self.spreadsheet.worksheet('Меню')
            
            # Отримуємо всі дані
            data = worksheet.get_all_records()
            
            # Фільтруємо активні товари
            active_items = [
                item for item in data 
                if item.get('Активний', '').lower() in ['yes', 'так', 'true', '1', 'активний']
            ]
            
            logger.info(f"📋 Loaded {len(active_items)} menu items from Google Sheets")
            return active_items
            
        except gspread.exceptions.WorksheetNotFound:
            logger.error("❌ Worksheet 'Меню' not found")
            return self._get_demo_menu()
        except Exception as e:
            logger.error(f"❌ Error loading menu: {e}")
            return self._get_demo_menu()
    
    def add_order(self, order_data: Dict) -> bool:
        """
        Додати замовлення в Google Sheets
        
        Очікувана структ 
