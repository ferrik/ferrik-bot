"""
User model для роботи з користувачами
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATABASE_PATH = "bot_data.db"

def init_user_db():
    """Ініціалізація бази даних користувачів"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("User database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing user database: {e}")
        return False

def create_user(user_id, username=None, first_name=None, last_name=None):
    """Створення нового користувача"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, created_at, last_activity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, datetime.now(), datetime.now()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"User created/updated: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating user {user_id}: {e}")
        return False

def get_user(user_id):
    """Отримання користувача за ID"""
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
                'created_at': user[5],
                'last_activity': user[6],
                'is_active': user[7]
            }
        return None
        
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

def update_user_activity(user_id):
    """Оновлення останньої активності користувача"""
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
        logger.error(f"Error updating user activity {user_id}: {e}")
        return False

def get_all_users():
    """Отримання всіх користувачів"""
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
            'created_at': user[5],
            'last_activity': user[6],
            'is_active': user[7]
        } for user in users]
        
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []

def get_user_count():
    """Отримання кількості користувачів"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
        
    except Exception as e:
        logger.error(f"Error getting user count: {e}")
        return 0

# Ініціалізація бази при імпорті модуля
init_user_db()
