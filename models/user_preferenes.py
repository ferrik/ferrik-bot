"""
User preferences and dietary restrictions
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class UserPreferences:
    """User preferences for personalization"""
    user_id: int
    
    # Food preferences
    favorite_categories: List[str] = field(default_factory=list)
    dietary_restrictions: List[str] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    
    # Delivery preferences
    preferred_delivery_method: str = "delivery"  # delivery, pickup
    preferred_restaurant_id: Optional[str] = None
    
    # Budget preferences
    avg_budget: float = 0.0
    max_budget: float = 10000.0
    
    # Notification preferences
    push_notifications: bool = True
    email_notifications: bool = False
    remind_inactive_days: int = 2  # Remind after 2 days of inactivity
    
    # Time preferences
    preferred_order_time: Optional[str] = None  # e.g., "12:00", "19:30"
    preferred_order_days: List[str] = field(default_factory=lambda: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_dietary_restriction(self, restriction: str):
        """Add a dietary restriction"""
        if restriction not in self.dietary_restrictions:
            self.dietary_restrictions.append(restriction)
            self.updated_at = datetime.now()
    
    def remove_dietary_restriction(self, restriction: str):
        """Remove a dietary restriction"""
        if restriction in self.dietary_restrictions:
            self.dietary_restrictions.remove(restriction)
            self.updated_at = datetime.now()
    
    def add_allergy(self, allergy: str):
        """Add an allergy"""
        if allergy not in self.allergies:
            self.allergies.append(allergy)
            self.updated_at = datetime.now()
    
    def remove_allergy(self, allergy: str):
        """Remove an allergy"""
        if allergy in self.allergies:
            self.allergies.remove(allergy)
            self.updated_at = datetime.now()
    
    def add_favorite_category(self, category: str):
        """Add favorite category"""
        if category not in self.favorite_categories:
            self.favorite_categories.append(category)
            self.updated_at = datetime.now()
    
    def remove_favorite_category(self, category: str):
        """Remove favorite category"""
        if category in self.favorite_categories:
            self.favorite_categories.remove(category)
            self.updated_at = datetime.now()
    
    def get_dietary_emoji(self) -> str:
        """Get emoji for dietary restrictions"""
        emojis = []
        if "vegan" in [r.lower() for r in self.dietary_restrictions]:
            emojis.append("🌱")
        if "vegetarian" in [r.lower() for r in self.dietary_restrictions]:
            emojis.append("🥬")
        if "gluten-free" in [r.lower() for r in self.dietary_restrictions]:
            emojis.append("🌾")
        return " ".join(emojis) if emojis else ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'favorite_categories': self.favorite_categories,
            'dietary_restrictions': self.dietary_restrictions,
            'allergies': self.allergies,
            'preferred_delivery_method': self.preferred_delivery_method,
            'preferred_restaurant_id': self.preferred_restaurant_id,
            'avg_budget': self.avg_budget,
            'max_budget': self.max_budget,
            'push_notifications': self.push_notifications,
            'email_notifications': self.email_notifications,
            'remind_inactive_days': self.remind_inactive_days,
            'preferred_order_time': self.preferred_order_time,
            'preferred_order_days': self.preferred_order_days,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserPreferences':
        """Create from dictionary (from storage)"""
        return cls(
            user_id=data['user_id'],
            favorite_categories=data.get('favorite_categories', []),
            dietary_restrictions=data.get('dietary_restrictions', []),
            allergies=data.get('allergies', []),
            preferred_delivery_method=data.get('preferred_delivery_method', 'delivery'),
            preferred_restaurant_id=data.get('preferred_restaurant_id'),
            avg_budget=data.get('avg_budget', 0.0),
            max_budget=data.get('max_budget', 10000.0),
            push_notifications=data.get('push_notifications', True),
            email_notifications=data.get('email_notifications', False),
            remind_inactive_days=data.get('remind_inactive_days', 2),
            preferred_order_time=data.get('preferred_order_time'),
            preferred_order_days=data.get('preferred_order_days', 
                                          ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now()
        )