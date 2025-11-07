"""
🔄 FSM MANAGER - Finite State Machine для користувачів
Керує станами користувачів під час замовлення
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================================
# СТАНИ КОРИСТУВАЧІВ
# ============================================================================

STATES = {
    'idle': {
        'name': 'Головне меню',
        'emoji': '🏠',
        'description': 'Користувач на головному меню'
    },
    'browsing_menu': {
        'name': 'Перегляд меню',
        'emoji': '📋',
        'description': 'Користувач переглядає товари'
    },
    'awaiting_phone': {
        'name': 'Очікування телефону',
        'emoji': '📱',
        'description': 'Чекаємо введення телефону'
    },
    'awaiting_address': {
        'name': 'Очікування адреси',
        'emoji': '📍',
        'description': 'Чекаємо введення адреси'
    },
    'confirming_order': {
        'name': 'Підтвердження замовлення',
        'emoji': '✅',
        'description': 'Користувач підтверджує замовлення'
    },
    'order_placed': {
        'name': 'Замовлення оформлено',
        'emoji': '🎉',
        'description': 'Замовлення успішно оформлено'
    }
}

# ============================================================================
# STATE MANAGER
# ============================================================================

_user_states: Dict[int, Dict[str, Any]] = {}


def get_user_state(user_id: int) -> str:
    """
    Отримати поточний стан користувача
    
    Args:
        user_id: ID користувача
    
    Returns:
        Поточний стан (за замовчуванням 'idle')
    """
    if user_id not in _user_states:
        _user_states[user_id] = {'state': 'idle', 'data': {}}
    
    return _user_states[user_id]['state']


def set_user_state(user_id: int, state: str, data: Dict[str, Any] = None):
    """
    Встановити стан користувача
    
    Args:
        user_id: ID користувача
        state: Новий стан
        data: Додаткові дані
    """
    if state not in STATES:
        logger.warning(f"⚠️ Unknown state: {state}")
        return
    
    if user_id not in _user_states:
        _user_states[user_id] = {}
    
    old_state = _user_states[user_id].get('state', 'idle')
    _user_states[user_id]['state'] = state
    
    if data:
        _user_states[user_id]['data'] = data
    
    logger.info(f"🔄 User {user_id}: {old_state} → {state}")


def get_user_state_data(user_id: int) -> Dict[str, Any]:
    """Отримати додаткові дані стану"""
    if user_id not in _user_states:
        return {}
    
    return _user_states[user_id].get('data', {})


def update_state_data(user_id: int, key: str, value: Any):
    """Оновити значення в даних стану"""
    if user_id not in _user_states:
        _user_states[user_id] = {'state': 'idle', 'data': {}}
    
    _user_states[user_id]['data'][key] = value


def reset_user_state(user_id: int):
    """Скинути стан користувача до idle"""
    if user_id in _user_states:
        _user_states[user_id] = {'state': 'idle', 'data': {}}
        logger.info(f"🔄 User {user_id} state reset to idle")


def is_state(user_id: int, state: str) -> bool:
    """Перевірити чи користувач у певному стані"""
    return get_user_state(user_id) == state


def get_state_info(state: str) -> Dict[str, str]:
    """Отримати інформацію про стан"""
    return STATES.get(state, {
        'name': 'Невідомий',
        'emoji': '❓',
        'description': 'Невідомий стан'
    })
