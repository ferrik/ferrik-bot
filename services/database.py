"""
🗄️ Database Service - PostgreSQL + SQLite підтримка
Автоматично визначає тип БД з environment
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

try:
    from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Text, func
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import QueuePool
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ SQLAlchemy not installed, using simple dict storage")

logger = logging.getLogger(__name__)

if HAS_SQLALCHEMY:
    Base = declarative_base()

    # ========================================================================
    # ORM MODELS
    # ========================================================================

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
        self.use_sqlalchemy = HAS_SQLALCHEMY
        
        if self.use_sqlalchemy:
            self._initialize_connection()
            self._create_tables()
        else:
            # Fallback до in-memory storage
            self._init_simple_storage()
    
    def _init_simple_storage(self):
        """Простий in-memory storage якщо SQLAlchemy недоступний"""
        self.storage = {
            'user_states': {},
            'user_carts': {},
            'orders': [],
            'user_profiles': {}
        }
        logger.info("💾 Using simple in-memory storage (no SQLAlchemy)")
    
    def _initialize_connection(self):
        """Ініціалізація з'єднання з БД"""
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # PostgreSQL
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            logger.info("🐘 Using PostgreSQL database")
            
            self.engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
        else:
            # SQLite
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
    
    @contextmanager
    def get_session(self) -> Session:
        """Context manager для сесій"""
        if not self.use_sqlalchemy:
            yield None
            return
            
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
        if not self.use_sqlalchemy:
            return self.storage['user_states'].get(user_id)
        
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
        if not self.use_sqlalchemy:
            self.storage['user_states'][user_id] = {
                'state': state,
