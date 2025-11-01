"""
🏆 Gamification - Бейджі, рівні, досягнення
"""
from datetime import datetime, timedelta
from typing import Dict, List

EMOJI = {
    'seedling': '🌱',
    'fork': '🍴',
    'chef': '👨‍🍳',
    'star': '⭐',
    'crown': '👑',
    'fire': '🔥',
    'trophy': '🏆',
    'medal': '🥇',
    'gift': '🎁',
    'rocket': '🚀'
}

class GamificationSystem:
    """Система досягнень та бейджів"""
    
    LEVELS = [
        {'name': 'Новачок', 'emoji': EMOJI['seedling'], 'orders': 0},
        {'name': 'Любитель', 'emoji': EMOJI['fork'], 'orders': 3},
        {'name': 'Гурман', 'emoji': EMOJI['chef'], 'orders': 7},
        {'name': 'Майстер', 'emoji': EMOJI['star'], 'orders': 15},
        {'name': 'Легенда', 'emoji': EMOJI['crown'], 'orders': 30},
    ]
    
    BADGES = {
        'first_order': {
            'name': 'Перші кроки',
            'emoji': '🎯',
            'description': 'Перше замовлення',
            'condition': lambda stats: stats['total_orders'] >= 1
        },
        'early_bird': {
            'name': 'Рання пташка',
            'emoji': '🌅',
            'description': 'Замовлення до 9 ранку',
            'condition': lambda stats: stats['early_orders'] >= 1
        },
        'night_owl': {
            'name': 'Нічний філін',
            'emoji': '🦉',
            'description': 'Замовлення після 22:00',
            'condition': lambda stats: stats['late_orders'] >= 1
        },
        'pizza_lover': {
            'name': 'Любитель піци',
            'emoji': '🍕',
            'description': '10 піц замовлено',
            'condition': lambda stats: stats.get('pizza_count', 0) >= 10
        },
        'big_spender': {
            'name': 'Великий споживач',
            'emoji': '💎',
            'description': 'Сума замовлень >5000 грн',
            'condition': lambda stats: stats['total_spent'] >= 5000
        },
        'loyal': {
            'name': 'Вірний друг',
            'emoji': '❤️',
            'description': '30 замовлень',
            'condition': lambda stats: stats['total_orders'] >= 30
        },
        'speed_demon': {
            'name': 'Швидкісний',
            'emoji': '⚡',
            'description': 'Замовлення за <2 хвилини',
            'condition': lambda stats: stats.get('fast_orders', 0) >= 5
        },
        'variety_seeker': {
            'name': 'Шукач різноманітності',
            'emoji': '🌈',
            'description': 'Замовлено >20 різних страв',
            'condition': lambda stats: stats.get('unique_items', 0) >= 20
        }
    }
    
    def __init__(self, db):
        self.db = db
    
    def get_user_level(self, user_id: int) -> Dict:
        """Отримати рівень користувача"""
        orders = self.db.get_user_orders(user_id)
        order_count = len(orders)
        
        # Знаходимо поточний рівень
        current_level = self.LEVELS[0]
        for level in self.LEVELS:
            if order_count >= level['orders']:
                current_level = level
            else:
                break
        
        # Наступний рівень
        current_idx = self.LEVELS.index(current_level)
        next_level = None
        if current_idx < len(self.LEVELS) - 1:
            next_level = self.LEVELS[current_idx + 1]
        
        return {
            'level': current_level['name'],
            'emoji': current_level['emoji'],
            'orders': order_count,
            'next_level': next_level['name'] if next_level else None,
            'orders_to_next': next_level['orders'] - order_count if next_level else 0
        }
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Статистика користувача"""
        orders = self.db.get_user_orders(user_id)
        
        stats = {
            'total_orders': len(orders),
            'total_spent': sum(o.get('total_amount', 0) for o in orders),
            'early_orders': 0,
            'late_orders': 0,
            'pizza_count': 0,
            'unique_items': set(),
            'fast_orders': 0
        }
        
        for order in orders:
            # Час замовлення
            timestamp = order.get('created_at')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                hour = timestamp.hour
                
                if hour < 9:
                    stats['early_orders'] += 1
                if hour >= 22:
                    stats['late_orders'] += 1
            
            # Піци
            items = order.get('items_json', [])
            if isinstance(items, str):
                import json
                items = json.loads(items)
            
            for item in items:
                name = item.get('name', '').lower()
                if 'піца' in name:
                    stats['pizza_count'] += 1
                
                stats['unique_items'].add(item.get('item_id'))
        
        stats['unique_items'] = len(stats['unique_items'])
        
        return stats
    
    def get_earned_badges(self, user_id: int) -> List[Dict]:
        """Отримані бейджі"""
        stats = self.get_user_stats(user_id)
        
        earned = []
        for badge_id, badge in self.BADGES.items():
            if badge['condition'](stats):
                earned.append({
                    'id': badge_id,
                    'name': badge['name'],
                    'emoji': badge['emoji'],
                    'description': badge['description']
                })
        
        return earned
    
    def get_available_badges(self, user_id: int) -> List[Dict]:
        """Доступні для отримання бейджі"""
        stats = self.get_user_stats(user_id)
        
        available = []
        for badge_id, badge in self.BADGES.items():
            if not badge['condition'](stats):
                available.append({
                    'id': badge_id,
                    'name': badge['name'],
                    'emoji': badge['emoji'],
                    'description': badge['description']
                })
        
        return available
    
    def check_new_achievements(self, user_id: int, prev_stats: Dict) -> List[Dict]:
        """Перевірка нових досягнень"""
        new_achievements = []
        
        current_stats = self.get_user_stats(user_id)
        
        for badge_id, badge in self.BADGES.items():
            was_earned = badge['condition'](prev_stats)
            is_earned = badge['condition'](current_stats)
            
            if not was_earned and is_earned:
                new_achievements.append({
                    'id': badge_id,
                    'name': badge['name'],
                    'emoji': badge['emoji'],
                    'description': badge['description']
                })
        
        return new_achievements
    
    def get_profile_summary(self, user_id: int) -> str:
        """Форматований профіль користувача"""
        level = self.get_user_level(user_id)
        stats = self.get_user_stats(user_id)
        badges = self.get_earned_badges(user_id)
        
        text = f"""
{level['emoji']} <b>Рівень: {level['level']}</b>

📊 <b>Статистика:</b>
• Замовлень: {stats['total_orders']}
• Витрачено: {stats['total_spent']:.0f} грн
• Унікальних страв: {stats['unique_items']}

🏆 <b>Бейджі ({len(badges)}):</b>
"""
        
        for badge in badges:
            text += f"{badge['emoji']} {badge['name']}\n"
        
        if level['next_level']:
            text += f"\n🎯 До рівня <b>{level['next_level']}</b>: "
            text += f"ще {level['orders_to_next']} замовлень"
        
        return text
    
    def get_daily_challenge(self) -> Dict:
        """Щоденний челендж"""
        challenges = [
            {
                'title': 'Спробуй щось нове',
                'description': 'Замов страву, яку ще не пробував',
                'reward': '10% знижка',
                'emoji': '🌟'
            },
            {
                'title': 'Комбо майстер',
                'description': 'Замов 3 різні страви за раз',
                'reward': 'Безкоштовний десерт',
                'emoji': '🎁'
            },
            {
                'title': 'Рання пташка',
                'description': 'Замов сніданок до 10:00',
                'reward': 'Безкоштовна кава',
                'emoji': '☕'
            },
            {
                'title': 'Поділись з другом',
                'description': 'Запроси друга в Ferrik',
                'reward': '50 грн на рахунок',
                'emoji': '👥'
            }
        ]
        
        # Вибираємо по дню тижня
        day = datetime.now().weekday()
        return challenges[day % len(challenges)]
