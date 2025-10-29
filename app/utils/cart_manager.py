"""
🛒 CART MANAGER - Управління кошиком користувача
Окремий модуль для роботи з кошиком
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# CART STORAGE
# ============================================================================

_carts: Dict[int, List[Dict[str, Any]]] = {}


def get_user_cart(user_id: int) -> List[Dict[str, Any]]:
    """
    Отримати кошик користувача
    
    Args:
        user_id: ID користувача
    
    Returns:
        Список товарів у кошику
    """
    if user_id not in _carts:
        _carts[user_id] = []
    
    return _carts[user_id]


def add_to_cart(user_id: int, item: Dict[str, Any]) -> bool:
    """
    Додати товар до кошика
    
    Args:
        user_id: ID користувача
        item: Товар {'id', 'name', 'price', 'quantity'}
    
    Returns:
        True якщо успішно
    """
    try:
        cart = get_user_cart(user_id)
        
        # Перевірити чи товар уже в кошику
        for cart_item in cart:
            if cart_item.get('id') == item.get('id'):
                # Збільшити кількість
                cart_item['quantity'] = cart_item.get('quantity', 1) + item.get('quantity', 1)
                logger.info(f"✏️ Updated {item.get('name')} qty in cart")
                return True
        
        # Додати новий товар
        cart.append(item)
        logger.info(f"➕ Added {item.get('name')} to cart")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error adding to cart: {e}")
        return False


def remove_from_cart(user_id: int, item_id: str) -> bool:
    """
    Видалити товар з кошика
    
    Args:
        user_id: ID користувача
        item_id: ID товара
    
    Returns:
        True якщо успішно
    """
    try:
        cart = get_user_cart(user_id)
        _carts[user_id] = [item for item in cart if item.get('id') != item_id]
        logger.info(f"🗑️ Removed item {item_id} from cart")
        return True
    except Exception as e:
        logger.error(f"❌ Error removing from cart: {e}")
        return False


def update_cart_item(user_id: int, item_id: str, quantity: int) -> bool:
    """
    Оновити кількість товара в кошику
    
    Args:
        user_id: ID користувача
        item_id: ID товара
        quantity: Нова кількість
    
    Returns:
        True якщо успішно
    """
    try:
        cart = get_user_cart(user_id)
        
        for item in cart:
            if item.get('id') == item_id:
                if quantity <= 0:
                    return remove_from_cart(user_id, item_id)
                
                item['quantity'] = quantity
                logger.info(f"📝 Updated item {item_id} quantity to {quantity}")
                return True
        
        return False
    except Exception as e:
        logger.error(f"❌ Error updating cart: {e}")
        return False


def clear_user_cart(user_id: int) -> bool:
    """Очистити кошик користувача"""
    try:
        _carts[user_id] = []
        logger.info(f"🧹 Cleared cart for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error clearing cart: {e}")
        return False


def get_cart_total(user_id: int) -> float:
    """
    Розрахувати загальну вартість кошика
    
    Args:
        user_id: ID користувача
    
    Returns:
        Загальна вартість
    """
    cart = get_user_cart(user_id)
    total = sum(
        item.get('price', 0) * item.get('quantity', 1)
        for item in cart
    )
    return round(total, 2)


def get_cart_item_count(user_id: int) -> int:
    """Отримати кількість товарів у кошику"""
    cart = get_user_cart(user_id)
    return sum(item.get('quantity', 1) for item in cart)


def is_cart_empty(user_id: int) -> bool:
    """Перевірити чи кошик порожній"""
    return len(get_user_cart(user_id)) == 0
