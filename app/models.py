from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Text, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# ============================================================================
# 1. РЕСТОРАН (ПАРТНЕР)
# ============================================================================

class Restaurant(Base):
    __tablename__ = 'restaurants'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    commission_rate = Column(Float, default=15.0)
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime)
    status = Column(String(50), default='active')
    phone = Column(String(20))
    rating = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    menu_items = relationship('MenuItem', back_populates='restaurant', cascade='all, delete-orphan')
    orders = relationship('Order', back_populates='restaurant')
    reviews = relationship('Review', back_populates='restaurant')
    promo_codes = relationship('PromoCode', back_populates='restaurant')
    
    __table_args__ = (
        Index('idx_restaurant_status', 'status'),
        Index('idx_restaurant_premium', 'is_premium'),
    )

# ============================================================================
# 2. ПОЗИЦІЯ МЕНЮ
# ============================================================================

class MenuItem(Base):
    __tablename__ = 'menu_items'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False)
    preparation_time = Column(Integer, default=20)
    photo_url = Column(Text)
    is_active = Column(Boolean, default=True)
    allergens = Column(Text)
    rating = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    restaurant = relationship('Restaurant', back_populates='menu_items')
    order_items = relationship('OrderItem', back_populates='menu_item')
    
    __table_args__ = (
        Index('idx_menu_restaurant', 'restaurant_id'),
        Index('idx_menu_active', 'is_active'),
    )

# ============================================================================
# 3. КОРИСТУВАЧ
# ============================================================================

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    bonus_points = Column(Integer, default=0)
    user_level = Column(String(50), default='novice')
    favorite_dishes = Column(Text)
    last_order_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    orders = relationship('Order', back_populates='user')
    reviews = relationship('Review', back_populates='user')
    
    __table_args__ = (
        Index('idx_user_telegram_id', 'telegram_id'),
    )

# ============================================================================
# 4. ЗАМОВЛЕННЯ (ФІКСОВАНО - INTEGER id)
# ============================================================================

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(100), unique=True, nullable=False)
    telegram_user_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False)
    total_amount = Column(Float, nullable=False)
    delivery_cost = Column(Float, default=30.0)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(20), nullable=False)
    payment_method = Column(String(50), default='cash')
    status = Column(String(50), default='new')
    promo_code = Column(String(50))
    commission_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='orders')
    restaurant = relationship('Restaurant', back_populates='orders')
    items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    review = relationship('Review', uselist=False, back_populates='order')
    
    __table_args__ = (
        Index('idx_order_user', 'telegram_user_id'),
        Index('idx_order_restaurant', 'restaurant_id'),
        Index('idx_order_status', 'status'),
    )

# ============================================================================
# 5. ТОВАР У ЗАМОВЛЕННІ (ФІКСОВАНО)
# ============================================================================

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    menu_item_id = Column(Integer, ForeignKey('menu_items.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    order = relationship('Order', back_populates='items')
    menu_item = relationship('MenuItem', back_populates='order_items')

# ============================================================================
# 6. ПРОМОКОД
# ============================================================================

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'))
    discount_percent = Column(Float)
    discount_fixed = Column(Float)
    usage_limit = Column(Integer)
    usage_count = Column(Integer, default=0)
    expires_at = Column(DateTime)
    status = Column(String(50), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    restaurant = relationship('Restaurant', back_populates='promo_codes')
    
    def is_valid(self):
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        return True

# ============================================================================
# 7. ВІДГУК (ФІКСОВАНО)
# ============================================================================

class Review(Base):
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False)
    telegram_user_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    order = relationship('Order', back_populates='review')
    restaurant = relationship('Restaurant', back_populates='reviews')
    user = relationship('User', back_populates='reviews')
    
    __table_args__ = (
        Index('idx_review_restaurant', 'restaurant_id'),
    )

# ============================================================================
# 8. КОНФІГ
# ============================================================================

class Config(Base):
    __tablename__ = 'config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
