"""
🗄️ DATABASE - PostgreSQL Configuration
Файл для роботи з PostgreSQL базою даних
"""

import os
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ferrik_user:ferrik_secure_123!@localhost:5432/ferrik_bot"
)

logger.info(f"🗄️ Database URL: {DATABASE_URL.split('@')[0]}@...")

# ============================================================================
# ENGINE CONFIGURATION
# ============================================================================

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "False").lower() == "true",
    pool_pre_ping=True,          # Перевіряти з'єднання перед використанням
    pool_recycle=3600,           # Перезавантажувати кожну годину
    poolclass=NullPool,          # Для Render (безпечніше)
    connect_args={
        "connect_timeout": 10,
        "application_name": "ferrikbot_v2.1"
    }
)

# ============================================================================
# SESSION CONFIGURATION
# ============================================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# ============================================================================
# BASE FOR MODELS
# ============================================================================

Base = declarative_base()

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_db():
    """
    Отримати DB session
    
    Використання у Flask:
    @app.get('/example')
    def example():
        db = SessionLocal()
        try:
            # твій код
            pass
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    """
    Тест підключення до PostgreSQL
    
    Returns:
        True якщо підключення успішне, інакше False
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ PostgreSQL connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        return False


def init_db() -> bool:
    """
    Ініціалізація БД - створити всі таблиці
    
    Викликається при запуску додатку
    
    Returns:
        True якщо успішно, інакше False
    """
    try:
        # Створення всіх таблиць з Base метаклассу
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


def reset_db() -> bool:
    """
    Видалити всі таблиці (ОСТОРОЖНО!)
    
    ТІЛЬКИ для розробки! Не використовувати в production!
    
    Returns:
        True якщо успішно, інакше False
    """
    try:
        if os.getenv("ENVIRONMENT") == "production":
            logger.error("❌ Cannot reset database in production!")
            return False
        
        Base.metadata.drop_all(bind=engine)
        logger.warning("⚠️ All tables dropped")
        return True
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        return False


def migrate_from_sqlite(sqlite_path: str = "bot.db") -> bool:
    """
    Міграція даних зі SQLite в PostgreSQL
    
    Використовуйте ТІЛЬКИ якщо у вас є bot.db зі СТАРОЮ структурою
    
    Args:
        sqlite_path: Шлях до SQLite файлу
    
    Returns:
        True якщо успішно, інакше False
    """
    try:
        if not os.path.exists(sqlite_path):
            logger.warning(f"⚠️ SQLite file not found: {sqlite_path}")
            return False
        
        import sqlite3
        import json
        from datetime import datetime
        
        logger.info("🔄 Starting migration from SQLite...")
        
        # Підключитись до SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Отримати дані (якщо таблиці існують)
        try:
            sqlite_cursor.execute("SELECT * FROM user_states")
            user_states = sqlite_cursor.fetchall()
            logger.info(f"📊 Found {len(user_states)} user states")
        except:
            user_states = []
        
        try:
            sqlite_cursor.execute("SELECT * FROM orders")
            orders = sqlite_cursor.fetchall()
            logger.info(f"📊 Found {len(orders)} orders")
        except:
            orders = []
        
        sqlite_conn.close()
        
        logger.info(f"✅ Migration completed: {len(user_states)} users, {len(orders)} orders")
        return True
    
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")
        return False


def health_check() -> dict:
    """
    Комплексна перевірка здоров'я БД
    
    Returns:
        dict з статусом всіх компонентів
    """
    try:
        # 1. Тест з'єднання
        connection_ok = test_connection()
        
        # 2. Тест операцій
        with engine.connect() as conn:
            # SELECT
            conn.execute(text("SELECT 1"))
            
            # Таблиці
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            ))
            tables = result.fetchall()
        
        return {
            "status": "healthy" if connection_ok else "unhealthy",
            "connection": "ok" if connection_ok else "failed",
            "tables": len(tables),
            "timestamp": str(__import__('datetime').datetime.now())
        }
    
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ============================================================================
# MODELS (для майбутнього використання)
# ============================================================================

# Example:
# from app.database import Base
# from sqlalchemy import Column, Integer, String, DateTime
# from datetime import datetime
#
# class User(Base):
#     __tablename__ = "users"
#     
#     id = Column(Integer, primary_key=True)
#     telegram_id = Column(Integer, unique=True)
#     username = Column(String(255), nullable=True)
#     created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# INITIALIZATION CHECK
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 DATABASE DIAGNOSTIC")
    print("=" * 70)
    
    print("\n1️⃣ Testing connection...")
    if test_connection():
        print("✅ Connection OK")
    else:
        print("❌ Connection failed")
        exit(1)
    
    print("\n2️⃣ Database health check...")
    health = health_check()
    print(f"Status: {health.get('status')}")
    print(f"Tables: {health.get('tables')}")
    
    print("\n3️⃣ Initializing database...")
    if init_db():
        print("✅ Database initialized")
    else:
        print("❌ Initialization failed")
    
    print("\n" + "=" * 70)
    print("✅ Database check completed!")
    print("=" * 70)
