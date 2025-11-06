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
    category = Column(String(100))  # Італійська, Суші, Українська
    commission_rate = Column(Float, default=15.0)  # % комісія
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime)
    status = Column(String(50), default='active')  # active/inactive
    phone = Column(String(20))
    rating = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    menu_items = relationship('MenuItem', back_populates='restaurant', cascade='all, delete-orphan')
    orders = relationship('Order', back_populates='restaurant')
    reviews = relationship('Review', back_populates='restaurant')
    promo_codes = relationship('PromoCode', back_populates='restaurant')
    
    __table_args__ = (
        Index('idx_restaurant_status', 'status'),
        Index('idx_restaurant_premium', 'is_premium'),
    )
    
    def __repr__(self):
        return f"<Restaurant {self.name}>"


# ============================================================================
# 2. ПОЗИЦІЯ МЕНЮ
# ============================================================================

class MenuItem(Base):
    __tablename__ = 'menu_items'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # Піца, Салати, Напої
    description = Column(Text)
    price = Column(Float, nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False)
    preparation_time = Column(Integer, default=20)  # хвилини
    photo_url = Column(Text)
    is_active = Column(Boolean, default=True)
    allergens = Column(Text)  # Глютен, Молоко
    rating = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    restaurant = relationship('Restaurant', back_populates='menu_items')
    order_items = relationship('OrderItem', back_populates='menu_item')
    
    __table_args__ = (
        Index('idx_menu_restaurant', 'restaurant_id'),
        Index('idx_menu_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<MenuItem {self.name} - {self.price}₴>"


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
    user_level = Column(String(50), default='novice')  # novice/gourmet/foodie/vip
    favorite_dishes = Column(Text)  # JSON
    last_order_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    orders = relationship('Order', back_populates='user')
    reviews = relationship('Review', back_populates='user')
    
    __table_args__ = (
        Index('idx_user_telegram_id', 'telegram_id'),
    )
    
    def __repr__(self):
        return f"<User {self.username or self.telegram_id}>"


# ============================================================================
# 4. ЗАМОВЛЕННЯ
# ============================================================================

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(100), unique=True, nullable=False)
    telegram_user_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False)
    total_amount = Column(Float, nullable=False)  # Без доставки
    delivery_cost = Column(Float, default=30.0)  # Фіксована 30₴
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)  # З доставкою
    address = Column(Text, nullable=False)
    phone = Column(String(20), nullable=False)
    payment_method = Column(String(50), default='cash')  # cash/card
    status = Column(String(50), default='new')  # new/cooking/delivering/delivered/cancelled
    promo_code = Column(String(50))
    commission_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship('User', back_populates='orders')
    restaurant = relationship('Restaurant', back_populates='orders')
    items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    review = relationship('Review', uselist=False, back_populates='order')
    
    __table_args__ = (
        Index('idx_order_user', 'telegram_user_id'),
        Index('idx_order_restaurant', 'restaurant_id'),
        Index('idx_order_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Order {self.external_id} - {self.status}>"


# ============================================================================
# 5. ТОВАР У ЗАМОВЛЕННІ
# ============================================================================

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    menu_item_id = Column(Integer, ForeignKey('menu_items.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Relationship
    order = relationship('Order', back_populates='items')
    menu_item = relationship('MenuItem', back_populates='order_items')
    
    def __repr__(self):
        return f"<OrderItem {self.menu_item} x{self.quantity}>"


# ============================================================================
# 6. ПРОМОКОД
# ============================================================================

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'))  # NULL = для всіх
    discount_percent = Column(Float)
    discount_fixed = Column(Float)
    usage_limit = Column(Integer)
    usage_count = Column(Integer, default=0)
    expires_at = Column(DateTime)
    status = Column(String(50), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    restaurant = relationship('Restaurant', back_populates='promo_codes')
    
    def is_valid(self):
        """Перевірити валідність"""
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        return True
    
    def __repr__(self):
        return f"<PromoCode {self.code}>"


# ============================================================================
# 7. ВІДГУК
# ============================================================================

class Review(Base):
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False)
    telegram_user_id = Column(Integer, ForeignKey('users.telegram_id'), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    order = relationship('Order', back_populates='review')
    restaurant = relationship('Restaurant', back_populates='reviews')
    user = relationship('User', back_populates='reviews')
    
    __table_args__ = (
        Index('idx_review_restaurant', 'restaurant_id'),
    )
    
    def __repr__(self):
        return f"<Review {self.restaurant.name} - {self.rating}⭐>"


# ============================================================================
# 8. КОНФІГ
# ============================================================================

class Config(Base):
    __tablename__ = 'config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Config {self.key}={self.value}>"
