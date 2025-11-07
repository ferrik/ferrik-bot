"""
💾 Управління сесіями користувачів + бейджи + статистика
"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# ============================================================================
# Бейджи та рівні
# ============================================================================

BADGES = {
    1: {"emoji": "🆕", "name": "Новачок", "color": "🔵"},
    3: {"emoji": "👨‍🍳", "name": "Гурман", "color": "🟠"},
    10: {"emoji": "🏆", "name": "Фанат FerrikFoot", "color": "🟡"},
    25: {"emoji": "⭐", "name": "Майстер смаку", "color": "✨"},
    50: {"emoji": "👑", "name": "Легенда", "color": "👑"},
}

ACHIEVEMENTS = {
    'first_order': {"emoji": "🎯", "title": "Перший крок", "bonus": 50},
    'order_5': {"emoji": "🌟", "title": "П'ять замовлень", "bonus": 100},
    'order_10': {"emoji": "🔥", "title": "Десять замовлень", "bonus": 200},
    'refer_friend': {"emoji": "👥", "title": "Привів друга", "bonus": 150},
    'review_posted': {"emoji": "⭐", "title": "Залишив відгук", "bonus": 50},
    'challenge_weekly': {"emoji": "🎪", "title": "Завершив челлендж", "bonus": 100},
}

# ============================================================================
# Інкрементальне зберігання (для демо)
# ============================================================================

_USERS_DATA = {}  # user_id -> session_data
_CARTS = {}  # user_id -> [items]
_SESSIONS_EXPIRY = {}  # user_id -> expiry_time


# ============================================================================
# Session Manager Functions
# ============================================================================

def get_user_session(user_id: int, create_if_missing: bool = True) -> Dict[str, Any]:
    """Отримати сесію користувача"""
    
    if user_id not in _USERS_DATA:
        if create_if_missing:
            _USERS_DATA[user_id] = {
                'user_id': user_id,
                'state': 'idle',
                'order_count': 0,
                'total_spent': 0.0,
                'favorite_items': [],
                'last_order_date': None,
                'created_at': datetime.now().isoformat(),
                'bonus_points': 0,
                'promocodes_used': [],
                'achievements': [],
                'preferences': {},
                'phone': None,
                'address': None,
            }
        else:
            return {}
    
    return _USERS_DATA[user_id]


def update_user_session(user_id: int, updates: Dict[str, Any]):
    """Оновити сесію користувача"""
    session = get_user_session(user_id)
    session.update(updates)
    _USERS_DATA[user_id] = session
    
    logger.info(f"✅ Session updated for user {user_id}: {list(updates.keys())}")


def get_user_cart(user_id: int) -> List[Dict[str, Any]]:
    """Отримати кошик користувача"""
    if user_id not in _CARTS:
        _CARTS[user_id] = []
    
    return _CARTS[user_id]


def add_to_cart(user_id: int, item: Dict[str, Any]) -> bool:
    """Додати товар до кошика"""
    try:
        cart = get_user_cart(user_id)
        
        # Перевіряємо чи товар уже в кошику
        for cart_item in cart:
            if cart_item.get('id') == item.get('id'):
                # Збільшуємо кількість
                cart_item['quantity'] = cart_item.get('quantity', 1) + item.get('quantity', 1)
                logger.info(f"📦 Item {item.get('name')} quantity updated to {cart_item['quantity']}")
                return True
        
        # Додаємо новий товар
        cart.append(item)
        _CARTS[user_id] = cart
        
        logger.info(f"✅ Item {item.get('name')} added to cart for user {user_id}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error adding to cart: {e}")
        return False


def remove_from_cart(user_id: int, item_id: str) -> bool:
    """Видалити товар з кошика"""
    try:
        cart = get_user_cart(user_id)
        cart = [item for item in cart if item.get('id') != item_id]
        _CARTS[user_id] = cart
        
        logger.info(f"🗑️ Item {item_id} removed from cart")
        return True
    except Exception as e:
        logger.error(f"❌ Error removing from cart: {e}")
        return False


def update_cart_item(user_id: int, item_id: str, quantity: int) -> bool:
    """Оновити кількість товару в кошику"""
    try:
        cart = get_user_cart(user_id)
        
        for item in cart:
            if item.get('id') == item_id:
                if quantity <= 0:
                    remove_from_cart(user_id, item_id)
                else:
                    item['quantity'] = quantity
                logger.info(f"📝 Item {item_id} quantity updated to {quantity}")
                return True
        
        return False
    except Exception as e:
        logger.error(f"❌ Error updating cart: {e}")
        return False


def clear_user_cart(user_id: int) -> bool:
    """Очистити кошик"""
    try:
        _CARTS[user_id] = []
        logger.info(f"🗑️ Cart cleared for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error clearing cart: {e}")
        return False


# ============================================================================
# Бейджи та досягнення
# ============================================================================

def get_user_badge(order_count: int) -> Dict[str, str]:
    """Отримати бейдж за кількість замовлень"""
    for count in sorted(BADGES.keys(), reverse=True):
        if order_count >= count:
            badge = BADGES[count]
            return {
                'emoji': badge['emoji'],
                'name': badge['name'],
                'milestone': count,
                'next_milestone': next(
                    (c for c in sorted(BADGES.keys()) if c > count),
                    None
                )
            }
    
    return {'emoji': '👤', 'name': 'Користувач', 'milestone': 0, 'next_milestone': 1}


def award_achievement(user_id: int, achievement_key: str) -> bool:
    """Видалити досягнення"""
    try:
        session = get_user_session(user_id)
        achievements = session.get('achievements', [])
        
        if achievement_key not in achievements:
            achievements.append(achievement_key)
            bonus = ACHIEVEMENTS[achievement_key]['bonus']
            
            # Додаємо бонуси
            session['bonus_points'] = session.get('bonus_points', 0) + bonus
            
            update_user_session(user_id, {
                'achievements': achievements,
                'bonus_points': session['bonus_points']
            })
            
            logger.info(f"🎉 Achievement '{achievement_key}' awarded to user {user_id} (+{bonus} bonus)")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"❌ Error awarding achievement: {e}")
        return False


def check_and_award_achievements(user_id: int, order_count: int) -> List[str]:
    """Перевірити та видалити досягнення за кількість замовлень"""
    awarded = []
    
    if order_count == 1:
        if award_achievement(user_id, 'first_order'):
            awarded.append('first_order')
    
    elif order_count == 5:
        if award_achievement(user_id, 'order_5'):
            awarded.append('order_5')
    
    elif order_count == 10:
        if award_achievement(user_id, 'order_10'):
            awarded.append('order_10')
    
    return awarded


# ============================================================================
# Статистика користувача
# ============================================================================

def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Отримати повну статистику користувача"""
    session = get_user_session(user_id)
    order_count = session.get('order_count', 0)
    badge = get_user_badge(order_count)
    
    return {
        'user_id': user_id,
        'order_count': order_count,
        'badge': badge,
        'badge_display': f"{badge['emoji']} {badge['name']}",
        'next_badge_in': badge['next_milestone'] - order_count if badge['next_milestone'] else None,
        'total_spent': round(session.get('total_spent', 0), 2),
        'avg_order_value': round(
            session.get('total_spent', 0) / max(order_count, 1), 2
        ),
        'bonus_points': session.get('bonus_points', 0),
        'achievements_count': len(session.get('achievements', [])),
        'last_order_date': session.get('last_order_date'),
        'favorite_item': session.get('favorite_items', [])[-1] if session.get('favorite_items') else None,
        'created_at': session.get('created_at'),
    }


def register_order(
    user_id: int,
    items: List[Dict[str, Any]],
    total_amount: float,
    favorite_item_id: Optional[str] = None
) -> Dict[str, Any]:
    """Зареєструвати замовлення та оновити статистику"""
    session = get_user_session(user_id)
    
    # Оновлюємо лічильники
    order_count = session.get('order_count', 0) + 1
    total_spent = session.get('total_spent', 0) + total_amount
    
    # Відслідковуємо улюблений товар
    favorite_items = session.get('favorite_items', [])
    if favorite_item_id and favorite_item_id not in favorite_items:
        favorite_items.append(favorite_item_id)
    
    # Оновляємо сесію
    update_user_session(user_id, {
        'order_count': order_count,
        'total_spent': total_spent,
        'favorite_items': favorite_items,
        'last_order_date': datetime.now().isoformat(),
    })
    
    # Перевіряємо досягнення
    awarded = check_and_award_achievements(user_id, order_count)
    
    # Повертаємо результати
    stats = get_user_stats(user_id)
    
    result = {
        'stats': stats,
        'achievements_awarded': [ACHIEVEMENTS[key] for key in awarded],
        'new_badge': None,
        'bonus_earned': 0,
    }
    
    # Перевіряємо чи змінився бейдж
    old_badge = get_user_badge(order_count - 1)
    new_badge = get_user_badge(order_count)
    
    if old_badge['milestone'] != new_badge['milestone']:
        result['new_badge'] = new_badge
        logger.info(f"🏆 User {user_id} reached new badge: {new_badge['name']}")
    
    return result


# ============================================================================
# Щотижневі челенджі
# ============================================================================

def get_weekly_challenge(week: int = 0) -> Dict[str, Any]:
    """Отримати челлендж тижня"""
    challenges = [
        {
            'title': '🌅 Сніданок Чемпіона',
            'description': 'Замовте 3 різні сніданки',
            'target': 3,
            'reward': 150,
            'category': 'breakfast'
        },
        {
            'title': '🍕 Піца Маніак',
            'description': 'Замовте піцу 5 разів',
            'target': 5,
            'reward': 200,
            'category': 'pizza'
        },
        {
            'title': '🥗 Здоровенько Їдимо',
            'description': 'Замовте 4 салати',
            'target': 4,
            'reward': 120,
            'category': 'salad'
        },
        {
            'title': '🍣 Суші Сенсей',
            'description': 'Замовте суші 6 разів',
            'target': 6,
            'reward': 250,
            'category': 'sushi'
        },
    ]
    
    return challenges[week % len(challenges)]


def get_user_challenge_progress(user_id: int) -> Dict[str, Any]:
    """Отримати прогрес челленджа користувача"""
    session = get_user_session(user_id)
    challenge = get_weekly_challenge()
    
    progress = session.get('challenge_progress', {})
    current_progress = progress.get(challenge['category'], 0)
    
    return {
        'challenge': challenge,
        'current_progress': current_progress,
        'remaining': max(0, challenge['target'] - current_progress),
        'percentage': min(100, int((current_progress / challenge['target']) * 100)),
        'completed': current_progress >= challenge['target'],
        'reward': challenge['reward'] if current_progress >= challenge['target'] else 0,
    }


# ============================================================================
# Реферальна система
# ============================================================================

def get_referral_link(user_id: int) -> str:
    """Отримати реферальне посилання"""
    # Простий формат: t.me/ferrikfoot_bot?ref=user_id
    return f"https://t.me/ferrikfoot_bot?start=ref_{user_id}"


def apply_referral(referrer_id: int, new_user_id: int) -> Dict[str, Any]:
    """Застосувати реферальний бонус"""
    # Обидва отримують бонус
    referrer_session = get_user_session(referrer_id)
    new_session = get_user_session(new_user_id)
    
    referrer_bonus = 100
    new_user_bonus = 100
    
    update_user_session(referrer_id, {
        'bonus_points': referrer_session.get('bonus_points', 0) + referrer_bonus,
        'referred_users': referrer_session.get('referred_users', []) + [new_user_id],
    })
    
    update_user_session(new_user_id, {
        'bonus_points': new_session.get('bonus_points', 0) + new_user_bonus,
        'referred_by': referrer_id,
    })
    
    logger.info(f"✅ Referral applied: {referrer_id} → {new_user_id}")
    
    return {
        'referrer_bonus': referrer_bonus,
        'new_user_bonus': new_user_bonus,
        'total_bonus': referrer_bonus + new_user_bonus,
    }


# ============================================================================
# Очищення застарілих даних
# ============================================================================

def cleanup_expired_sessions(max_age_hours: int = 24 * 30):  # 30 днів
    """Очистити застарілі сесії"""
    try:
        cutoff_date = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
        
        expired = [
            uid for uid, session in _USERS_DATA.items()
            if session.get('last_order_date', '') < cutoff_date and 
            session.get('order_count', 0) == 0
        ]
        
        for uid in expired:
            del _USERS_DATA[uid]
            if uid in _CARTS:
                del _CARTS[uid]
        
        logger.info(f"🧹 Cleaned up {len(expired)} expired sessions")
        return len(expired)
    
    except Exception as e:
        logger.error(f"❌ Error cleaning sessions: {e}")
        return 0


# ============================================================================
# Статистика всієї платформи
# ============================================================================

def get_platform_stats() -> Dict[str, Any]:
    """Отримати глобальну статистику"""
    active_users = len(_USERS_DATA)
    total_orders = sum(u.get('order_count', 0) for u in _USERS_DATA.values())
    total_revenue = sum(u.get('total_spent', 0) for u in _USERS_DATA.values())
    
    return {
        'active_users': active_users,
        'total_orders': total_orders,
        'total_revenue': round(total_revenue, 2),
        'avg_orders_per_user': round(total_orders / max(active_users, 1), 2),
        'avg_revenue_per_user': round(total_revenue / max(active_users, 1), 2),
    }


# ============================================================================
# Тестування
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTING SESSION MANAGER")
    print("=" * 60)
    
    # Тест 1: Створення користувача
    print("\n1️⃣ Створення користувача:")
    session = get_user_session(123)
    print(f"✅ User 123 created: {session['user_id']}")
    
    # Тест 2: Додавання в кошик
    print("\n2️⃣ Додавання в кошик:")
    add_to_cart(123, {'id': '1', 'name': 'Піца', 'price': 120, 'quantity': 2})
    add_to_cart(123, {'id': '2', 'name': 'Cola', 'price': 30, 'quantity': 1})
    cart = get_user_cart(123)
    print(f"✅ Cart items: {len(cart)}")
    
    # Тест 3: Реєстрація замовлення
    print("\n3️⃣ Реєстрація замовлення:")
    result = register_order(123, cart, 270, favorite_item_id='1')
    print(f"✅ Order registered")
    print(f"   Stats: {result['stats']['order_count']} замовлення, {result['stats']['badge_display']}")
    
    # Тест 4: Досягнення
    print("\n4️⃣ Досягнення:")
    for i in range(4):
        result = register_order(123, cart, 270, favorite_item_id='1')
    print(f"✅ Order count: {result['stats']['order_count']}")
    print(f"✅ Badge: {result['stats']['badge_display']}")
    if result.get('new_badge'):
        print(f"🏆 NEW BADGE: {result['new_badge']['emoji']} {result['new_badge']['name']}")
    
    # Тест 5: Реферальна система
    print("\n5️⃣ Реферальна система:")
    referral = apply_referral(123, 456)
    print(f"✅ Referral applied: +{referral['total_bonus']} бонусів обом")
    
    # Тест 6: Статистика
    print("\n6️⃣ Статистика платформи:")
    stats = get_platform_stats()
    print(f"✅ Platform stats:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
