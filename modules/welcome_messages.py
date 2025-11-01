"""
🎭 Персоналізовані привітання для Ferrik Bot
"""
import random
from datetime import datetime

class WelcomeMessages:
    """Генератор теплих привітань залежно від контексту"""
    
    # Емодзі для різних настроїв
    EMOJI_HAPPY = ["😊", "🤗", "✨", "🌟", "💫"]
    EMOJI_FOOD = ["🍕", "🍔", "🍜", "🥗", "🍰", "🥘", "🌮", "🍱"]
    EMOJI_TIME = {
        'morning': "🌅",
        'day': "☀️",
        'evening': "🌆",
        'night': "🌙"
    }
    
    @staticmethod
    def get_time_period():
        """Визначає частину доби"""
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'day'
        elif 18 <= hour < 23:
            return 'evening'
        else:
            return 'night'
    
    @staticmethod
    def get_greeting_text(user_name: str = None, is_new_user: bool = True) -> str:
        """Генерує персоналізоване привітання"""
        time_period = WelcomeMessages.get_time_period()
        emoji = WelcomeMessages.EMOJI_TIME[time_period]
        food_emoji = random.choice(WelcomeMessages.EMOJI_FOOD)
        happy_emoji = random.choice(WelcomeMessages.EMOJI_HAPPY)
        
        # Вітання для нових користувачів
        if is_new_user:
            greetings = [
                f"{emoji} Вітаю{f', {user_name}' if user_name else ''}! Я — Ferrik, твій особистий помічник у світі смачної їжі {food_emoji}\n\n"
                f"Я знаю секрети найкращих страв міста і допоможу тобі обрати ідеальний обід, вечерю чи перекус!\n\n"
                f"Готовий(а) розпочати смачну подорож? {happy_emoji}",
                
                f"{food_emoji} Привіт{f', {user_name}' if user_name else ''}! Мене звуть Ferrik {happy_emoji}\n\n"
                f"Я тут, щоб зробити твоє життя смачнішим! Я знаю все про їжу в місті — від ранкової кави до пізньої вечері.\n\n"
                f"Давай познайомимось ближче — розкажи, що любиш їсти? 🤔",
                
                f"{emoji} Раді познайомитись{f', {user_name}' if user_name else ''}! {happy_emoji}\n\n"
                f"Я — Ferrik, твій AI-друг, який завжди знає, що замовити {food_emoji}\n\n"
                f"Обіцяю: ніколи не залишу тебе голодним(ою) і завжди підкажу щось смачненьке!"
            ]
        else:
            # Вітання для постійних користувачів
            greetings = [
                f"{emoji} З поверненням{f', {user_name}' if user_name else ''}! {happy_emoji}\n\n"
                f"Скучив(ла) за смачненьким? Я вже підготував для тебе кілька ідей! {food_emoji}",
                
                f"{happy_emoji} Оо, мій улюблений клієнт{f' {user_name}' if user_name else ''} повернувся! {emoji}\n\n"
                f"Що сьогодні замовляємо — щось звичне чи спробуємо щось нове? {food_emoji}",
                
                f"{food_emoji} Привіт, {user_name if user_name else 'друже'}! {happy_emoji}\n\n"
                f"Я вже тут з новими смачними ідеями для тебе! {emoji}"
            ]
        
        return random.choice(greetings)
    
    @staticmethod
    def get_onboarding_keyboard():
        """Клавіатура для онбордингу"""
        return {
            'inline_keyboard': [
                [
                    {'text': '🔍 Підказати страву', 'callback_data': 'recommend'},
                    {'text': '📋 Показати меню', 'callback_data': 'menu'}
                ],
                [
                    {'text': '🎁 Актуальні акції', 'callback_data': 'promo'},
                    {'text': '⭐ Хіти тижня', 'callback_data': 'hits'}
                ],
                [
                    {'text': '🎯 Пройти смаковий квест', 'callback_data': 'quest_start'}
                ]
            ]
        }
    
    @staticmethod
    def get_mood_selection_text():
        """Текст для вибору настрою"""
        return (
            "🎭 Давай підберемо щось під твій настрій!\n\n"
            "Як ти себе почуваєш сьогодні?"
        )
    
    @staticmethod
    def get_mood_keyboard():
        """Клавіатура вибору настрою"""
        return {
            'inline_keyboard': [
                [
                    {'text': '😊 Щасливий(а)', 'callback_data': 'mood_happy'},
                    {'text': '😌 Спокійно', 'callback_data': 'mood_calm'}
                ],
                [
                    {'text': '💪 Енергійно', 'callback_data': 'mood_energetic'},
                    {'text': '🤗 Романтично', 'callback_data': 'mood_romantic'}
                ],
                [
                    {'text': '😋 Просто голодний(а)!', 'callback_data': 'mood_hungry'},
                    {'text': '🤔 Не впевнений(а)', 'callback_data': 'mood_surprise'}
                ]
            ]
        }


# ============================================================================
# Приклади використання
# ============================================================================
if __name__ == "__main__":
    # Тест привітань
    print("=== Нові користувачі ===")
    for i in range(3):
        print(f"\n{i+1}. {WelcomeMessages.get_greeting_text('Олександр', is_new_user=True)}")
    
    print("\n\n=== Постійні користувачі ===")
    for i in range(3):
        print(f"\n{i+1}. {WelcomeMessages.get_greeting_text('Марія', is_new_user=False)}")
    
    print("\n\n=== Вибір настрою ===")
    print(WelcomeMessages.get_mood_selection_text())
