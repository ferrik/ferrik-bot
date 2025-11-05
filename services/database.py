"""
Simple SQLite Database for activity logging
Проста БД для логування активності та статистики
"""
import logging
import sqlite3
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("ferrik_bot.db")


def get_connection() -> Optional[sqlite3.Connection]:
    """
    Отримати з'єднання з БД
    
    Returns:
        sqlite3.Connection або None
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row  # Доступ по іменам колонок
        return conn
    except sqlite3.Error as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None


def init_database() -> bool:
    """
    Ініціалізувати базу даних
    
    Returns:
        bool: True якщо успішно
    """
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Таблиця активності
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблиця замовлень (дублікат для швидкого доступу)
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблиця популярних страв
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dish_popularity (
                dish_name TEXT PRIMARY KEY,
                order_count INTEGER DEFAULT 0,
                last_ordered DATETIME
            )
        """)
        
        # Індекси для швидкості
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_user 
            ON activity_log(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_timestamp 
            ON activity_log(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_user 
            ON orders(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_status 
            ON orders(status)
        """)
        
        conn.commit()
        logger.info("✅ Database initialized")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ Database init failed: {e}")
        return False
    finally:
        conn.close()


def log_activity(user_id: int, action: str, details: Dict[str, Any] = None) -> bool:
    """
    Логувати активність користувача
    
    Args:
        user_id: ID користувача
        action: Тип дії (start, view_menu, add_to_cart, тощо)
        details: Додаткові деталі
    
    Returns:
        bool: True якщо успішно
    """
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        details_json = json.dumps(details) if details else None
        
        cursor.execute("""
            INSERT INTO activity_log (user_id, action, details)
            VALUES (?, ?, ?)
        """, (user_id, action, details_json))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ Log activity failed: {e}")
        return False
    finally:
        conn.close()


def save_order(
    order_id: str,
    user_id: int,
    username: str,
    items: List[Dict[str, Any]],
    total: float,
    phone: str = "",
    address: str = "",
    notes: str = ""
) -> bool:
    """
    Зберегти замовлення в локальну БД
    
    Args:
        order_id: ID замовлення
        user_id: ID користувача
        username: Username
        items: Список товарів
        total: Загальна сума
        phone: Телефон
        address: Адреса
        notes: Примітки
    
    Returns:
        bool: True якщо успішно
    """
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        items_json = json.dumps(items, ensure_ascii=False)
        
        cursor.execute("""
            INSERT OR REPLACE INTO orders 
            (id, user_id, username, items, total, phone, address, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, user_id, username, items_json, total, phone, address, notes))
        
        # Оновити популярність страв
        for item in items:
            dish_name = item.get('name', '')
            if dish_name:
                cursor.execute("""
                    INSERT INTO dish_popularity (dish_name, order_count, last_ordered)
                    VALUES (?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(dish_name) DO UPDATE SET
                        order_count = order_count + 1,
                        last_ordered = CURRENT_TIMESTAMP
                """, (dish_name,))
        
        conn.commit()
        logger.info(f"✅ Order saved to DB: {order_id}")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ Save order failed: {e}")
        return False
    finally:
        conn.close()


def get_user_orders(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Отримати історію замовлень користувача
    
    Args:
        user_id: ID користувача
        limit: Максимум замовлень
    
    Returns:
        list: Список замовлень
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        
        orders = []
        for row in rows:
            orders.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'username': row['username'],
                'items': json.loads(row['items']),
                'total': row['total'],
                'status': row['status'],
                'phone': row['phone'],
                'address': row['address'],
                'notes': row['notes'],
                'created_at': row['created_at']
            })
        
        return orders
        
    except sqlite3.Error as e:
        logger.error(f"❌ Get user orders failed: {e}")
        return []
    finally:
        conn.close()


def get_popular_items(limit: int = 5) -> List[Tuple[str, int]]:
    """
    Отримати топ популярних страв
    
    Args:
        limit: Максимум страв
    
    Returns:
        list: [(назва, кількість), ...]
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT dish_name, order_count
            FROM dish_popularity
            ORDER BY order_count DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        return [(row['dish_name'], row['order_count']) for row in rows]
        
    except sqlite3.Error as e:
        logger.error(f"❌ Get popular items failed: {e}")
        return []
    finally:
        conn.close()


def get_stats_today() -> Dict[str, Any]:
    """
    Отримати статистику за сьогодні
    
    Returns:
        dict: Статистика
    """
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Кількість замовлень
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM orders
            WHERE created_at >= ?
        """, (today_start,))
        
        orders_count = cursor.fetchone()['count']
        
        # Загальна сума
        cursor.execute("""
            SELECT SUM(total) as total
            FROM orders
            WHERE created_at >= ?
        """, (today_start,))
        
        total_revenue = cursor.fetchone()['total'] or 0
        
        # Унікальні користувачі
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM orders
            WHERE created_at >= ?
        """, (today_start,))
        
        unique_users = cursor.fetchone()['count']
        
        return {
            'orders_count': orders_count,
            'total_revenue': total_revenue,
            'unique_users': unique_users,
            'average_check': total_revenue / orders_count if orders_count > 0 else 0
        }
        
    except sqlite3.Error as e:
        logger.error(f"❌ Get stats failed: {e}")
        return {}
    finally:
        conn.close()


def test_connection() -> Tuple[bool, str]:
    """
    Тест підключення до БД
    
    Returns:
        tuple: (success, message)
    """
    conn = get_connection()
    if not conn:
        return False, "Cannot connect to database"
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        orders_count = cursor.fetchone()[0]
        
        return True, f"SQLite {version}, {orders_count} orders"
        
    except sqlite3.Error as e:
        return False, str(e)
    finally:
        conn.close()


# Тестування при імпорті
if __name__ == "__main__":
    print("🧪 Testing database service...")
    
    if init_database():
        print("✅ Database initialized")
        
        success, info = test_connection()
        if success:
            print(f"✅ Database connection OK: {info}")
        else:
            print(f"❌ Database connection FAILED: {info}")
    else:
        print("❌ Database initialization FAILED")
