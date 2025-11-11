"""
🛒 Cart Manager з Redis підтримкою
Зберігає кошики навіть після рестарту
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Спроба імпорту Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️ Redis not installed, using in-memory fallback")

# Fallback: in-memory storage
_carts: Dict[int, List[Dict[str, Any]]] = {}


class CartManager:
    """Менеджер кошика з підтримкою Redis або in-memory"""
    
    def __init__(self):
        self.redis_client = None
        self.use_redis = False
        
        if REDIS_AVAILABLE:
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                try:
                    self.redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_timeout=5
                    )
                    # Тест з'єднання
                    self.redis_client.ping()
                    self.use_redis = True
                    logger.info("✅ Redis connected for cart storage")
                except Exception as e:
                    logger.error(f"❌ Redis connection failed: {e}")
                    self.use_redis = False
    
    def _get_key(self, user_id: int) -> str:
        """Генерація ключа для Redis"""
        return f"cart:{user_id}"
    
    def get_cart(self, user_id: int) -> List[Dict[str, Any]]:
        """Отримати кошик користувача"""
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get(self._get_key(user_id))
                if data:
                    return json.loads(data)
                return []
            except Exception as e:
                logger.error(f"❌ Redis get error: {e}")
                # Fallback to memory
                return _carts.get(user_id, [])
        else:
            return _carts.get(user_id, [])
    
    def save_cart(self, user_id: int, cart: List[Dict[str, Any]]) -> bool:
        """Зберегти кошик"""
        if self.use_redis and self.redis_client:
            try:
                key = self._get_key(user_id)
                # Зберігаємо на 7 днів
                self.redis_client.setex(
                    key,
                    7 * 24 * 60 * 60,  # 7 днів у секундах
                    json.dumps(cart)
                )
                return True
            except Exception as e:
                logger.error(f"❌ Redis save error: {e}")
                # Fallback to memory
                _carts[user_id] = cart
                return True
        else:
            _carts[user_id] = cart
            return True
    
    def add_item(self, user_id: int, item: Dict[str, Any]) -> bool:
        """Додати товар до кошика"""
        cart = self.get_cart(user_id)
        
        # Перевірити чи товар уже є
        for cart_item in cart:
            if cart_item.get('id') == item.get('id'):
                # Збільшити кількість
                cart_item['quantity'] = cart_item.get('quantity', 1) + item.get('quantity', 1)
                return self.save_cart(user_id, cart)
        
        # Додати новий товар
        cart.append(item)
        return self.save_cart(user_id, cart)
    
    def remove_item(self, user_id: int, item_id: str) -> bool:
        """Видалити товар з кошика"""
        cart = self.get_cart(user_id)
        cart = [item for item in cart if item.get('id') != item_id]
        return self.save_cart(user_id, cart)
    
    def clear_cart(self, user_id: int) -> bool:
        """Очистити кошик"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(self._get_key(user_id))
                return True
            except Exception as e:
                logger.error(f"❌ Redis delete error: {e}")
        
        _carts[user_id] = []
        return True
    
    def get_total(self, user_id: int) -> float:
        """Розрахувати загальну вартість"""
        cart = self.get_cart(user_id)
        total = sum(
            item.get('price', 0) * item.get('quantity', 1)
            for item in cart
        )
        return round(total, 2)
    
    def get_item_count(self, user_id: int) -> int:
        """Кількість товарів у кошику"""
        cart = self.get_cart(user_id)
        return sum(item.get('quantity', 1) for item in cart)


# Глобальний екземпляр
cart_manager = CartManager()


# ============================================================================
# ПУБЛІЧНІ ФУНКЦІЇ (для сумісності зі старим кодом)
# ============================================================================

def get_user_cart(user_id: int) -> List[Dict[str, Any]]:
    """Отримати кошик користувача"""
    return cart_manager.get_cart(user_id)


def add_to_cart(user_id: int, item: Dict[str, Any]) -> bool:
    """Додати товар до кошика"""
    return cart_manager.add_item(user_id, item)


def remove_from_cart(user_id: int, item_id: str) -> bool:
    """Видалити товар з кошика"""
    return cart_manager.remove_item(user_id, item_id)


def clear_user_cart(user_id: int) -> bool:
    """Очистити кошик"""
    return cart_manager.clear_cart(user_id)


def get_cart_total(user_id: int) -> float:
    """Загальна вартість кошика"""
    return cart_manager.get_total(user_id)


def get_cart_item_count(user_id: int) -> int:
    """Кількість товарів"""
    return cart_manager.get_item_count(user_id)