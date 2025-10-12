"""
Personalization service for recommendations and customized messages
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from models.user_profile import UserProfile, UserLevel
from models.user_preferences import UserPreferences

logger = logging.getLogger(__name__)


class PersonalizationService:
    """Service for personalization logic"""
    
    @staticmethod
    def get_greeting(profile: UserProfile) -> str:
        """Generate personalized greeting message"""
        emoji = profile.get_level_emoji()
        level_name = profile.get_level_name()
        
        # Base greeting
        greeting = f"👋 Привіт, {profile.name}!\n\n"
        
        # Show level if not novice
        if profile.level != UserLevel.NOVICE:
            greeting += f"{emoji} Ти вже {level_name}! (+20 бонус-балів)\n\n"
        
        # Show stats
        if profile.total_orders > 0:
            greeting += f"📊 Твої замовлення: {profile.total_orders}\n"
            greeting += f"💰 Витрачено: {profile.total_spent:.2f} грн\n"
            greeting += f"🎁 Бонус-балів: {profile.points}\n\n"
        
        # Show days since last order
        if profile.last_order_date:
            days_ago = (datetime.now() - profile.last_order_date).days
            if days_ago == 1:
                greeting += "📅 Останнє замовлення: вчора\n\n"
            elif days_ago > 1:
                greeting += f"📅 Останнє замовлення: {days_ago} днів тому\n\n"
        
        return greeting
    
    @staticmethod
    def get_recommendations(
        profile: UserProfile,
        all_menu_items: List[Dict[str, Any]],
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get personalized recommendations based on order history"""
        
        if not profile.favorite_dishes and not profile.favorite_categories:
            # No history - return random popular items
            return all_menu_items[:limit]
        
        recommendations = []
        
        # Prioritize favorite categories
        if profile.favorite_categories:
            for item in all_menu_items:
                if len(recommendations) >= limit:
                    break
                item_category = item.get('category', '').lower()
                for fav_cat in profile.favorite_categories:
                    if fav_cat.lower() in item_category:
                        recommendations.append(item)
                        break
        
        # Add favorite dishes
        if len(recommendations) < limit:
            for item in all_menu_items:
                if len(recommendations) >= limit:
                    break
                item_name = item.get('name', '').lower()
                for fav_dish in profile.favorite_dishes[:5]:  # Check top 5 favorites
                    if fav_dish.lower() in item_name or item_name in fav_dish.lower():
                        if item not in recommendations:
                            recommendations.append(item)
                        break
        
        # Fill remaining with popular items
        if len(recommendations) < limit:
            for item in all_menu_items:
                if len(recommendations) >= limit:
                    break
                if item not in recommendations:
                    recommendations.append(item)
        
        return recommendations[:limit]
    
    @staticmethod
    def get_quick_reorder_suggestion(profile: UserProfile) -> Optional[Dict[str, Any]]:
        """Get most recent favorite dish for quick reorder"""
        if not profile.favorite_dishes:
            return None
        
        # Return most recent favorite
        return {
            'dish_name': profile.favorite_dishes[0],
            'times_ordered': profile.favorite_dishes.count(profile.favorite_dishes[0])
        }
    
    @staticmethod
    def should_remind_user(profile: UserProfile, days_threshold: int = 2) -> bool:
        """Check if user should be reminded about ordering"""
        if not profile.last_order_date:
            return profile.total_orders > 0 and (datetime.now() - profile.registered_at).days >= days_threshold
        
        days_since_order = (datetime.now() - profile.last_order_date).days
        return days_since_order >= days_threshold
    
    @staticmethod
    def get_reminder_message(profile: UserProfile) -> str:
        """Generate reminder message"""
        emoji = profile.get_level_emoji()
        
        message = f"🔔 Привіт, {profile.name}! {emoji}\n\n"
        
        # Suggest favorite dish
        if profile.favorite_dishes:
            favorite = profile.favorite_dishes[0]
            message += f"Скучив за тобою! 😢\n"
            message += f"Замовити {favorite} як звичайно? 🍽️\n\n"
        else:
            message += f"Давно не замовляв...\n"
            message += f"Час перекусити? 😋\n\n"
        
        # Show bonus
        message += f"💡 +10 бонус-балів за замовлення сьогодні!"
        
        return message
    
    @staticmethod
    def get_level_up_message(profile: UserProfile, old_level: UserLevel) -> Optional[str]:
        """Generate level-up message"""
        if profile.level == old_level:
            return None
        
        old_emoji = UserLevel[old_level.name].name if hasattr(UserLevel, old_level.name) else "🆕"
        new_emoji = profile.get_level_emoji()
        new_level_name = profile.get_level_name()
        
        message = f"🎉 РІВЕНЬ ПІДВИЩЕНО!\n\n"
        message += f"{new_emoji} Ти тепер {new_level_name}!\n"
        message += f"📊 Замовлень: {profile.total_orders}\n"
        message += f"💰 Витрачено: {profile.total_spent:.2f} грн\n\n"
        message += f"🎁 Бонус: +50 бонус-балів!"
        
        return message
    
    @staticmethod
    def format_user_stats(profile: UserProfile) -> str:
        """Format user profile statistics"""
        emoji = profile.get_level_emoji()
        level_name = profile.get_level_name()
        
        stats = f"👤 МІЙ ПРОФІЛЬ\n\n"
        stats += f"Ім'я: {profile.name}\n"
        stats += f"Рівень: {emoji} {level_name}\n"
        stats += f"Бонус-бали: {profile.points} 🎁\n\n"
        stats += f"📊 Статистика:\n"
        stats += f"• Замовлень: {profile.total_orders}\n"
        stats += f"• Витрачено: {profile.total_spent:.2f} грн\n"
        
        if profile.total_orders > 0:
            avg_order = profile.total_spent / profile.total_orders
            stats += f"• Середній чек: {avg_order:.2f} грн\n"
        
        if profile.last_order_date:
            days_ago = (datetime.now() - profile.last_order_date).days
            stats += f"• Останнє замовлення: {days_ago} днів тому\n"
        
        if profile.favorite_dishes:
            stats += f"\n⭐ Твої улюблені:\n"
            for i, dish in enumerate(profile.favorite_dishes[:3], 1):
                stats += f"{i}. {dish}\n"
        
        return stats
    
    @staticmethod
    def get_discount_offer(profile: UserProfile) -> Optional[str]:
        """Generate discount offer based on user level and inactivity"""
        if profile.total_orders < 3:
            return None  # Only for repeat customers
        
        days_since_order = (datetime.now() - profile.last_order_date).days if profile.last_order_date else None
        
        if not days_since_order:
            return None
        
        if days_since_order >= 7:
            discount = 15
        elif days_since_order >= 5:
            discount = 10
        elif days_since_order >= 3:
            discount = 5
        else:
            return None
        
        offer = f"🎁 Спеціальна пропозиція!\n\n"
        offer += f"Тобі припасована знижка {discount}% на наступне замовлення\n"
        offer += f"Поспіш - дійсна 24 години! ⏰"
        
        return offer


class UserAnalyticsService:
    """Service for user analytics"""
    
    @staticmethod
    def get_inactive_users(
        all_profiles: List[UserProfile],
        days_threshold: int = 2
    ) -> List[UserProfile]:
        """Get users inactive for more than X days"""
        inactive = []
        
        for profile in all_profiles:
            if not profile.last_order_date:
                if (datetime.now() - profile.registered_at).days >= days_threshold:
                    inactive.append(profile)
            else:
                days_since = (datetime.now() - profile.last_order_date).days
                if days_since >= days_threshold:
                    inactive.append(profile)
        
        return inactive
    
    @staticmethod
    def get_top_users(
        all_profiles: List[UserProfile],
        limit: int = 10
    ) -> List[UserProfile]:
        """Get top users by order count"""
        sorted_profiles = sorted(all_profiles, key=lambda p: p.total_orders, reverse=True)
        return sorted_profiles[:limit]
    
    @staticmethod
    def get_user_insights(profile: UserProfile) -> Dict[str, Any]:
        """Get detailed insights about user"""
        avg_order = profile.total_spent / profile.total_orders if profile.total_orders > 0 else 0
        
        if profile.favorite_categories:
            favorite_category = profile.favorite_categories[0]
        else:
            favorite_category = "Unknown"
        
        days_since_last_order = (datetime.now() - profile.last_order_date).days if profile.last_order_date else None
        
        return {
            'user_id': profile.user_id,
            'total_orders': profile.total_orders,
            'total_spent': profile.total_spent,
            'avg_order_value': avg_order,
            'level': profile.level.value,
            'points': profile.points,
            'favorite_category': favorite_category,
            'days_since_last_order': days_since_last_order,
            'is_inactive': PersonalizationService.should_remind_user(profile, 2)
        }