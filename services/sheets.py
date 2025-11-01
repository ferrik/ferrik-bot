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
                logger.warning("⚠️ Google Sheets not initialized, returning demo menu")
                return self._get_demo_menu()
            
            # Отримуємо лист "Меню"
            worksheet = self.spreadsheet.worksheet('Меню')
            
            # Отримуємо всі дані
            data = worksheet.get_all_records()
            
            # Фільтруємо активні товари
            active_items = [
                item for item in data 
                if str(item.get('Активний', '')).lower() in ['yes', 'так', 'true', '1', 'активний']
            ]
            
            logger.info(f"📋 Loaded {len(active_items)} menu items from Google Sheets")
            return active_items if active_items else self._get_demo_menu()
            
        except gspread.exceptions.WorksheetNotFound:
            logger.error("❌ Worksheet 'Меню' not found")
            return self._get_demo_menu()
        except Exception as e:
            logger.error(f"❌ Error loading menu: {e}")
            return self._get_demo_menu()
    
    def add_order(self, order_data: Dict) -> bool:
        """
        Додати замовлення в Google Sheets
        
        Очікувана структура листа "Замовлення":
        ID Замовлення | Telegram User ID | Час Замовлення | Товари (JSON) | 
        Загальна Сума | Адреса | Телефон | Статус
        """
        try:
            if not self.spreadsheet:
                logger.warning("⚠️ Google Sheets not initialized, order not saved")
                return False
            
            # Отримуємо лист "Замовлення"
            worksheet = self.spreadsheet.worksheet('Замовлення')
            
            # Формуємо рядок даних
            row = [
                order_data.get('order_id', ''),
                order_data.get('user_id', ''),
                order_data.get('timestamp', datetime.now().isoformat()),
                order_data.get('items', ''),
                order_data.get('total', 0),
                order_data.get('address', ''),
                order_data.get('phone', ''),
                order_data.get('status', 'pending')
            ]
            
            # Додаємо рядок
            worksheet.append_row(row)
            
            logger.info(f"✅ Order {order_data.get('order_id')} saved to Google Sheets")
            return True
            
        except gspread.exceptions.WorksheetNotFound:
            logger.error("❌ Worksheet 'Замовлення' not found")
            return False
        except Exception as e:
            logger.error(f"❌ Error saving order: {e}")
            return False
    
    def get_promocodes(self) -> List[Dict]:
        """Отримати промокоди"""
        try:
            if not self.spreadsheet:
                return []
            
            worksheet = self.spreadsheet.worksheet('Промокоди')
            data = worksheet.get_all_records()
            
            # Фільтруємо активні промокоди
            active_promos = [
                promo for promo in data
                if str(promo.get('Статус', '')).lower() == 'активний'
            ]
            
            return active_promos
            
        except Exception as e:
            logger.error(f"❌ Error loading promocodes: {e}")
            return []
    
    def get_partners(self) -> List[Dict]:
        """Отримати список партнерів"""
        try:
            if not self.spreadsheet:
                return []
            
            worksheet = self.spreadsheet.worksheet('Партнери')
            data = worksheet.get_all_records()
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading partners: {e}")
            return []
    
    def add_review(self, review_data: Dict) -> bool:
        """Додати відгук"""
        try:
            if not self.spreadsheet:
                return False
            
            worksheet = self.spreadsheet.worksheet('Відгуки')
            
            row = [
                review_data.get('review_id', ''),
                review_data.get('partner_id', ''),
                review_data.get('user_id', ''),
                review_data.get('rating', 0),
                review_data.get('comment', ''),
                review_data.get('order_id', ''),
                datetime.now().isoformat()
            ]
            
            worksheet.append_row(row)
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving review: {e}")
            return False
    
    def get_config(self) -> Dict:
        """Отримати конфігурацію"""
        try:
            if not self.spreadsheet:
                return self._get_default_config()
            
            worksheet = self.spreadsheet.worksheet('Конфіг')
            data = worksheet.get_all_records()
            
            # Конвертуємо в dict
            config = {row['Ключ']: row['Значення'] for row in data}
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return self._get_default_config()
    
    def _get_demo_menu(self) -> List[Dict]:
        """Демо-меню якщо Google Sheets недоступний"""
        return [
            {
                'ID': '1',
                'Категорія': 'Піца',
                'Страви': 'Піца Маргарита',
                'Опис': 'Класична італійська піца з моцарелою та базиліком',
                'Ціна': 180,
                'Ресторан': 'Ferrik Pizza',
                'Час Доставки (хв)': 30,
                'Фото URL': 'https://via.placeholder.com/300x200/FF6B6B/FFFFFF?text=Pizza',
                'Активний': 'Так',
                'Рейтинг': 4.8
            },
            {
                'ID': '2',
                'Категорія': 'Бургери',
                'Страви': 'Бургер Класик',
                'Опис': 'Соковитий бургер з яловичиною та свіжими овочами',
                'Ціна': 150,
                'Ресторан': 'Ferrik Burgers',
                'Час Доставки (хв)': 25,
                'Фото URL': 'https://via.placeholder.com/300x200/4ECDC4/FFFFFF?text=Burger',
                'Активний': 'Так',
                'Рейтинг': 4.6
            },
            {
                'ID': '3',
                'Категорія': 'Суші',
                'Страви': 'Філадельфія',
                'Опис': 'Рол з лососем, вершковим сиром та огірком',
                'Ціна': 220,
                'Ресторан': 'Ferrik Sushi',
                'Час Доставки (хв)': 35,
                'Фото URL': 'https://via.placeholder.com/300x200/95E1D3/FFFFFF?text=Sushi',
                'Активний': 'Так',
                'Рейтинг': 4.9
            },
            {
                'ID': '4',
                'Категорія': 'Салати',
                'Страви': 'Цезар',
                'Опис': 'Салат з куркою, листям салату та пармезаном',
                'Ціна': 120,
                'Ресторан': 'Ferrik Kitchen',
                'Час Доставки (хв)': 20,
                'Фото URL': 'https://via.placeholder.com/300x200/F38181/FFFFFF?text=Salad',
                'Активний': 'Так',
                'Рейтинг': 4.5
            },
            {
                'ID': '5',
                'Категорія': 'Десерти',
                'Страви': 'Тірамісу',
                'Опис': 'Італійський десерт з маскарпоне та кавою',
                'Ціна': 95,
                'Ресторан': 'Ferrik Desserts',
                'Час Доставки (хв)': 25,
                'Фото URL': 'https://via.placeholder.com/300x200/AA96DA/FFFFFF?text=Tiramisu',
                'Активний': 'Так',
                'Рейтинг': 4.7
            }
        ]
    
    def _get_default_config(self) -> Dict:
        """Дефолтна конфігурація"""
        return {
            'OPEN_HOUR': '8',
            'CLOSE_HOUR': '23',
            'MIN_ORDER_AMOUNT': '100',
            'DELIVERY_COST': '50',
            'FREE_DELIVERY_FROM': '500'
        }
    
    def is_connected(self) -> bool:
        """Перевірка підключення"""
        return self.client is not None and self.spreadsheet is not None


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
_sheets_instance = None

def get_sheets_service() -> SheetsService:
    """Отримати singleton instance сервісу"""
    global _sheets_instance
    if _sheets_instance is None:
        _sheets_instance = SheetsService()
    return _sheets_instance
