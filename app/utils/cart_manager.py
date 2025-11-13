"""
Cart Manager - Shopping cart management with Redis/Memory support
FerrikBot v3.2
"""

import os
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️ Redis not available, using in-memory storage")


class CartManager:
    """
    Manages shopping carts for users
    Supports both Redis and in-memory storage
    """
    
    def __init__(self):
        """Initialize cart manager with Redis or memory storage"""
        self.redis_url = os.environ.get('REDIS_URL')
        
        if self.redis_url and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                self.storage_type = 'redis'
                logger.info("✅ Redis connected for cart storage")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}, using in-memory")
                self.redis_client = None
                self.storage_type = 'memory'
                self.carts = {}
        else:
            self.redis_client = None
            self.storage_type = 'memory'
            self.carts = {}
            if not REDIS_AVAILABLE:
                logger.info("💾 Using in-memory cart storage (Redis not installed)")
            else:
                logger.info("💾 Using in-memory cart storage (REDIS_URL not set)")
    
    def _get_key(self, user_id: int) -> str:
        """
        Generate Redis key for user cart
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            str: Redis key
        """
        return f"cart:{user_id}"
    
    def get_cart(self, user_id: int) -> List[Dict]:
        """
        Get user's cart items
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            list: Cart items as list of dicts
        """
        try:
            if self.storage_type == 'redis':
                data = self.redis_client.get(self._get_key(user_id))
                return json.loads(data) if data else []
            else:
                return self.carts.get(user_id, [])
        except Exception as e:
            logger.error(f"❌ Error getting cart for {user_id}: {e}")
            return []
    
    def add_item(self, user_id: int, item: Dict) -> bool:
        """
        Add item to cart or increase quantity if exists
        
        Args:
            user_id: Telegram user ID
            item: Item dict with keys: id, name, price, etc.
            
        Returns:
            bool: Success status
        """
        try:
            cart = self.get_cart(user_id)
            
            # Check if item already exists
            item_exists = False
            for existing_item in cart:
                if existing_item.get('id') == item.get('id'):
                    # Increase quantity
                    existing_item['quantity'] = existing_item.get('quantity', 1) + 1
                    item_exists = True
                    break
            
            if not item_exists:
                # Add new item with quantity 1
                item['quantity'] = item.get('quantity', 1)
                cart.append(item)
            
            success = self._save_cart(user_id, cart)
            if success:
                logger.info(f"✅ Added item {item.get('name')} to cart for user {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error adding item to cart: {e}")
            return False
    
    def remove_item(self, user_id: int, item_id: int) -> bool:
        """
        Remove item from cart
        
        Args:
            user_id: Telegram user ID
            item_id: Item ID to remove
            
        Returns:
            bool: Success status
        """
        try:
            cart = self.get_cart(user_id)
            original_length = len(cart)
            
            # Filter out item
            cart = [item for item in cart if item.get('id') != item_id]
            
            if len(cart) < original_length:
                logger.info(f"✅ Removed item {item_id} from cart for user {user_id}")
            
            return self._save_cart(user_id, cart)
            
        except Exception as e:
            logger.error(f"❌ Error removing item: {e}")
            return False
    
    def update_quantity(self, user_id: int, item_id: int, quantity: int) -> bool:
        """
        Update item quantity in cart
        
        Args:
            user_id: Telegram user ID
            item_id: Item ID
            quantity: New quantity (0 removes item)
            
        Returns:
            bool: Success status
        """
        try:
            if quantity <= 0:
                return self.remove_item(user_id, item_id)
            
            cart = self.get_cart(user_id)
            
            for item in cart:
                if item.get('id') == item_id:
                    item['quantity'] = quantity
                    break
            
            return self._save_cart(user_id, cart)
            
        except Exception as e:
            logger.error(f"❌ Error updating quantity: {e}")
            return False
    
    def clear_cart(self, user_id: int) -> bool:
        """
        Clear user's cart completely
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: Success status
        """
        try:
            if self.storage_type == 'redis':
                self.redis_client.delete(self._get_key(user_id))
            else:
                self.carts[user_id] = []
            
            logger.info(f"✅ Cleared cart for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing cart: {e}")
            return False
    
    def _save_cart(self, user_id: int, cart: List[Dict]) -> bool:
        """
        Save cart to storage
        
        Args:
            user_id: Telegram user ID
            cart: Cart items list
            
        Returns:
            bool: Success status
        """
        try:
            if self.storage_type == 'redis':
                key = self._get_key(user_id)
                if cart:
                    # Save with 24 hours TTL
                    self.redis_client.setex(
                        key,
                        86400,  # 24 hours
                        json.dumps(cart, ensure_ascii=False)
                    )
                else:
                    # Delete key if cart is empty
                    self.redis_client.delete(key)
            else:
                self.carts[user_id] = cart
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving cart: {e}")
            return False
    
    def get_cart_total(self, user_id: int) -> float:
        """
        Calculate total price of cart
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            float: Total price
        """
        cart = self.get_cart(user_id)
        total = sum(
            float(item.get('price', 0)) * int(item.get('quantity', 1))
            for item in cart
        )
        return round(total, 2)
    
    def get_cart_count(self, user_id: int) -> int:
        """
        Get total number of items in cart
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            int: Total item count
        """
        cart = self.get_cart(user_id)
        return sum(int(item.get('quantity', 1)) for item in cart)
    
    def get_cart_summary(self, user_id: int) -> Dict:
        """
        Get cart summary with items, count, and total
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            dict: Cart summary
        """
        cart = self.get_cart(user_id)
        return {
            'items': cart,
            'count': self.get_cart_count(user_id),
            'total': self.get_cart_total(user_id),
            'is_empty': len(cart) == 0
        }


# Global cart manager instance
cart_manager = CartManager()


# ============================================================================
# Helper functions for backwards compatibility and convenience
# ============================================================================

def get_user_cart(user_id: int) -> List[Dict]:
    """
    Get user cart (wrapper function)
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        list: Cart items
    """
    return cart_manager.get_cart(user_id)


def add_to_cart(user_id: int, item: Dict) -> bool:
    """
    Add item to cart (wrapper function)
    
    Args:
        user_id: Telegram user ID
        item: Item to add
        
    Returns:
        bool: Success status
    """
    return cart_manager.add_item(user_id, item)


def remove_from_cart(user_id: int, item_id: int) -> bool:
    """
    Remove item from cart (wrapper function)
    
    Args:
        user_id: Telegram user ID
        item_id: Item ID to remove
        
    Returns:
        bool: Success status
    """
    return cart_manager.remove_item(user_id, item_id)


def clear_user_cart(user_id: int) -> bool:
    """
    Clear user cart (wrapper function)
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        bool: Success status
    """
    return cart_manager.clear_cart(user_id)


def is_cart_empty(user_id: int) -> bool:
    """
    Check if cart is empty
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        bool: True if cart is empty
    """
    cart = get_user_cart(user_id)
    return len(cart) == 0


def get_cart_item_count(user_id: int) -> int:
    """
    Get total item count in cart
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        int: Total items
    """
    return cart_manager.get_cart_count(user_id)


def get_cart_total(user_id: int) -> float:
    """
    Get cart total price
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        float: Total price
    """
    return cart_manager.get_cart_total(user_id)


def get_cart_summary(user_id: int) -> Dict:
    """
    Get full cart summary
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        dict: Cart summary with items, count, total
    """
    return cart_manager.get_cart_summary(user_id)


def update_item_quantity(user_id: int, item_id: int, quantity: int) -> bool:
    """
    Update item quantity
    
    Args:
        user_id: Telegram user ID
        item_id: Item ID
        quantity: New quantity
        
    Returns:
        bool: Success status
    """
    return cart_manager.update_quantity(user_id, item_id, quantity)


def format_cart_message(user_id: int) -> str:
    """
    Format cart as text message
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        str: Formatted cart message
    """
    summary = get_cart_summary(user_id)
    
    if summary['is_empty']:
        return "🛒 Ваш кошик порожній\n\nВикористайте /menu щоб додати товари"
    
    message = "🛒 Ваш кошик:\n\n"
    
    for item in summary['items']:
        name = item.get('name', 'Товар')
        price = float(item.get('price', 0))
        quantity = int(item.get('quantity', 1))
        subtotal = price * quantity
        
        message += f"▪️ {name}\n"
        message += f"   {quantity} × {price} грн = {subtotal} грн\n\n"
    
    message += f"━━━━━━━━━━━━━━━━\n"
    message += f"💰 Всього: {summary['total']} грн\n"
    message += f"📦 Товарів: {summary['count']}"
    
    return message


# Export all public functions
__all__ = [
    'CartManager',
    'cart_manager',
    'get_user_cart',
    'add_to_cart',
    'remove_from_cart',
    'clear_user_cart',
    'is_cart_empty',
    'get_cart_item_count',
    'get_cart_total',
    'get_cart_summary',
    'update_item_quantity',
    'format_cart_message'
]
