# handlers/cart.py
"""
Обробники корзини — простий варіант, який використовує services.sheets.get_item_by_id
Функції експортуються у main.py:
- add_item_to_cart(chat_id, item_id, quantity=1)
- show_cart(chat_id)
(адаптуй під твою архітектуру збереження корзини — тут використовуємо простий in-memory fallback)
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from services.sheets import get_item_by_id, get_min_delivery_amount

# Простий in-memory storage для корзин (в продакшні треба замінити на БД або Redis)
_CARTS: Dict[str, Dict[str, Any]] = {}

def _get_cart_key(chat_id: str) -> str:
    return str(chat_id)

def add_item_to_cart(chat_id: str, item_id: str, quantity: int = 1) -> Dict:
    """
    Додає товар до корзини. Повертає оновлену корзину.
    """
    if not chat_id:
        raise ValueError("chat_id is required")
    if not item_id:
        raise ValueError("item_id is required")

    item = get_item_by_id(item_id)
    if not item:
        logger.warning("Item with id %s not found", item_id)
        return {"error": "Item not found"}

    key = _get_cart_key(chat_id)
    cart = _CARTS.setdefault(key, {"items": {}, "total": 0.0})
    items = cart["items"]

    # Припускаємо, що у item є поле "price"
    price = float(item.get("price", 0))
    if item_id in items:
        items[item_id]["quantity"] += quantity
    else:
        items[item_id] = {
            "id": item_id,
            "name": item.get("name") or item.get("title") or "Item",
            "price": price,
            "quantity": quantity
        }

    # Оновлюємо total
    total = 0.0
    for it in items.values():
        total += float(it["price"]) * int(it["quantity"])
    cart["total"] = total

    logger.info("Added item %s x%s to cart %s. New total: %s", item_id, quantity, chat_id, total)
    return cart

def show_cart(chat_id: str) -> Dict:
    """
    Повертає корзину для chat_id у вигляді словника.
    """
    key = _get_cart_key(chat_id)
    cart = _CARTS.get(key)
    if not cart:
        return {"items": {}, "total": 0.0}
    return cart

def clear_cart(chat_id: str) -> None:
    key = _get_cart_key(chat_id)
    if key in _CARTS:
        del _CARTS[key]
