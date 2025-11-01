"""
🤝 Реферальна програма Ferrik Bot
"""
import hashlib
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ReferralSystem:
    """Система рефералів"""
    
    # Винагороди
    REWARDS = {
        'referrer': {
            'bonus_per_friend': 50,  # Бали за кожного друга
            'discount_per_friend': 5,  # % знижки
            'first_friend_bonus': 100  # Додатковий бонус за першого друга
        },
        'referee': {
            'welcome_bonus': 30,  # Бали за реєстрацію по реферальному коду
            'welcome_discount': 10,  # % знижки на перше замовлення
            'promo_valid_days': 14  # Дні дії промокоду
        }
    }
    
    @staticmethod
    def generate_referral_code(user_id: int) -> str:
        """
        Генерує унікальний реферальний код для користувача
        
        Формат: FERRIK_XXXXXX
        """
        # Створюємо хеш на основі user_id
        hash_input = f"ferrik_{user_id}_{datetime.now().year}"
        hash_obj = hashlib.sha256(hash_input.encode())
        hash_hex = hash_obj.hexdigest()[:6].upper()
        
        return f"FERRIK_{hash_hex}"
    
    @staticmethod
    def validate_referral_code(code: str) -> bool:
        """Перевіряє валідність реферального коду"""
        if not code:
            return False
        
        # Базова валідація формату
        if not code.startswith('FERRIK_'):
            return False
        
        if len(code) != 13:  # FERRIK_ + 6 символів
            return False
        
        return True
    
    @staticmethod
    def get_referral_info(user_id: int, referrals_count: int = 0) -> Dict:
        """Повертає інформацію про реферальну програму користувача"""
        code = ReferralSystem.generate_referral_code(user_id)
        
        # Розраховуємо винагороди
        total_bonus = referrals_count * ReferralSystem.REWARDS['referrer']['bonus_per_friend']
        if referrals_count > 0:
            total_bonus += ReferralSystem.REWARDS['referrer']['first_friend_bonus']
        
        total_discount = min(25, referrals_count * ReferralSystem.REWARDS['referrer']['discount_per_friend'])
        
        return {
            'code': code,
            'referrals_count': referrals_count,
            'total_bonus': total_bonus,
            'total_discount': total_discount,
            'potential_next_bonus': ReferralSystem.REWARDS['referrer']['bonus_per_friend']
        }
    
    @staticmethod
    def format_referral_message(referral_info: Dict, user_name: str = None) -> str:
        """Форматує повідомлення про реферальну програму"""
        code = referral_info['code']
        referrals_count = referral_info['referrals_count']
        total_bonus = referral_info['total_bonus']
        total_discount = referral_info['total_discount']
        next_bonus = referral_info['potential_next_bonus']
        
        result = "🎁 **Реферальна програма Ferrik**\n\n"
        
        if user_name:
            result += f"Привіт, {user_name}! "
        
        result += "Запрошуй друзів і отримуй бонуси! 🤗\n\n"
        
        result += f"🔑 **Твій реферальний код:**\n"
        result += f"`{code}`\n\n"
        
        result += "💡 **Як це працює:**\n"
        result += "1️⃣ Поділись своїм кодом з друзями\n"
        result += "2️⃣ Друг вводить код при реєстрації\n"
        result += "3️⃣ Ви обидва отримуєте бонуси!\n\n"
        
        result += "🎁 **Винагороди:**\n"
        result += f"• Ти отримуєш: **{next_bonus} балів** + **5% знижка**\n"
        result += f"• Твій друг отримує: **30 балів** + **10% знижка**\n\n"
        
        if referrals_count > 0:
            result += "📊 **Твоя статистика:**\n"
            result += f"👥 Запрошених друзів: **{referrals_count}**\n"
            result += f"⭐ Зароблено балів: **{total_bonus}**\n"
            result += f"💰 Активна знижка: **{total_discount}%**\n\n"
        
        result += "💬 Поділитись кодом: /share_referral"
        
        return result
    
    @staticmethod
    def create_share_message(code: str, user_name: str = None) -> str:
        """Створює повідомлення для шерінгу"""
        sender = user_name if user_name else "Твій друг"
        
        message = f"🍴 {sender} запрошує тебе в Ferrik!\n\n"
        message += "Ferrik — це найкращий спосіб замовити смачну їжу з доставкою! 🚀\n\n"
        message += "🎁 **Використай мій код і отримай:**\n"
        message += "• 30 бонусних балів\n"
        message += "• 10% знижки на перше замовлення\n"
        message += "• Безкоштовну доставку*\n\n"
        message += f"🔑 Код: `{code}`\n\n"
        message += "👉 Натисни: @FerrikBot і введи код при реєстрації!\n\n"
        message += "_*Умови акції на сайті_"
        
        return message
    
    @staticmethod
    def create_referral_keyboard(code: str) -> Dict:
        """Створює клавіатуру для реферальної програми"""
        share_url = f"https://t.me/share/url?url=https://t.me/FerrikBot?start={code}&text=Приєднуйся до Ferrik! Використай мій код {code} і отримай знижку!"
        
        return {
            'inline_keyboard': [
                [
                    {'text': '📤 Поділитись кодом', 'url': share_url}
                ],
                [
                    {'text': '📋 Копіювати код', 'callback_data': f'copy_{code}'},
                    {'text': '📊 Моя статистика', 'callback_data': 'ref_stats'}
                ],
                [
                    {'text': '💡 Як це працює?', 'callback_data': 'ref_help'},
                    {'text': '🏠 Головна', 'callback_data': 'main_menu'}
                ]
            ]
        }
    
    @staticmethod
    def apply_referral_bonus(referrer_id: int, referee_id: int) -> Dict:
        """
        Застосовує бонуси для обох учасників
        
        Returns:
            Dict з інформацією про винагороди
        """
        # Визначаємо, чи це перший реферал
        # (В реальності перевіряємо в БД)
        is_first_referral = True  # Placeholder
        
        # Бонуси для реферера
        referrer_bonus = ReferralSystem.REWARDS['referrer']['bonus_per_friend']
        if is_first_referral:
            referrer_bonus += ReferralSystem.REWARDS['referrer']['first_friend_bonus']
        
        referrer_discount = ReferralSystem.REWARDS['referrer']['discount_per_friend']
        
        # Бонуси для реферала
        referee_bonus = ReferralSystem.REWARDS['referee']['welcome_bonus']
        referee_discount = ReferralSystem.REWARDS['referee']['welcome_discount']
        
        return {
            'referrer': {
                'user_id': referrer_id,
                'bonus_points': referrer_bonus,
                'discount_percent': referrer_discount,
                'is_first': is_first_referral
            },
            'referee': {
                'user_id': referee_id,
                'bonus_points': referee_bonus,
                'discount_percent': referee_discount,
                'promo_code': f'WELCOME{referee_id}'
            }
        }
    
    @staticmethod
    def format_bonus_notification(bonus_data: Dict, user_type: str) -> str:
        """Форматує повідомлення про отриману винагороду"""
        if user_type == 'referrer':
            bonus_points = bonus_data['bonus_points']
            discount = bonus_data['discount_percent']
            is_first = bonus_data.get('is_first', False)
            
            result = "🎉 **Вітаємо! Твій друг приєднався до Ferrik!**\n\n"
            result += "🎁 Ти отримуєш:\n"
            result += f"• **+{bonus_points} балів**\n"
            result += f"• **+{discount}% знижки** на наступне замовлення\n"
            
            if is_first:
                result += "\n✨ Це твій перший реферал — додатковий бонус!\n"
            
            result += "\n💡 Запрошуй більше друзів і збільшуй свої бонуси!"
            
        else:  # referee
            bonus_points = bonus_data['bonus_points']
            discount = bonus_data['discount_percent']
            promo = bonus_data['promo_code']
            
            result = "🎊 **Вітаємо в Ferrik!**\n\n"
            result += "Ти успішно використав реферальний код!\n\n"
            result += "🎁 Твої бонуси:\n"
            result += f"• **{bonus_points} балів** на рахунок\n"
            result += f"• **{discount}% знижка** на перше замовлення\n"
            result += f"• Промокод: `{promo}`\n\n"
            result += "👉 Переглянь меню: /menu"
        
        return result


class ReferralDatabase:
    """Робота з БД для рефералів"""
    
    @staticmethod
    def save_referral(referrer_id: int, referee_id: int, code: str) -> bool:
        """Зберігає зв'язок реферал-реферер"""
        # Псевдокод для збереження в БД
        # INSERT INTO referrals (referrer_id, referee_id, code, created_at)
        logger.info(f"Referral saved: {referrer_id} -> {referee_id} (code: {code})")
        return True
    
    @staticmethod
    def get_referrals_count(user_id: int) -> int:
        """Отримує кількість рефералів користувача"""
        # SELECT COUNT(*) FROM referrals WHERE referrer_id = ?
        return 0  # Placeholder
    
    @staticmethod
    def get_referrer_by_code(code: str) -> Optional[int]:
        """Знаходить користувача за реферальним кодом"""
        # SELECT user_id FROM users WHERE referral_code = ?
        return None  # Placeholder
    
    @staticmethod
    def is_code_used(user_id: int) -> bool:
        """Перевіряє, чи використав користувач реферальний код"""
        # SELECT COUNT(*) FROM referrals WHERE referee_id = ?
        return False  # Placeholder


# ============================================================================
# Тестування
# ============================================================================
if __name__ == "__main__":
    print("=== Реферальна система ===\n")
    
    # Генерація коду
    user_id = 12345
    code = ReferralSystem.generate_referral_code(user_id)
    print(f"Код користувача {user_id}: {code}\n")
    
    # Інформація про реферальну програму
    ref_info = ReferralSystem.get_referral_info(user_id, referrals_count=3)
    print(ReferralSystem.format_referral_message(ref_info, "Олександр"))
    
    print("\n\n=== Повідомлення для шерінгу ===")
    print(ReferralSystem.create_share_message(code, "Марія"))
    
    print("\n\n=== Застосування бонусів ===")
    bonus_data = ReferralSystem.apply_referral_bonus(12345, 67890)
    print("Реферер отримує:")
    print(ReferralSystem.format_bonus_notification(bonus_data['referrer'], 'referrer'))
    print("\n\nРеферал отримує:")
    print(ReferralSystem.format_bonus_notification(bonus_data['referee'], 'referee'))
