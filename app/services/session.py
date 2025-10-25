"""
🗄️ Управління сесіями та станами користувачів

Зберігає стани в БД замість глобальних словників
ВИПРАВЛЕНО: Автоматично створює SQLite підключення
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Управління сесіями користувачів
    
    Зберігає:
    - Поточний стан користувача (STATE_*)
    - Дані сесії (тимчасові дані для checkout)
    - Кошик покупок
    """
    
    def __init__(self, database=None, db_path='bot.db'):
        """
        Args:
            database: Об'єкт database з методами execute, fetchone, commit
                      АБО None (тоді створить власне SQLite підключення)
            db_path: Шлях до SQLite БД (якщо database=None)
        """
        if database is None:
            # Створити власне SQLite підключення
            import sqlite3
            self.db = sqlite3.connect(db_path, check_same_thread=False)
            self.db.row_factory = sqlite3.Row
            self._own_connection = True
            logger.info("✅ SessionManager: Created own SQLite connection")
        else:
            # Використати передане підключення
            # Перевірити чи це справжнє підключення
            if hasattr(database, 'execute') and hasattr(database, 'commit'):
                self.db = database
                self._own_connection = False
                logger.info("✅ SessionManager: Using provided database connection")
            else:
                # Fallback: створити власне підключення
                import sqlite3
                self.db = sqlite3.connect(db_path, check_same_thread=False)
                self.db.row_factory = sqlite3.Row
                self._own_connection = True
                logger.warning("⚠️ SessionManager: Provided object has no execute(), creating own connection")
        
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Створює таблиці, якщо їх немає"""
        try:
            # Таблиця станів користувачів
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id INTEGER PRIMARY KEY,
                    state TEXT DEFAULT 'STATE_IDLE',
                    state_data TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблиця кошиків
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS user_carts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    item_id TEXT,
                    quantity INTEGER DEFAULT 1,
                    price REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, item_id)
                )
            """)
            
            # Індекси для швидкості
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_carts_user 
                ON user_carts(user_id)
            """)
            
            self.db.commit()
            logger.info("✅ Session tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Error creating session tables: {e}")
    
    # =========================================================================
    # Управління станами
    # =========================================================================
    
    def get_state(self, user_id: int) -> str:
        """Отримати поточний стан користувача"""
        try:
            row = self.db.execute(
                "SELECT state FROM user_states WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            return row[0] if row else 'STATE_IDLE'
            
        except Exception as e:
            logger.error(f"❌ Error getting state for {user_id}: {e}")
            return 'STATE_IDLE'
    
    def set_state(self, user_id: int, state: str, data: Optional[Dict] = None):
        """Встановити стан користувача"""
        try:
            state_data = json.dumps(data or {})
            
            self.db.execute("""
                INSERT INTO user_states (user_id, state, state_data, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    state = excluded.state,
                    state_data = excluded.state_data,
                    updated_at = excluded.updated_at
            """, (user_id, state, state_data, datetime.now()))
            
            self.db.commit()
            logger.debug(f"✅ State set for {user_id}: {state}")
            
        except Exception as e:
            logger.error(f"❌ Error setting state for {user_id}: {e}")
    
    def get_state_data(self, user_id: int) -> Dict[str, Any]:
        """Отримати дані сесії користувача"""
        try:
            row = self.db.execute(
                "SELECT state_data FROM user_states WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if row and row[0]:
                return json.loads(row[0])
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error getting state data for {user_id}: {e}")
            return {}
    
    def clear_state(self, user_id: int):
        """Очистити стан користувача"""
        self.set_state(user_id, 'STATE_IDLE', {})
    
    # =========================================================================
    # Управління кошиком
    # =========================================================================
    
    def add_to_cart(self, user_id: int, item_id: str, quantity: int = 1, price: float = 0):
        """Додати товар в кошик"""
        try:
            # Перевірка чи товар вже є
            existing = self.db.execute("""
                SELECT quantity FROM user_carts 
                WHERE user_id = ? AND item_id = ?
            """, (user_id, item_id)).fetchone()
            
            if existing:
                # Оновлюємо кількість
                new_qty = existing[0] + quantity
                self.db.execute("""
                    UPDATE user_carts 
                    SET quantity = ?, updated_at = ?
                    WHERE user_id = ? AND item_id = ?
                """, (new_qty, datetime.now(), user_id, item_id))
            else:
                # Додаємо новий
                self.db.execute("""
                    INSERT INTO user_carts (user_id, item_id, quantity, price, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, item_id, quantity, price, datetime.now()))
            
            self.db.commit()
            logger.debug(f"✅ Added to cart: user={user_id}, item={item_id}, qty={quantity}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding to cart: {e}")
            return False
    
    def get_cart(self, user_id: int) -> list:
        """Отримати кошик користувача"""
        try:
            rows = self.db.execute("""
                SELECT item_id, quantity, price 
                FROM user_carts 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,)).fetchall()
            
            return [
                {
                    'id': row[0],
                    'quantity': row[1],
                    'price': row[2]
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"❌ Error getting cart for {user_id}: {e}")
            return []
    
    def update_cart_quantity(self, user_id: int, item_id: str, quantity: int):
        """Оновити кількість товару"""
        try:
            if quantity <= 0:
                # Видалити з кошика
                self.remove_from_cart(user_id, item_id)
            else:
                self.db.execute("""
                    UPDATE user_carts 
                    SET quantity = ?, updated_at = ?
                    WHERE user_id = ? AND item_id = ?
                """, (quantity, datetime.now(), user_id, item_id))
                self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating cart quantity: {e}")
            return False
    
    def remove_from_cart(self, user_id: int, item_id: str):
        """Видалити товар з кошика"""
        try:
            self.db.execute("""
                DELETE FROM user_carts 
                WHERE user_id = ? AND item_id = ?
            """, (user_id, item_id))
            self.db.commit()
            logger.debug(f"🗑️ Removed from cart: user={user_id}, item={item_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing from cart: {e}")
            return False
    
    def clear_cart(self, user_id: int):
        """Очистити весь кошик"""
        try:
            self.db.execute("""
                DELETE FROM user_carts WHERE user_id = ?
            """, (user_id,))
            self.db.commit()
            logger.info(f"🗑️ Cart cleared for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing cart: {e}")
            return False
    
    def get_cart_total(self, user_id: int) -> float:
        """Розрахувати загальну суму кошика"""
        try:
            row = self.db.execute("""
                SELECT SUM(quantity * price) 
                FROM user_carts 
                WHERE user_id = ?
            """, (user_id,)).fetchone()
            
            return float(row[0] or 0)
            
        except Exception as e:
            logger.error(f"❌ Error calculating cart total: {e}")
            return 0.0
    
    def get_cart_count(self, user_id: int) -> int:
        """Кількість товарів у кошику"""
        try:
            row = self.db.execute("""
                SELECT SUM(quantity) 
                FROM user_carts 
                WHERE user_id = ?
            """, (user_id,)).fetchone()
            
            return int(row[0] or 0)
            
        except Exception as e:
            logger.error(f"❌ Error getting cart count: {e}")
            return 0
    
    def close(self):
        """Закрити підключення якщо воно власне"""
        if self._own_connection and self.db:
            try:
                self.db.close()
                logger.info("✅ SessionManager: Database connection closed")
            except Exception as e:
                logger.error(f"❌ Error closing database: {e}")


# ============================================================================
# Backward compatibility wrapper (для поступового переходу)
# ============================================================================

class LegacyDictWrapper:
    """
    Обгортка для збереження сумісності зі старим кодом
    
    Працює як словник, але зберігає в БД
    """
    def __init__(self, session_manager, dict_type='states'):
        self.sm = session_manager
        self.dict_type = dict_type
    
    def __getitem__(self, user_id):
        if self.dict_type == 'states':
            return self.sm.get_state(user_id)
        else:  # carts
            return self.sm.get_cart(user_id)
    
    def __setitem__(self, user_id, value):
        if self.dict_type == 'states':
            if isinstance(value, dict):
                self.sm.set_state(user_id, value.get('state'), value.get('data'))
            else:
                self.sm.set_state(user_id, value)
    
    def get(self, user_id, default=None):
        try:
            return self[user_id]
        except:
            return default
