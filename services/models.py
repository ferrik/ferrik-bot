# services/models.py
"""
🗄️ МОДЕЛІ БД - Структура таблиць
"""

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

# ============================================================================
# МЕНЮ ТОВАРІВ
# ============================================================================

class MenuItem(Base):
    """Модель товару в меню"""
    __tablename__ = 'menu_items'
    
    id = Column(String, primary_key=True)
    category = Column(String, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    restaurant = Column(String)
    delivery_time = Column(Integer)  # хвилини
    photo_url = Column(String)
    active = Column(Boolean, default=True)
    prep_time = Column(Integer)  # час приготування
    allergens = Column(String)
    rating = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'description': self.description,
            'photo_url': self.photo_url,
            'rating': self.rating,
            'delivery_time': self.delivery_time,
        }


# ============================================================================
# КОШИК КОРИСТУВАЧА
# ============================================================================

class UserCart(Base):
    """Модель кошика користувача"""
    __tablename__ = 'user_carts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    item_id = Column(String, nullable=False)
    item_name = Column(String)  # Зберігаємо назву для швидкого доступу
    quantity = Column(Integer, default=1)
    price = Column(Float)  # Ціна при додаванні
    added_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_name': self.item_name,
            'quantity': self.quantity,
            'price': self.price,
            'total': self.quantity * self.price,
        }


# ============================================================================
# ЗАМОВЛЕННЯ
# ============================================================================

class Order(Base):
    """Модель замовлення"""
    __tablename__ = 'orders'
    
    id = Column(String, primary_key=True)
    order_number = Column(String, unique=True, index=True)  # #00001, #00002
    user_id = Column(String, nullable=False, index=True)
    
    # Товари
    items = Column(JSON, nullable=False)  # [{id, name, qty, price}, ...]
    total_amount = Column(Float, nullable=False)
    
    # Доставка
    address = Column(String)
    phone = Column(String)
    delivery_time = Column(Integer)  # хвилини
    
    # Оплата
    payment_method = Column(String)  # card, cash, online
    status = Column(String, default='pending')  # pending, confirmed, delivered, cancelled
    
    # Комісія
    restaurant_id = Column(String)
    commission_rate = Column(Float)  # %
    commission_amount = Column(Float)  # грн
    
    # Промокод
    promo_code = Column(String)
    discount_amount = Column(Float, default=0)
    
    # Бонуси
    bonus_used = Column(Float, default=0)
    bonus_earned = Column(Float)  # 5% від суми
    
    # Часові мітки
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)
    delivered_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'user_id': self.user_id,
            'items': self.items,
            'total_amount': self.total_amount,
            'address': self.address,
            'phone': self.phone,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# КОРИСТУВАЧ & БОНУСИ
# ============================================================================

class User(Base):
    """Модель користувача"""
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)  # Telegram user_id
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String)
    
    # Статистика
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0)
    
    # Бонуси
    bonus_balance = Column(Float, default=0)
    
    # Реферали
    referral_code = Column(String, unique=True)
    referred_by = Column(String)  # user_id того хто запросив
    referrals_count = Column(Integer, default=0)
    
    # Статус
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_order_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'phone': self.phone,
            'total_orders': self.total_orders,
            'total_spent': self.total_spent,
            'bonus_balance': self.bonus_balance,
        }


# ============================================================================
# ПРОМОКОДИ
# ============================================================================

class PromoCode(Base):
    """Модель промокоду"""
    __tablename__ = 'promo_codes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, index=True)
    discount_percent = Column(Float)  # % знижки
    discount_amount = Column(Float)  # абсолютна знижка
    
    limit_uses = Column(Integer)  # ліміт використання
    current_uses = Column(Integer, default=0)
    
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    
    status = Column(String, default='active')  # active, expired, disabled
    created_by = Column(String)  # partner_id
    
    def to_dict(self):
        return {
            'code': self.code,
            'discount_percent': self.discount_percent,
            'discount_amount': self.discount_amount,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
        }


# ============================================================================
# ІНІЦІАЛІЗАЦІЯ БД
# ============================================================================

def init_db(database_url: str):
    """Ініціалізуй БД та створи всі таблиці"""
    try:
        engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(engine)
        logger.info("✅ Database tables created/verified")
        return engine
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        raise


def get_session(engine):
    """Отримай сесію для роботи з БД"""
    Session = sessionmaker(bind=engine)
    return Session()