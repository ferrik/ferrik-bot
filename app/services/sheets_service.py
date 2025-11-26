"""
📊 Google Sheets Service - Інтеграція з базою даних
"""
import os
import json
import logging
from typing import List, Dict, Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)

# ============================================================================
# GOOGLE SHEETS SERVICE
# ============================================================================

class SheetsService:
    """
    Сервіс для роботи з Google Sheets
    
    Структура Spreadsheet:
    - Меню (Menu)
    - Замовлення (Orders)
    - Промокоди (Promo Codes)
    - Відгуки (Reviews)
    - Конфіг (Config)
    - Партнери (Partners)
    """
    
    def __init__(self):
        self.spreadsheet = None
        self._connect()
    
    def _connect(self):
        """Підключення до Google Sheets"""
        try:
            # Отримати credentials з environment
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
            
            if not creds_json or not spreadsheet_id:
                logger.warning("⚠️ Google Sheets credentials not configured - using mock data")
                return
            
            # Парсити JSON credentials
            creds_dict = json.loads(creds_json)
            
            # Авторизація
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            
            # Відкрити spreadsheet
            self.spreadsheet = client.open_by_key(spreadsheet_id)
            
            logger.info("✅ Connected to Google Sheets")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Google Sheets: {e}")
            self.spreadsheet = None
    
    def _get_worksheet(self, name: str):
        """Отримати worksheet по імені"""
        if not self.spreadsheet:
            return None
        
        try:
            return self.spreadsheet.worksheet(name)
        except Exception as e:
            logger.error(f"❌ Worksheet '{name}' not found: {e}")
            return None
    
    # ========================================================================
    # МЕНЮ
    # ========================================================================
    
    def get_menu(self) -> List[Dict]:
        """
        Отримати повне меню
        
        Returns:
            List з товарами у форматі:
            {
                'ID': '1',
                'Категорія': 'Піца',
                'Страва': 'Маргарита',
                'Опис': '...',
                'Ціна': '180',
                'Ресторан': 'FerrikPizza',
                'Час_доставки_хв': '30',
                'Фото_URL': '...',
                'Активний': 'TRUE',
                'Час_приготування_хв': '15',
                'Алергени': 'milk',
                'Рейтинг': '4.8',
                'Mood_Tags': 'calm,romantic,movie'
            }
        """
        sheet = self._get_worksheet("Меню")
        
        if not sheet:
            # Mock data для розробки
            logger.warning("⚠️ Using mock menu data")
            return self._get_mock_menu()
        
        try:
            data = sheet.get_all_records()
            logger.info(f"✅ Loaded {len(data)} menu items from Sheets")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading menu: {e}")
            return self._get_mock_menu()
    
    def _get_mock_menu(self) -> List[Dict]:
        """Mock дані для тестування (якщо Sheets недоступний)"""
        return [
            {
                'ID': '1',
                'Категорія': 'Піца',
                'Страва': 'Маргарита',
                'Опис': 'Класична піца з томатами та моцарелою',
                'Ціна': '180',
                'Ресторан': 'FerrikPizza',
                'Час_доставки_хв': '30',
                'Фото_URL': 'https://via.placeholder.com/300x200?text=Margherita',
                'Активний': 'TRUE',
                'Час_приготування_хв': '15',
                'Алергени': 'milk',
                'Рейтинг': '4.8',
                'Mood_Tags': 'calm,romantic,movie'
            },
            {
                'ID': '2',
                'Категорія': 'Піца',
                'Страва': 'Пепероні',
                'Опис': 'Гостра піца з ковбаскою пепероні',
                'Ціна': '200',
                'Ресторан': 'FerrikPizza',
                'Час_доставки_хв': '30',
                'Фото_URL': 'https://via.placeholder.com/300x200?text=Pepperoni',
                'Активний': 'TRUE',
                'Час_приготування_хв': '15',
                'Алергени': 'milk,meat',
                'Рейтинг': '4.9',
                'Mood_Tags': 'energy,party,spicy'
            },
            {
                'ID': '3',
                'Категорія': 'Бургери',
                'Страва': 'Чізбургер',
                'Опис': 'Соковитий бургер з сиром',
                'Ціна': '150',
                'Ресторан': 'BurgerHub',
                'Час_доставки_хв': '25',
                'Фото_URL': 'https://via.placeholder.com/300x200?text=Cheeseburger',
                'Активний': 'TRUE',
                'Час_приготування_хв': '12',
                'Алергени': 'milk,meat,gluten',
                'Рейтинг': '4.7',
                'Mood_Tags': 'energy,movie'
            },
            {
                'ID': '4',
                'Категорія': 'Салати',
                'Страва': 'Цезар',
                'Опис': 'Салат Цезар з куркою',
                'Ціна': '120',
                'Ресторан': 'FerrikPizza',
                'Час_доставки_хв': '20',
                'Фото_URL': 'https://via.placeholder.com/300x200?text=Caesar',
                'Активний': 'TRUE',
                'Час_приготування_хв': '10',
                'Алергени': 'milk,eggs',
                'Рейтинг': '4.6',
                'Mood_Tags': 'calm,romantic'
            },
            {
                'ID': '5',
                'Категорія': 'Закуски',
                'Страва': 'Крила BBQ',
                'Опис': 'Курячі крильця в соусі барбекю',
                'Ціна': '140',
                'Ресторан': 'BurgerHub',
                'Час_доставки_хв': '25',
                'Фото_URL': 'https://via.placeholder.com/300x200?text=BBQ+Wings',
                'Активний': 'TRUE',
                'Час_приготування_хв': '18',
                'Алергени': 'meat',
                'Рейтинг': '4.8',
                'Mood_Tags': 'party,spicy,movie'
            }
        ]
    
    # ========================================================================
    # ПАРТНЕРИ
    # ========================================================================
    
    def get_partners(self) -> List[Dict]:
        """
        Отримати список партнерів (ресторанів)
        
        Returns:
            List партнерів у форматі:
            {
                'ID': 'P001',
                'Назва_партнера': 'FerrikPizza',
                'Категорія': 'Піцерія',
                'Комісія_%': '10',
                'Рівень': 'Gold',
                'Преміум_до': '2025-12-31',
                'Статус': 'Активний',
                'Телефон': '+380501234567',
                'Активних_замовлень': '5',
                'Дохід_тиждень': '5000',
                'Рейтинг': '4.8'
            }
        """
        sheet = self._get_worksheet("Партнери")
        
        if not sheet:
            logger.warning("⚠️ Using mock partners data")
            return self._get_mock_partners()
        
        try:
            data = sheet.get_all_records()
            logger.info(f"✅ Loaded {len(data)} partners from Sheets")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading partners: {e}")
            return self._get_mock_partners()
    
    def _get_mock_partners(self) -> List[Dict]:
        """Mock дані партнерів"""
        return [
            {
                'ID': 'P001',
                'Назва_партнера': 'FerrikPizza',
                'Категорія': 'Піцерія',
                'Комісія_%': '10',
                'Рівень': 'Gold',
                'Преміум_до': '2025-12-31',
                'Статус': 'Активний',
                'Телефон': '+380501234567',
                'Активних_замовлень': '5',
                'Дохід_тиждень': '5000',
                'Рейтинг': '4.8'
            },
            {
                'ID': 'P002',
                'Назва_партнера': 'BurgerHub',
                'Категорія': 'Бургерна',
                'Комісія_%': '12',
                'Рівень': 'Silver',
                'Преміум_до': '2025-12-31',
                'Статус': 'Активний',
                'Телефон': '+380502345678',
                'Активних_замовлень': '3',
                'Дохід_тиждень': '3500',
                'Рейтинг': '4.5'
            }
        ]
    
    # ========================================================================
    # ЗАМОВЛЕННЯ
    # ========================================================================
    
    def save_order(self, order_data: Dict) -> bool:
        """
        Зберегти замовлення в Google Sheets
        
        Args:
            order_data: Дані замовлення у форматі:
            {
                'ID_Замовлення': 'ORD_20251126_120000_123456',
                'Telegram_User_ID': 123456,
                'Час_Замовлення': '2025-11-26 12:00:00',
                'Товари_JSON': '[{...}]',
                'Загальна_Сума': 410,
                'Адреса': 'вул. Хрещатик, 1',
                'Телефон': '+380501234567',
                'Спосіб_Оплати': 'cash',
                'Статус': 'Новий',
                'Канал': 'Mini App',
                'Вартість_доставки': 50,
                'Тип_доставки': 'delivery',
                'Примітки': '...',
                'Промокод': 'WELCOME10'
            }
        
        Returns:
            True якщо успішно, False якщо помилка
        """
        sheet = self._get_worksheet("Замовлення")
        
        if not sheet:
            logger.warning("⚠️ Sheets not available - order not saved (would save in production)")
            logger.info(f"📦 Order data: {json.dumps(order_data, ensure_ascii=False)}")
            return True  # Для розробки вважаємо успішним
        
        try:
            # Підготувати рядок для додавання
            row = [
                order_data.get('ID_Замовлення', ''),
                order_data.get('Telegram_User_ID', ''),
                order_data.get('Час_Замовлення', ''),
                order_data.get('Товари_JSON', ''),
                order_data.get('Загальна_Сума', 0),
                order_data.get('Адреса', ''),
                order_data.get('Телефон', ''),
                order_data.get('Спосіб_Оплати', 'cash'),
                order_data.get('Статус', 'Новий'),
                order_data.get('Канал', 'Telegram Bot'),
                order_data.get('Вартість_доставки', 0),
                order_data.get('Тип_доставки', 'delivery'),
                order_data.get('Час_доставки', ''),
                order_data.get('Оператор', ''),
                order_data.get('Примітки', ''),
                order_data.get('ID_партнера', ''),
                order_data.get('Сума_комісії', 0),
                order_data.get('Сплачена_комісія', 'Ні'),
                order_data.get('Статус_оплати', 'Очікується'),
                order_data.get('Дохід_платформи', 0),
                order_data.get('Промокод', ''),
                order_data.get('Застосована_знижка', 0),
                order_data.get('Статус_повернення', '')
            ]
            
            # Додати рядок в таблицю
            sheet.append_row(row)
            
            logger.info(f"✅ Order {order_data['ID_Замовлення']} saved to Sheets")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving order: {e}")
            return False
    
    def get_user_orders(self, telegram_user_id: int, limit: int = 10) -> List[Dict]:
        """
        Отримати замовлення користувача
        
        Args:
            telegram_user_id: ID користувача в Telegram
            limit: Максимум замовлень
        
        Returns:
            List замовлень (останні спочатку)
        """
        sheet = self._get_worksheet("Замовлення")
        
        if not sheet:
            logger.warning("⚠️ Using mock orders data")
            return []
        
        try:
            all_orders = sheet.get_all_records()
            
            # Фільтр по user_id
            user_orders = [
                order for order in all_orders
                if order.get('Telegram_User_ID') == telegram_user_id
            ]
            
            # Сортування по даті (останні спочатку)
            user_orders.sort(
                key=lambda x: x.get('Час_Замовлення', ''),
                reverse=True
            )
            
            return user_orders[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error loading user orders: {e}")
            return []
    
    # ========================================================================
    # ПРОМОКОДИ
    # ========================================================================
    
    def get_promo_codes(self) -> List[Dict]:
        """
        Отримати всі промокоди
        
        Returns:
            List промокодів у форматі:
            {
                'Код': 'WELCOME10',
                'ID_партнера': 'P001',
                'Знижка_%': '10',
                'Ліміт_використань': '100',
                'Використано': '5',
                'Дійсний_до': '2025-12-31',
                'Статус': 'Активний',
                'Створив': 'admin'
            }
        """
        sheet = self._get_worksheet("Промокоди")
        
        if not sheet:
            logger.warning("⚠️ Using mock promo codes")
            return self._get_mock_promos()
        
        try:
            data = sheet.get_all_records()
            logger.info(f"✅ Loaded {len(data)} promo codes from Sheets")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading promo codes: {e}")
            return self._get_mock_promos()
    
    def _get_mock_promos(self) -> List[Dict]:
        """Mock промокоди"""
        return [
            {
                'Код': 'WELCOME10',
                'ID_партнера': '',
                'Знижка_%': '10',
                'Ліміт_використань': '100',
                'Використано': '5',
                'Дійсний_до': '2025-12-31',
                'Статус': 'Активний',
                'Створив': 'admin'
            },
            {
                'Код': 'PIZZA20',
                'ID_партнера': 'P001',
                'Знижка_%': '20',
                'Ліміт_використань': '50',
                'Використано': '12',
                'Дійсний_до': '2025-12-31',
                'Статус': 'Активний',
                'Створив': 'admin'
            }
        ]
    
    def increment_promo_usage(self, promo_code: str) -> bool:
        """Збільшити лічильник використання промокоду"""
        sheet = self._get_worksheet("Промокоди")
        
        if not sheet:
            logger.warning("⚠️ Cannot increment promo usage - Sheets not available")
            return False
        
        try:
            # Знайти рядок з промокодом
            cell = sheet.find(promo_code)
            
            if not cell:
                logger.warning(f"⚠️ Promo code {promo_code} not found")
                return False
            
            # Отримати поточне значення Використано (колонка E)
            current_value = sheet.cell(cell.row, 5).value
            new_value = int(current_value or 0) + 1
            
            # Оновити значення
            sheet.update_cell(cell.row, 5, new_value)
            
            logger.info(f"✅ Promo code {promo_code} usage incremented to {new_value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error incrementing promo usage: {e}")
            return False
    
    # ========================================================================
    # КОНФІГ
    # ========================================================================
    
    def get_config(self) -> Dict[str, str]:
        """
        Отримати конфігурацію з Google Sheets
        
        Returns:
            Dict з налаштуваннями:
            {
                'OPEN_HOUR': '8',
                'CLOSE_HOUR': '23',
                'MIN_ORDER_AMOUNT': '100',
                'FREE_DELIVERY_FROM': '300',
                'DELIVERY_COST': '50'
            }
        """
        sheet = self._get_worksheet("Конфіг")
        
        if not sheet:
            logger.warning("⚠️ Using mock config")
            return self._get_mock_config()
        
        try:
            data = sheet.get_all_records()
            
            # Конвертувати в dict
            config = {row['Ключ']: row['Значення'] for row in data}
            
            logger.info(f"✅ Loaded config from Sheets")
            return config
            
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return self._get_mock_config()
    
    def _get_mock_config(self) -> Dict[str, str]:
        """Mock конфіг"""
        return {
            'OPEN_HOUR': '8',
            'CLOSE_HOUR': '23',
            'MIN_ORDER_AMOUNT': '100',
            'FREE_DELIVERY_FROM': '300',
            'DELIVERY_COST': '50'
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
sheets_service = SheetsService()
