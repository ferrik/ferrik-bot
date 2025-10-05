import logging
from datetime import datetime
from services.database import (
    get_orders_by_status, update_order_status, 
    get_statistics, get_popular_items
)

logger = logging.getLogger("admin_handler")

def is_admin(user_id, operator_chat_id):
    """Перевірка чи користувач - адмін"""
    if not operator_chat_id:
        return False
    return str(user_id) == str(operator_chat_id)

def show_admin_menu(chat_id, send_message_func):
    """Головне меню адміна"""
    text = """
🔧 <b>Панель адміністратора</b>

Оберіть дію:
"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 Статистика", "callback_data": "admin_stats"}],
            [{"text": "📋 Нові замовлення", "callback_data": "admin_orders_new"}],
            [{"text": "🔥 Топ страв", "callback_data": "admin_popular"}],
            [{"text": "🔄 Оновити меню", "callback_data": "admin_reload_menu"}],
            [{"text": "🏠 Головна", "callback_data": "start"}]
        ]
    }
    
    send_message_func(chat_id, text, reply_markup=keyboard)

def show_statistics(chat_id, send_message_func, days=1):
    """Показати статистику"""
    try:
        stats = get_statistics(days)
        
        total_orders = stats.get('total_orders', 0) or 0
        total_revenue = stats.get('total_revenue', 0) or 0
        avg_order = stats.get('avg_order', 0) or 0
        by_status = stats.get('by_status', {})
        
        period_text = "сьогодні" if days == 1 else f"за {days} днів"
        
        text = f"""
📊 <b>Статистика {period_text}</b>

💰 Виручка: <b>{total_revenue:.2f} грн</b>
📦 Замовлень: <b>{total_orders}</b>
💵 Середній чек: <b>{avg_order:.2f} грн</b>

<b>По статусах:</b>
"""
        
        status_emoji = {
            'new': '🆕',
            'cooking': '🍳',
            'ready': '✅',
            'delivering': '🚗',
            'completed': '✔️',
            'cancelled': '❌'
        }
        
        status_names = {
            'new': 'Нові',
            'cooking': 'Готуються',
            'ready': 'Готові',
            'delivering': 'Доставляються',
            'completed': 'Завершені',
            'cancelled': 'Скасовані'
        }
        
        for status, count in by_status.items():
            emoji = status_emoji.get(status, '•')
            name = status_names.get(status, status)
            text += f"{emoji} {name}: {count}\n"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📅 За тиждень", "callback_data": "admin_stats_7"},
                    {"text": "📆 За місяць", "callback_data": "admin_stats_30"}
                ],
                [{"text": "🔙 Назад", "callback_data": "admin_menu"}]
            ]
        }
        
        send_message_func(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Show statistics error: {e}")
        send_message_func(chat_id, "❌ Помилка отримання статистики")

def show_new_orders(chat_id, send_message_func):
    """Показати нові замовлення"""
    try:
        orders = get_orders_by_status('new', limit=10)
        
        if not orders:
            text = "📋 <b>Нові замовлення</b>\n\nНемає нових замовлень"
            keyboard = {"inline_keyboard": [[
                {"text": "🔙 Назад", "callback_data": "admin_menu"}
            ]]}
            send_message_func(chat_id, text, reply_markup=keyboard)
            return
        
        text = f"📋 <b>Нові замовлення ({len(orders)})</b>\n\n"
        
        keyboard = {"inline_keyboard": []}
        
        for order in orders[:5]:  # Показуємо перші 5
            order_id = order['id']
            total = order['total']
            created = order['created_at']
            username = order.get('username', 'Користувач')
            
            # Форматуємо час
            try:
                dt = datetime.fromisoformat(created)
                time_str = dt.strftime("%H:%M")
            except:
                time_str = created[:5]
            
            text += f"🆔 <code>{order_id[-8:]}</code>\n"
            text += f"👤 {username}\n"
            text += f"💰 {total:.2f} грн • 🕐 {time_str}\n\n"
            
            keyboard["inline_keyboard"].append([
                {"text": f"📦 {order_id[-8:]}", "callback_data": f"admin_order_{order_id}"}
            ])
        
        keyboard["inline_keyboard"].append([
            {"text": "🔙 Назад", "callback_data": "admin_menu"}
        ])
        
        send_message_func(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Show new orders error: {e}")
        send_message_func(chat_id, "❌ Помилка отримання замовлень")

def show_order_details(chat_id, order_id, send_message_func, get_order_func):
    """Детальна інформація про замовлення"""
    try:
        order = get_order_func(order_id)
        
        if not order:
            send_message_func(chat_id, "❌ Замовлення не знайдено")
            return
        
        import json
        items = json.loads(order['items'])
        
        text = f"""
📦 <b>Замовлення #{order['id'][-8:]}</b>

👤 Користувач: {order.get('username', 'N/A')}
🆔 ID: <code>{order['user_id']}</code>
📞 Телефон: {order.get('phone', 'N/A')}
📍 Адреса: {order.get('address', 'N/A')}

<b>Страви:</b>
"""
        
        for item in items:
            name = item.get('name', 'N/A')
            price = item.get('price', 0)
            text += f"• {name} - {price} грн\n"
        
        text += f"\n💰 <b>Всього: {order['total']:.2f} грн</b>"
        text += f"\n📅 {order['created_at']}"
        
        if order.get('notes'):
            text += f"\n\n📝 Примітка: {order['notes']}"
        
        status = order['status']
        status_emoji = {
            'new': '🆕 Нове',
            'cooking': '🍳 Готується',
            'ready': '✅ Готове',
            'delivering': '🚗 Доставляється',
            'completed': '✔️ Завершено',
            'cancelled': '❌ Скасовано'
        }
        
        text += f"\n\n📊 Статус: {status_emoji.get(status, status)}"
        
        # Кнопки зміни статусу
        keyboard = {"inline_keyboard": []}
        
        if status == 'new':
            keyboard["inline_keyboard"].append([
                {"text": "🍳 Готується", "callback_data": f"admin_status_{order_id}_cooking"}
            ])
        elif status == 'cooking':
            keyboard["inline_keyboard"].append([
                {"text": "✅ Готове", "callback_data": f"admin_status_{order_id}_ready"}
            ])
        elif status == 'ready':
            keyboard["inline_keyboard"].append([
                {"text": "🚗 Доставляється", "callback_data": f"admin_status_{order_id}_delivering"}
            ])
        elif status == 'delivering':
            keyboard["inline_keyboard"].append([
                {"text": "✔️ Завершено", "callback_data": f"admin_status_{order_id}_completed"}
            ])
        
        if status not in ['completed', 'cancelled']:
            keyboard["inline_keyboard"].append([
                {"text": "❌ Скасувати", "callback_data": f"admin_status_{order_id}_cancelled"}
            ])
        
        keyboard["inline_keyboard"].append([
            {"text": "🔙 До списку", "callback_data": "admin_orders_new"}
        ])
        
        send_message_func(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Show order details error: {e}")
        send_message_func(chat_id, "❌ Помилка відображення замовлення")

def change_order_status(order_id, new_status, update_status_func):
    """Змінити статус замовлення"""
    try:
        success = update_status_func(order_id, new_status)
        
        if success:
            status_names = {
                'cooking': 'Готується',
                'ready': 'Готове',
                'delivering': 'Доставляється',
                'completed': 'Завершено',
                'cancelled': 'Скасовано'
            }
            return f"✅ Статус змінено на: {status_names.get(new_status, new_status)}"
        else:
            return "❌ Помилка зміни статусу"
            
    except Exception as e:
        logger.error(f"Change status error: {e}")
        return "❌ Помилка"

def show_popular_items(chat_id, send_message_func):
    """Топ популярних страв"""
    try:
        popular = get_popular_items(limit=10)
        
        if not popular:
            text = "🔥 <b>Топ страв</b>\n\nНедостатньо даних"
            keyboard = {"inline_keyboard": [[
                {"text": "🔙 Назад", "callback_data": "admin_menu"}
            ]]}
            send_message_func(chat_id, text, reply_markup=keyboard)
            return
        
        text = "🔥 <b>Топ страв за тиждень</b>\n\n"
        
        for i, (name, count) in enumerate(popular, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {count} замовлень\n"
        
        keyboard = {"inline_keyboard": [[
            {"text": "🔙 Назад", "callback_data": "admin_menu"}
        ]]}
        
        send_message_func(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Show popular items error: {e}")
        send_message_func(chat_id, "❌ Помилка отримання даних")

def reload_menu(chat_id, send_message_func, reload_func):
    """Перезавантажити меню"""
    try:
        count = reload_func()
        text = f"✅ Меню оновлено!\n\nЗавантажено: {count} страв"
        
        keyboard = {"inline_keyboard": [[
            {"text": "🔙 Назад", "callback_data": "admin_menu"}
        ]]}
        
        send_message_func(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Reload menu error: {e}")
        send_message_func(chat_id, "❌ Помилка оновлення меню")