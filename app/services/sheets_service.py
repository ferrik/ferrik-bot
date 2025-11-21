"""
Google Sheets Service
Handles all interactions with the Google Sheet database
"""
import os
import json
import logging
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.menu_cache = []
        self.last_cache_time = None
        self.CACHE_DURATION = 300  # 5 minutes cache
        
        # Column structure for Orders (must match exact order in Sheet)
        self.ORDER_COLUMNS = [
            "ID Замовлення", "Telegram User ID", "Час Замовлення", 
            "Товари (JSON)", "Загальна Сума", "Адреса", "Телефон", 
            "Спосіб Оплати", "Статус", "Канал", "Вартість доставки", 
            "Тип доставки", "Час доставки/самовивозу", "Оператор", 
            "Примітки", "ID_партнера", "Сума_комісії", "Сплачена_комісія",
            "Статус_оплати", "Дохід_платформи", "Промокод", 
            "Застосована_знижка", "Статус_повернення_коштів"
        ]

    def connect(self):
        """Connect to Google Sheets"""
        try:
            creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
            sheet_id = os.environ.get('GOOGLE_SHEETS_ID')

            if not creds_json or not sheet_id:
                logger.warning("⚠️ Google Sheets credentials not found in env")
                return False

            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(sheet_id)
            logger.info("✅ Connected to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"❌ Sheets connection error: {e}")
            return False

    def is_connected(self):
        """Check if connected, try to reconnect if not"""
        if self.client and self.spreadsheet:
            return True
        return self.connect()

    def get_menu_items(self):
        """Get all active menu items with caching"""
        # Check cache
        import time
        if self.menu_cache and self.last_cache_time and \
           (time.time() - self.last_cache_time < self.CACHE_DURATION):
            return self.menu_cache

        if not self.is_connected():
            return []

        try:
            worksheet = self.spreadsheet.worksheet("Меню")
            records = worksheet.get_all_records()
            
            # Filter active items and convert types
            active_items = []
            for item in records:
                # Robust check for 'TRUE' string or boolean True
                is_active = str(item.get('Активний', '')).upper() == 'TRUE'
                
                if is_active:
                    # Ensure ID is int
                    try:
                        item['ID'] = int(item['ID'])
                    except:
                        continue
                        
                    # Ensure Price is int/float
                    try:
                        item['Ціна'] = float(str(item['Ціна']).replace(',', '.'))
                    except:
                        item['Ціна'] = 0
                        
                    active_items.append(item)
            
            self.menu_cache = active_items
            self.last_cache_time = time.time()
            return active_items
            
        except Exception as e:
            logger.error(f"❌ Error fetching menu: {e}")
            return []

    def get_menu_item(self, item_id):
        """Get single item by ID"""
        items = self.get_menu_items()
        for item in items:
            if item.get('ID') == item_id:
                return item
        return None

    def get_menu_by_category(self, category):
        """Get items by category"""
        items = self.get_menu_items()
        # Support both English (code) and Ukrainian (sheet) category names
        category_map = {
            'pizza': 'Піца',
            'burgers': 'Бургери',
            'snacks': 'Закуски',
            'drinks': 'Напої'
        }
        target_cat = category_map.get(category, category)
        
        return [
            i for i in items 
            if str(i.get('Категорія', '')).lower() == target_cat.lower()
        ]

    def add_order(self, order_data):
        """
        Add new order to 'Замовлення' sheet.
        Maps dictionary data to the specific column order.
        """
        if not self.is_connected():
            return False

        try:
            worksheet = self.spreadsheet.worksheet("Замовлення")
            
            # Generate Order ID (simple incremental based on rows)
            # In production, use UUID or handle concurrency better
            try:
                # Assumes header is row 1
                next_id = len(worksheet.col_values(1)) 
            except:
                next_id = 1001

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Prepare row data maintaining the exact column order
            row = []
            
            # Mapping logic
            items_json = json.dumps(order_data.get('items', []), ensure_ascii=False)
            total = order_data.get('total', 0)
            delivery_cost = order_data.get('delivery_cost', 0)
            total_sum = total + delivery_cost
            
            # Fill row based on self.ORDER_COLUMNS
            data_map = {
                "ID Замовлення": next_id,
                "Telegram User ID": order_data.get('user_id', ''),
                "Час Замовлення": timestamp,
                "Товари (JSON)": items_json,
                "Загальна Сума": total_sum,
                "Адреса": order_data.get('address', ''),
                "Телефон": order_data.get('phone', ''),
                "Спосіб Оплати": order_data.get('payment_method', 'Готівка'),
                "Статус": "Новий",
                "Канал": "Telegram Bot",
                "Вартість доставки": delivery_cost,
                "Тип доставки": order_data.get('delivery_type', 'Доставка'),
                "Час доставки/самовивозу": "", # Можна додати логіку пізніше
                "Оператор": "",
                "Примітки": order_data.get('notes', ''),
                "ID_партнера": order_data.get('partner_id', ''),
                "Сума_комісії": "",
                "Сплачена_комісія": "FALSE",
                "Статус_оплати": "Не оплачено",
                "Дохід_платформи": "",
                "Промокод": order_data.get('promo_code', ''),
                "Застосована_знижка": order_data.get('discount_amount', 0),
                "Статус_повернення_коштів": ""
            }
            
            for col in self.ORDER_COLUMNS:
                row.append(data_map.get(col, ""))
            
            worksheet.append_row(row)
            logger.info(f"✅ Order #{next_id} saved to Sheets")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding order: {e}")
            return False

# Create singleton instance
sheets_service = GoogleSheetsService()
