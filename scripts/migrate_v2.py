"""
Database migration script v2.0 - Add personalization tables
Run this after updating code to v2.0
"""
import sqlite3
import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "ferrik_bot.db"


def migrate_v2():
    """Run migration to v2.0 with personalization tables"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        logger.info("🔄 Starting migration to v2.0...")
        
        # 1. Create user_profiles table if not exists
        logger.info("📊 Creating user_profiles table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                total_orders INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0,
                points INTEGER DEFAULT 0,
                level TEXT DEFAULT 'novice',
                registered_at TEXT NOT NULL,
                last_order_date TEXT,
                favorite_restaurants TEXT,
                favorite_dishes TEXT,
                favorite_categories TEXT,
                dietary_restrictions TEXT,
                preferred_delivery_method TEXT DEFAULT 'delivery',
                avg_budget REAL DEFAULT 0.0,
                notifications_enabled INTEGER DEFAULT 1,
                last_seen TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 2. Create user_preferences table
        logger.info("⚙️ Creating user_preferences table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                favorite_categories TEXT,
                dietary_restrictions TEXT,
                allergies TEXT,
                preferred_delivery_method TEXT DEFAULT 'delivery',
                preferred_restaurant_id TEXT,
                avg_budget REAL DEFAULT 0.0,
                max_budget REAL DEFAULT 10000.0,
                push_notifications INTEGER DEFAULT 1,
                email_notifications INTEGER DEFAULT 0,
                remind_inactive_days INTEGER DEFAULT 2,
                preferred_order_time TEXT,
                preferred_order_days TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            )
        """)
        
        # 3. Create order_history table
        logger.info("📜 Creating order_history table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_history (
                order_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                restaurant_id TEXT,
                items_ordered TEXT,
                total_amount REAL,
                rating INTEGER,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            )
        """)
        
        # 4. Check if old users table exists and migrate data
        logger.info("🔄 Checking for existing user data...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            logger.info("📤 Migrating data from old users table...")
            
            cursor.execute("SELECT * FROM users LIMIT 1")
            old_columns = [description[0] for description in cursor.description]
            
            cursor.execute("""
                INSERT OR IGNORE INTO user_profiles (
                    user_id, name, phone, address, registered_at, created_at, updated_at
                )
                SELECT 
                    user_id, 
                    COALESCE(first_name, 'User'),
                    phone,
                    address,
                    COALESCE(registered_at, datetime('now')),
                    datetime('now'),
                    datetime('now')
                FROM users
            """)
            logger.info("✅ Data migrated successfully")
        
        # 5. Create indices for performance
        logger.info("🔍 Creating indices...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_profiles_level 
            ON user_profiles(level)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_history_user 
            ON order_history(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_history_timestamp 
            ON order_history(timestamp)
        """)
        
        conn.commit()
        logger.info("✅ Migration v2.0 completed successfully!")
        logger.info(f"📍 Database: {DB_PATH}")
        
        # Print summary
        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        user_count = cursor.fetchone()[0]
        logger.info(f"👥 Users in database: {user_count}")
        
        cursor.execute("SELECT COUNT(*) FROM order_history")
        order_count = cursor.fetchone()[0]
        logger.info(f"📦 Orders in database: {order_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def rollback_v2():
    """Rollback v2.0 changes (optional)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        logger.warning("🔙 Rolling back v2.0 changes...")
        
        cursor.execute("DROP TABLE IF EXISTS user_preferences")
        cursor.execute("DROP TABLE IF EXISTS order_history")
        cursor.execute("DROP INDEX IF EXISTS idx_user_profiles_level")
        cursor.execute("DROP INDEX IF EXISTS idx_order_history_user")
        cursor.execute("DROP INDEX IF EXISTS idx_order_history_timestamp")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Rollback completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_v2()
    else:
        success = migrate_v2()
        sys.exit(0 if success else 1)