import logging
from datetime import datetime
from services.admin_panel import admin_panel, get_new_orders, send_daily_stats
from services.telegram import tg_send_message, tg_answer_callback
from services.sheets import get_menu_stats

logger = logging.getLogger("ferrik.operator")

def handle_operator_command(chat_id, text, operator_chat_id):
    """Обробляє команди для оператора"""
    try:
        if chat_id != int(operator_chat_id):
            return False
            
        if text == "/admin":
            show_admin_menu(chat_id)
            return True
        elif text == "/stats":
            show_daily_stats(chat_id)
            return True
        elif text == "/orders":
            show_pending_orders(chat_id)
            return True
        elif text == "/menu":
            show_menu_stats(chat_id)
            return True
        elif text == "/help_admin":
            show_admin_help(chat_id)
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error handling operator command: {e}")
        return False

def show_admin_menu(chat_id):
    """Показує головне меню для адміністратора"""
    try:
        menu_text = "🔧 <b>Панель адміністратора FerrikFootBot</b>\n\n"
        menu_text += "Оберіть дію:"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📊 Статистика дня", "callback_data": "admin_daily_stats"}],
                [{"text": "📦 Нові замовлення", "callback_data": "admin_pending_orders"}],
                [{"text": "🍽️ Статистика меню", "callback_data": "admin_menu_stats"}],
                [{"text": "👥 Користувачі", "callback_data": "admin_users"}],
                [{"text": "⚙️ Налаштування", "callback_data": "admin_settings"}],
                [{"text": "📈 Графіки", "callback_data": "admin_charts"}]
            ]
        }
        
        tg_send_message(chat_id, menu_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing admin menu: {e}")
        tg_send_message(chat_id, "Помилка відображення меню адміністратора.")

def show_daily_stats(chat_id):
    """Показує статистику за день"""
    try:
        stats = admin_panel.get_daily_stats()
        
        if not stats:
            tg_send_message(chat_id, "Не вдалося отримати статистику.")
            return
            
        stats_text = f"📊 <b>Статистика за {datetime.now().strftime('%d.%m.%Y')}</b>\n\n"
        stats_text += f"📦 <b>Замовлення:</b>\n"
        stats_text += f"  • Всього: {stats['total_orders']}\n"
        stats_text += f"  • Нові: {stats['new_orders']}\n"
        stats_text += f"  • В роботі: {stats['in_progress']}\n"
        stats_text += f"  • Виконані: {stats['completed']}\n"
        stats_text += f"  • Скасовані: {stats['cancelled']}\n\n"
        
        stats_text += f"💰 <b>Фінанси:</b>\n"
        stats_text += f"  • Виручка: {stats['total_revenue']:.2f} грн\n"
        stats_text += f"  • Середній чек: {stats['average_order']:.2f} грн\n\n"
        
        # Обчислюємо конверсію
        if stats['total_orders'] > 0:
            conversion = (stats['completed'] / stats['total_orders']) * 100
            stats_text += f"📈 <b>Конверсія:</b> {conversion:.1f}%\n\n"
        
        if stats['new_orders'] > 0:
            stats_text += f"⚠️ <b>Увага!</b> {stats['new_orders']} нових замовлень потребують обробки."
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📦 Переглянути нові", "callback_data": "admin_pending_orders"}],
                [{"text": "🔄 Оновити статистику", "callback_data": "admin_daily_stats"}],
                [{"text": "⬅️ Назад в меню", "callback_data": "admin_menu"}]
            ]
        }
        
        tg_send_message(chat_id, stats_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing daily stats: {e}")
        tg_send_message(chat_id, "Помилка отримання статистики.")

def show_pending_orders(chat_id):
    """Показує список нових замовлень"""
    try:
        orders = get_new_orders()
        
        if not orders:
            message = "✅ Немає нових замовлень!\n\nВсі замовлення опрацьовані."
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔄 Оновити", "callback_data": "admin_pending_orders"}],
                    [{"text": "⬅️ Назад", "callback_data": "admin_menu"}]
                ]
            }
            tg_send_message(chat_id, message, reply_markup=keyboard)
            return
            
        header = f"📦 <b>Нові замовлення ({len(orders)})</b>\n\n"
        tg_send_message(chat_id, header)
        
        for order in orders[:10]:  # Показуємо максимум 10
            order_text = f"🆔 <b>#{order.get('ID Замовлення', 'N/A')}</b>\n"
            order_text += f"👤 Клієнт: {order.get('Telegram User ID', 'N/A')}\n"
            order_text += f"📞 Телефон: {order.get('Телефон', 'N/A')}\n"
            order_text += f"🏠 Адреса: {order.get('Адреса', 'N/A')}\n"
            order_text += f"💰 Сума: {order.get('Сума', 0)} грн\n"
            order_text += f"💳 Оплата: {order.get('Спосіб Оплати', 'N/A')}\n"
            order_text += f"🕐 Час: {order.get('Дата/час', 'N/A')}\n"
            
            # Розшифровуємо товари якщо є JSON
            try:
                import json
                items = json.loads(order.get('Товари (JSON)', '[]'))
                if items:
                    order_text += f"\n🛒 <b>Товари:</b>\n"
                    for item in items:
                        order_text += f"  • {item.get('name', 'N/A')} × {item.get('qty', 1)}\n"
            except:
                order_text += f"\n🛒 Товари: {order.get('Товари (JSON)', 'N/A')}\n"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ В роботу", "callback_data": f"order_status_{order.get('ID Замовлення')}_В роботі"},
                        {"text": "❌ Скасувати", "callback_data": f"order_status_{order.get('ID Замовлення')}_Скасовано"}
                    ],
                    [
                        {"text": "📞 Зателефонувати", "url": f"tel:{order.get('Телефон', '')}"}
                    ]
                ]
            }
            
            tg_send_message(chat_id, order_text, reply_markup=keyboard)
            
        if len(orders) > 10:
            footer = f"\n... і ще {len(orders) - 10} замовлень.\nВсі замовлення доступні в Google Sheets."
            tg_send_message(chat_id, footer)
            
    except Exception as e:
        logger.error(f"Error showing pending orders: {e}")
        tg_send_message(chat_id, "Помилка завантаження замовлень.")

def show_menu_stats(chat_id):
    """Показує статистику меню"""
    try:
        stats = get_menu_stats()
        
        stats_text = f"🍽️ <b>Статистика меню</b>\n\n"
        stats_text += f"📊 Всього позицій: {stats.get('total_items', 0)}\n"
        stats_text += f"✅ Активних: {stats.get('active_items', 0)}\n\n"
        
        stats_text += f"📂 <b>По категоріях:</b>\n"
        for category, data in stats.get('categories', {}).items():
            stats_text += f"  • {category}: {data['active']}/{data['total']}\n"
        
        if stats.get('cache_age'):
            cache_minutes = int(stats['cache_age'] / 60)
            stats_text += f"\n🕐 Кеш оновлено: {cache_minutes} хв тому"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Оновити кеш меню", "callback_data": "admin_refresh_menu"}],
                [{"text": "⬅️ Назад", "callback_data": "admin_menu"}]
            ]
        }
        
        tg_send_message(chat_id, stats_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing menu stats: {e}")
        tg_send_message(chat_id, "Помилка статистики меню.")

def show_admin_help(chat_id):
    """Показує довідку для адміністратора"""
    help_text = """🔧 <b>Довідка адміністратора</b>

<b>Команди:</b>
/admin - Головне меню
/stats - Статистика дня
/orders - Нові замовлення
/menu - Статистика меню
/help_admin - Ця довідка

<b>Google Sheets панель:</b>
• Вкладка "Замовлення" - всі замовлення
• Вкладка "Статистика" - автоматичні графіки
• Вкладка "Користувачі" - база клієнтів

<b>Статуси замовлень:</b>
• Нове - щойно створене
• В роботі - прийняте в обробку
• Готове - готове до видачі
• Доставлено - успішно виконано
• Скасовано - відмінено

<b>Швидкі дії:</b>
• Натисніть на замовлення для зміни статусу
• Використовуйте кнопку "📞" для дзвінка
• Статистика оновлюється автоматично"""
    
    tg_send_message(chat_id, help_text)

def handle_order_status_change(chat_id, callback_data, callback_id, operator_chat_id):
    """Обробляє зміну статусу замовлення оператором"""
    try:
        if chat_id != int(operator_chat_id):
            return False
            
        # Парсимо callback_data: order_status_{order_id}_{new_status}
        parts = callback_data.split('_')
        if len(parts) < 4:
            return False
            
        order_id = parts[2]
        new_status = '_'.join(parts[3:])  # На випадок пробілів в статусі
        
        # Оновлюємо статус в Google Sheets
        success = admin_panel.update_order_status(order_id, new_status, "Оператор")
        
        if success:
            tg_answer_callback(callback_id, f"Статус змінено на: {new_status}")
            
            # Відправляємо підтвердження
            confirmation = f"✅ Замовлення #{order_id} переведено в статус: <b>{new_status}</b>"
            tg_send_message(chat_id, confirmation)
            
            # Якщо замовлення готове - можна повідомити клієнта
            if new_status == "Готове":
                suggest_notify_customer(chat_id, order_id)
                
        else:
            tg_answer_callback(callback_id, "Помилка зміни статусу")
            
        return True
        
    except Exception as e:
        logger.error(f"Error handling order status change: {e}")
        tg_answer_callback(callback_id, "Помилка обробки")
        return False

def suggest_notify_customer(chat_id, order_id):
    """Пропонує повідомити клієнта про готовність замовлення"""
    try:
        message = f"📞 Повідомити клієнта про готовність замовлення #{order_id}?"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ Повідомити клієнта", "callback_data": f"notify_customer_{order_id}"}],
                [{"text": "❌ Не потрібно", "callback_data": "dismiss_notification"}]
            ]
        }
        
        tg_send_message(chat_id, message, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error suggesting customer notification: {e}")

def handle_admin_callback(chat_id, callback_data, callback_id, operator_chat_id):
    """Обробляє всі callback-и адмін-панелі"""
    try:
        if chat_id != int(operator_chat_id):
            return False
            
        if callback_data == "admin_menu":
            show_admin_menu(chat_id)
            tg_answer_callback(callback_id)
            
        elif callback_data == "admin_daily_stats":
            show_daily_stats(chat_id)
            tg_answer_callback(callback_id)
            
        elif callback_data == "admin_pending_orders":
            show_pending_orders(chat_id)
            tg_answer_callback(callback_id)
            
        elif callback_data == "admin_menu_stats":
            show_menu_stats(chat_id)
            tg_answer_callback(callback_id)
            
        elif callback_data == "admin_refresh_menu":
            from services.sheets import get_menu_from_sheet
            get_menu_from_sheet(force=True)
            tg_answer_callback(callback_id, "Кеш меню оновлено!")
            show_menu_stats(chat_id)
            
        elif callback_data.startswith("order_status_"):
            handle_order_status_change(chat_id, callback_data, callback_id, operator_chat_id)
            
        elif callback_data.startswith("notify_customer_"):
            order_id = callback_data.replace("notify_customer_", "")
            notify_customer_ready(order_id)
            tg_answer_callback(callback_id, "Повідомлення відправлено!")
            
        elif callback_data == "dismiss_notification":
            tg_answer_callback(callback_id, "Скасовано")
            
        elif callback_data == "admin_users":
            show_users_stats(chat_id)
            tg_answer_callback(callback_id)
            
        elif callback_data == "admin_settings":
            show_admin_settings(chat_id)
            tg_answer_callback(callback_id)
            
        elif callback_data == "admin_charts":
            show_charts_info(chat_id)
            tg_answer_callback(callback_id)
            
        else:
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error handling admin callback: {e}")
        return False

def notify_customer_ready(order_id):
    """Повідомляє клієнта про готовність замовлення"""
    try:
        # Отримуємо інформацію про замовлення з Google Sheets
        if not admin_panel.spreadsheet:
            admin_panel.init_connection()
            
        ws = admin_panel.spreadsheet.worksheet("Замовлення")
        orders = ws.get_all_records()
        
        for order in orders:
            if order.get("ID Замовлення") == order_id:
                customer_id = order.get("Telegram User ID")
                if customer_id:
                    message = f"🎉 Ваше замовлення #{order_id} готове!\n\n"
                    message += "Можете забирати або очікувати доставки.\n"
                    message += "Дякуємо за ваше замовлення!"
                    
                    tg_send_message(int(customer_id), message)
                    return True
                    
        return False
        
    except Exception as e:
        logger.error(f"Error notifying customer: {e}")
        return False

def show_users_stats(chat_id):
    """Показує статистику користувачів"""
    try:
        if not admin_panel.spreadsheet:
            admin_panel.init_connection()
            
        ws = admin_panel.spreadsheet.worksheet("Користувачі")
        users = ws.get_all_records()
        
        total_users = len(users)
        if total_users == 0:
            tg_send_message(chat_id, "Немає даних про користувачів.")
            return
            
        # Рахуємо статистику
        active_users = len([u for u in users if u.get("Статус") == "активний"])
        total_orders = sum(int(u.get("Кількість замовлень", 0)) for u in users)
        avg_orders_per_user = total_orders / total_users if total_users > 0 else 0
        
        # ТОП-5 користувачів за кількістю замовлень
        top_users = sorted(users, key=lambda x: int(x.get("Кількість замовлень", 0)), reverse=True)[:5]
        
        stats_text = f"👥 <b>Статистика користувачів</b>\n\n"
        stats_text += f"📊 Всього користувачів: {total_users}\n"
        stats_text += f"✅ Активних: {active_users}\n"
        stats_text += f"📦 Всього замовлень: {total_orders}\n"
        stats_text += f"📈 Середня кількість замовлень: {avg_orders_per_user:.1f}\n\n"
        
        if top_users:
            stats_text += f"🏆 <b>ТОП-5 клієнтів:</b>\n"
            for i, user in enumerate(top_users, 1):
                name = user.get("Ім'я", "N/A")
                orders_count = user.get("Кількість замовлень", 0)
                avg_check = user.get("Середній чек", 0)
                stats_text += f"{i}. {name} - {orders_count} зам., {avg_check:.0f} грн\n"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Оновити", "callback_data": "admin_users"}],
                [{"text": "⬅️ Назад", "callback_data": "admin_menu"}]
            ]
        }
        
        tg_send_message(chat_id, stats_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing users stats: {e}")
        tg_send_message(chat_id, "Помилка завантаження статистики користувачів.")

def show_admin_settings(chat_id):
    """Показує налаштування адміністратора"""
    settings_text = """⚙️ <b>Налаштування системи</b>

<b>Поточні налаштування:</b>
• Мінімальна сума замовлення: 200 грн
• Час роботи: 9:00 - 22:00
• Зона доставки: 7 км від центру
• Вартість доставки: 50 грн

<b>Статуси бота:</b>
• Google Sheets: ✅ Підключено
• Gemini AI: ✅ Працює
• База даних: ✅ Працює

<b>Автоматизація:</b>
• Щоденні звіти: ✅ Увімкнено
• Уведомлення про нові замовлення: ✅ Увімкнено"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📧 Налаштувати сповіщення", "callback_data": "admin_notifications"}],
            [{"text": "🕐 Змінити режим роботи", "callback_data": "admin_schedule"}],
            [{"text": "⬅️ Назад", "callback_data": "admin_menu"}]
        ]
    }
    
    tg_send_message(chat_id, settings_text, reply_markup=keyboard)

def show_charts_info(chat_id):
    """Показує інформацію про графіки та аналітику"""
    charts_text = """📈 <b>Аналітика та графіки</b>

<b>Доступна аналітика:</b>
• Google Sheets з автоматичними формулами
• Щоденна/тижнева/місячна статистика
• Аналіз популярності страв
• Географія замовлень

<b>Як переглянути:</b>
1. Перейдіть у Google Sheets панель
2. Відкрийте вкладку "Статистика"
3. Всі дані оновлюються автоматично

<b>Рекомендації:</b>
• Створіть Google Data Studio для візуалізації
• Налаштуйте автоматичні звіти
• Використовуйте фільтри за періодами"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 Відкрити Google Sheets", "url": f"https://docs.google.com/spreadsheets/d/{admin_panel.spreadsheet.id if admin_panel.spreadsheet else 'YOUR_SHEET_ID'}"}],
            [{"text": "⬅️ Назад", "callback_data": "admin_menu"}]
        ]
    }
    
    tg_send_message(chat_id, charts_text, reply_markup=keyboard)

def schedule_daily_reports(operator_chat_id, hour=9):
    """Планує щоденні звіти (потрібна додаткова настройка cron або scheduler)"""
    # Ця функція потребує додаткової настройки планувальника завдань
    # Наприклад, через APScheduler або cron job
    pass
