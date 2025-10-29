"""🛒 Cart Management"""

_CARTS = {}

def get_user_cart(user_id):
    if user_id not in _CARTS:
        _CARTS[user_id] = []
    return _CARTS[user_id]

def add_to_cart(user_id, item):
    cart = get_user_cart(user_id)
    # ... логіка додавання
    
def clear_user_cart(user_id):
    _CARTS[user_id] = []
