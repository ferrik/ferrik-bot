"""
Unit tests for personalization module
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from models.user_profile import UserProfile, UserLevel
from models.user_preferences import UserPreferences
from services.personalization_service import PersonalizationService, UserAnalyticsService
from storage.user_repository import UserRepository
from utils.personalization_helpers import (
    format_user_greeting_message,
    format_level_badge,
    format_recommendations_message,
    get_emoji_for_category
)


class TestUserProfile:
    """Test UserProfile model"""
    
    def test_user_profile_creation(self):
        """Test creating user profile"""
        profile = UserProfile(user_id=123, name="Test User")
        
        assert profile.user_id == 123
        assert profile.name == "Test User"
        assert profile.total_orders == 0
        assert profile.level == UserLevel.NOVICE
    
    def test_user_profile_add_order(self):
        """Test adding order to profile"""
        profile = UserProfile(user_id=123, name="Test User")
        
        profile.add_order(
            amount=250.0,
            dish_names=["Pizza", "Salad"],
            restaurant_id="rest_1"
        )
        
        assert profile.total_orders == 1
        assert profile.total_spent == 250.0
        assert profile.points == 2  # 250 / 100 = 2
        assert "Pizza" in profile.favorite_dishes
        assert "rest_1" in profile.favorite_restaurants
    
    def test_user_level_update(self):
        """Test user level updates"""
        profile = UserProfile(user_id=123, name="Test User")
        
        assert profile.level == UserLevel.NOVICE
        
        # Add 3 orders
        for i in range(3):
            profile.add_order(100.0, [f"Dish {i}"], f"rest_{i}")
        
        assert profile.level == UserLevel.GOURMET
        assert profile.total_orders == 3
        
        # Add 8 more orders to reach FOODIE
        for i in range(8):
            profile.add_order(100.0, [f"Dish {3+i}"], f"rest_{3+i}")
        
        assert profile.level == UserLevel.FOODIE
        assert profile.total_orders == 11
    
    def test_user_profile_to_dict_and_back(self):
        """Test serialization and deserialization"""
        profile = UserProfile(
            user_id=123,
            name="Test User",
            phone="+380123456789",
            total_orders=5,
            total_spent=1000.0,
            points=10
        )
        
        profile_dict = profile.to_dict()
        restored = UserProfile.from_dict(profile_dict)
        
        assert restored.user_id == profile.user_id
        assert restored.name == profile.name
        assert restored.total_orders == profile.total_orders
        assert restored.points == profile.points


class TestUserPreferences:
    """Test UserPreferences model"""
    
    def test_preferences_creation(self):
        """Test creating preferences"""
        prefs = UserPreferences(user_id=123)
        
        assert prefs.user_id == 123
        assert prefs.push_notifications == True
        assert prefs.preferred_delivery_method == "delivery"
    
    def test_add_dietary_restriction(self):
        """Test adding dietary restrictions"""
        prefs = UserPreferences(user_id=123)
        
        prefs.add_dietary_restriction("vegan")
        assert "vegan" in prefs.dietary_restrictions
        
        # Adding same restriction twice
        prefs.add_dietary_restriction("vegan")
        assert prefs.dietary_restrictions.count("vegan") == 1
    
    def test_add_allergy(self):
        """Test adding allergies"""
        prefs = UserPreferences(user_id=123)
        
        prefs.add_allergy("peanuts")
        prefs.add_allergy("shellfish")
        
        assert "peanuts" in prefs.allergies
        assert "shellfish" in prefs.allergies
        assert len(prefs.allergies) == 2


class TestPersonalizationService:
    """Test PersonalizationService"""
    
    def test_greeting_message_novice(self):
        """Test greeting for novice user"""
        profile = UserProfile(user_id=123, name="John")
        message = PersonalizationService.get_greeting(profile)
        
        assert "John" in message
        assert "Привіт" in message
    
    def test_greeting_message_gourmet(self):
        """Test greeting for gourmet user"""
        profile = UserProfile(user_id=123, name="John")
        
        for _ in range(5):
            profile.add_order(100.0, ["Dish"], "rest")
        
        message = PersonalizationService.get_greeting(profile)
        
        assert "Гурман" in message or "gourmet" in message.lower()
        assert str(profile.total_orders) in message
    
    def test_recommendations_empty_history(self):
        """Test recommendations with empty order history"""
        profile = UserProfile(user_id=123, name="John")
        menu_items = [
            {"id": "1", "name": "Pizza", "category": "pizza", "price": 100},
            {"id": "2", "name": "Salad", "category": "salad", "price": 80},
        ]
        
        recommendations = PersonalizationService.get_recommendations(profile, menu_items, limit=2)
        assert len(recommendations) <= 2
    
    def test_recommendations_with_history(self):
        """Test recommendations based on history"""
        profile = UserProfile(user_id=123, name="John")
        profile.add_order(100.0, ["Pizza Margherita"], "rest_1")
        profile.favorite_categories.append("pizza")
        
        menu_items = [
            {"id": "1", "name": "Pizza Margherita", "category": "pizza", "price": 100},
            {"id": "2", "name": "Pizza Pepperoni", "category": "pizza", "price": 120},
            {"id": "3", "name": "Salad", "category": "salad", "price": 80},
        ]
        
        recommendations = PersonalizationService.get_recommendations(profile, menu_items, limit=2)
        assert len(recommendations) > 0
        # Should recommend pizza items since user likes them
        pizza_count = sum(1 for r in recommendations if "pizza" in r.get("category", "").lower())
        assert pizza_count > 0
    
    def test_should_remind_user(self):
        """Test reminder logic"""
        profile = UserProfile(user_id=123, name="John")
        
        # New user, no orders
        assert not PersonalizationService.should_remind_user(profile, days_threshold=2)
        
        # Add order today
        profile.last_order_date = datetime.now()
        assert not PersonalizationService.should_remind_user(profile, days_threshold=2)
        
        # Simulate 3 days passed
        profile.last_order_date = datetime.now() - timedelta(days=3)
        assert PersonalizationService.should_remind_user(profile, days_threshold=2)
    
    def test_level_up_message(self):
        """Test level-up message generation"""
        profile = UserProfile(user_id=123, name="John")
        old_level = profile.level
        
        # Add orders to level up
        for _ in range(5):
            profile.add_order(100.0, ["Dish"], "rest")
        
        message = PersonalizationService.get_level_up_message(profile, old_level)
        
        if message and profile.level != old_level:
            assert "РІВЕНЬ" in message or "LEVEL" in message.upper()
            assert "🎉" in message


class TestUserAnalyticsService:
    """Test UserAnalyticsService"""
    
    def test_get_top_users(self):
        """Test getting top users"""
        profiles = [
            UserProfile(user_id=1, name="User1"),
            UserProfile(user_id=2, name="User2"),
            UserProfile(user_id=3, name="User3"),
        ]
        
        # Give different order counts
        profiles[0].total_orders = 10
        profiles[1].total_orders = 5
        profiles[2].total_orders = 15
        
        top_users = UserAnalyticsService.get_top_users(profiles, limit=2)
        
        assert len(top_users) == 2
        assert top_users[0].total_orders == 15  # Highest first
        assert top_users[1].total_orders == 10
    
    def test_get_inactive_users(self):
        """Test getting inactive users"""
        now = datetime.now()
        profiles = [
            UserProfile(user_id=1, name="User1"),
            UserProfile(user_id=2, name="User2"),
        ]
        
        profiles[0].last_order_date = now - timedelta(days=5)
        profiles[1].last_order_date = now - timedelta(days=1)
        
        inactive = UserAnalyticsService.get_inactive_users(profiles, days_threshold=2)
        
        assert len(inactive) == 1
        assert inactive[0].user_id == 1


class TestFormattingHelpers:
    """Test formatting helper functions"""
    
    def test_greeting_message_formatting(self):
        """Test greeting message formatting"""
        profile = UserProfile(user_id=123, name="John")
        message = format_user_greeting_message(profile)
        
        assert "John" in message
        assert "👋" in message
    
    def test_level_badge_formatting(self):
        """Test level badge formatting"""
        profile = UserProfile(user_id=123, name="John")
        badge = format_level_badge(profile)
        
        assert "🆕" in badge or "Новачок" in badge
    
    def test_emoji_for_category(self):
        """Test emoji selection for categories"""
        assert get_emoji_for_category("pizza") == "🍕"
        assert get_emoji_for_category("салат") == "🥗"
        assert get_emoji_for_category("бургер") == "🍔"
        assert get_emoji_for_category("unknown") == "🍽️"
    
    def test_recommendations_message_formatting(self):
        """Test recommendations message formatting"""
        recommendations = [
            {"name": "Pizza", "price": 100, "category": "pizza"},
            {"name": "Salad", "price": 80, "category": "salad"},
        ]
        
        message = format_recommendations_message(recommendations)
        
        assert "Pizza" in message
        assert "Salad" in message
        assert "100" in message
        assert "80" in message


class TestUserRepository:
    """Test UserRepository (basic tests without real DB)"""
    
    def test_profile_dict_operations(self):
        """Test profile dictionary conversion"""
        profile = UserProfile(
            user_id=123,
            name="Test User",
            phone="+380123456789",
            total_orders=5
        )
        
        profile_dict = profile.to_dict()
        restored = UserProfile.from_dict(profile_dict)
        
        assert restored.user_id == profile.user_id
        assert restored.name == profile.name
        assert restored.phone == profile.phone
        assert restored.total_orders == profile.total_orders


if __name__ == "__main__":
    pytest.main([__file__, "-v"])