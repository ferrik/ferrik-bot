"""
📊 Сервіс для роботи з Google Sheets
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

from app.utils.validators import validate_item_data, safe_parse_price, format_price

logger = logging.getLogger(__name__)


class SheetsService:
    """Сервіс для роботи з Google Sheets"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self, config):
        """
        Ініціалізація сервісу
        
        Args:
            config: GoogleSheetsConfig з credentials та spreadsheet_id
        """
        self.config = config
        self.client = None
        self.spreadsheet = None
        
        self._initialize()
    
    def _initialize(self):
        """Ініціалізація підключення до Google Sheets"""
        try:
            # Парсимо credentials з JSON
            credentials_dict = json.loads(self.config.credentials_json)
            
            # Створюємо credentials
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=self.SCOPES
            )
            
            # Авторизація
            self.client = gspread.authorize(credentials)
            
            # Відкриваємо spreadsheet
            self.spreadsheet = self.client.open_by_key(self.config.spreadsheet_id)
            
            logger.info(f"✅ Connected to Google Sheets: {self.spreadsheet.title}")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets: {e}")
            raise
    
    # ========================================================================
    # Робота з меню
    # ========================================================================
    
    def get_menu(self) -> List[Dict[str, Any]]:
        """
        Отримати меню з Google Sheets
        
        Returns:
            list: [{'id': '1', 'name': 'Pizza', 'category': 'Main', 'price': 120, ...}, ...]
        """
        try:
            # Отримуємо worksheet
            worksheet = self.spreadsheet.worksheet(self.config.menu_sheet_name)
            
            # Отримуємо всі дані
            records = worksheet.get_all_records()
            
            # Фільтруємо та валідуємо
            menu_items = []
            for record in records:
                # Пропускаємо неактивні товари
                if not record.get('active', True):
                    continue
                
                # Форматуємо товар
                item = {
                    'id': str(record.get('id', '')),
                    'name': record.get('name', ''),
                    'category': record.get('category', 'Інше'),
                    'price': safe_parse_price(record.get('price', 0)),
                    'description': record.get('description', ''),
                    'image_url': record.get('image_url', ''),
                    'available': record.get('available', True)
                }
                
                # Валідація
                if validate_item_data(item):
                    menu_items.append(item)
            
            logger.info(f"📋 Loaded {len(menu_items)} menu items")
            return menu_items
        
        except Exception as e:
            logger.error(f"❌ Error loading menu: {e}")
            return []
    
    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Отримати товар за ID"""
        menu_items = self.get_menu()
        
        for item in menu_items:
            if item.get('id') == item_id:
                return item
        
        return None
    
    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """
        Пошук товарів за назвою або описом
        
        Args:
            query: Пошуковий запит
        
        Returns:
            list: Знайдені товари
        """
        menu_items = self.get_menu()
        query_lower = query.lower()
        
        results = []
        for item in menu_items:
            name = item.get('name', '').lower()
            description = item.get('description', '').lower()
            category = item.get('category', '').lower()
            
            if (query_lower in name or 
                query_lower in description or 
                query_lower in category):
                results.append(item)
        
        return results
    
    # ========================================================================
    # Робота з замовленнями
    # ========================================================================
    
    def save_order(self, order_data: Dict[str, Any]) -> str:
        """
        Зберегти замовлення в Google Sheets
        
        Args:
            order_data: Дані замовлення
        
        Returns:
            str: ID замовлення
        """
        try:
            # Отримуємо worksheet
            worksheet = self.spreadsheet.worksheet(self.config.orders_sheet_name)
            
            # Генеруємо ID замовлення
            existing_orders = worksheet.get_all_records()
            order_id = str(len(existing_orders) + 1).zfill(4)
            
            # Формуємо рядок для збереження
            timestamp = order_data.get('timestamp', datetime.now().isoformat())
            user_id = order_data.get('user_id', 'N/A')
            username = order_data.get('username', 'N/A')
            phone = order_data.get('phone', 'N/A')
            address = order_data.get('address', 'N/A')
            comment = order_data.get('comment', '')
            status = order_data.get('status', 'Новий')
            
            # Формуємо список товарів
            items_text = []
            total = 0.0
            
            for item in order_data.get('items', []):
                name = item.get('name', 'Unknown')
                price = safe_parse_price(item.get('price', 0))
                quantity = item.get('quantity', 1)
                item_total = price * quantity
                total += item_total
                
                items_text.append(f"{name} x{quantity} = {format_price(item_total)}")
            
            items_str = "\n".join(items_text)
            
            # Додаємо рядок
            row = [
                order_id,
                timestamp,
                user_id,
                username,
                phone,
                address,
                items_str,
                format_price(total),
                comment,
                status
            ]
            
            worksheet.append_row(row)
            
            logger.info(f"✅ Order #{order_id} saved to Google Sheets")
            return order_id
        
        except Exception as e:
            logger.error(f"❌ Error saving order: {e}")
            raise
    
    def get_orders(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Отримати замовлення
        
        Args:
            user_id: Фільтр за користувачем (опціонально)
        
        Returns:
            list: Список замовлень
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.config.orders_sheet_name)
            records = worksheet.get_all_records()
            
            if user_id:
                # Фільтруємо за користувачем
                records = [r for r in records if str(r.get('user_id')) == str(user_id)]
            
            return records
        
        except Exception as e:
            logger.error(f"❌ Error loading orders: {e}")
            return []
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """
        Оновити статус замовлення
        
        Args:
            order_id: ID замовлення
            status: Новий статус
        
        Returns:
            bool: True якщо успішно оновлено
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.config.orders_sheet_name)
            
            # Знаходимо рядок замовлення
            cell = worksheet.find(order_id)
            
            if cell:
                # Оновлюємо статус (припускаємо, що статус в останній колонці)
                worksheet.update_cell(cell.row, 10, status)  # 10 = колонка Status
                logger.info(f"✅ Order #{order_id} status updated to '{status}'")
                return True
            
            logger.warning(f"⚠️ Order #{order_id} not found")
            return False
        
        except Exception as e:
            logger.error(f"❌ Error updating order status: {e}")
            return False
    
    # ========================================================================
    # Допоміжні методи
    # ========================================================================
    
    def get_categories(self) -> List[str]:
        """Отримати список категорій"""
        menu_items = self.get_menu()
        categories = set(item.get('category', 'Інше') for item in menu_items)
        return sorted(list(categories))
    
    def get_items_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Отримати товари за категорією"""
        menu_items = self.get_menu()
        return [item for item in menu_items if item.get('category') == category]
    
    def test_connection(self) -> bool:
        """Тест підключення до Google Sheets"""
        try:
            title = self.spreadsheet.title
            logger.info(f"✅ Connection test successful: {title}")
            return True
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def get_spreadsheet_info(self) -> Dict[str, Any]:
        """Отримати інформацію про spreadsheet"""
        try:
            worksheets = self.spreadsheet.worksheets()
            
            return {
                'title': self.spreadsheet.title,
                'id': self.spreadsheet.id,
                'url': self.spreadsheet.url,
                'worksheets': [ws.title for ws in worksheets],
                'menu_sheet': self.config.menu_sheet_name,
                'orders_sheet': self.config.orders_sheet_name
            }
        except Exception as e:
            logger.error(f"❌ Error getting spreadsheet info: {e}")
            return {}


# ============================================================================
# Debugging
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTING SHEETS SERVICE")
    print("=" * 60)
    
    # Для тестування потрібно створити config
    # from app.config import load_config
    # _, _, sheets_config, _ = load_config()
    # service = SheetsService(sheets_config)
    
    print("\nThis module requires proper configuration to test.")
    print("Use it within the application context.")
