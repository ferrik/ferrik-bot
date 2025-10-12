"""
User repository - Data access layer for user profiles and preferences
Supports SQLite storage (CONTINUATION)
"""
import logging
import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.user_profile import UserProfile, UserLevel
from models.user_preferences import UserPreferences

logger = logging.getLogger(__name__)

DB_PATH = "ferrik_bot.db"


class UserRepository:
    """Repository for user data persistence"""
    
    @staticmethod
    def save_preferences(preferences: UserPreferences) -> bool:
        """Save or update user preferences"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            prefs_dict = preferences.to_dict()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (
                    user_id, favorite_categories, dietary_restrictions, allergies,
                    preferred_delivery_method, preferred_restaurant_id, avg_budget,
                    max_budget, push_notifications, email_notifications,
                    remind_inactive_days, preferred_order_time, preferred_order_days,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                preferences.user_id,
                json.dumps(preferences.favorite_categories),
                json.dumps(preferences.dietary_restrictions),
                json.dumps(preferences.allergies),
                preferences.preferred_delivery_method,
                preferences.preferred_restaurant_id,
                preferences.avg_budget,
                preferences.max_budget,
                1 if preferences.push_notifications else 0,
                1 if preferences.email_notifications else 0,
                preferences.remind_inactive_days,
                preferences.preferred_order_time,
                json.dumps(preferences.preferred_order_days),
                prefs_dict['created_at'],
                prefs_dict['updated_at']
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"Preferences saved for user {preferences.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            return False
    
    @staticmethod
    def get_preferences(user_id: int) -> Optional[UserPreferences]:
        """Get user preferences by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM user_preferences WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return UserPreferences(user_id=user_id)
            
            prefs = UserPreferences(
                user_id=row[0],
                favorite_categories=json.loads(row[1]) if row[1] else [],
                dietary_restrictions=json.loads(row[2]) if row[2] else [],
                allergies=json.loads(row[3]) if row[3] else [],
                preferred_delivery_method=row[4],
                preferred_restaurant_id=row[5],
                avg_budget=row[6],
                max_budget=row[7],
                push_notifications=bool(row[8]),
                email_notifications=bool(row[9]),
                remind_inactive_days=row[10],
                preferred_order_time=row[11],
                preferred_order_days=json.loads(row[12]) if row[12] else [],
                created_at=datetime.fromisoformat(row[13]) if row[13] else datetime.now(),
                updated_at=datetime.fromisoformat(row[14]) if row[14] else datetime.now()
            )
            
            return prefs
            
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return UserPreferences(user_id=user_id)
    
    @staticmethod
    def update_order_history(user_id: int, order_data: Dict[str, Any]) -> bool:
        """Update user order history"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO order_history (
                    order_id, user_id, restaurant_id, items_ordered, total_amount, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                order_data.get('order_id'),
                user_id,
                order_data.get('restaurant_id'),
                json.dumps(order_data.get('items', [])),
                order_data.get('total_amount'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"Order history updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating order history: {e}")
            return False
    
    @staticmethod
    def increment_points(user_id: int, points: int) -> bool:
        """Add points to user account"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_profiles 
                SET points = points + ?, updated_at = ?
                WHERE user_id = ?
            """, (points, datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing points: {e}")
            return False
    
    @staticmethod
    def increment_level(user_id: int) -> Optional[str]:
        """Increment user level, return new level or None"""
        try:
            profile = UserRepository.get_profile(user_id)
            if not profile:
                return None
            
            old_level = profile.level
            profile.update_level()
            
            if profile.level != old_level:
                UserRepository.save_profile(profile)
                # Add bonus points for level up
                UserRepository.increment_points(user_id, 50)
                return profile.level.value
            
            return None
            
        except Exception as e:
            logger.error(f"Error incrementing level: {e}")
            return None
    
    @staticmethod
    def add_to_favorites(user_id: int, dish_name: str, restaurant_id: str) -> bool:
        """Add dish to user favorites"""
        try:
            profile = UserRepository.get_profile(user_id)
            if not profile:
                return False
            
            if dish_name not in profile.favorite_dishes:
                profile.favorite_dishes.insert(0, dish_name)
            
            if restaurant_id not in profile.favorite_restaurants:
                profile.favorite_restaurants.append(restaurant_id)
            
            UserRepository.save_profile(profile)
            return True
            
        except Exception as e:
            logger.error(f"Error adding to favorites: {e}")
            return False
    
    @staticmethod
    def get_all_profiles() -> List[UserProfile]:
        """Get all user profiles"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT user_id FROM user_profiles")
            rows = cursor.fetchall()
            conn.close()
            
            profiles = []
            for row in rows:
                profile = UserRepository.get_profile(row[0])
                if profile:
                    profiles.append(profile)
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error getting all profiles: {e}")
            return []
    
    @staticmethod
    def get_user_order_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user order history"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT order_id, restaurant_id, items_ordered, total_amount, timestamp
                FROM order_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            orders = []
            for row in rows:
                orders.append({
                    'order_id': row[0],
                    'restaurant_id': row[1],
                    'items': json.loads(row[2]),
                    'total_amount': row[3],
                    'timestamp': row[4]
                })
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []
    
    @staticmethod
    def update_last_seen(user_id: int) -> bool:
        """Update last seen timestamp for user"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_profiles
                SET last_seen = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating last_seen: {e}")
            return False
    
    @staticmethod
    def delete_profile(user_id: int) -> bool:
        """Delete user profile and related data"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM order_history WHERE user_id = ?", (user_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"Profile deleted for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting profile: {e}")
            return False