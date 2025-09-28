import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from services.sheets import get_item_by_id, get_min_delivery_amount
from models.user import get_cart, set_cart  # Використовуємо SQLite замість in-memory

def add_item_to_cart(chat_id: str, user_id: str, item_id: str, quantity: int = 1) -> Dict:
    """
    Додає товар до корзини. Повертає оновлену корзину.
    """
    if not chat_id or not user_id:
        raise ValueError("chat_id and user_id are required")
    if not item_id:
        raise ValueError("item_id is required")

    item = get_item_by_id(item_id)
    if not item:
        logger.warning("Item with id %s not found", item_id)
        return {"error": "Item not found"}

    # Отримуємо поточну корзину з БД
    cart = get_cart(user_id)
    if not cart:
        cart = {"items": [], "total": 0.0}

    items = cart["items"]

    # Шукаємо існуючий item
    existing_item = next((i for i in items if i['id'] == item_id), None)
    price = float(item.get("price", 0))

    if existing_item:
        existing_item["quantity"] += quantity
    else:
        new_item = {
            "id": item_id,
            "name": item.get("name") or item.get("title") or "Item",
            "price": price,
            "quantity": quantity
        }
        items.append(new_item)

    # Оновлюємо total
    total = sum(float(it["price"]) * int(it["quantity"]) for it in items)
    cart["total"] = total
    set_cart(user_id, cart)  # Зберігаємо в БД

    logger.info("Added item %s x%s to cart %s. New total: %s", item_id, quantity, user_id, total)
    return cart

def show_cart(chat_id: str, user_id: str) -> Dict:
    """
    Повертає корзину для user_id у вигляді словника.
    """
    cart = get_cart(user_id)
    if not cart:
        cart = {"items": [], "total": 0.0}
    min_delivery = get_min_delivery_amount()
    if cart["total"] < min_delivery:
        message = f"Ваш кошик: {cart['total']:.2f} грн (мінімум для доставки: {min_delivery:.2f} грн)"
    else:
        message = f"Ваш кошик: {cart['total']:.2f} грн"
    # Відправляємо повідомлення (інтеграція з tg_send_message)
    from services.telegram import tg_send_message
    tg_send_message(chat_id, message)
    return cart

def clear_cart(user_id: str) -> None:
    set_cart(user_id, {"items": [], "total": 0.0})