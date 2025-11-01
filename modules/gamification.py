"""
🎮 Система гейміфікації для Ferrik Bot
Бейджі, рівні, челенджі, досягнення
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class BadgeType(Enum):
    """Типи бейджів"""
    # Онбординг
    EXPLORER = "explorer"
    FIRST_ORDER = "first_order"
    SHOPPER = "shopper"
    
    # Активність
    REGULAR = "regular"  # 10 замовлень
    FOODIE = "foodie"  # 25 замовлень
    GOURMET = "gourmet"  # 50 замовлень
    LEGEND = "legend"  # 100 замовлень
    
    # Спеціальні
    PIZZA_LOVER = "pizza_lover"  # 10 піц
    SWEET_TOOTH = "sweet_tooth"  # 10 десертів
    HEALTHY = "healthy"  # 10 салатів
    NIGHT_OWL = "night_owl"  # 5 замовлень після 22:00
    EARLY_BIRD = "early_bird"  # 5 замовлень до 9:00
    
    # Соціальні
    REFERRER = "referrer"  # Запросив 3 друзів
    INFLUENCER = "influencer"  # Запросив 10 друзів
    
    # Рейтинг
    REVIEWER = "reviewer"  # 5 відгуків
    CRITIC = "critic"  # 20 відгуків


class Badge:
    """Опис бейджу"""
    
    BADGES = {
        BadgeType.EXPLORER: {
            'name': 'Дослідник смаку',
            'emoji': '🔍',
            'description': 'Переглянув меню вперше',
            'points': 10
        },
        BadgeType.FIRST_ORDER: {
            'name': 'Перше замовлення',
            'emoji': '🎉',
            'description': 'Зробив перше замовлення',
            'points': 50
        },
        BadgeType.SHOPPER: {
            'name': 'Покупець',
            'emoji': '🛒',
            'description': 'Додав товар у кошик',
            'points': 20
        },
        BadgeType.REGULAR: {
            'name': 'Постійний клієнт',
            'emoji': '⭐',
            'description': '10 замовлень',
            'points': 100
        },
        BadgeType.FOODIE: {
            'name': 'Фуді',
            'emoji': '🍽️',
            'description': '25 замовлень',
            'points': 250
        },
        BadgeType.GOURMET: {
            'name': 'Гурман',
            'emoji': '👨‍🍳',
            'description': '50 замовлень',
            'points': 500
        },
        BadgeType.LEGEND: {
            'name': 'Легенда',
            'emoji': '🏆',
            'description': '100 замовлень',
            'points': 1000
        },
        BadgeType.PIZZA_LOVER: {
            'name': 'Любитель піци',
            'emoji': '🍕',
            'description': 'Замовив 10 піц',
            'points': 150
        },
        BadgeType.SWEET_TOOTH: {
            'name': 'Ласунчик',
            'emoji': '🍰',
            'description': 'Замовив 10 десертів',
            'points': 150
        },
        BadgeType.HEALTHY: {
            'name': 'Здоровий стиль',
            'emoji': '🥗',
            'description': 'Замовив 10 салатів',
            'points': 150
        },
        BadgeType.NIGHT_OWL: {
            'name': 'Нічна сова',
            'emoji': '🦉',
            'description': '5 замовлень після 22:00',
            'points': 75
        },
        BadgeType.EARLY_BIRD: {
            'name': 'Рання пташка',
            'emoji': '🐦',
            'description': '5 замовлень до 9:00',
            'points': 75
        },
        BadgeType.REFERRER: {
            'name': 'Друг друзів',
            'emoji': '🤝',
            'description': 'Запросив 3 друзів',
            'points': 200
        },
        BadgeType.INFLUENCER: {
            'name': 'Інфлюенсер',
            'emoji': '📱',
            'description': 'Запросив 10 друзів',
            'points': 500
        },
        BadgeType.REVIEWER: {
            'name': 'Рецензент',
            'emoji': '📝',
            'description': 'Залишив 5 відгуків',
            'points': 100
        },
        BadgeType.CRITIC: {
            'name': 'Критик',
            'emoji': '🎭',
            'description': 'Залишив 20 відгуків',
            'points': 300
        }
    }
    
    @staticmethod
    def get_badge_info(badge_type: BadgeType) -> Dict:
        """Отримує інформацію про бейдж"""
        return Badge.BADGES.get(badge_type, {})
    
    @staticmethod
    def format_badge(badge_type: BadgeType) -> str:
        """Форматує бейдж для відображення"""
        info = Badge.get_badge_info(badge_type)
        return f"{info['emoji']} **{info['name']}**"


class UserLevel:
    """Система рівнів користувача"""
    
    # Досвід для кожного рівня
    LEVELS = {
        1: {'xp': 0, 'title': 'Новачок', 'emoji': '🌱'},
        2: {'xp': 100, 'title': 'Аматор', 'emoji': '🌿'},
        3: {'xp': 300, 'title': 'Любитель', 'emoji': '🍀'},
        4: {'xp': 600, 'title': 'Фуді', 'emoji': '🌳'},
        5: {'xp': 1000, 'title': 'Ентузіаст', 'emoji': '⭐'},
        6: {'xp': 1500, 'title': 'Експерт', 'emoji': '💎'},
        7: {'xp': 2200, 'title': 'Майстер', 'emoji': '👑'},
        8: {'xp': 3000, 'title': 'Гурман', 'emoji': '🏆'},
        9: {'xp': 4000, 'title': 'Магістр смаку', 'emoji': '🌟'},
        10: {'xp': 5500, 'title': 'Легенда', 'emoji': '✨'}
    }
    
    @staticmethod
    def calculate_level(total_xp: int) -> Dict:
        """Розраховує рівень на основі XP"""
        current_level = 1
        for level, data in sorted(UserLevel.LEVELS.items(), reverse=True):
            if total_xp >= data['xp']:
                current_level = level
                break
        
        level_data = UserLevel.LEVELS[current_level]
        next_level = current_level + 1
        
        if next_level in UserLevel.LEVELS:
            next_level_data = UserLevel.LEVELS[next_level]
            xp_to_next = next_level_data['xp'] - total_xp
            progress = (total_xp - level_data['xp']) / (next_level_data['xp'] - level_data['xp'])
        else:
            xp_to_next = 0
            progress = 1.0
        
        return {
            'level': current_level,
            'title': level_data['title'],
            'emoji': level_data['emoji'],
            'current_xp': total_xp,
            'xp_to_next': xp_to_next,
            'progress': progress
        }
    
    @staticmethod
    def format_level(level_data: Dict) -> str:
        """Форматує рівень для відображення"""
        level = level_data['level']
        title = level_data['title']
        emoji = level_data['emoji']
        current_xp = level_data['current_xp']
        xp_to_next = level_data['xp_to_next']
        progress = level_data['progress']
        
        # Прогрес-бар
        bar_length = 10
        filled = int(progress * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        result = f"{emoji} **Рівень {level}: {title}**\n"
        result += f"⭐ XP: {current_xp}\n"
        
        if xp_to_next > 0:
            result += f"📊 {bar} {int(progress * 100)}%\n"
            result += f"🎯 До наступного рівня: {xp_to_next} XP\n"
        else:
            result += "🏆 Максимальний рівень досягнуто!\n"
        
        return result


class Challenge:
    """Тижневі челенджі"""
    
    CHALLENGES = [
        {
            'id': 'variety',
            'name': 'Різноманітність',
            'description': 'Замов страви з 3 різних категорій',
            'emoji': '🎨',
            'reward_xp': 100,
            'reward_discount': 5,
            'duration_days': 7
        },
        {
            'id': 'breakfast_week',
            'name': 'Тиждень сніданків',
            'description': 'Замов 3 сніданки за тиждень',
            'emoji': '🍳',
            'reward_xp': 120,
            'reward_discount': 10,
            'duration_days': 7
        },
        {
            'id': 'weekend_feast',
            'name': 'Вихідний пір',
            'description': 'Зроби 2 замовлення у вихідні',
            'emoji': '🎉',
            'reward_xp': 80,
            'reward_discount': 7,
            'duration_days': 7
        },
        {
            'id': 'healthy_week',
            'name': 'Здорове тиждень',
            'description': 'Замов 3 салати за тиждень',
            'emoji': '🥗',
            'reward_xp': 100,
            'reward_discount': 8,
            'duration_days': 7
        },
        {
            'id': 'early_bird',
            'name': 'Рання пташка',
            'description': 'Замов до 10:00 три рази',
            'emoji': '🌅',
            'reward_xp': 90,
            'reward_discount': 5,
            'duration_days': 7
        }
    ]
    
    @staticmethod
    def get_weekly_challenge() -> Dict:
        """Повертає поточний тижневий челендж"""
        import random
        # В реальності вибирається на основі тижня року
        return random.choice(Challenge.CHALLENGES)
    
    @staticmethod
    def format_challenge(challenge: Dict, progress: int = 0, goal: int = 3) -> str:
        """Форматує челендж для відображення"""
        name = challenge['name']
        description = challenge['description']
        emoji = challenge['emoji']
        reward_xp = challenge['reward_xp']
        reward_discount = challenge['reward_discount']
        
        # Прогрес
        percentage = min(100, int(progress / goal * 100))
        bar_length = 10
        filled = int(percentage / 10)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        result = f"{emoji} **{name}**\n"
        result += f"_{description}_\n\n"
        result += f"📊 Прогрес: {bar} {progress}/{goal}\n"
        result += f"🎁 Винагорода: {reward_xp} XP + {reward_discount}% знижка\n"
        
        if progress >= goal:
            result += "\n✅ **Челендж завершено!**"
        
        return result


class GamificationManager:
    """Менеджер гейміфікації"""
    
    @staticmethod
    def award_badge(user_id: int, badge_type: BadgeType) -> Dict:
        """Видає бейдж користувачу"""
        badge_info = Badge.get_badge_info(badge_type)
        
        # Логування
        logger.info(f"Awarding badge {badge_type.value} to user {user_id}")
        
        # Повертаємо дані для збереження в БД
        return {
            'user_id': user_id,
            'badge_type': badge_type.value,
            'awarded_at': datetime.now().isoformat(),
            'xp_bonus': badge_info.get('points', 0)
        }
    
    @staticmethod
    def check_badge_eligibility(user_stats: Dict) -> List[BadgeType]:
        """Перевіряє, які бейджі користувач може отримати"""
        earned_badges = []
        
        total_orders = user_stats.get('total_orders', 0)
        pizza_orders = user_stats.get('pizza_orders', 0)
        dessert_orders = user_stats.get('dessert_orders', 0)
        salad_orders = user_stats.get('salad_orders', 0)
        night_orders = user_stats.get('night_orders', 0)
        morning_orders = user_stats.get('morning_orders', 0)
        referrals = user_stats.get('referrals', 0)
        reviews = user_stats.get('reviews', 0)
        
        # Перевірка на основі статистики
        if total_orders >= 10:
            earned_badges.append(BadgeType.REGULAR)
        if total_orders >= 25:
            earned_badges.append(BadgeType.FOODIE)
        if total_orders >= 50:
            earned_badges.append(BadgeType.GOURMET)
        if total_orders >= 100:
            earned_badges.append(BadgeType.LEGEND)
        
        if pizza_orders >= 10:
            earned_badges.append(BadgeType.PIZZA_LOVER)
        if dessert_orders >= 10:
            earned_badges.append(BadgeType.SWEET_TOOTH)
        if salad_orders >= 10:
            earned_badges.append(BadgeType.HEALTHY)
        
        if night_orders >= 5:
            earned_badges.append(BadgeType.NIGHT_OWL)
        if morning_orders >= 5:
            earned_badges.append(BadgeType.EARLY_BIRD)
        
        if referrals >= 3:
            earned_badges.append(BadgeType.REFERRER)
        if referrals >= 10:
            earned_badges.append(BadgeType.INFLUENCER)
        
        if reviews >= 5:
            earned_badges.append(BadgeType.REVIEWER)
        if reviews >= 20:
            earned_badges.append(BadgeType.CRITIC)
        
        return earned_badges
    
    @staticmethod
    def format_profile(user_data: Dict) -> str:
        """Форматує профіль користувача з досягненнями"""
        name = user_data.get('name', 'Користувач')
        total_xp = user_data.get('total_xp', 0)
        badges = user_data.get('badges', [])
        total_orders = user_data.get('total_orders', 0)
        total_spent = user_data.get('total_spent', 0)
        
        # Рівень
        level_data = UserLevel.calculate_level(total_xp)
        
        result = f"👤 **Профіль: {name}**\n\n"
        result += UserLevel.format_level(level_data)
        result += "\n"
        
        result += "📊 **Статистика:**\n"
        result += f"🛍️ Замовлень: {total_orders}\n"
        result += f"💰 Витрачено: {total_spent} грн\n"
        result += f"🏆 Бейджів: {len(badges)}\n\n"
        
        if badges:
            result += "🏅 **Досягнення:**\n"
            for badge_type_str in badges[:5]:  # Показуємо перші 5
                try:
                    badge_type = BadgeType(badge_type_str)
                    result += Badge.format_badge(badge_type) + "\n"
                except:
                    continue
            
            if len(badges) > 5:
                result += f"\n_...та ще {len(badges) - 5} бейджів_\n"
        
        return result


# ============================================================================
# Тестування
# ============================================================================
if __name__ == "__main__":
    print("=== Система гейміфікації ===\n")
    
    # Тест рівнів
    for xp in [0, 150, 500, 1200, 3500]:
        print(f"\n--- XP: {xp} ---")
        level_data = UserLevel.calculate_level(xp)
        print(UserLevel.format_level(level_data))
    
    # Тест челенджу
    print("\n\n=== Тижневий челендж ===")
    challenge = Challenge.get_weekly_challenge()
    print(Challenge.format_challenge(challenge, progress=2, goal=3))
    
    # Тест профілю
    print("\n\n=== Профіль користувача ===")
    user_data = {
        'name': 'Олександр',
        'total_xp': 1250,
        'badges': ['first_order', 'regular', 'pizza_lover'],
        'total_orders': 15,
        'total_spent': 4500
    }
    print(GamificationManager.format_profile(user_data))
