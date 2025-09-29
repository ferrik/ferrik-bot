import sqlite3
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DB_PATH = "bot_data.db"

def init_db(check_only=False):
    """Ініціалізує базу даних SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                chat_id TEXT,
                user_name TEXT,
                state TEXT,
                cart TEXT,
                chat_history TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def get_or_create_user(user_id, chat_id, user_name):
    """Отримує або створює користувача."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute("""
                INSERT INTO users (user_id, chat_id, user_name, state, cart, chat_history, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, chat_id, user_name, "", json.dumps({"items": [], "total": 0.0}), json.dumps([]), datetime.now().isoformat()))
            conn.commit()
            user = (user_id, chat_id, user_name, "", json.dumps({"items": [], "total": 0.0}), json.dumps([]), datetime.now().isoformat())
        
        conn.close()
        return {
            "user_id": user[0],
            "chat_id": user[1],
            "user_name": user[2],
            "state": user[3],
            "cart": json.loads(user[4]),
            "chat_history": json.loads(user[5]),
            "created_at": user[6]
        }
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        return None

def get_state(user_id):
    """Отримує стан користувача."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else ""
    except Exception as e:
        logger.error(f"Error in get_state: {e}")
        return ""

def set_state(user_id, state):
    """Встановлює стан користувача."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET state = ? WHERE user_id = ?", (state, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error in set_state: {e}")
        return False

def get_cart(user_id):
    """Отримує корзину користувача."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT cart FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return json.loads(result[0]) if result else {"items": [], "total": 0.0}
    except Exception as e:
        logger.error(f"Error in get_cart: {e}")
        return {"items": [], "total": 0.0}

def set_cart(user_id, cart):
    """Зберігає корзину користувача."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET cart = ? WHERE user_id = ?", (json.dumps(cart), user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error in set_cart: {e}")
        return False

def add_chat_history(user_id, role, text):
    """Додає повідомлення до історії чату."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_history FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        history = json.loads(result[0]) if result else []
        history.append({"role": role, "text": text, "timestamp": datetime.now().isoformat()})
        cursor.execute("UPDATE users SET chat_history = ? WHERE user_id = ?", (json.dumps(history), user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error in add_chat_history: {e}")
        return False

def get_chat_history(user_id):
    """Отримує історію чату користувача."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_history FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return json.loads(result[0]) if result else []
    except Exception as e:
        logger.error(f"Error in get_chat_history: {e}")
        return []