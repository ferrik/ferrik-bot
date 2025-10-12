"""
User profile model with history and personalization data
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class UserLevel(Enum):
    """User levels based on order count"""
    NOVICE = "novice"          # 0-2 orders
    GOURMET = "gourmet"        # 3-10 orders
    FOODIE = "foodie"          # 11+ orders
    VIP = "vip"                # Premium


@dataclass
class UserProfile:
    """User profile with personalization data"""
    user_id: int
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    
    # Personalization data
    total_orders: int = 0
    total_spent: float = 0.0
    points: int = 0
    level: UserLevel = UserLevel.NOVICE
    
    # Timestamps
    registered_at: datetime = field(default_factory=datetime.now)
    last_order_date: Optional[datetime] = None
    
    # Favorites
    favorite_restaurants: List[str] = field(default_factory=list)
    favorite_dishes: List[str] = field(default_factory=list)
    favorite_categories: List[str] = field(default_factory=list)
    
    # Preferences
    dietary_restrictions: List[str] = field(default_factory=list)
    preferred_delivery_method: str = "delivery"
    avg_budget: float = 0.0
    notifications_enabled: bool = True
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_seen: Optional[datetime] = None
    
    def get_level_emoji(self) -> str:
        """Return emoji for user level"""
        level_emoji = {
            UserLevel.NOVICE: "🆕",
            UserLevel.GOURMET: "🍽️",
            UserLevel.FOODIE: "👨‍🍳",
            UserLevel.VIP: "👑"
        }
        return level_emoji.get(self.level, "🆕")
    
    def get_level_name(self) -> str:
        """Return readable level name"""
        level_names = {
            UserLevel.NOVICE: "Новачок",
            UserLevel.GOURMET: "Гурман",
            UserLevel.FOODIE: "Фуді",
            UserLevel.VIP: "VIP"
        }
        return level_names.get(self.level, "Новачок")
    
    def update_level(self) -> bool:
        """Update user level based on order count, return True if changed"""
        old_level = self.level
        
        if self.total_orders >= 11:
            self.level = UserLevel.FOODIE
        elif self.total_orders >= 3:
            self.level = UserLevel.GOURMET
        else:
            self.level = UserLevel.NOVICE
        
        self.updated_at = datetime.now()
        return old_level != self.level
    
    def add_order(self, amount: float, dish_names: List[str], restaurant_id: str):
        """Record a new order"""
        self.total_orders += 1
        self.total_spent += amount
        self.points += int(amount // 100)  # 1 point per 100 currency units
        self.last_order_date = datetime.now()
        
        # Add to favorites
        for dish in dish_names:
            if dish not in self.favorite_dishes:
                self.favorite_dishes.append(dish)
            else:
                # Move to beginning (most recent favorite)
                self.favorite_dishes.remove(dish)
                self.favorite_dishes.insert(0, dish)
        
        if restaurant_id not in self.favorite_restaurants:
            self.favorite_restaurants.append(restaurant_id)
        
        # Update level
        self.update_level()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'phone': self.phone,
            'address': self.address,
            'total_orders': self.total_orders,
            'total_spent': self.total_spent,
            'points': self.points,
            'level': self.level.value,
            'registered_at': self.registered_at.isoformat(),
            'last_order_date': self.last_order_date.isoformat() if self.last_order_date else None,
            'favorite_restaurants': self.favorite_restaurants,
            'favorite_dishes': self.favorite_dishes,
            'favorite_categories': self.favorite_categories,
            'dietary_restrictions': self.dietary_restrictions,
            'preferred_delivery_method': self.preferred_delivery_method,
            'avg_budget': self.avg_budget,
            'notifications_enabled': self.notifications_enabled,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserProfile':
        """Create from dictionary (from storage)"""
        profile = cls(
            user_id=data['user_id'],
            name=data['name'],
            phone=data.get('phone'),
            address=data.get('address'),
            total_orders=data.get('total_orders', 0),
            total_spent=data.get('total_spent', 0.0),
            points=data.get('points', 0),
            level=UserLevel(data.get('level', 'novice')),
            registered_at=datetime.fromisoformat(data['registered_at']) if 'registered_at' in data else datetime.now(),
            last_order_date=datetime.fromisoformat(data['last_order_date']) if data.get('last_order_date') else None,
            favorite_restaurants=data.get('favorite_restaurants', []),
            favorite_dishes=data.get('favorite_dishes', []),
            favorite_categories=data.get('favorite_categories', []),
            dietary_restrictions=data.get('dietary_restrictions', []),
            preferred_delivery_method=data.get('preferred_delivery_method', 'delivery'),
            avg_budget=data.get('avg_budget', 0.0),
            notifications_enabled=data.get('notifications_enabled', True)
        )
        return profile