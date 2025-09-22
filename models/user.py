import sqlite3
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("ferrik.user")

# Шлях до бази даних
DB_PATH = os.environ.get("DB_PATH", "bot_data.db")

def init_db():
    """Ініціалізація бази даних користувачів"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Таблиця користувачів
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                state TEXT DEFAULT 'normal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблиця кошиків
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carts (
                chat_id INTEGER PRIMARY KEY,
                items TEXT DEFAULT '[]',
                phone TEXT,
                address TEXT,
                coords TEXT,
                payment_method TEXT,
                delivery_type TEXT,
                notes TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users (chat_id)
            )
        ''')
        
        # Таблиця історії чату (для AI)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message TEXT,
                is_user BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users (chat_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False

def get_or_create_user(chat_id, username=None, first_name=None, last_name=None):
    """Отримує або створює користувача"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Перевіряємо чи існує користувач
        cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        user = cursor.fetchone()
        
        if not user:
            # Створюємо нового користувача
            cursor.execute('''
                INSERT INTO users (chat_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (chat_id, username, first_name, last_name))
            
            # Створюємо порожній кошик
            cursor.execute('''
                INSERT INTO carts (chat_id, items) VALUES (?, ?)
            ''', (chat_id, '[]'))
            
            logger.info(f"Created new user: {chat_id}")
        else:
            # Оновлюємо інформацію користувача
            cursor.execute('''
                UPDATE users SET 
                username = COALESCE(?, username),
                first_name = COALESCE(?, first_name),
                last_name = COALESCE(?, last_name),
                updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ?
            ''', (username, first_name, last_name, chat_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error creating/updating user {chat_id}: {e}")
        return False

def get_state(chat_id):
    """Отримує поточний стан користувача"""
    try:
        get_or_create_user(chat_id)  # Гарантуємо, що користувач існує
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT state FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else "normal"
        
    except Exception as e:
        logger.error(f"Error getting state for user {chat_id}: {e}")
        return "normal"

def set_state(chat_id, state):
    """Встановлює стан користувача"""
    try:
        get_or_create_user(chat_id)  # Гарантуємо, що користувач існує
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET state = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE chat_id = ?
        ''', (state, chat_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error setting state for user {chat_id}: {e}")
        return False

def get_cart(chat_id):
    """Отримує кошик користувача"""
    try:
        get_or_create_user(chat_id)  # Гарантуємо, що користувач існує
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT items, phone, address, coords, payment_method, delivery_type, notes
            FROM carts WHERE chat_id = ?
        ''', (chat_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {
                "items": json.loads(result[0]) if result[0] else [],
                "phone": result[1],
                "address": result[2],
                "coords": json.loads(result[3]) if result[3] else None,
                "payment_method": result[4],
                "delivery_type": result[5],
                "notes": result[6]
            }
        else:
            return {"items": []}
            
    except Exception as e:
        logger.error(f"Error getting cart for user {chat_id}: {e}")
        return {"items": []}

def set_cart(chat_id, cart_data):
    """Оновлює кошик користувача"""
    try:
        get_or_create_user(chat_id)  # Гарантуємо, що користувач існує
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE carts SET 
                items = ?,
                phone = ?,
                address = ?,
                coords = ?,
                payment_method = ?,
                delivery_type = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        ''', (
            json.dumps(cart_data.get("items", [])),
            cart_data.get("phone"),
            cart_data.get("address"),
            json.dumps(cart_data.get("coords")) if cart_data.get("coords") else None,
            cart_data.get("payment_method"),
            cart_data.get("delivery_type"),
            cart_data.get("notes"),
            chat_id
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error setting cart for user {chat_id}: {e}")
        return False

def clear_cart(chat_id):
    """Очищує кошик користувача"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE carts SET 
                items = '[]',
                phone = NULL,
                address = NULL,
                coords = NULL,
                payment_method = NULL,
                delivery_type = NULL,
                notes = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        ''', (chat_id,))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error clearing cart for user {chat_id}: {e}")
        return False

def add_chat_history(chat_id, message, is_user=True):
    """Додає повідомлення до історії чату"""
    try:
        get_or_create_user(chat_id)  # Гарантуємо, що користувач існує
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chat_history (chat_id, message, is_user)
            VALUES (?, ?, ?)
        ''', (chat_id, message, is_user))
        
        # Зберігаємо тільки останні 50 повідомлень
        cursor.execute('''
            DELETE FROM chat_history 
            WHERE chat_id = ? AND id NOT IN (
                SELECT id FROM chat_history 
                WHERE chat_id = ? 
                ORDER BY id DESC LIMIT 50
            )
        ''', (chat_id, chat_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error adding chat history for user {chat_id}: {e}")
        return False

def get_chat_history(chat_id, limit=20):
    """Отримує історію чату користувача"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message, is_user, timestamp 
            FROM chat_history 
            WHERE chat_id = ? 
            ORDER BY id DESC LIMIT ?
        ''', (chat_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        # Повертаємо в хронологічному порядку (старіші спочатку)
        history = []
        for msg, is_user, timestamp in reversed(results):
            history.append({
                "message": msg,
                "is_user": bool(is_user),
                "timestamp": timestamp
            })
            
        return history
        
    except Exception as e:
        logger.error(f"Error getting chat history for user {chat_id}: {e}")
        return []

def get_user_stats():
    """Отримує статистику користувачів"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Загальна кількість користувачів
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Активні користувачі (за останні 7 днів)
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE updated_at > datetime('now', '-7 days')
        ''')
        active_users = cursor.fetchone()[0]
        
        # Користувачі з товарами в кошику
        cursor.execute('''
            SELECT COUNT(*) FROM carts 
            WHERE items != '[]' AND items IS NOT NULL
        ''')
        users_with_items = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_users": total_users,
            "active_users_7d": active_users,
            "users_with_cart": users_with_items
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {"total_users": 0, "active_users_7d": 0, "users_with_cart": 0}

def set_user_phone(chat_id, phone):
    """Встановлює номер телефону користувача"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET phone = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE chat_id = ?
        ''', (phone, chat_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error setting phone for user {chat_id}: {e}")
        return False

def get_user_phone(chat_id):
    """Отримує номер телефону користувача"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT phone FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result and result[0] else None
        
    except Exception as e:
        logger.error(f"Error getting phone for user {chat_id}: {e}")
        return None
