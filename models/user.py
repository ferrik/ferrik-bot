"""
User model для роботи з користувачами, кошиком та станами
"""

import sqlite3
import logging
import json
from datetime import datetime

logger = logging.getLogger('ferrik')

DATABASE_PATH = "bot_data.db"

def init_user_db():
    """Ініціалізація бази даних"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Таблиця користувачів
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Таблиця станів користувачів
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT DEFAULT 'normal',
                data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблиця кошиків
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                user_id INTEGER PRIMARY KEY,
                items TEXT,
                phone TEXT,
                address TEXT,
                delivery_type TEXT,
                delivery_cost REAL DEFAULT 0,
                payment_method TEXT,
                delivery_time TEXT,
                notes TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("✅ User database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing user database: {e}")
        return False


def create_user(user_id, username=None, first_name=None, last_name=None):
    """Створення/оновлення користувача"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, last_activity)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, datetime.now()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ User created/updated: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating user {user_id}: {e}")
        return False


def get_user(user_id):
    """Отримання користувача"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'user_id': user[1],
                'username': user[2],
                'first_name': user[3],
                'last_name': user[4],
                'phone': user[5],
                'created_at': user[6],
                'last_activity': user[7],
                'is_active': user[8]
            }
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting user {user_id}: {e}")
        return None


def update_user_activity(user_id):
    """Оновлення активності"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET last_activity = ? 
            WHERE user_id = ?
        """, (datetime.now(), user_id))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating activity {user_id}: {e}")
        return False


# ========== СТАНИ КОРИСТУВАЧІВ ==========

def set_state(user_id, state, data=None):
    """Встановлення стану користувача"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        data_json = json.dumps(data) if data else None
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_states 
            (user_id, state, data, updated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, state, data_json, datetime.now()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"State set for {user_id}: {state}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error setting state for {user_id}: {e}")
        return False


def get_state(user_id):
    """Отримання стану користувача"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT state, data FROM user_states WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            state = result[0]
            data = json.loads(result[1]) if result[1] else None
            return state, data
        
        return 'normal', None
        
    except Exception as e:
        logger.error(f"❌ Error getting state for {user_id}: {e}")
        return 'normal', None


# ========== КОШИК ==========

def get_cart(user_id):
    """Отримання кошика користувача"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM carts WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {
                'items': json.loads(result[1]) if result[1] else [],
                'phone': result[2],
                'address': result[3],
                'delivery_type': result[4],
                'delivery_cost': result[5],
                'payment_method': result[6],
                'delivery_time': result[7],
                'notes': result[8]
            }
        
        return {'items': []}
        
    except Exception as e:
        logger.error(f"❌ Error getting cart for {user_id}: {e}")
        return {'items': []}


def set_cart(user_id, cart_data):
    """Збереження кошика"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        items_json = json.dumps(cart_data.get('items', []))
        
        cursor.execute("""
            INSERT OR REPLACE INTO carts 
            (user_id, items, phone, address, delivery_type, delivery_cost, 
             payment_method, delivery_time, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            items_json,
            cart_data.get('phone'),
            cart_data.get('address'),
            cart_data.get('delivery_type'),
            cart_data.get('delivery_cost', 0),
            cart_data.get('payment_method'),
            cart_data.get('delivery_time'),
            cart_data.get('notes'),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cart updated for {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error setting cart for {user_id}: {e}")
        return False


def clear_cart(user_id):
    """Очищення кошика"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM carts WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cart cleared for {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error clearing cart for {user_id}: {e}")
        return False


# ========== СТАТИСТИКА ==========

def get_user_count():
    """Кількість користувачів"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
        
    except Exception as e:
        logger.error(f"❌ Error getting user count: {e}")
        return 0


def get_all_users():
    """Всі користувачі"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        
        conn.close()
        
        return [{
            'id': user[0],
            'user_id': user[1],
            'username': user[2],
            'first_name': user[3],
            'last_name': user[4],
            'phone': user[5],
            'created_at': user[6],
            'last_activity': user[7],
            'is_active': user[8]
        } for user in users]
        
    except Exception as e:
        logger.error(f"❌ Error getting all users: {e}")
        return []


# Ініціалізація при імпорті
init_user_db()