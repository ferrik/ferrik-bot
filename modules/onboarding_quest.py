"""
🎮 Онбординг-квест для нових користувачів Ferrik Bot
"""
from enum import Enum
from typing import Dict, Optional
import json

class QuestStage(Enum):
    """Етапи квесту"""
    NOT_STARTED = 0
    CHOOSE_CATEGORY = 1
    ADD_TO_CART = 2
    CHECKOUT = 3
    COMPLETED = 4


class OnboardingQuest:
    """Управління онбординг-квестом"""
    
    # Винагороди за етапи
    REWARDS = {
        QuestStage.CHOOSE_CATEGORY: {'badge': 'explorer', 'points': 10},
        QuestStage.ADD_TO_CART: {'badge': 'shopper', 'points': 20},
        QuestStage.COMPLETED: {'badge': 'first_order', 'points': 50, 'discount': 10}
    }
    
    @staticmethod
    def get_quest_intro():
        """Вступ до квесту"""
        return (
            "🎯 *Смаковий квест для новачків!*\n\n"
            "Давай познайомимося ближче! Пройди 3 прості кроки і отримай:\n\n"
            "✨ Бейдж «Дослідник смаку»\n"
            "🎁 Знижку 10% на перше замовлення\n"
            "⭐ 50 бонусних балів\n\n"
            "Готовий(а) розпочати?"
        )
    
    @staticmethod
    def get_quest_keyboard(stage: QuestStage):
        """Клавіатура залежно від етапу"""
        if stage == QuestStage.NOT_STARTED:
            return {
                'inline_keyboard': [
                    [{'text': '🚀 Розпочати квест!', 'callback_data': 'quest_start'}],
                    [{'text': '⏭️ Пропустити', 'callback_data': 'quest_skip'}]
                ]
            }
        
        elif stage == QuestStage.CHOOSE_CATEGORY:
            return {
                'inline_keyboard': [
                    [
                        {'text': '🍕 Піца', 'callback_data': 'quest_cat_pizza'},
                        {'text': '🍔 Бургери', 'callback_data': 'quest_cat_burgers'}
                    ],
                    [
                        {'text': '🍜 Супи', 'callback_data': 'quest_cat_soups'},
                        {'text': '🥗 Салати', 'callback_data': 'quest_cat_salads'}
                    ],
                    [
                        {'text': '🍰 Десерти', 'callback_data': 'quest_cat_desserts'}
                    ]
                ]
            }
        
        elif stage == QuestStage.ADD_TO_CART:
            return {
                'inline_keyboard': [
                    [{'text': '🛒 Додати в кошик', 'callback_data': 'quest_add_cart'}],
                    [{'text': '👀 Вибрати іншу страву', 'callback_data': 'quest_change_item'}]
                ]
            }
        
        elif stage == QuestStage.CHECKOUT:
            return {
                'inline_keyboard': [
                    [{'text': '✅ Оформити замовлення', 'callback_data': 'quest_checkout'}],
                    [{'text': '📝 Переглянути кошик', 'callback_data': 'view_cart'}]
                ]
            }
        
        return None
    
    @staticmethod
    def get_stage_message(stage: QuestStage, context: Dict = None) -> str:
        """Повідомлення для кожного етапу"""
        messages = {
            QuestStage.CHOOSE_CATEGORY: (
                "🎯 *Крок 1/3: Обери категорію*\n\n"
                "Що тебе найбільше приваблює? Обери одну з категорій:\n\n"
                "💡 Порада: Не хвилюйся, потім зможеш переглянути всі страви!"
            ),
            
            QuestStage.ADD_TO_CART: (
                f"🎯 *Крок 2/3: Додай страву*\n\n"
                f"{'Чудовий вибір! ' if context else ''}"
                f"Тепер просто додай обрану страву в кошик.\n\n"
                f"✨ Ти отримаєш +10 балів за цей крок!"
            ),
            
            QuestStage.CHECKOUT: (
                "🎯 *Крок 3/3: Оформи замовлення*\n\n"
                "Останній крок! Оформи своє перше замовлення.\n\n"
                "🎁 Після завершення ти отримаєш:\n"
                "✅ Бейдж «Перше замовлення»\n"
                "✅ Знижку 10% (вже застосовано!)\n"
                "✅ 50 бонусних балів\n\n"
                "Готовий(а)?"
            ),
            
            QuestStage.COMPLETED: (
                "🎉 *Вітаю! Квест завершено!*\n\n"
                "Ти успішно пройшов(ла) смаковий квест і тепер офіційно є частиною спільноти Ferrik! 🌟\n\n"
                "📊 *Твої досягнення:*\n"
                "🏆 Бейдж «Дослідник смаку»\n"
                "🏆 Бейдж «Перше замовлення»\n"
                "⭐ 50 бонусних балів\n"
                "🎁 Знижка 10% (активна)\n\n"
                "Що далі? Переглянь повне меню або дізнайся про актуальні акції! 😊"
            )
        }
        
        return messages.get(stage, "")
    
    @staticmethod
    def award_completion_badge(user_id: int) -> Dict:
        """Видає винагороду за завершення квесту"""
        return {
            'user_id': user_id,
            'badges': ['explorer', 'shopper', 'first_order'],
            'points': 50,
            'discount': 10,
            'promo_code': f'FIRST{user_id}'
        }
    
    @staticmethod
    def track_progress(user_id: int, stage: QuestStage) -> Dict:
        """Відстежує прогрес користувача"""
        progress = {
            'user_id': user_id,
            'current_stage': stage.value,
            'completed_stages': [],
            'total_points': 0
        }
        
        # Додаємо бали за завершені етапи
        for completed_stage in QuestStage:
            if completed_stage.value <= stage.value and completed_stage in OnboardingQuest.REWARDS:
                progress['completed_stages'].append(completed_stage.name)
                progress['total_points'] += OnboardingQuest.REWARDS[completed_stage]['points']
        
        return progress


class QuestMessages:
    """Текстові повідомлення з емоціями"""
    
    @staticmethod
    def get_encouragement():
        """Підбадьорювальні повідомлення"""
        import random
        messages = [
            "Чудово! Ти впораєшся! 💪",
            "Супер! Так тримати! ✨",
            "Молодець! Майже готово! 🌟",
            "Ого! Ти швидко вчишся! 🚀",
            "Ідеально! Залишився останній крок! 🎯"
        ]
        return random.choice(messages)
    
    @staticmethod
    def get_completion_celebration():
        """Святкове повідомлення"""
        return (
            "🎊🎉🎊🎉🎊\n\n"
            "ВІТАЄМО З ПЕРШИМ ЗАМОВЛЕННЯМ!\n\n"
            "🎊🎉🎊🎉🎊\n\n"
            "Ти тепер офіційно частина родини Ferrik! "
            "Запрошуй друзів і отримуй додаткові бонуси! 🤗"
        )


# ============================================================================
# Інтеграція з базою даних
# ============================================================================
class QuestDatabase:
    """Зберігання прогресу квесту в БД"""
    
    @staticmethod
    def save_progress(user_id: int, stage: QuestStage, data: Dict = None):
        """Зберігає прогрес в БД"""
        # Псевдокод для інтеграції
        progress_data = {
            'user_id': user_id,
            'quest_stage': stage.value,
            'quest_data': json.dumps(data or {}),
            'completed': stage == QuestStage.COMPLETED
        }
        # INSERT або UPDATE в таблицю user_quest_progress
        return progress_data
    
    @staticmethod
    def get_progress(user_id: int) -> Optional[QuestStage]:
        """Отримує поточний етап квесту"""
        # Псевдокод: SELECT quest_stage FROM user_quest_progress WHERE user_id = ?
        # Повертає QuestStage enum
        pass
    
    @staticmethod
    def mark_completed(user_id: int):
        """Позначає квест як завершений"""
        # UPDATE user_quest_progress SET completed = 1, completed_at = NOW()
        pass


# ============================================================================
# Тестування
# ============================================================================
if __name__ == "__main__":
    print("=== Онбординг-квест ===\n")
    
    # Тест всіх етапів
    for stage in QuestStage:
        if stage != QuestStage.NOT_STARTED:
            print(f"\n{'='*50}")
            print(f"ЕТАП: {stage.name}")
            print(f"{'='*50}")
            print(OnboardingQuest.get_stage_message(stage))
            print(f"\n{QuestMessages.get_encouragement()}")
    
    print("\n\n" + "="*50)
    print("COMPLETION!")
    print("="*50)
    print(QuestMessages.get_completion_celebration())
