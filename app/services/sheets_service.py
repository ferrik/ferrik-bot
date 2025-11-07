"""
📊 Сервіс для роботи з Google Sheets
Підтримка всіх 6 листів для багатопартнерської платформи
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, time
import gspread
from google.oauth2.service_account import Credentials

from app.utils.validators import safe_parse_price, format_price

logger = logging.getLogger(__name__)


class SheetsService:
    """Сервіс для роботи з Google Sheets"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Назви листів
    SHEET_MENU = "Menu"
    SHEET_ORDERS = "Orders"
    SHEET_PROMOCODES = "Promocodes"
    SHEET_REVIEWS = "Reviews"
    SHEET_CONFIG = "Config"
    SHEET_PARTNERS = "Partners"
    
    def __init__(self, config):
        """Ініціалізація сервісу"""
        self.config = config
        self.client = None
        self.spreadsheet = None
        self._cache = {}
        
        self._initialize()
    
    def _initialize(self):
        """Ініціалізація підключення до Google Sheets"""
        try:
            credentials_dict = json.loads(self.config.credentials_json)
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=self.SCOPES
            )
            
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(self.config.spreadsheet_id)
            
            logger.info(f"✅ Connected to Google Sheets: {self.spreadsheet.title}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets: {e}")
            raise
    
    # ========================================================================
    # МЕНЮ
    # ========================================================================
    
    def get_menu(self, partner_id: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Отримати меню"""
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_MENU)
            records = worksheet.get_all_records()
            
            menu_items = []
            for record in records:
                if not record.get('Активний', True):
                    continue
                
                item = {
                    'id': str(record.get('ID', '')),
                    'name': record.get('Страви', ''),
                    'category': record.get('Категорія', 'Other'),
                    'description': record.get('Опис', ''),
                    'price': safe_parse_price(record.get('Ціна', 0)),
                    'restaurant': record.get('Ресторан', ''),
                    'partner_id': record.get('ID_партнера', ''),
                    'delivery_time': record.get('Час Доставки (хв)', 30),
                    'cooking_time': record.get('Час_приготування', 20),
                    'photo_url': record.get('Фото URL', ''),
                    'allergens': record.get('Аллергени', ''),
                    'rating': float(record.get('Рейтинг', 0) or 0),
                    'active': record.get('Активний', True)
                }
                
                if partner_id and item['partner_id'] != partner_id:
                    continue
                
                if category and item['category'] != category:
                    continue
                
                if item['price'] > 0:
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
    
    def search_items(self, query: str, partner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Пошук товарів"""
        menu_items = self.get_menu(partner_id=partner_id)
        query_lower = query.lower()
        
        results = []
        for item in menu_items:
            if (query_lower in item.get('name', '').lower() or 
                query_lower in item.get('description', '').lower() or 
                query_lower in item.get('category', '').lower()):
                results.append(item)
        
        return results
    
    def get_categories(self, partner_id: Optional[str] = None) -> List[str]:
        """Отримати список категорій"""
        menu_items = self.get_menu(partner_id=partner_id)
        categories = set(item.get('category', 'Other') for item in menu_items)
        return sorted(list(categories))
    
    # ========================================================================
    # ЗАМОВЛЕННЯ
    # ========================================================================
    
    def save_order(self, order_data: Dict[str, Any]) -> str:
        """Зберегти замовлення"""
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_ORDERS)
            existing_orders = worksheet.get_all_records()
            order_id = str(len(existing_orders) + 1).zfill(4)
            
            items_json = json.dumps(order_data.get('items', []), ensure_ascii=False)
            
            subtotal = sum(
                safe_parse_price(item.get('price', 0)) * item.get('quantity', 1)
                for item in order_data.get('items', [])
            )
            
            delivery_cost = order_data.get('delivery_cost', 0)
            discount = order_data.get('discount', 0)
            total = subtotal + delivery_cost - discount
            
            partner_id = order_data.get('partner_id', '')
            commission_rate = self._get_partner_commission(partner_id)
            commission_amount = total * (commission_rate / 100) if commission_rate else 0
            platform_income = commission_amount
            
            row = [
                order_id,
                order_data.get('user_id', ''),
                order_data.get('timestamp', datetime.now().isoformat()),
                items_json,
                subtotal,
                order_data.get('address', ''),
                order_data.get('phone', ''),
                order_data.get('payment_method', 'Cash'),
                order_data.get('status', 'New'),
                'Telegram Bot',
                delivery_cost,
                total,
                order_data.get('delivery_type', 'Delivery'),
                order_data.get('delivery_time', ''),
                '',
                order_data.get('comment', ''),
                partner_id,
                commission_amount,
                False,
                order_data.get('payment_status', 'Not Paid'),
                platform_income,
                order_data.get('promocode', ''),
                discount,
                '',
            ]
            
            worksheet.append_row(row)
            
            if order_data.get('promocode'):
                self._increment_promocode_usage(order_data['promocode'])
            
            logger.info(f"✅ Order #{order_id} saved")
            return order_id
        
        except Exception as e:
            logger.error(f"❌ Error saving order: {e}")
            raise
    
    def get_orders(self, user_id: Optional[int] = None, partner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Отримати замовлення"""
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_ORDERS)
            records = worksheet.get_all_records()
            
            if user_id:
                records = [r for r in records if str(r.get('Telegram User ID')) == str(user_id)]
            
            if partner_id:
                records = [r for r in records if str(r.get('ID_партнера')) == str(partner_id)]
            
            return records
        except Exception as e:
            logger.error(f"❌ Error loading orders: {e}")
            return []
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Оновити статус замовлення"""
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_ORDERS)
            cell = worksheet.find(order_id)
            
            if cell:
                worksheet.update_cell(cell.row, 9, status)
                logger.info(f"✅ Order #{order_id} status: {status}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"❌ Error updating status: {e}")
            return False
    
    # ========================================================================
    # ПРОМОКОДИ
    # ========================================================================
    
    def validate_promocode(self, code: str, partner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Валідація промокоду"""
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_PROMOCODES)
            records = worksheet.get_all_records()
            
            for record in records:
                if record.get('Код', '').upper() == code.upper():
                    if record.get('Статус') != 'Активний':
                        return None
                    
                    promo_partner = str(record.get('ID_партнера', ''))
                    if partner_id and promo_partner and promo_partner != str(partner_id):
                        return None
                    
                    limit = record.get('Ліміт_використання', 0)
                    used = record.get('Кількість_використань', 0)
                    if limit > 0 and used >= limit:
                        return None
                    
                    expiry = record.get('Дата_закінчення_терміну', '')
                    if expiry:
                        try:
                            expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
                            if datetime.now() > expiry_date:
                                return None
                        except:
                            pass
                    
                    return {
                        'code': code,
                        'discount_percent': float(record.get('Знижка_%', 0)),
                        'valid': True,
                        'partner_id': promo_partner
                    }
            
            return None
        
        except Exception as e:
            logger.error(f"❌ Error validating promocode: {e}")
            return None
    
    def _increment_promocode_usage(self, code: str):
        """Збільшити лічильник використання промокоду"""
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_PROMOCODES)
            cell = worksheet.find(code)
            
            if cell:
                current = worksheet.cell(cell.row, 5).value or 0
                worksheet.update_cell(cell.row, 5, int(current) + 1)
        except Exception as e:
            logger.error(f"❌ Error incrementing promocode: {e}")
    
    # ========================================================================
    # КОНФІГ
    # ========================================================================
    
    def get_config(self, key: str) -> Optional[str]:
        """Отримати значення з конфігу"""
        try:
            if 'config' not in self._cache:
                worksheet = self.spreadsheet.worksheet(self.SHEET_CONFIG)
                records = worksheet.get_all_records()
                self._cache['config'] = {r['Ключ']: r['Значення'] for r in records}
            
            return self._cache['config'].get(key)
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return None
    
    def is_open_now(self) -> bool:
        """Перевірка чи зараз робочий час"""
        try:
            open_hour = int(self.get_config('OPEN_HOUR') or 8)
            close_hour = int(self.get_config('CLOSE_HOUR') or 23)
            
            current_hour = datetime.now().hour
            return open_hour <= current_hour < close_hour
        except:
            return True
    
    # ========================================================================
    # ПАРТНЕРИ
    # ========================================================================
    
    def get_partners(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Отримати список партнерів"""
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_PARTNERS)
            records = worksheet.get_all_records()
            
            partners = []
            for record in records:
                if active_only and record.get('Статус') != 'Активний':
                    continue
                
                partners.append({
                    'id': str(record.get('ID', '')),
                    'name': record.get('Ім\'я_партнера', ''),
                    'category': record.get('Категорія', ''),
                    'commission_rate': float(record.get('Ставка_комісії (%)', 0)),
                    'premium': record.get('Рівень_премії', '') == 'Преміум',
                    'rating': float(record.get('Рейтинг', 0) or 0),
                    'phone': record.get('Контактний_телефон', ''),
                    'status': record.get('Статус', '')
                })
            
            return partners
        except Exception as e:
            logger.error(f"❌ Error loading partners: {e}")
            return []
    
    def get_partner_by_id(self, partner_id: str) -> Optional[Dict[str, Any]]:
        """Отримати партнера за ID"""
        partners = self.get_partners(active_only=False)
        for partner in partners:
            if partner['id'] == partner_id:
                return partner
        return None
    
    def _get_partner_commission(self, partner_id: str) -> float:
        """Отримати ставку комісії партнера"""
        partner = self.get_partner_by_id(partner_id)
        return partner['commission_rate'] if partner else 0.0
    
    # ========================================================================
    # СТАТИСТИКА
    # ========================================================================
    
    def get_statistics(self, partner_id: Optional[str] = None) -> Dict[str, Any]:
        """Отримати статистику"""
        orders = self.get_orders(partner_id=partner_id)
        
        total_orders = len(orders)
        total_revenue = sum(float(o.get('Загальна сума', 0) or 0) for o in orders)
        avg_order = total_revenue / total_orders if total_orders > 0 else 0
        
        return {
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'avg_order_value': avg_order,
            'orders_today': len([o for o in orders if o.get('Час Замовлення', '').startswith(datetime.now().strftime('%Y-%m-%d'))])
        }
