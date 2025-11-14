"""
Google Sheets Service - Database operations
FerrikBot v3.2
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import Google Sheets libraries
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    logger.warning("⚠️ Google Sheets libraries not available")


class SheetsService:
    """Service for Google Sheets operations"""
    
    def __init__(self):
        """Initialize Google Sheets connection"""
        self.client = None
        self.spreadsheet = None
        self.connected = False
        
        if not SHEETS_AVAILABLE:
            logger.error("❌ gspread not installed")
            return
        
        # Get credentials from environment
        sheets_id = os.environ.get('GOOGLE_SHEETS_ID')
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        
        if not sheets_id or not credentials_json:
            logger.warning("⚠️ Google Sheets credentials not found in environment")
            return
        
        try:
            # Parse credentials
            credentials_dict = json.loads(credentials_json)
            
            # Define scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Authorize
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                credentials_dict,
                scope
            )
            
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(sheets_id)
            
            self.connected = True
            logger.info("✅ Google Sheets connected successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Google Sheets: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to Google Sheets"""
        return self.connected
    
    # ==================== MENU OPERATIONS ====================
    
    def get_menu(self) -> List[Dict]:
        """
        Get all active menu items
        
        Returns:
            list: Menu items with structure matching your sheet
        """
        if not self.connected:
            logger.warning("⚠️ Sheets not connected, returning empty menu")
            return []
        
        try:
            sheet = self.spreadsheet.worksheet("Меню")
            records = sheet.get_all_records()
            
            # Filter only active items
            active_items = [
                item for item in records
                if str(item.get('Активний', '')).upper() in ['TRUE', 'ТАК', '1', 'YES']
            ]
            
            logger.info(f"✅ Loaded {len(active_items)} menu items")
            return active_items
            
        except Exception as e:
            logger.error(f"❌ Error loading menu: {e}")
            return []
    
    def get_menu_by_category(self, category: str) -> List[Dict]:
        """
        Get menu items by category
        
        Args:
            category: Category name (e.g., "Піца", "Бургери")
            
        Returns:
            list: Filtered menu items
        """
        menu = self.get_menu()
        return [item for item in menu if item.get('Категорія') == category]
    
    def get_menu_item(self, item_id: int) -> Optional[Dict]:
        """
        Get specific menu item by ID
        
        Args:
            item_id: Item ID
            
        Returns:
            dict or None: Menu item details
        """
        menu = self.get_menu()
        for item in menu:
            if item.get('ID') == item_id:
                return item
        return None
    
    # ==================== ORDER OPERATIONS ====================
    
    def add_order(self, order_data: Dict) -> bool:
        """
        Add new order to sheet
        
        Args:
            order_data: Order details
            
        Returns:
            bool: Success status
        """
        if not self.connected:
            logger.error("❌ Cannot add order: Sheets not connected")
            return False
        
        try:
            sheet = self.spreadsheet.worksheet("Замовлення")
            
            # Get next order ID
            all_orders = sheet.get_all_values()
            next_id = len(all_orders)  # Row count = ID (minus header)
            
            # Prepare row according to your structure
            row = [
                next_id,  # ID Замовлення
                order_data.get('user_id', ''),  # Telegram User ID
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Час Замовлення
                json.dumps(order_data.get('items', []), ensure_ascii=False),  # Товари (JSON)
                order_data.get('total', 0),  # Загальна Сума
                order_data.get('address', ''),  # Адреса
                order_data.get('phone', ''),  # Телефон
                order_data.get('payment_method', 'Готівка'),  # Спосіб Оплати
                'Нове',  # Статус
                'Telegram Bot',  # Канал
                order_data.get('delivery_cost', 0),  # Вартість доставки
                order_data.get('total', 0) + order_data.get('delivery_cost', 0),  # Загальна сума
                order_data.get('delivery_type', 'Доставка'),  # Тип доставки
                order_data.get('delivery_time', ''),  # Час доставки/самовивозу
                '',  # Оператор
                order_data.get('notes', ''),  # Примітки
                order_data.get('partner_id', ''),  # ID_партнера
                order_data.get('commission', 0),  # Сума_комісії
                'Ні',  # Сплачена_комісія
                'Не оплачено',  # Статус_оплати
                0,  # Дохід_платформи
                order_data.get('promo_code', ''),  # Промокод
                order_data.get('discount', 0),  # Застосована_знижка
                '',  # Статус_повернення_коштів
            ]
            
            # Append row
            sheet.append_row(row, value_input_option='USER_ENTERED')
            
            logger.info(f"✅ Order #{next_id} added successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding order: {e}", exc_info=True)
            return False
    
    def get_user_orders(self, user_id: int) -> List[Dict]:
        """
        Get all orders for specific user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            list: User's orders
        """
        if not self.connected:
            return []
        
        try:
            sheet = self.spreadsheet.worksheet("Замовлення")
            records = sheet.get_all_records()
            
            user_orders = [
                order for order in records
                if order.get('Telegram User ID') == user_id
            ]
            
            logger.info(f"✅ Found {len(user_orders)} orders for user {user_id}")
            return user_orders
            
        except Exception as e:
            logger.error(f"❌ Error getting user orders: {e}")
            return []
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        """
        Update order status
        
        Args:
            order_id: Order ID
            status: New status
            
        Returns:
            bool: Success status
        """
        if not self.connected:
            return False
        
        try:
            sheet = self.spreadsheet.worksheet("Замовлення")
            
            # Find order row (order_id + 2 because of header and 1-based indexing)
            row_number = order_id + 2
            
            # Update status column (column 9: Статус)
            sheet.update_cell(row_number, 9, status)
            
            logger.info(f"✅ Order #{order_id} status updated to '{status}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating order status: {e}")
            return False
    
    # ==================== PROMO CODE OPERATIONS ====================
    
    def get_promo_code(self, code: str) -> Optional[Dict]:
        """
        Get promo code details
        
        Args:
            code: Promo code
            
        Returns:
            dict or None: Promo code details
        """
        if not self.connected:
            return None
        
        try:
            sheet = self.spreadsheet.worksheet("Промокоди")
            records = sheet.get_all_records()
            
            for promo in records:
                if promo.get('Код', '').upper() == code.upper():
                    # Check if active
                    if promo.get('Статус') == 'Активний':
                        return promo
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting promo code: {e}")
            return None
    
    def use_promo_code(self, code: str) -> bool:
        """
        Increment promo code usage counter
        
        Args:
            code: Promo code
            
        Returns:
            bool: Success status
        """
        if not self.connected:
            return False
        
        try:
            sheet = self.spreadsheet.worksheet("Промокоди")
            cell = sheet.find(code)
            
            if cell:
                # Get current usage count
                usage_col = 5  # Кількість_використань
                current_usage = int(sheet.cell(cell.row, usage_col).value or 0)
                
                # Increment
                sheet.update_cell(cell.row, usage_col, current_usage + 1)
                
                logger.info(f"✅ Promo code '{code}' usage incremented")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error using promo code: {e}")
            return False
    
    # ==================== CONFIG OPERATIONS ====================
    
    def get_config(self, key: str) -> Optional[str]:
        """
        Get configuration value
        
        Args:
            key: Config key
            
        Returns:
            str or None: Config value
        """
        if not self.connected:
            return None
        
        try:
            sheet = self.spreadsheet.worksheet("Конфіг")
            records = sheet.get_all_records()
            
            for config in records:
                if config.get('Ключ') == key:
                    return config.get('Значення')
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting config: {e}")
            return None
    
    def is_open(self) -> bool:
        """
        Check if restaurant is open based on config
        
        Returns:
            bool: True if open
        """
        try:
            open_hour = int(self.get_config('OPEN_HOUR') or 8)
            close_hour = int(self.get_config('CLOSE_HOUR') or 23)
            
            current_hour = datetime.now().hour
            
            return open_hour <= current_hour < close_hour
            
        except:
            return True  # Default: always open
    
    # ==================== PARTNER OPERATIONS ====================
    
    def get_partners(self) -> List[Dict]:
        """
        Get all active partners
        
        Returns:
            list: Active partners
        """
        if not self.connected:
            return []
        
        try:
            sheet = self.spreadsheet.worksheet("Партнери")
            records = sheet.get_all_records()
            
            active_partners = [
                partner for partner in records
                if partner.get('Статус') == 'Активний'
            ]
            
            logger.info(f"✅ Loaded {len(active_partners)} active partners")
            return active_partners
            
        except Exception as e:
            logger.error(f"❌ Error getting partners: {e}")
            return []
    
    def get_partner(self, partner_id: str) -> Optional[Dict]:
        """
        Get specific partner by ID
        
        Args:
            partner_id: Partner ID
            
        Returns:
            dict or None: Partner details
        """
        partners = self.get_partners()
        for partner in partners:
            if partner.get('ID') == partner_id:
                return partner
        return None
    
    # ==================== REVIEW OPERATIONS ====================
    
    def add_review(self, review_data: Dict) -> bool:
        """
        Add review to sheet
        
        Args:
            review_data: Review details
            
        Returns:
            bool: Success status
        """
        if not self.connected:
            return False
        
        try:
            sheet = self.spreadsheet.worksheet("Відгуки")
            
            # Get next review ID
            all_reviews = sheet.get_all_values()
            next_id = len(all_reviews)
            
            row = [
                next_id,  # ID_відгуку
                review_data.get('partner_id', ''),  # ID_партнера
                review_data.get('user_id', ''),  # ID_користувача
                review_data.get('rating', 5),  # Рейтинг
                review_data.get('comment', ''),  # Коментар
                review_data.get('order_id', ''),  # ID_замовлення
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Дата
                0  # Кількість_корисних_посилань
            ]
            
            sheet.append_row(row, value_input_option='USER_ENTERED')
            
            logger.info(f"✅ Review #{next_id} added")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding review: {e}")
            return False


# Global instance
sheets_service = SheetsService()


# Export
__all__ = ['SheetsService', 'sheets_service']
