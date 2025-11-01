"""
🗄️ Database Service - PostgreSQL + SQLite підтримка
Автоматично визначає тип БД з environment
"""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

Base = declarative_base()

# ============================================================================
# ORM MODELS
# ============================================================================

class UserState(Base):
    """Стани користувачів"""
    __tablename__ = 'user_states'
    
    user_id = Column(Integer, primary_key=True)
    state = Column(String(50), default='idle')
    state_data = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserCart(Base):
    """Кошики покупок"""
    __tablename__ = 'user_carts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    item_id = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    """Історія замовлень"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(50), unique=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=False)
    items_json = Column(JSON, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)


class UserProfile(Base):
    """Профілі користувачів для геймифікації"""
    __tablename__ = 'user_profiles'
    
    user_id = Column(Integer, primary_key=True)
    username = Column(String(100))
    first_name = Column(String(100))
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    level = Column(String(50), default='Новачок')
    badges = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# DATABASE CLASS
# ============================================================================

class Database:
    """
    Універсальний Database Manager
    Підтримує PostgreSQL (production) та SQLite (development)
    """
    
    def __init__(self):
        self.engine = None
        self.Session = None
        self._initialize_connection()
        self._create_tables()
    
    def _initialize_connection(self):
        """Ініціалізація з'єднання з БД"""
        # Визначаємо DATABASE_URL з environment
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # PostgreSQL (Render/Heroku)
            # Виправляємо старий формат postgres:// на postgresql://
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            logger.info("🐘 Using PostgreSQL database")
            
            # Connection pool для production
            self.engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Перевірка з'єднання
                echo=False
            )
        else:
            # SQLite (Local development)
            db_path = os.getenv('SQLITE_DB_PATH', 'bot.db')
            logger.info(f"💾 Using SQLite database: {db_path}")
            
            self.engine = create_engine(
                f'sqlite:///{db_path}',
                echo=False,
                connect_args={'check_same_thread': False}
            )
        
        self.Session = sessionmaker(bind=self.engine)
    
    def _create_tables(self):
        """Створення таблиць"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """Context manager для сесій"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Database error: {e}")
            raise
        finally:
            session.close()
    
    # ========================================================================
    # USER STATE METHODS
    # ========================================================================
    
    def get_user_state(self, user_id: int) -> Optional[Dict]:
        """Отримати стан користувача"""
        with self.get_session() as session:
            user_state = session.query(UserState).filter_by(user_id=user_id).first()
            
            if user_state:
                return {
                    'state': user_state.state,
                    'state_data': user_state.state_data or {}
                }
            return None
    
    def set_user_state(self, user_id: int, state: str, data: Optional[Dict] = None):
        """Встановити стан користувача"""
        with self.get_session() as session:
            user_state = session.query(UserState).filter_by(user_id=user_id).first()
            
            if user_state:
                user_state.state = state
                user_state.state_data = data or {}
                user_state.updated_at = datetime.utcnow()
            else:
                user_state = UserState(
                    user_id=user_id,
                    state=state,
                    state_data=data or {}
                )
                session.add(user_state)
    
    # ========================================================================
    # CART METHODS
    # ========================================================================
    
    def get_cart(self, user_id: int) -> List[Dict]:
        """Отримати кошик користувача"""
        with self.get_session() as session:
            cart_items = session.query(UserCart).filter_by(user_id=user_id).all()
            
            return [{
                'id': item.id,
                'item_id': item.item_id,
                'name': item.name,
                'price': item.price,
                'quantity': item.quantity
            } for item in cart_items]
    
    def add_to_cart(self, user_id: int, item_id: str, name: str, price: float, quantity: int = 1):
        """Додати товар у кошик"""
        with self.get_session() as session:
            # Перевірка, чи вже є
            existing = session.query(UserCart).filter_by(
                user_id=user_id,
                item_id=item_id
            ).first()
            
            if existing:
                existing.quantity += quantity
                existing.updated_at = datetime.utcnow()
            else:
                cart_item = UserCart(
                    user_id=user_id,
                    item_id=item_id,
                    name=name,
                    price=price,
                    quantity=quantity
                )
                session.add(cart_item)
    
    def remove_from_cart(self, user_id: int, item_id: str):
        """Видалити товар з кошика"""
        with self.get_session() as session:
            session.query(UserCart).filter_by(
                user_id=user_id,
                item_id=item_id
            ).delete()
    
    def clear_cart(self, user_id: int):
        """Очистити кошик"""
        with self.get_session() as session:
            session.query(UserCart).filter_by(user_id=user_id).delete()
    
    def update_cart_quantity(self, user_id: int, item_id: str, quantity: int):
        """Оновити кількість товару"""
        with self.get_session() as session:
            cart_item = session.query(UserCart).filter_by(
                user_id=user_id,
                item_id=item_id
            ).first()
            
            if cart_item:
                if quantity > 0:
                    cart_item.quantity = quantity
                    cart_item.updated_at = datetime.utcnow()
                else:
                    session.delete(cart_item)
    
    # ========================================================================
    # ORDER METHODS
    # ========================================================================
    
    def create_order(
        self,
        user_id: int,
        phone: str,
        address: str,
        items_json: str,
        total_amount: float
    ) -> str:
        """Створити замовлення"""
        with self.get_session() as session:
            # Генеруємо номер замовлення
            order_number = f"F{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            order = Order(
                order_number=order_number,
                user_id=user_id,
                phone=phone,
                address=address,
                items_json=items_json if isinstance(items_json, str) else json.dumps(items_json),
                total_amount=total_amount,
                status='pending'
            )
            session.add(order)
            session.flush()
            
            # Оновлюємо профіль користувача
            self._update_user_profile(session, user_id, total_amount)
            
            return order_number
    
    def get_user_orders(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Отримати замовлення користувача"""
        with self.get_session() as session:
            orders = session.query(Order)\
                .filter_by(user_id=user_id)\
                .order_by(Order.created_at.desc())\
                .limit(limit)\
                .all()
            
            return [{
                'id': order.id,
                'order_number': order.order_number,
                'total_amount': order.total_amount,
                'status': order.status,
                'created_at': order.created_at,
                'items_json': order.items_json
            } for order in orders]
    
    def update_order_status(self, order_number: str, status: str):
        """Оновити статус замовлення"""
        with self.get_session() as session:
            order = session.query(Order).filter_by(order_number=order_number).first()
            if order:
                order.status = status
    
    # ========================================================================
    # USER PROFILE METHODS (для геймифікації)
    # ========================================================================
    
    def _update_user_profile(self, session: Session, user_id: int, amount: float):
        """Оновити профіль користувача (внутрішній метод)"""
        profile = session.query(UserProfile).filter_by(user_id=user_id).first()
        
        if profile:
            profile.total_orders += 1
            profile.total_spent += amount
            profile.updated_at = datetime.utcnow()
        else:
            profile = UserProfile(
                user_id=user_id,
                total_orders=1,
                total_spent=amount
            )
            session.add(profile)
    
    def get_user_profile(self, user_id: int) -> Optional[Dict]:
        """Отримати профіль користувача"""
        with self.get_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            
            if profile:
                return {
                    'user_id': profile.user_id,
                    'username': profile.username,
                    'total_orders': profile.total_orders,
                    'total_spent': profile.total_spent,
                    'level': profile.level,
                    'badges': profile.badges or []
                }
            return None
    
    def update_user_profile(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        level: Optional[str] = None,
        badges: Optional[List] = None
    ):
        """Оновити профіль користувача"""
        with self.get_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            
            if not profile:
                profile = UserProfile(user_id=user_id)
                session.add(profile)
            
            if username:
                profile.username = username
            if first_name:
                profile.first_name = first_name
            if level:
                profile.level = level
            if badges is not None:
                profile.badges = badges
            
            profile.updated_at = datetime.utcnow()
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Отримати загальну статистику"""
        with self.get_session() as session:
            total_users = session.query(UserProfile).count()
            total_orders = session.query(Order).count()
            total_revenue = session.query(Order).with_entities(
                sqlalchemy.func.sum(Order.total_amount)
            ).scalar() or 0.0
            
            return {
                'total_users': total_users,
                'total_orders': total_orders,
                'total_revenue': total_revenue
            }
    
    def cleanup_old_carts(self, days: int = 7):
        """Очистити старі кошики"""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted = session.query(UserCart)\
                .filter(UserCart.updated_at < cutoff_date)\
                .delete()
            logger.info(f"🧹 Cleaned {deleted} old cart items")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
_db_instance = None

def get_database() -> Database:
    """Отримати singleton instance бази даних"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


# Для зручності
db = get_database()
