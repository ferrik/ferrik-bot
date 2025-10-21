import logging
import json
import os
from datetime import datetime
from threading import Lock
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

logger = logging.getLogger("database")

# Визначаємо тип БД з environment
DATABASE_URL = os.getenv('DATABASE_URL')
USE_POSTGRES = DATABASE_URL and DATABASE_URL.startswith('postgres')

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    logger.info("🐘 Using PostgreSQL database")
else:
    import sqlite3
    logger.info("📁 Using SQLite database")
    DB_PATH = "hubsy_data.db"

db_lock = Lock()

@contextmanager
def get_db():
    """Thread-safe database connection"""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        conn.autocommit = False
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def init_database():
    """Ініціалізація бази даних"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            if USE_POSTGRES:
                # PostgreSQL синтаксис
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        id TEXT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username TEXT,
                        items TEXT NOT NULL,
                        total DECIMAL(10,2) NOT NULL,
                        status TEXT DEFAULT 'new',
                        phone TEXT,
                        address TEXT,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_activity (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        action TEXT NOT NULL,
                        data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Індекси
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity(user_id)")
                
            else:
                # SQLite синтаксис
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        username TEXT,
                        items TEXT NOT NULL,
                        total REAL NOT NULL,
                        status TEXT DEFAULT 'new',
                        phone TEXT,
                        address TEXT,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        action TEXT NOT NULL,
                        data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Індекси
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity(user_id)")
            
            conn.commit()
            logger.info("Database initialized")
            return True
            
    except Exception as e:
        logger.error(f"Database init error: {e}", exc_info=True)
        return False


def save_order(order_id, user_id, username, items, total, phone="", address="", notes=""):
    """Зберегти замовлення"""
    try:
        with db_lock:
            with get_db() as conn:
                cursor = conn.cursor()
                
                if USE_POSTGRES:
                    cursor.execute("""
                        INSERT INTO orders (id, user_id, username, items, total, phone, address, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (order_id, user_id, username, json.dumps(items, ensure_ascii=False), 
                          total, phone, address, notes))
                else:
                    cursor.execute("""
                        INSERT INTO orders (id, user_id, username, items, total, phone, address, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (order_id, user_id, username, json.dumps(items, ensure_ascii=False), 
                          total, phone, address, notes))
                
                conn.commit()
                
        logger.info(f"Order saved: {order_id}")
        return True
        
    except Exception as e:
        logger.error(f"Save order error: {e}", exc_info=True)
        return False


def get_order(order_id):
    """Отримати замовлення за ID"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            if USE_POSTGRES:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            else:
                cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
            
    except Exception as e:
        logger.error(f"Get order error: {e}")
        return None


def update_order_status(order_id, status):
    """Оновити статус замовлення"""
    try:
        with db_lock:
            with get_db() as conn:
                cursor = conn.cursor()
                
                if USE_POSTGRES:
                    cursor.execute("""
                        UPDATE orders 
                        SET status = %s, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, (status, order_id))
                else:
                    cursor.execute("""
                        UPDATE orders 
                        SET status = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (status, order_id))
                
                conn.commit()
                
        logger.info(f"Order {order_id} status: {status}")
        return True
        
    except Exception as e:
        logger.error(f"Update status error: {e}")
        return False


def get_orders_by_status(status="new", limit=50):
    """Отримати замовлення за статусом"""
    try:
        with get_db() as conn:
            if USE_POSTGRES:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT * FROM orders 
                    WHERE status = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (status, limit))
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM orders 
                    WHERE status = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (status, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
    except Exception as e:
        logger.error(f"Get orders error: {e}")
        return []


def get_user_orders(user_id, limit=10):
    """Історія замовлень користувача"""
    try:
        with get_db() as conn:
            if USE_POSTGRES:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT * FROM orders 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (user_id, limit))
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM orders 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
    except Exception as e:
        logger.error(f"Get user orders error: {e}")
        return []


def log_activity(user_id, action, data=None):
    """Логування активності"""
    try:
        with db_lock:
            with get_db() as conn:
                cursor = conn.cursor()
                
                if USE_POSTGRES:
                    cursor.execute("""
                        INSERT INTO user_activity (user_id, action, data)
                        VALUES (%s, %s, %s)
                    """, (user_id, action, json.dumps(data, ensure_ascii=False) if data else None))
                else:
                    cursor.execute("""
                        INSERT INTO user_activity (user_id, action, data)
                        VALUES (?, ?, ?)
                    """, (user_id, action, json.dumps(data, ensure_ascii=False) if data else None))
                
                conn.commit()
                
    except Exception as e:
        logger.error(f"Log activity error: {e}")


def get_statistics(days=1):
    """Статистика за період"""
    try:
        with get_db() as conn:
            if USE_POSTGRES:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_orders,
                        SUM(total) as total_revenue,
                        AVG(total) as avg_order
                    FROM orders
                    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                """, (days,))
                
                stats = dict(cursor.fetchone())
                
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM orders
                    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    GROUP BY status
                """, (days,))
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_orders,
                        SUM(total) as total_revenue,
                        AVG(total) as avg_order
                    FROM orders
                    WHERE created_at >= datetime('now', '-' || ? || ' days')
                """, (days,))
                
                stats = dict(cursor.fetchone())
                
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM orders
                    WHERE created_at >= datetime('now', '-' || ? || ' days')
                    GROUP BY status
                """, (days,))
            
            stats['by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            return stats
            
    except Exception as e:
        logger.error(f"Get statistics error: {e}")
        return {}


def get_popular_items(limit=5):
    """Топ популярних страв"""
    try:
        with get_db() as conn:
            if USE_POSTGRES:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT items FROM orders
                    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                """)
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT items FROM orders
                    WHERE created_at >= datetime('now', '-7 days')
                """)
            
            # Рахуємо страви
            item_counts = {}
            for row in cursor.fetchall():
                try:
                    items = json.loads(row['items'])
                    for item in items:
                        name = item.get('name', '')
                        if name:
                            item_counts[name] = item_counts.get(name, 0) + 1
                except:
                    continue
            
            # Сортуємо
            sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_items[:limit]
            
    except Exception as e:
        logger.error(f"Get popular items error: {e}")
        return []


def cleanup_old_data(days=90):
    """Очистка старих даних"""
    try:
        with db_lock:
            with get_db() as conn:
                cursor = conn.cursor()
                
                if USE_POSTGRES:
                    cursor.execute("""
                        DELETE FROM user_activity
                        WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '%s days'
                    """, (days,))
                    
                    cursor.execute("""
                        UPDATE orders
                        SET status = 'archived'
                        WHERE status IN ('completed', 'cancelled')
                        AND created_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                    """, (days,))
                else:
                    cursor.execute("""
                        DELETE FROM user_activity
                        WHERE timestamp < datetime('now', '-' || ? || ' days')
                    """, (days,))
                    
                    cursor.execute("""
                        UPDATE orders
                        SET status = 'archived'
                        WHERE status IN ('completed', 'cancelled')
                        AND created_at < datetime('now', '-' || ? || ' days')
                    """, (days,))
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days} days")
                
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

def sync_menu_from_sheets():
    """Синхронізує меню з Google Sheets в PostgreSQL"""
    if not USE_POSTGRES:
        logger.info("Skipping menu sync - not using PostgreSQL")
        return False
    
    try:
        from services.sheets import get_menu_from_sheet
        
        logger.info("📥 Syncing menu from Google Sheets...")
        menu_items = get_menu_from_sheet()
        
        with db_lock:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Створюємо таблицю якщо не існує
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS menu (
                        id TEXT PRIMARY KEY,
                        category TEXT,
                        name TEXT NOT NULL,
                        description TEXT,
                        price DECIMAL(10,2),
                        restaurant TEXT,
                        delivery_time INTEGER,
                        photo_url TEXT,
                        is_active BOOLEAN DEFAULT true,
                        prep_time INTEGER,
                        allergens TEXT,
                        rating DECIMAL(3,1),
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Вставляємо/оновлюємо кожен елемент
                synced = 0
                for item in menu_items:
                    try:
                        cursor.execute("""
                            INSERT INTO menu (
                                id, category, name, description, price, 
                                restaurant, delivery_time, photo_url, is_active,
                                prep_time, allergens, rating
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                category = EXCLUDED.category,
                                name = EXCLUDED.name,
                                description = EXCLUDED.description,
                                price = EXCLUDED.price,
                                restaurant = EXCLUDED.restaurant,
                                delivery_time = EXCLUDED.delivery_time,
                                photo_url = EXCLUDED.photo_url,
                                is_active = EXCLUDED.is_active,
                                prep_time = EXCLUDED.prep_time,
                                allergens = EXCLUDED.allergens,
                                rating = EXCLUDED.rating,
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            item.get('ID'),
                            item.get('Категорія'),
                            item.get('Страви'),
                            item.get('Опис'),
                            item.get('Ціна', 0),
                            item.get('Ресторан'),
                            int(str(item.get('Час Доставки (хв)', 0) or 0)),
                            item.get('Фото URL'),
                            True,
                            int(str(item.get('Час_приготування', 0) or 0)),
                            item.get('Аллергени'),
                            float(str(item.get('Рейтинг', 0) or 0).replace(',', '.'))
                        ))
                        synced += 1
                    except Exception as e:
                        logger.error(f"Error syncing item {item.get('ID')}: {e}")
                
                conn.commit()
                logger.info(f"✅ Synced {synced}/{len(menu_items)} menu items to PostgreSQL")
                return True
                
    except Exception as e:
        logger.error(f"❌ Menu sync error: {e}", exc_info=True)
        return False


def get_menu_from_postgres() -> List[Dict[str, Any]]:
    """Читає меню з PostgreSQL"""
    if not USE_POSTGRES:
        logger.warning("Not using PostgreSQL, returning empty menu")
        return []
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT 
                    id as "ID",
                    category as "Категорія",
                    name as "Страви",
                    description as "Опис",
                    price as "Ціна",
                    restaurant as "Ресторан",
                    delivery_time as "Час Доставки (хв)",
                    photo_url as "Фото URL",
                    is_active as "Активний",
                    prep_time as "Час_приготування",
                    allergens as "Аллергени",
                    rating as "Рейтинг"
                FROM menu
                WHERE is_active = true
                ORDER BY category, name
            """)
            
            menu = [dict(row) for row in cursor.fetchall()]
            logger.info(f"📊 Loaded {len(menu)} items from PostgreSQL")
            return menu
            
    except Exception as e:
        logger.error(f"❌ Error loading menu from PostgreSQL: {e}")
        return []

def test_connection():
    """Перевірка з'єднання з базою даних при старті"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                db_type = "PostgreSQL" if USE_POSTGRES else "SQLite"
                db_info = DATABASE_URL.split('@')[1].split('/')[0] if USE_POSTGRES else f"sqlite://{DB_PATH}"
                return True, f"{db_type}: {db_info}"
            return False, "No result from test query"
    except Exception as e:
        return False, str(e)
