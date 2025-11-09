"""
📊 Сервіс для роботи з Google Sheets
Оновлено під актуальну структуру таблиці (українські назви колонок)
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

from app.utils.validators import safe_parse_price

logger = logging.getLogger(__name__)


class SheetsService:
    """Сервіс для роботи з Google Sheets"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Назви аркушів (українською)
    SHEET_MENU = "Меню"
    SHEET_ORDERS = "Замовлення"
    SHEET_PROMOCODES = "Промокоди"
    SHEET_REVIEWS = "Відгуки"
    SHEET_CONFIG = "Конфіг"
    SHEET_PARTNERS = "Партнери"
    
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
        """
        Отримати меню
        
        Args:
            partner_id: Фільтр по партнеру (опціонально)
            category: Фільтр по категорії (опціонально)
        
        Returns:
            Список товарів
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_MENU)
            records = worksheet.get_all_records()
            
            menu_items = []
            for record in records:
                # Пропустити неактивні товари
                if not record.get('Активний', False):
                    continue
                
                item = {
                    'id': str(record.get('ID', '')),
                    'category': record.get('Категорія', ''),
                    'name': record.get('Страви', ''),
                    'description': record.get('Опис', ''),
                    'price': safe_parse_price(record.get('Ціна', 0)),
                    'restaurant': record.get('Ресторан', ''),
                    'delivery_time': int(record.get('Час Доставки (хв)', 30) or 30),
                    'photo_url': record.get('Фото URL', ''),
                    'active': record.get('Активний', False),
                    'cooking_time': int(record.get('Час_приготування', 20) or 20),
                    'allergens': record.get('Аллергени', ''),
                    'rating': float(record.get('Рейтинг', 0) or 0),
                }
                
                # Фільтр по партнеру (якщо вказано)
                if partner_id and item['restaurant'] != partner_id:
                    continue
                
                # Фільтр по категорії (якщо вказано)
                if category and item['category'] != category:
                    continue
                
                # Додати тільки товари з ціною > 0
                if item['price'] > 0:
                    menu_items.append(item)
            
            logger.info(f"📋 Loaded {len(menu_items)} menu items")
            return menu_items
        
        except Exception as e:
            logger.error(f"❌ Error loading menu: {e}")
            return []
    
    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Отримати товар за ID
        
        Args:
            item_id: ID товару
        
        Returns:
            Товар або None
        """
        menu_items = self.get_menu()
        for item in menu_items:
            if item.get('id') == str(item_id):
                return item
        return None
    
    def search_items(self, query: str, partner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Пошук товарів за запитом
        
        Args:
            query: Пошуковий запит
            partner_id: Фільтр по партнеру (опціонально)
        
        Returns:
            Список знайдених товарів
        """
        menu_items = self.get_menu(partner_id=partner_id)
        query_lower = query.lower()
        
        results = []
        for item in menu_items:
            # Пошук в назві, описі або категорії
            if (query_lower in item.get('name', '').lower() or 
                query_lower in item.get('description', '').lower() or 
                query_lower in item.get('category', '').lower()):
                results.append(item)
        
        return results
    
    def get_categories(self, partner_id: Optional[str] = None) -> List[str]:
        """
        Отримати список унікальних категорій
        
        Args:
            partner_id: Фільтр по партнеру (опціонально)
        
        Returns:
            Список категорій (відсортовано)
        """
        menu_items = self.get_menu(partner_id=partner_id)
        categories = set(item.get('category', 'Інше') for item in menu_items)
        return sorted(list(categories))
    
    # ========================================================================
    # ЗАМОВЛЕННЯ
    # ========================================================================
    
    def save_order(self, order_data: Dict[str, Any]) -> str:
        """
        Зберегти замовлення в Google Sheets
        
        Args:
            order_data: Дані замовлення
        
        Returns:
            ID створеного замовлення
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_ORDERS)
            existing_orders = worksheet.get_all_records()
            order_id = str(len(existing_orders) + 1).zfill(4)
            
            # Серіалізувати товари в JSON
            items_json = json.dumps(order_data.get('items', []), ensure_ascii=False)
            
            # Розрахувати суми
            subtotal = sum(
                safe_parse_price(item.get('price', 0)) * item.get('quantity', 1)
                for item in order_data.get('items', [])
            )
            
            delivery_cost = order_data.get('delivery_cost', 0)
            discount = order_data.get('discount', 0)
            total = subtotal + delivery_cost - discount
            
            # Розрахувати комісію
            partner_id = order_data.get('partner_id', '')
            commission_rate = self._get_partner_commission(partner_id)
            commission_amount = total * (commission_rate / 100) if commission_rate else 0
            
            # Формуємо рядок для Google Sheets
            row = [
                order_id,                                      # ID Замовлення
                order_data.get('user_id', ''),                # Telegram User ID
                order_data.get('timestamp', datetime.now().isoformat()),  # Час Замовлення
                items_json,                                    # Товари (JSON)
                subtotal,                                      # Загальна Сума (проміжна)
                order_data.get('address', ''),                # Адреса
                order_data.get('phone', ''),                  # Телефон
                order_data.get('payment_method', 'Cash'),     # Спосіб Оплати
                order_data.get('status', 'New'),              # Статус
                'Telegram Bot',                                # Канал
                delivery_cost,                                 # Вартість доставки
                total,                                         # Загальна сума
                order_data.get('delivery_type', 'Delivery'),  # Тип доставки
                order_data.get('delivery_time', ''),          # Час доставки/самовивозу
                '',                                            # Оператор
                order_data.get('comment', ''),                # Примітки
                partner_id,                                    # ID_партнера
                commission_amount,                             # Сума_комісії
                False,                                         # Сплачена_комісія
                order_data.get('payment_status', 'Not Paid'), # Статус_оплати
                commission_amount,                             # Дохід_платформи
                order_data.get('promocode', ''),              # Промокод
                discount,                                      # Застосована_знижка
                '',                                            # Статус_повернення_коштів
            ]
            
            worksheet.append_row(row)
            
            # Якщо використано промокод - збільшити лічильник
            if order_data.get('promocode'):
                self._increment_promocode_usage(order_data['promocode'])
            
            logger.info(f"✅ Order #{order_id} saved")
            return order_id
        
        except Exception as e:
            logger.error(f"❌ Error saving order: {e}")
            raise
    
    def get_orders(self, user_id: Optional[int] = None, partner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримати список замовлень
        
        Args:
            user_id: Фільтр по користувачу (опціонально)
            partner_id: Фільтр по партнеру (опціонально)
        
        Returns:
            Список замовлень
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_ORDERS)
            records = worksheet.get_all_records()
            
            # Фільтрація по user_id
            if user_id:
                records = [r for r in records if str(r.get('Telegram User ID')) == str(user_id)]
            
            # Фільтрація по partner_id
            if partner_id:
                records = [r for r in records if str(r.get('ID_партнера')) == str(partner_id)]
            
            return records
        except Exception as e:
            logger.error(f"❌ Error loading orders: {e}")
            return []
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """
        Оновити статус замовлення
        
        Args:
            order_id: ID замовлення
            status: Новий статус (New, Processing, Delivered)
        
        Returns:
            True якщо успішно
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_ORDERS)
            cell = worksheet.find(order_id)
            
            if cell:
                # Колонка "Статус" - 9-та колонка (0-indexed: 8)
                worksheet.update_cell(cell.row, 9, status)
                logger.info(f"✅ Order #{order_id} status updated to: {status}")
                return True
            
            logger.warning(f"⚠️ Order #{order_id} not found")
            return False
        except Exception as e:
            logger.error(f"❌ Error updating order status: {e}")
            return False
    
    # ========================================================================
    # ПРОМОКОДИ
    # ========================================================================
    
    def validate_promocode(self, code: str, partner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Валідація промокоду
        
        Args:
            code: Код промокоду
            partner_id: ID партнера (для перевірки специфічних промокодів)
        
        Returns:
            Дані промокоду або None якщо невалідний
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_PROMOCODES)
            records = worksheet.get_all_records()
            
            for record in records:
                if record.get('Код', '').upper() == code.upper():
                    # Перевірка статусу
                    if record.get('Статус') != 'Активний':
                        return None
                    
                    # Перевірка партнера
                    promo_partner = str(record.get('ID_партнера', ''))
                    if partner_id and promo_partner and promo_partner != str(partner_id):
                        return None
                    
                    # Перевірка ліміту використань
                    limit = record.get('Ліміт_використання', 0)
                    used = record.get('Кількість_використань', 0)
                    if limit > 0 and used >= limit:
                        return None
                    
                    # Перевірка дати закінчення
                    expiry = record.get('Дата_закінчення_терміну_терміну', '')
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
        """
        Збільшити лічильник використання промокоду
        
        Args:
            code: Код промокоду
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_PROMOCODES)
            cell = worksheet.find(code)
            
            if cell:
                # Колонка "Кількість_використань" - 5-та колонка (0-indexed: 4)
                current = worksheet.cell(cell.row, 5).value or 0
                worksheet.update_cell(cell.row, 5, int(current) + 1)
                logger.info(f"✅ Promocode {code} usage incremented")
        except Exception as e:
            logger.error(f"❌ Error incrementing promocode: {e}")
    
    # ========================================================================
    # КОНФІГ
    # ========================================================================
    
    def get_config(self, key: str) -> Optional[str]:
        """
        Отримати значення з конфігу
        
        Args:
            key: Ключ конфігурації
        
        Returns:
            Значення або None
        """
        try:
            # Кешування конфігу
            if 'config' not in self._cache:
                worksheet = self.spreadsheet.worksheet(self.SHEET_CONFIG)
                records = worksheet.get_all_records()
                self._cache['config'] = {r['Ключ']: r['Значення'] for r in records}
            
            return self._cache['config'].get(key)
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return None
    
    def is_open_now(self) -> bool:
        """
        Перевірка чи зараз робочий час
        
        Returns:
            True якщо відкрито
        """
        try:
            open_hour = int(self.get_config('OPEN_HOUR') or 8)
            close_hour = int(self.get_config('CLOSE_HOUR') or 23)
            
            current_hour = datetime.now().hour
            return open_hour <= current_hour < close_hour
        except:
            return True  # За замовчуванням завжди відкрито
    
    # ========================================================================
    # ПАРТНЕРИ
    # ========================================================================
    
    def get_partners(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Отримати список партнерів
        
        Args:
            active_only: Тільки активні партнери
        
        Returns:
            Список партнерів
        """
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
                    'premium_level': record.get('Рівень_премії', 'Стандарт'),
                    'premium_until': record.get('Преміум_до', ''),
                    'status': record.get('Статус', ''),
                    'phone': record.get('Контактний_телефон', ''),
                    'weekly_orders': int(record.get('Тиждень_активних_замовлень', 0) or 0),
                    'weekly_revenue': float(record.get('Тиждень_доходу', 0) or 0),
                    'rating': float(record.get('Рейтинг', 0) or 0),
                })
            
            return partners
        except Exception as e:
            logger.error(f"❌ Error loading partners: {e}")
            return []
    
    def get_partner_by_id(self, partner_id: str) -> Optional[Dict[str, Any]]:
        """
        Отримати партнера за ID
        
        Args:
            partner_id: ID партнера
        
        Returns:
            Партнер або None
        """
        partners = self.get_partners(active_only=False)
        for partner in partners:
            if partner['id'] == partner_id:
                return partner
        return None
    
    def _get_partner_commission(self, partner_id: str) -> float:
        """
        Отримати ставку комісії партнера
        
        Args:
            partner_id: ID партнера
        
        Returns:
            Ставка комісії (%)
        """
        partner = self.get_partner_by_id(partner_id)
        return partner['commission_rate'] if partner else 0.0
    
    # ========================================================================
    # ВІДГУКИ
    # ========================================================================
    
    def save_review(self, review_data: Dict[str, Any]) -> str:
        """
        Зберегти відгук
        
        Args:
            review_data: Дані відгуку
        
        Returns:
            ID створеного відгуку
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_REVIEWS)
            existing_reviews = worksheet.get_all_records()
            review_id = f"R{str(len(existing_reviews) + 1).zfill(3)}"
            
            row = [
                review_id,
                review_data.get('partner_id', ''),
                review_data.get('user_id', ''),
                review_data.get('rating', 5),
                review_data.get('comment', ''),
                review_data.get('order_id', ''),
                datetime.now().isoformat(),
                0  # Початкова кількість корисних посилань
            ]
            
            worksheet.append_row(row)
            logger.info(f"✅ Review {review_id} saved")
            return review_id
        except Exception as e:
            logger.error(f"❌ Error saving review: {e}")
            raise
    
    def get_reviews(self, partner_id: Optional[str] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Отримати відгуки
        
        Args:
            partner_id: Фільтр по партнеру (опціонально)
            user_id: Фільтр по користувачу (опціонально)
        
        Returns:
            Список відгуків
        """
        try:
            worksheet = self.spreadsheet.worksheet(self.SHEET_REVIEWS)
            records = worksheet.get_all_records()
            
            if partner_id:
                records = [r for r in records if str(r.get('ID_партнера')) == str(partner_id)]
            
            if user_id:
                records = [r for r in records if str(r.get('ID_користувача')) == str(user_id)]
            
            return records
        except Exception as e:
            logger.error(f"❌ Error loading reviews: {e}")
            return []
    
    # ========================================================================
    # СТАТИСТИКА
    # ========================================================================
    
    def get_statistics(self, partner_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Отримати статистику
        
        Args:
            partner_id: Фільтр по партнеру (опціонально)
        
        Returns:
            Словник зі статистикою
        """
        orders = self.get_orders(partner_id=partner_id)
        
        total_orders = len(orders)
        total_revenue = sum(float(o.get('Загальна сума', 0) or 0) for o in orders)
        avg_order = total_revenue / total_orders if total_orders > 0 else 0
        
        # Замовлення сьогодні
        today = datetime.now().strftime('%Y-%m-%d')
        orders_today = len([
            o for o in orders 
            if o.get('Час Замовлення', '').startswith(today)
        ])
        
        return {
            'total_orders': total_orders,
            'total_revenue': round(total_revenue, 2),
            'avg_order_value': round(avg_order, 2),
            'orders_today': orders_today
        }
    
    # ========================================================================
    # КЕШУВАННЯ
    # ========================================================================
    
    def clear_cache(self):
        """Очистити кеш"""
        self._cache = {}
        logger.info("🧹 Cache cleared")
