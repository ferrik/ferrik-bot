# services/sheets_sync.py
"""
🔄 СИНХРОНІЗАЦІЯ З GOOGLE SHEETS
Автоматичне оновлення БД при змінах у таблиці
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)

class GoogleSheetsSync:
    """Синхронізація з Google Sheets"""
    
    def __init__(self, credentials_json: str, sheets_id: str):
        """
        Args:
            credentials_json: JSON із Google Service Account
            sheets_id: ID Google Sheets
        """
        self.sheets_id = sheets_id
        self.client = None
        self.spreadsheet = None
        
        try:
            # Парси credentials
            creds_dict = json.loads(credentials_json)
            
            # Авторизація
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            self.client = gspread.authorize(creds)
            
            # Відкрий таблицю
            self.spreadsheet = self.client.open_by_key(sheets_id)
            logger.info(f"✅ Google Sheets connected: {sheets_id}")
        
        except Exception as e:
            logger.error(f"❌ Google Sheets connection error: {e}")
            raise
    
    def get_sheet_data(self, sheet_name: str) -> List[Dict[str, Any]]:
        """
        Отримай всі дані з листа
        Перший рядок = заголовки
        """
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            all_rows = worksheet.get_all_values()
            
            if not all_rows or len(all_rows) < 2:
                logger.warning(f"⚠️ Sheet '{sheet_name}' is empty")
                return []
            
            headers = all_rows[0]
            data = []
            
            for row in all_rows[1:]:
                if not any(row):  # Пропусти порожні рядки
                    continue
                
                # Створи dict: header -> value
                item = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        item[header.strip()] = row[i].strip()
                    else:
                        item[header.strip()] = ""
                
                data.append(item)
            
            logger.info(f"✅ Fetched {len(data)} rows from '{sheet_name}'")
            return data
        
        except Exception as e:
            logger.error(f"❌ Error fetching '{sheet_name}': {e}")
            return []
    
    def get_menu(self) -> List[Dict[str, Any]]:
        """Отримай меню зі звичайного листа"""
        return self.get_sheet_data("Меню")
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Отримай замовлення"""
        return self.get_sheet_data("Замовлення")
    
    def get_promo_codes(self) -> List[Dict[str, Any]]:
        """Отримай промокоди"""
        return self.get_sheet_data("Промокоди")
    
    def get_reviews(self) -> List[Dict[str, Any]]:
        """Отримай відгуки"""
        return self.get_sheet_data("Відгуки")
    
    def get_config(self) -> Dict[str, str]:
        """Отримай конфіг (Ключ -> Значення)"""
        data = self.get_sheet_data("Конфіг")
        config = {}
        for row in data:
            key = row.get("Ключ", "")
            value = row.get("Значення", "")
            if key:
                config[key] = value
        return config
    
    def get_partners(self) -> List[Dict[str, Any]]:
        """Отримай партнерів"""
        return self.get_sheet_data("Партнери")
    
    def add_order(self, order_data: Dict[str, Any]) -> bool:
        """
        Додай замовлення в таблицю
        """
        try:
            worksheet = self.spreadsheet.worksheet("Замовлення")
            
            # Отримай всі рядки (для знаходження індекса)
            all_rows = worksheet.get_all_values()
            headers = all_rows[0] if all_rows else []
            
            # Підготуй рядок
            new_row = [order_data.get(h, "") for h in headers]
            
            # Додай рядок
            worksheet.append_row(new_row)
            logger.info(f"✅ Order added to Sheets")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error adding order: {e}")
            return False


# ============================================================================
# DATABASE SYNC
# ============================================================================

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class MenuItem(Base):
    """Модель меню"""
    __tablename__ = 'menu_items'
    
    id = Column(String, primary_key=True)
    category = Column(String)
    name = Column(String)
    description = Column(String)
    price = Column(Float)
    restaurant = Column(String)
    delivery_time = Column(Integer)
    photo_url = Column(String)
    active = Column(Boolean, default=True)
    prep_time = Column(Integer)
    allergens = Column(String)
    rating = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    """Модель замовлення"""
    __tablename__ = 'orders'
    
    id = Column(String, primary_key=True)
    telegram_user_id = Column(String)
    order_time = Column(DateTime)
    items = Column(JSON)
    total_sum = Column(Float)
    address = Column(String)
    phone = Column(String)
    payment_method = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseSync:
    """Синхронізація БД з Google Sheets"""
    
    def __init__(self, database_url: str):
        """
        Args:
            database_url: PostgreSQL URL (з Render)
        """
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"✅ Database connected")
    
    def sync_menu(self, menu_data: List[Dict[str, Any]]) -> bool:
        """Синхронізуй меню з Sheets в БД"""
        try:
            session = self.Session()
            
            # Видали старе меню
            session.query(MenuItem).delete()
            
            # Додай нове
            for item in menu_data:
                menu_item = MenuItem(
                    id=item.get("ID", ""),
                    category=item.get("Категорія", ""),
                    name=item.get("Страви", ""),
                    description=item.get("Опис", ""),
                    price=float(item.get("Ціна", 0) or 0),
                    restaurant=item.get("Ресторан", ""),
                    delivery_time=int(item.get("Час Доставки (хв)", 0) or 0),
                    photo_url=item.get("Фото URL", ""),
                    active=item.get("Активний", "").lower() == "так",
                    prep_time=int(item.get("Час_приготування", 0) or 0),
                    allergens=item.get("Аллергени", ""),
                    rating=float(item.get("Рейтинг", 0) or 0),
                )
                session.add(menu_item)
            
            session.commit()
            logger.info(f"✅ Synced {len(menu_data)} menu items")
            return True
        
        except Exception as e:
            logger.error(f"❌ Menu sync error: {e}")
            session.rollback()
            return False
        
        finally:
            session.close()
    
    def add_order(self, order_data: Dict[str, Any]) -> bool:
        """Додай замовлення в БД"""
        try:
            session = self.Session()
            
            order = Order(
                id=order_data.get("id"),
                telegram_user_id=order_data.get("telegram_user_id"),
                order_time=datetime.fromisoformat(order_data.get("order_time", datetime.utcnow().isoformat())),
                items=order_data.get("items", []),
                total_sum=order_data.get("total_sum", 0),
                address=order_data.get("address", ""),
                phone=order_data.get("phone", ""),
                payment_method=order_data.get("payment_method", ""),
                status=order_data.get("status", "pending"),
            )
            
            session.add(order)
            session.commit()
            logger.info(f"✅ Order added to DB")
            return True
        
        except Exception as e:
            logger.error(f"❌ Order add error: {e}")
            session.rollback()
            return False
        
        finally:
            session.close()
    
    def get_menu(self) -> List[Dict[str, Any]]:
        """Отримай все меню з БД"""
        try:
            session = self.Session()
            items = session.query(MenuItem).filter(MenuItem.active == True).all()
            
            result = [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "price": item.price,
                    "category": item.category,
                    "photo_url": item.photo_url,
                    "rating": item.rating,
                }
                for item in items
            ]
            
            return result
        
        finally:
            session.close()
    
    def get_menu_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Отримай меню по категорії"""
        try:
            session = self.Session()
            items = session.query(MenuItem).filter(
                MenuItem.category == category,
                MenuItem.active == True
            ).all()
            
            result = [
                {
                    "id": item.id,
                    "name": item.name,
                    "price": item.price,
                    "description": item.description,
                    "photo_url": item.photo_url,
                }
                for item in items
            ]
            
            return result
        
        finally:
            session.close()


# ============================================================================
# SCHEDULER (РЕГУЛЯРНЕ ОНОВЛЕННЯ)
# ============================================================================

from apscheduler.schedulers.background import BackgroundScheduler
import atexit

class SyncScheduler:
    """Регулярна синхронізація"""
    
    def __init__(self, sheets_sync: GoogleSheetsSync, db_sync: DatabaseSync):
        self.sheets_sync = sheets_sync
        self.db_sync = db_sync
        self.scheduler = BackgroundScheduler()
    
    def sync_menu_job(self):
        """Синхронізуй меню"""
        logger.info("🔄 Starting menu sync...")
        try:
            menu_data = self.sheets_sync.get_menu()
            self.db_sync.sync_menu(menu_data)
            logger.info("✅ Menu sync completed")
        except Exception as e:
            logger.error(f"❌ Menu sync failed: {e}")
    
    def start(self):
        """Запусти scheduler"""
        # Синхронізуй меню кожні 30 хвилин
        self.scheduler.add_job(
            self.sync_menu_job,
            'interval',
            minutes=30,
            id='sync_menu',
            name='Sync menu from Google Sheets'
        )
        
        self.scheduler.start()
        logger.info("✅ Sync scheduler started (every 30 minutes)")
        
        # Зупини при виході
        atexit.register(lambda: self.scheduler.shutdown())
    
    def stop(self):
        """Зупини scheduler"""
        self.scheduler.shutdown()
        logger.info("⏹️ Sync scheduler stopped")