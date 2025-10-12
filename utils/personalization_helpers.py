"""
Helper functions for personalization UI and formatting
"""
from typing import List, Dict, Any, Optional
from models.user_profile import UserProfile, UserLevel
from models.user_preferences import UserPreferences


def format_user_greeting_message(profile: UserProfile) -> str:
    """Format greeting message with user info"""
    message = f"👋 <b>Привіт, {profile.name}!</b>\n\n"
    
    if profile.level != UserLevel.NOVICE:
        emoji = profile.get_level_emoji()
        level_name = profile.get_level_name()
        message += f"{emoji} <i>Ти вже {level_name}!</i>\n"
        message += f"🎁 <i>+20 бонус-балів</i>\n\n"
    
    if profile.total_orders > 0:
        message += f"<b>Твої замовлення:</b>\n"
        message += f"📊 Всього: <code>{profile.total_orders}</code>\n"
        message += f"💰 Витрачено: <code>{profile.total_spent:.2f} грн</code>\n"
        message += f"🎁 Бонус-балів: <code>{profile.points}</code>\n\n"
    
    return message


def format_level_badge(profile: UserProfile) -> str:
    """Format level badge with emoji and name"""
    emoji = profile.get_level_emoji()
    level_name = profile.get_level_name()
    return f"{emoji} <b>{level_name}</b>"


def format_points_display(profile: UserProfile) -> str:
    """Format points display"""
    return f"🎁 <code>{profile.points} балів</code>"


def format_recommendations_message(recommendations: List[Dict[str, Any]]) -> str:
    """Format recommendations as message"""
    if not recommendations:
        return "📭 Рекомендацій немає"
    
    message = "<b>⭐ Рекомендовані для тебе:</b>\n\n"
    
    for i, item in enumerate(recommendations, 1):
        name = item.get('name', 'Unknown')
        price = item.get('price', 0)
        category = item.get('category', '')
        message += f"{i}. <b>{name}</b>\n"
        message += f"   💰 {price} грн"
        if category:
            message += f" | 📁 {category}"
        message += "\n\n"
    
    return message


def format_quick_reorder_button_text(profile: UserProfile) -> str:
    """Format quick reorder suggestion"""
    if not profile.favorite_dishes:
        return "🍽️ Замовити"
    
    favorite = profile.favorite_dishes[0]
    return f"🍕 {favorite}"


def format_order_history_message(order_history: List[Dict[str, Any]]) -> str:
    """Format order history display"""
    if not order_history:
        return "📭 Історія замовлень порожня"
    
    message = "<b>📜 Твої останні замовлення:</b>\n\n"
    
    for i, order in enumerate(order_history, 1):
        items = order.get('items', [])
        total = order.get('total_amount', 0)
        timestamp = order.get('timestamp', '')
        
        message += f"{i}. <b>Замовлення #{order.get('order_id', 'N/A')}</b>\n"
        message += f"   💰 {total} грн\n"
        
        if items:
            items_text = ", ".join([item if isinstance(item, str) else item.get('name', 'Item') 
                                   for item in items[:3]])
            if len(items) > 3:
                items_text += f" +{len(items)-3}"
            message += f"   🍽️ {items_text}\n"
        
        if timestamp:
            message += f"   📅 {timestamp[:10]}\n"
        
        message += "\n"
    
    return message


def format_reminder_message(profile: UserProfile) -> str:
    """Format reminder message"""
    emoji = profile.get_level_emoji()
    message = f"🔔 <b>Привіт, {profile.name}! {emoji}</b>\n\n"
    
    if profile.favorite_dishes:
        favorite = profile.favorite_dishes[0]
        message += f"Скучив за тобою! 😢\n"
        message += f"Замовити <b>{favorite}</b> як звичайно?\n\n"
    else:
        message += f"Давно не замовляв...\n"
        message += f"Час перекусити? 😋\n\n"
    
    message += f"💡 <i>+10 бонус-балів за замовлення сьогодні!</i>"
    
    return message


def format_level_up_message(profile: UserProfile) -> str:
    """Format level-up achievement message"""
    emoji = profile.get_level_emoji()
    level_name = profile.get_level_name()
    
    message = "🎉 <b>РІВЕНЬ ПІДВИЩЕНО!</b>\n\n"
    message += f"{emoji} <b>Ти тепер {level_name}!</b>\n"
    message += f"📊 Замовлень: <code>{profile.total_orders}</code>\n"
    message += f"💰 Витрачено: <code>{profile.total_spent:.2f} грн</code>\n\n"
    message += "🎁 <b>+50 бонус-балів!</b>"
    
    return message


def format_profile_message(profile: UserProfile, order_history: List[Dict[str, Any]]) -> str:
    """Format complete profile display"""
    emoji = profile.get_level_emoji()
    level_name = profile.get_level_name()
    
    message = f"👤 <b>МІЙ ПРОФІЛЬ</b>\n\n"
    message += f"<b>Ім'я:</b> {profile.name}\n"
    message += f"<b>Рівень:</b> {emoji} {level_name}\n"
    message += f"<b>Бонус-бали:</b> 🎁 <code>{profile.points}</code>\n\n"
    
    message += f"<b>📊 Статистика:</b>\n"
    message += f"• <b>Замовлень:</b> {profile.total_orders}\n"
    message += f"• <b>Витрачено:</b> {profile.total_spent:.2f} грн\n"
    
    if profile.total_orders > 0:
        avg_order = profile.total_spent / profile.total_orders
        message += f"• <b>Середній чек:</b> {avg_order:.2f} грн\n"
    
    if profile.last_order_date:
        from datetime import datetime
        days_ago = (datetime.now() - profile.last_order_date).days
        message += f"• <b>Останнє замовлення:</b> {days_ago} днів тому\n"
    
    if profile.favorite_dishes:
        message += f"\n<b>⭐ Твої улюблені:</b>\n"
        for i, dish in enumerate(profile.favorite_dishes[:5], 1):
            message += f"{i}. {dish}\n"
    
    return message


def format_discount_offer(profile: UserProfile) -> Optional[str]:
    """Format discount offer message"""
    from datetime import datetime
    
    if profile.total_orders < 3:
        return None
    
    if not profile.last_order_date:
        return None
    
    days_since_order = (datetime.now() - profile.last_order_date).days
    
    if days_since_order >= 7:
        discount = 15
    elif days_since_order >= 5:
        discount = 10
    elif days_since_order >= 3:
        discount = 5
    else:
        return None
    
    offer = f"🎁 <b>Спеціальна пропозиція!</b>\n\n"
    offer += f"Тобі припасована знижка <b>{discount}%</b> на наступне замовлення\n"
    offer += f"Поспіш - дійсна <b>24 години</b>! ⏰"
    
    return offer


def create_recommendations_keyboard(recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create inline keyboard for recommendations"""
    keyboard = {
        'inline_keyboard': []
    }
    
    for item in recommendations[:3]:
        item_name = item.get('name', 'Item')
        item_id = item.get('id', 'unknown')
        
        keyboard['inline_keyboard'].append([{
            'text': f"➕ {item_name}",
            'callback_data': f"add_to_cart_{item_id}"
        }])
    
    return keyboard


def create_quick_reorder_keyboard(profile: UserProfile) -> Dict[str, Any]:
    """Create keyboard for quick reorder"""
    keyboard = {
        'inline_keyboard': []
    }
    
    if profile.favorite_dishes:
        favorite = profile.favorite_dishes[0]
        keyboard['inline_keyboard'].append([{
            'text': f"🍕 Замовити {favorite}",
            'callback_data': f"quick_reorder_{favorite}"
        }])
    
    keyboard['inline_keyboard'].append([{
        'text': "📋 Повне меню",
        'callback_data': "show_menu"
    }])
    
    return keyboard


def create_profile_keyboard() -> Dict[str, Any]:
    """Create keyboard for profile menu"""
    return {
        'inline_keyboard': [
            [
                {'text': '📜 Історія', 'callback_data': 'view_history'},
                {'text': '🎁 Бонуси', 'callback_data': 'view_bonuses'}
            ],
            [
                {'text': '⚙️ Налаштування', 'callback_data': 'settings'},
                {'text': '🍽️ Улюблені', 'callback_data': 'view_favorites'}
            ],
            [
                {'text': '🔙 Назад', 'callback_data': 'back_to_menu'}
            ]
        ]
    }


def get_emoji_for_category(category: str) -> str:
    """Get emoji for food category"""
    emoji_map = {
        'pizza': '🍕',
        'піца': '🍕',
        'burger': '🍔',
        'бургер': '🍔',
        'salad': '🥗',
        'салат': '🥗',
        'soup': '🍲',
        'суп': '🍲',
        'sushi': '🍣',
        'суші': '🍣',
        'dessert': '🍰',
        'десерт': '🍰',
        'drink': '🥤',
        'напій': '🥤',
        'coffee': '☕',
        'кава': '☕'
    }
    
    for key, emoji in emoji_map.items():
        if key.lower() in category.lower():
            return emoji
    
    return '🍽️'