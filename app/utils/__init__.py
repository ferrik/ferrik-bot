"""Utility modules for Ferrik Bot"""

from app.utils.validators import (
    safe_parse_price,
    safe_parse_quantity,
    validate_phone,
    normalize_phone,
    validate_address,
    sanitize_input,
    validate_item_data,
    calculate_total_price,
    format_price,
    format_order_summary,
)

from app.utils.session import (
    get_user_session,
    update_user_session,
    get_user_cart,
    add_to_cart,
    remove_from_cart,
    clear_user_cart,
    get_user_stats,
    register_order,
)

__all__ = [
    # Validators
    'safe_parse_price',
    'safe_parse_quantity',
    'validate_phone',
    'normalize_phone',
    'validate_address',
    'sanitize_input',
    'validate_item_data',
    'calculate_total_price',
    'format_price',
    'format_order_summary',
    # Session
    'get_user_session',
    'update_user_session',
    'get_user_cart',
    'add_to_cart',
    'remove_from_cart',
    'clear_user_cart',
    'get_user_stats',
    'register_order',
]
