"""
📦 Система трекінгу замовлень та сповіщень
"""
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Статуси замовлення"""
    NEW = "new"  # Нове замовлення
    CONFIRMED = "confirmed"  # Підтверджено рестораном
    PREPARING = "preparing"  # Готується
    READY = "ready"  # Готове
    DELIVERING = "delivering"  # Доставляється
    DELIVERED = "delivered"  # Доставлено
    CANCELLED = "cancelled"  # Скасовано
    FAILED = "failed"  # Не вдалося


class OrderTracking:
    """Система відстеження замовлень"""
    
    # Описи статусів з емодзі
    STATUS_INFO = {
        OrderStatus.NEW: {
            'emoji': '🆕',
            'title': 'Нове замовлення',
            'message': 'Твоє замовлення прийнято! Очікуємо підтвердження від ресторану.',
            'estimated_time': 0
        },
        OrderStatus.CONFIRMED: {
            'emoji': '✅',
            'title': 'Підтверджено',
            'message': 'Ресторан підтвердив замовлення і почав готувати!',
            'estimated_time': 5
        },
        OrderStatus.PREPARING: {
            'emoji': '👨‍🍳',
            'title': 'Готується',
            'message': 'Наші шефи готують твоє замовлення з любов\'ю!',
            'estimated_time': 30
        },
        OrderStatus.READY: {
            'emoji': '✨',
            'title': 'Готове',
            'message': 'Замовлення готове! Кур\'єр вже в дорозі до тебе.',
            'estimated_time': 0
        },
        OrderStatus.DELIVERING: {
            'emoji': '🚚',
            'title': 'Доставляється',
            'message': 'Кур\'єр везе твоє замовлення! Очікуй дзвінка.',
            'estimated_time': 30
        },
        OrderStatus.DELIVERED: {
            'emoji': '🎉',
            'title': 'Доставлено',
            'message': 'Замовлення доставлено! Смачного! 😋',
            'estimated_time': 0
        },
        OrderStatus.CANCELLED: {
            'emoji': '❌',
            'title': 'Скасовано',
            'message': 'Замовлення скасовано. Якщо це помилка, зв\'яжись з підтримкою.',
            'estimated_time': 0
        },
        OrderStatus.FAILED: {
            'emoji': '⚠️',
            'title': 'Проблема',
            'message': 'Виникла проблема з замовленням. Наша підтримка зв\'яжеться з тобою.',
            'estimated_time': 0
        }
    }
    
    @staticmethod
    def get_status_progress(status: OrderStatus) -> float:
        """Повертає прогрес виконання замовлення (0-1)"""
        progress_map = {
            OrderStatus.NEW: 0.0,
            OrderStatus.CONFIRMED: 0.2,
            OrderStatus.PREPARING: 0.4,
            OrderStatus.READY: 0.6,
            OrderStatus.DELIVERING: 0.8,
            OrderStatus.DELIVERED: 1.0,
            OrderStatus.CANCELLED: 0.0,
            OrderStatus.FAILED: 0.0
        }
        return progress_map.get(status, 0.0)
    
    @staticmethod
    def format_tracking_info(order: Dict) -> str:
        """
        Форматує інформацію про відстеження замовлення
        
        Args:
            order: Dict з полями: order_number, status, created_at, items, total, address
        """
        order_number = order.get('order_number', 'N/A')
        status = OrderStatus(order.get('status', 'new'))
        created_at = order.get('created_at')
        items = order.get('items', [])
        total = order.get('total', 0)
        address = order.get('address', '')
        
        status_info = OrderTracking.STATUS_INFO[status]
        progress = OrderTracking.get_status_progress(status)
        
        # Заголовок
        result = f"{status_info['emoji']} **{status_info['title']}**\n\n"
        result += f"📋 Замовлення: `#{order_number}`\n"
        
        # Прогрес-бар
        bar_length = 20
        filled = int(progress * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        result += f"📊 {bar} {int(progress * 100)}%\n\n"
        
        # Повідомлення про статус
        result += f"💬 _{status_info['message']}_\n\n"
        
        # Оцінка часу
        if status in [OrderStatus.PREPARING, OrderStatus.DELIVERING]:
            estimated_time = status_info['estimated_time']
            if estimated_time > 0:
                result += f"⏰ Очікуваний час: ~{estimated_time} хв\n\n"
        
        # Інформація про замовлення
        result += "🍽️ **Твоє замовлення:**\n"
        for item in items[:3]:  # Показуємо перші 3
            name = item.get('name', 'Товар')
            qty = item.get('quantity', 1)
            result += f"• {name} x{qty}\n"
        
        if len(items) > 3:
            result += f"• _...та ще {len(items) - 3} позицій_\n"
        
        result += f"\n💰 Сума: **{total} грн**\n"
        
        # Адреса доставки
        if address:
            result += f"📍 Адреса: {address}\n"
        
        # Час замовлення
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            time_str = created_at.strftime("%H:%M, %d.%m.%Y")
            result += f"🕐 Оформлено: {time_str}\n"
        
        return result
    
    @staticmethod
    def create_tracking_keyboard(order: Dict) -> Dict:
        """Створює клавіатуру для трекінгу"""
        status = OrderStatus(order.get('status', 'new'))
        order_number = order.get('order_number')
        
        keyboard = {'inline_keyboard': []}
        
        # Кнопка оновлення статусу
        keyboard['inline_keyboard'].append([
            {'text': '🔄 Оновити статус', 'callback_data': f'track_{order_number}'}
        ])
        
        # Кнопка скасування (тільки для нових та підтверджених)
        if status in [OrderStatus.NEW, OrderStatus.CONFIRMED]:
            keyboard['inline_keyboard'].append([
                {'text': '❌ Скасувати замовлення', 'callback_data': f'cancel_{order_number}'}
            ])
        
        # Кнопка зв'язку з кур'єром (якщо доставляється)
        if status == OrderStatus.DELIVERING:
            keyboard['inline_keyboard'].append([
                {'text': '📞 Зв\'язатись з кур\'єром', 'callback_data': f'call_courier_{order_number}'}
            ])
        
        # Кнопка відгуку (якщо доставлено)
        if status == OrderStatus.DELIVERED:
            keyboard['inline_keyboard'].append([
                {'text': '⭐ Залишити відгук', 'callback_data': f'review_{order_number}'}
            ])
        
        # Додаткові опції
        keyboard['inline_keyboard'].append([
            {'text': '📜 Історія замовлень', 'callback_data': 'order_history'},
            {'text': '💬 Підтримка', 'callback_data': 'support'}
        ])
        
        return keyboard
    
    @staticmethod
    def format_order_history(orders: List[Dict], limit: int = 10) -> str:
        """Форматує історію замовлень"""
        if not orders:
            return (
                "📜 **Історія замовлень**\n\n"
                "У тебе ще немає замовлень.\n"
                "Переглянь меню і зроби перше замовлення! 😊"
            )
        
        result = f"📜 **Історія замовлень** (останні {min(len(orders), limit)})\n\n"
        
        for order in orders[:limit]:
            order_number = order.get('order_number', 'N/A')
            status = OrderStatus(order.get('status', 'new'))
            created_at = order.get('created_at')
            total = order.get('total', 0)
            
            status_info = OrderTracking.STATUS_INFO[status]
            
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            date_str = created_at.strftime("%d.%m.%Y")
            
            result += f"{status_info['emoji']} `#{order_number}`\n"
            result += f"   {date_str} • {total} грн • {status_info['title']}\n\n"
        
        return result
    
    @staticmethod
    def create_history_keyboard(orders: List[Dict]) -> Dict:
        """Створює клавіатуру для історії замовлень"""
        keyboard = {'inline_keyboard': []}
        
        for order in orders[:5]:  # Показуємо останні 5
            order_number = order.get('order_number')
            status = OrderStatus(order.get('status', 'new'))
            status_info = OrderTracking.STATUS_INFO[status]
            
            keyboard['inline_keyboard'].append([
                {
                    'text': f"{status_info['emoji']} #{order_number}",
                    'callback_data': f'track_{order_number}'
                }
            ])
        
        keyboard['inline_keyboard'].append([
            {'text': '🔙 Назад', 'callback_data': 'main_menu'}
        ])
        
        return keyboard


class NotificationManager:
    """Менеджер сповіщень про зміну статусу"""
    
    @staticmethod
    def should_notify(old_status: OrderStatus, new_status: OrderStatus) -> bool:
        """Перевіряє, чи потрібно надсилати сповіщення"""
        # Надсилаємо сповіщення при зміні на важливі статуси
        important_statuses = [
            OrderStatus.CONFIRMED,
            OrderStatus.PREPARING,
            OrderStatus.READY,
            OrderStatus.DELIVERING,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.FAILED
        ]
        return new_status in important_statuses
    
    @staticmethod
    def get_notification_message(order: Dict, new_status: OrderStatus) -> str:
        """Генерує повідомлення про зміну статусу"""
        order_number = order.get('order_number', 'N/A')
        status_info = OrderTracking.STATUS_INFO[new_status]
        
        message = f"🔔 **Оновлення замовлення #{order_number}**\n\n"
        message += f"{status_info['emoji']} **{status_info['title']}**\n\n"
        message += f"{status_info['message']}\n\n"
        
        if new_status == OrderStatus.DELIVERED:
            message += "Дякуємо за замовлення! Сподіваємось, все було смачно! 😊\n"
            message += "Залиш відгук і допоможи іншим з вибором!"
        elif new_status == OrderStatus.CANCELLED:
            message += "Якщо виникли питання, звертайся до підтримки: /support"
        
        return message
    
    @staticmethod
    def schedule_reminder(order_id: int, user_id: int, delay_minutes: int = 30):
        """
        Планує нагадування (для реалізації з Celery або іншим планувальником)
        
        Args:
            order_id: ID замовлення
            user_id: ID користувача
            delay_minutes: Затримка в хвилинах
        """
        # Псевдокод для планування
        # celery.send_task('send_reminder', args=[order_id, user_id], countdown=delay_minutes*60)
        logger.info(f"Scheduled reminder for order {order_id} in {delay_minutes} minutes")


class ReviewSystem:
    """Система відгуків"""
    
    @staticmethod
    def request_review(order: Dict) -> str:
        """Запит на відгук після доставки"""
        order_number = order.get('order_number', 'N/A')
        
        message = f"⭐ **Як тобі замовлення #{order_number}?**\n\n"
        message += "Будемо вдячні за твій відгук — це допомагає нам ставати кращими!\n\n"
        message += "Оціни замовлення від 1 до 5 зірок:"
        
        return message
    
    @staticmethod
    def create_review_keyboard(order_number: str) -> Dict:
        """Клавіатура для оцінки"""
        return {
            'inline_keyboard': [
                [
                    {'text': '⭐⭐⭐⭐⭐', 'callback_data': f'rate_{order_number}_5'},
                    {'text': '⭐⭐⭐⭐', 'callback_data': f'rate_{order_number}_4'}
                ],
                [
                    {'text': '⭐⭐⭐', 'callback_data': f'rate_{order_number}_3'},
                    {'text': '⭐⭐', 'callback_data': f'rate_{order_number}_2'},
                    {'text': '⭐', 'callback_data': f'rate_{order_number}_1'}
                ],
                [
                    {'text': '📝 Залишити коментар', 'callback_data': f'comment_{order_number}'}
                ]
            ]
        }
    
    @staticmethod
    def format_review_thanks(rating: int, order_number: str) -> str:
        """Подяка за відгук"""
        if rating >= 4:
            return (
                f"🎉 Дякуємо за відмінну оцінку!\n\n"
                f"Нам дуже приємно, що тобі сподобалось! 💚\n\n"
                f"Отримуєш +20 бонусних балів за відгук! ⭐"
            )
        elif rating == 3:
            return (
                f"🙏 Дякуємо за відгук!\n\n"
                f"Ми працюємо над покращенням якості сервісу.\n\n"
                f"+10 бонусних балів за відгук! ⭐"
            )
        else:
            return (
                f"😔 Вибач, що не сподобалось...\n\n"
                f"Твоя думка дуже важлива! Напиши, що пішло не так,\n"
                f"і ми обов'язково виправимо. /support\n\n"
                f"+10 бонусних балів за чесність! ⭐"
            )


# ============================================================================
# Тестування
# ============================================================================
if __name__ == "__main__":
    # Тестове замовлення
    test_order = {
        'order_number': '1234',
        'status': 'preparing',
        'created_at': datetime.now() - timedelta(minutes=15),
        'items': [
            {'name': 'Піца "Маргарита"', 'quantity': 2},
            {'name': 'Coca-Cola 0.5л', 'quantity': 1}
        ],
        'total': 395,
        'address': 'вул. Шевченка, 15, кв. 10'
    }
    
    print("=== Трекінг замовлення ===\n")
    print(OrderTracking.format_tracking_info(test_order))
    
    print("\n\n=== Історія замовлень ===")
    test_orders = [
        {**test_order, 'order_number': '1234', 'status': 'delivered'},
        {**test_order, 'order_number': '1235', 'status': 'preparing'},
        {**test_order, 'order_number': '1236', 'status': 'new'}
    ]
    print(OrderTracking.format_order_history(test_orders))
    
    print("\n\n=== Запит відгуку ===")
    print(ReviewSystem.request_review(test_order))
