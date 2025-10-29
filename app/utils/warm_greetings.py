"""
🌟 ТЕПЛІ ПРИВІТАННЯ - ПЕРСОНАЛІЗОВАНІ ДЛЯ КОЖНОГО КОРИСТУВАЧА
"""

from datetime import datetime
import random

class WarmGreetings:
    """Персоналізовані вітання для різних типів користувачів"""
    
    # НОВАЧКИ (перший раз)
    FIRST_TIME = {
        'main': """👋 **Вітаю у FerrikFoot!** 🍕

Я **Ferrik** — твій супер-помічник зі смаку 😋

Знаю, ти голодний! Вибери, що бажаєш:

✨ **Порадити страву** за твоїм настроєм
🎁 **Подарую 50 бонусів** на перше замовлення  
📋 **Показати меню** з кращих ресторанів
💬 **Розуміти** твої бажання як людина (не бот)

Чого чекаємо? Зробимо тебе щасливим! 🚀""",
        'buttons': {
            'recommend': '💡 Порадь',
            'menu': '📋 Меню',
            'profile': '⭐ Профіль'
        }
    }
    
    # ПОСТІЙНІ КЛІЄНТИ (2-9 замовлень)
    RETURNING_REGULAR = [
        """Оу, ти повернувся! 👋

Сподіваюсь, попереднє замовлення було смачним? 🍽️

Що сьогодні замовляємо? 😋""",
        
        """Привіт, облудниче! 🎉

Я знав що ти поповториш! 😄
Яку страву сьогодні? 🍕""",
        
        """Ти знов тут! 🌟

Уже скучив за твоїм смаком! 👨‍🍳
Давай щось смачне? 🔥""",
    ]
    
    # VIP (10+ замовлень)
    VIP_REGULAR = [
        """Привіт, **{badge}**! 👑

Ти вже {count} разів замовив! 🍕
Середня оцінка твоїх замовлень: ⭐⭐⭐⭐⭐

Для тебе сьогодні: **{bonus} бонусів** на замовлення! 🎁

Що на меню? 😋""",
        
        """Привіт, моя мегазірка! 🌟

{count} замовлень - це легенда! 🏆
Твої смаки уже легенда в нашій базі 😄

Спеціаль сьогодні: **{bonus} бонусів + -15% на всю піцу!** 🍕""",
    ]
    
    # ДАВНО НЕ БАЧИЛИ (останнього замовлення >30 днів)
    COMEBACK = [
        """Ми сумували за тобою! 💔

Де ти був {days} днів? 😢

Давай повернемось до смачного? 🍕
Для повернення: **+100 бонусів**! 🎁""",
        
        """Ти забув про нас? 😭

{days} днів без замовлень - це боль! 💔
Давай це виправимо? 

Повернися з **{bonus} бонусів**! 🎉""",
    ]
    
    @staticmethod
    def get_greeting_by_order_count(order_count: int, days_since_last: int = None, badge: str = None, bonus: int = 0) -> str:
        """Отримати привітання на основі історії користувача"""
        
        # Новачок
        if order_count == 0:
            return WarmGreetings.FIRST_TIME['main']
        
        # Давно не бачили
        if days_since_last and days_since_last > 30:
            msg = random.choice(WarmGreetings.COMEBACK)
            return msg.format(days=days_since_last, bonus=bonus)
        
        # Постійний
        if 1 <= order_count < 10:
            return random.choice(WarmGreetings.RETURNING_REGULAR)
        
        # VIP
        if order_count >= 10:
            msg = random.choice(WarmGreetings.VIP_REGULAR)
            return msg.format(badge=badge or '👑 Легенда', count=order_count, bonus=bonus)
        
        return "Привіт! 👋 Чого замовляємо? 😋"
    
    @staticmethod
    def get_add_to_cart_reaction(item_name: str, is_favorite: bool = False) -> str:
        """Реакція на додавання товара"""
        reactions = [
            f"✅ {item_name}? Чудовий вибір! 🛒",
            f"🎯 {item_name} додана! Ще щось? 😋",
            f"👌 {item_name} - це буде смачно! 🍕",
            f"🔥 Хіт! {item_name} у тебе! 🔥",
        ]
        
        if is_favorite:
            reactions.append(f"❤️ Ти вже знаєш смак! {item_name} знову? 😄")
        
        return random.choice(reactions)
    
    @staticmethod
    def get_checkout_encouragement() -> str:
        """Мотивація при оформленні"""
        msgs = [
            "🎉 Оформляємо? Буде смачно! 😋",
            "⏭️ Давай скоріше, голод не чекає! 🔥",
            "💨 Курс на доставку? Йдемо! 🚗",
            "🎁 А там ще і бонуси тобі! 💰",
        ]
        return random.choice(msgs)
    
    @staticmethod
    def get_order_success_message(order_id: str, est_time: int = 30) -> str:
        """Повідомлення про успішне замовлення"""
        msgs = [
            f"🎉 ЗАМОВЛЕННЯ #{order_id} ПРИЙНЯТО!\n⏰ Буде за ~{est_time} хв 🚗",
            f"✅ Супер! #{order_id} в дорозі! 🍕\n⏱️ Чекай {est_time} хв",
            f"🚀 Лет! #{order_id} прийнято!\n📍 Будемо за {est_time} хв! 🔔",
        ]
        return random.choice(msgs)


# ============================================================================
# ТЕСТ
# ============================================================================

if __name__ == "__main__":
    print("🧪 Testing warm greetings:\n")
    
    print("1️⃣ Новачок:")
    print(WarmGreetings.get_greeting_by_order_count(0))
    
    print("\n2️⃣ Постійний (5 замовлень):")
    print(WarmGreetings.get_greeting_by_order_count(5))
    
    print("\n3️⃣ VIP (25 замовлень):")
    print(WarmGreetings.get_greeting_by_order_count(25, badge="👑 Легенда", bonus=150))
    
    print("\n4️⃣ Давно не бачили:")
    print(WarmGreetings.get_greeting_by_order_count(10, days_since_last=45, bonus=100))
    
    print("\n5️⃣ Реакції:")
    print(WarmGreetings.get_add_to_cart_reaction("Піца Маргарита", is_favorite=True))
    print(WarmGreetings.get_checkout_encouragement())
    print(WarmGreetings.get_order_success_message("0042"))
