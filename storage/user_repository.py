"""
User repository - Data access layer for user profiles and preferences
Supports SQLite storage
"""
import logging
import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.user_profile import UserProfile, UserLevel
from models.user_preferences import UserPreferences

logger = logging.getLogger(__name__)

# Database path
DB_PATH = "ferrik_bot.db"


class UserRepository:
    """Repository for user data persistence"""
    
    @staticmethod
    def init_db():
        """Initialize database tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # User profiles table
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
        
        # User preferences table
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
        
        # Order history table
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
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    @staticmethod
    def save_profile(profile: UserProfile) -> bool:
        """Save or update user profile"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            profile_dict = profile.to_dict()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles (
                    user_id, name, phone, address, total_orders, total_spent, points, level,
                    registered_at, last_order_date, favorite_restaurants, favorite_dishes,
                    favorite_categories, dietary_restrictions, preferred_delivery_method,
                    avg_budget, notifications_enabled, last_seen, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id, profile.name, profile.phone, profile.address,
                profile.total_orders, profile.total_spent, profile.points, profile.level.value,
                profile_dict['registered_at'], profile_dict['last_order_date'],
                json.dumps(profile.favorite_restaurants),
                json.dumps(profile.favorite_dishes),
                json.dumps(profile.favorite_categories),
                json.dumps(profile.dietary_restrictions),
                profile.preferred_delivery_method,
                profile.avg_budget, 1 if profile.notifications_enabled else 0,
                profile_dict['last_seen'],
                profile_dict['created_at'],
                profile_dict['updated_at']
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"Profile saved for user {profile.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            return False
    
    @staticmethod
    def get_profile(user_id: int) -> Optional[UserProfile]:
        """Get user profile by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM user_profiles WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Construct UserProfile from database row
            profile = UserProfile(
                user_id=row[0],
                name=row[1],
                phone=row[2],
                address=row[3],
                total_orders=row[4],
                total_spent=row[5],
                points=row[6],
                level=UserLevel(row[7]),
                registered_at=datetime.fromisoformat(row[8]),
                last_order_date=datetime.fromisoformat(row[9]) if row[9] else None,
                favorite_restaurants=json.loads(row[10]) if row[10] else [],
                favorite_dishes=json.loads(row[11]) if row[11] else [],
                favorite_categories=json.loads(row[12]) if row[12] else [],
                dietary_restrictions=json.loads(row[13]) if row[13] else [],
                preferred_delivery_method=row[14],
                avg_budget=row[15],
                notifications_enabled=bool(row[16]),
                last_seen=datetime.fromisoformat(row[17]) if row[17] else None
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None
    
    @staticmethod
    def save_preferences(preferences: UserPreferences) -> bool:
        """Save or update user preferences"""
        try:
            conn = sqlite3.connect