import sqlite3
import json
import logging
from datetime import datetime

# Налаштування логування
logger = logging.getLogger("models.user")
logger.setLevel(logging.INFO)

# Конфігурація бази даних
# Припускаємо, що використовується bot_data.db (з config.py, або за замовчуванням)
DATABASE_URL = 'bot_data.db' 

def init_db():
    """Ініціалізація бази даних та створення таблиць, якщо вони не існують."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Створення таблиці користувачів (зберігає state, cart, history)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                state TEXT,
                cart_json TEXT,
                chat_history_json TEXT,
                last_activity TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database schema initialized.")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def get_or_create_user(user_id, username=None, first_name=None, last_name=None):
    """Отримати або створити користувача, оновивши його дані."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Перевірка на існування користувача
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        current_time = datetime.now().isoformat()

        if user_row is None:
            # Створення нового користувача
            initial_data = {
                'user_id': user_id,
                'username': username or '',
                'first_name': first_name or '',
                'last_name': last_name or '',
                'state': 'main',
                'cart_json': '[]',
                'chat_history_json': '[]',
                'last_activity': current_time
            }
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, state, cart_json, chat_history_json, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                initial_data['user_id'], initial_data['username'], initial_data['first_name'], initial_data['last_name'], 
                initial_data['state'], initial_data['cart_json'], initial_data['chat_history_json'], initial_data['last_activity']
            ))
            logger.info(f"Created new user: {user_id}")
            conn.commit()
        else:
            # Оновлення даних та часу активності
            cursor.execute('''
                UPDATE users SET last_activity = ?, username = ?, first_name = ?, last_name = ? WHERE user_id = ?
            ''', (current_time, username or user_row[1], first_name or user_row[2], last_name or user_row[3], user_id))
            conn.commit()

        # Повторне отримання даних для повернення
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        conn.close()
        return user_data
    except Exception as e:
        logger.error(f"Error getting/creating user {user_id}: {e}")
        return None

def get_state(user_id):
    """Отримати поточний стан користувача."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM users WHERE user_id = ?", (user_id,))
        state = cursor.fetchone()
        conn.close()
        return state[0] if state else 'main'
    except Exception as e:
        logger.error(f"Error getting state for user {user_id}: {e}")
        return 'main'

def set_state(user_id, state):
    """Встановити новий стан користувача."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET state = ? WHERE user_id = ?", (state, user_id))
        conn.commit()
        conn.close()
        logger.info(f"User {user_id} state set to: {state}")
        return True
    except Exception as e:
        logger.error(f"Error setting state for user {user_id}: {e}")
        return False

def get_cart(user_id):
    """Отримати вміст кошика користувача (список об'єктів товарів)."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT cart_json FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return json.loads(result[0])
        return []
    except Exception as e:
        logger.error(f"Error getting cart for user {user_id}: {e}")
        return []

def set_cart(user_id, cart_items):
    """Зберегти вміст кошика користувача (список об'єктів товарів)."""
    try:
        cart_json = json.dumps(cart_items)
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET cart_json = ? WHERE user_id = ?", (cart_json, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error setting cart for user {user_id}: {e}")
        return False

def get_chat_history(user_id):
    """Отримати історію чату користувача."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_history_json FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return json.loads(result[0])
        return []
    except Exception as e:
        logger.error(f"Error getting chat history for user {user_id}: {e}")
        return []

def add_chat_history(user_id, role, text):
    """Додати повідомлення до історії чату користувача."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 1. Отримати поточну історію
        cursor.execute("SELECT chat_history_json FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        history = json.loads(result[0]) if result and result[0] else []
        
        # 2. Додати нове повідомлення
        history.append({
            'role': role,
            'text': text,
            'timestamp': datetime.now().isoformat()
        })
        
        # 3. Обмежити історію (наприклад, останні 20 повідомлень)
        if len(history) > 20:
            history = history[-20:]
            
        history_json = json.dumps(history)
        
        # 4. Зберегти оновлену історію
        cursor.execute("UPDATE users SET chat_history_json = ? WHERE user_id = ?", (history_json, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error adding chat history for user {user_id}: {e}")
        return False

