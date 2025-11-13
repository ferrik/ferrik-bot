"""
Warm Greetings - Personalized user greetings and statistics
FerrikBot v3.2
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# Temporary in-memory storage
# TODO: Replace with Google Sheets integration
_user_stats_cache = {}


def get_user_stats(user_id: int) -> Dict:
    """
    Get user statistics
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        dict: User statistics with keys:
            - order_count: Number of completed orders
            - total_spent: Total amount spent (UAH)
            - last_order_date: ISO datetime of last order
            - favorite_category: Most ordered category
            - is_vip: VIP status (5+ orders or 1000+ UAH)
            - registration_date: First interaction date
            - last_login: Last bot interaction
    """
    if user_id in _user_stats_cache:
        stats = _user_stats_cache[user_id]
        # Update last login
        stats['last_login'] = datetime.now().isoformat()
        return stats
    
    # Default stats for new user
    now = datetime.now().isoformat()
    stats = {
        'order_count': 0,
        'total_spent': 0.0,
        'last_order_date': None,
        'favorite_category': None,
        'is_vip': False,
        'registration_date': now,
        'last_login': now
    }
    
    _user_stats_cache[user_id] = stats
    logger.info(f"📊 Created new user stats for {user_id}")
    return stats


def update_user_stats(
    user_id: int, 
    order_total: float, 
    category: str = None,
    items: List[Dict] = None
) -> None:
    """
    Update user statistics after order
    
    Args:
        user_id: Telegram user ID
        order_total: Order amount in UAH
        category: Order category (optional)
        items: List of ordered items (optional)
    """
    stats = get_user_stats(user_id)
    
    # Update order count and spending
    stats['order_count'] += 1
    stats['total_spent'] = round(stats['total_spent'] + order_total, 2)
    stats['last_order_date'] = datetime.now().isoformat()
    
    # Update favorite category
    if category:
        stats['favorite_category'] = category
    
    # Check VIP status
    # VIP criteria: 5+ orders OR 1000+ UAH spent
    if stats['order_count'] >= 5 or stats['total_spent'] >= 1000:
        if not stats['is_vip']:
            logger.info(f"🌟 User {user_id} achieved VIP status!")
        stats['is_vip'] = True
    
    _user_stats_cache[user_id] = stats
    logger.info(
        f"📊 Updated stats for {user_id}: "
        f"{stats['order_count']} orders, "
        f"{stats['total_spent']} UAH"
    )


def get_greeting_for_user(
    user_id: int, 
    username: str = None, 
    first_name: str = None
) -> str:
    """
    Generate personalized greeting based on user stats
    
    Args:
        user_id: Telegram user ID
        username: Telegram username (optional)
        first_name: User's first name (optional)
        
    Returns:
        str: Personalized greeting message
    """
    stats = get_user_stats(user_id)
    
    # Determine display name
    if first_name:
        name = first_name
    elif username:
        name = f"@{username}"
    else:
        name = "друже"
    
    # Get time-based greeting
    hour = datetime.now().hour
    
    if hour < 6:
        time_greeting = "Доброї ночі"
    elif hour < 12:
        time_greeting = "Доброго ранку"
    elif hour < 18:
        time_greeting = "Доброго дня"
    else:
        time_greeting = "Доброго вечора"
    
    # Personalize based on stats
    order_count = stats['order_count']
    
    if order_count == 0:
        # Brand new user
        return (
            f"👋 {time_greeting}, {name}!\n\n"
            f"Радий бачити тебе вперше в FerrikBot! 🍕\n"
            f"Тут ти можеш замовити смачну їжу від наших партнерів."
        )
    
    elif stats['is_vip']:
        # VIP customer
        return (
            f"⭐ {time_greeting}, {name}!\n\n"
            f"З поверненням! Ти наш VIP-клієнт!\n"
            f"📊 Замовлень: {order_count} | "
            f"💰 Витрачено: {stats['total_spent']:.0f} грн"
        )
    
    elif order_count >= 10:
        # Very frequent customer
        return (
            f"🎉 {time_greeting}, {name}!\n\n"
            f"Як завжди радий бачити тебе! Це вже твоє {order_count}-е замовлення! 🏆"
        )
    
    elif order_count >= 5:
        # Frequent customer
        return (
            f"🔥 {time_greeting}, {name}!\n\n"
            f"Радий бачити постійного клієнта! Замовлення #{order_count + 1} чекає!"
        )
    
    elif order_count >= 3:
        # Regular customer
        return (
            f"😊 {time_greeting}, {name}!\n\n"
            f"З поверненням! Рад бачити тебе знову!"
        )
    
    else:
        # New returning customer (1-2 orders)
        return (
            f"👋 {time_greeting}, {name}!\n\n"
            f"Радий, що ти повернувся! Що замовимо сьогодні?"
        )


def get_surprise_message(user_id: int) -> Optional[str]:
    """
    Get special surprise message for milestones
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        str or None: Surprise message if applicable
    """
    stats = get_user_stats(user_id)
    order_count = stats['order_count']
    
    # Milestone messages
    milestones = {
        5: "🎊 Вітаємо! Це твоє 5-е замовлення! Отримай знижку 15% з промокодом LOYAL5",
        10: "🎉 Неймовірно! 10 замовлень! Знижка 20% з промокодом LOYAL10",
        25: "🔥 Легенда! 25 замовлень! Безкоштовна доставка назавжди з промокодом VIP25",
        50: "🏆 Герой! 50 замовлень! Персональний менеджер та VIP підтримка!",
        100: "👑 ЧЕМПІОН! 100 замовлень! Ти частина сім'ї FerrikBot!"
    }
    
    if order_count in milestones:
        return milestones[order_count]
    
    # Check for spending milestones
    total_spent = stats['total_spent']
    
    if total_spent >= 5000 and not stats.get('milestone_5k_shown'):
        stats['milestone_5k_shown'] = True
        return "💎 Ти витратив 5000+ грн! Отримай золотий статус та знижку 25%!"
    
    if total_spent >= 10000 and not stats.get('milestone_10k_shown'):
        stats['milestone_10k_shown'] = True
        return "💎💎 ВАУ! 10000+ грн! Ти наш найкращий клієнт! Знижка 30% назавжди!"
    
    return None


def get_loyalty_tier(user_id: int) -> Dict:
    """
    Get user's loyalty tier information
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        dict: Loyalty tier info with keys:
            - tier: bronze/silver/gold/platinum/diamond
            - discount: Discount percentage
            - next_tier: Next tier name
            - orders_to_next: Orders needed for next tier
    """
    stats = get_user_stats(user_id)
    order_count = stats['order_count']
    
    if order_count >= 50:
        return {
            'tier': 'diamond',
            'emoji': '💎',
            'discount': 30,
            'next_tier': None,
            'orders_to_next': 0
        }
    elif order_count >= 25:
        return {
            'tier': 'platinum',
            'emoji': '⭐',
            'discount': 25,
            'next_tier': 'diamond',
            'orders_to_next': 50 - order_count
        }
    elif order_count >= 10:
        return {
            'tier': 'gold',
            'emoji': '🏆',
            'discount': 20,
            'next_tier': 'platinum',
            'orders_to_next': 25 - order_count
        }
    elif order_count >= 5:
        return {
            'tier': 'silver',
            'emoji': '🥈',
            'discount': 15,
            'next_tier': 'gold',
            'orders_to_next': 10 - order_count
        }
    else:
        return {
            'tier': 'bronze',
            'emoji': '🥉',
            'discount': 5,
            'next_tier': 'silver',
            'orders_to_next': 5 - order_count
        }


def format_user_profile(user_id: int, username: str = None) -> str:
    """
    Format user profile as text message
    
    Args:
        user_id: Telegram user ID
        username: Telegram username
        
    Returns:
        str: Formatted profile message
    """
    stats = get_user_stats(user_id)
    tier = get_loyalty_tier(user_id)
    
    message = f"👤 Профіль користувача\n\n"
    
    if username:
        message += f"📱 @{username}\n"
    
    message += f"🆔 ID: {user_id}\n\n"
    
    # Stats
    message += f"📊 Статистика:\n"
    message += f"▪️ Замовлень: {stats['order_count']}\n"
    message += f"▪️ Витрачено: {stats['total_spent']:.0f} грн\n"
    
    if stats['last_order_date']:
        last_order = datetime.fromisoformat(stats['last_order_date'])
        days_ago = (datetime.now() - last_order).days
        message += f"▪️ Останнє замовлення: {days_ago} днів тому\n"
    
    message += f"\n"
    
    # Loyalty tier
    message += f"{tier['emoji']} Рівень лояльності: {tier['tier'].upper()}\n"
    message += f"💰 Ваша знижка: {tier['discount']}%\n"
    
    if tier['next_tier']:
        message += f"\n"
        message += f"🎯 До наступного рівня ({tier['next_tier']}):\n"
        message += f"   Ще {tier['orders_to_next']} замовлень\n"
    
    # VIP status
    if stats['is_vip']:
        message += f"\n⭐ VIP статус активний"
    
    return message


def reset_user_stats(user_id: int) -> bool:
    """
    Reset user statistics (for GDPR or testing)
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        bool: Success status
    """
    try:
        if user_id in _user_stats_cache:
            del _user_stats_cache[user_id]
        logger.info(f"🗑️ Reset stats for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error resetting stats: {e}")
        return False


def get_all_users_stats() -> List[Dict]:
    """
    Get statistics for all users (admin function)
    
    Returns:
        list: List of user stats dicts
    """
    return [
        {'user_id': user_id, **stats}
        for user_id, stats in _user_stats_cache.items()
    ]


def get_user_count() -> int:
    """
    Get total number of users
    
    Returns:
        int: User count
    """
    return len(_user_stats_cache)


def get_vip_count() -> int:
    """
    Get number of VIP users
    
    Returns:
        int: VIP user count
    """
    return sum(1 for stats in _user_stats_cache.values() if stats.get('is_vip'))


# TODO: Google Sheets integration functions

def sync_stats_to_sheets(user_id: int) -> bool:
    """
    Sync user stats to Google Sheets
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        bool: Success status
    """
    # TODO: Implement Google Sheets integration
    logger.warning("⚠️ Google Sheets sync not implemented yet")
    return False


def load_stats_from_sheets(user_id: int) -> Optional[Dict]:
    """
    Load user stats from Google Sheets
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        dict or None: User stats if found
    """
    # TODO: Implement Google Sheets integration
    logger.warning("⚠️ Google Sheets load not implemented yet")
    return None


# Export all public functions
__all__ = [
    'get_user_stats',
    'update_user_stats',
    'get_greeting_for_user',
    'get_surprise_message',
    'get_loyalty_tier',
    'format_user_profile',
    'reset_user_stats',
    'get_all_users_stats',
    'get_user_count',
    'get_vip_count',
    'sync_stats_to_sheets',
    'load_stats_from_sheets'
]
