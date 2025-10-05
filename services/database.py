import sqlite3
import logging
import json
from datetime import datetime
from threading import Lock
from contextlib import contextmanager

logger = logging.getLogger("database")

DB_PATH = "hubsy_data.db"
db_lock = Lock()

@contextmanager
def get_db():
    """Thread-safe database connection"""
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
            
            # Таблиця замовлень
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
            
            # Таблиця активності
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
            cursor = conn.cursor()
            
            # Загальна кількість та сума
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total) as total_revenue,
                    AVG(total) as avg_order
                FROM orders
                WHERE created_at >= datetime('now', '-' || ? || ' days')
            """, (days,))
            
            stats = dict(cursor.fetchone())
            
            # По статусах
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
                
                # Видаляємо старі активності
                cursor.execute("""
                    DELETE FROM user_activity
                    WHERE timestamp < datetime('now', '-' || ? || ' days')
                """, (days,))
                
                # Архівуємо старі замовлення (статус = 'archived')
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