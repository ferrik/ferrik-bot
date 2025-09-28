import logging
from datetime import datetime, timedelta
from services.sheets import init_gspread_client, spreadsheet
from services.telegram import tg_send_message

logger = logging.getLogger("ferrik.admin")

class AdminPanel:
    def __init__(self):
        self.spreadsheet = None
        
    def init_connection(self):
        """Ініціалізує підключення до Google Sheets"""
        if init_gspread_client():
            global spreadsheet
            self.spreadsheet = spreadsheet
            return True
        return False
    
    def update_order_status(self, order_id, new_status, operator_name=None):
        """Оновлює статус замовлення в адмін-панелі"""
        try:
            if not self.spreadsheet:
                if not self.init_connection():
                    return False
                    
            ws = self.spreadsheet.worksheet("Замовлення")
            
            # Знаходимо рядок з замовленням
            orders = ws.get_all_records()
            for i, order in enumerate(orders, start=2):  # +2 для заголовків
                if order.get("ID Замовлення") == order_id:
                    # Оновлюємо статус (колонка J)
                    ws.update_cell(i, 10, new_status)
                    
                    # Оновлюємо оператора якщо передано
                    if operator_name:
                        ws.update_cell(i, 11, operator_name)
                        
                    # Додаємо час оновлення
                    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
                    current_notes = ws.cell(i, 12).value or ""
                    new_notes = f"{current_notes}\n[{timestamp}] Статус змінено на: {new_status}"
                    ws.update_cell(i, 12, new_notes.strip())
                    
                    logger.info(f"Order {order_id} status updated to {new_status}")
                    return True
                    
            logger.warning(f"Order {order_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False
    
    def get_pending_orders(self):
        """Отримує список нових замовлень"""
        try:
            if not self.spreadsheet:
                if not self.init_connection():
                    return []
                    
            ws = self.spreadsheet.worksheet("Замовлення")
            orders = ws.get_all_records()
            
            pending = [order for order in orders if order.get("Статус") == "Нове"]
            return pending
            
        except Exception as e:
            logger.error(f"Error getting pending orders: {e}")
            return []
    
    def get_daily_stats(self, date=None):
        """Отримує статистику за день"""
        try:
            if not date:
                date = datetime.now().date()
                
            if not self.spreadsheet:
                if not self.init_connection():
                    return {}
                    
            ws = self.spreadsheet.worksheet("Замовлення")
            orders = ws.get_all_records()
            
            # Фільтруємо замовлення за датою
            daily_orders = []
            for order in orders:
                order_date_str = order.get("Дата/час", "")
                try:
                    order_date = datetime.strptime(order_date_str[:10], "%Y-%m-%d").date()
                    if order_date == date:
                        daily_orders.append(order)
                except:
                    continue
            
            # Рахуємо статистику
            stats = {
                "total_orders": len(daily_orders),
                "new_orders": len([o for o in daily_orders if o.get("Статус") == "Нове"]),
                "in_progress": len([o for o in daily_orders if o.get("Статус") == "В роботі"]),
                "completed": len([o for o in daily_orders if o.get("Статус") == "Доставлено"]),
                "cancelled": len([o for o in daily_orders if o.get("Статус") == "Скасовано"]),
                "total_revenue": sum(float(o.get("Сума", 0)) for o in daily_orders if o.get("Статус") == "Доставлено"),
                "average_order": 0
            }
            
            if stats["completed"] > 0:
                completed_orders = [o for o in daily_orders if o.get("Статус") == "Доставлено"]
                stats["average_order"] = stats["total_revenue"] / len(completed_orders)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {}
    
    def add_user_data(self, chat_id, user_info):
        """Додає/оновлює дані користувача"""
        try:
            if not self.spreadsheet:
                if not self.init_connection():
                    return False
                    
            ws = self.spreadsheet.worksheet("Користувачі")
            
            # Перевіряємо чи користувач вже існує
            try:
                users = ws.get_all_records()
                existing_row = None
                
                for i, user in enumerate(users, start=2):
                    if str(user.get("User ID")) == str(chat_id):
                        existing_row = i
                        break
                
                if existing_row:
                    # Оновлюємо існуючого користувача
                    ws.update_cell(existing_row, 2, user_info.get("first_name", ""))
                    ws.update_cell(existing_row, 6, datetime.now().strftime("%d.%m.%Y %H:%M"))
                else:
                    # Додаємо нового користувача
                    new_row = [
                        chat_id,
                        user_info.get("first_name", ""),
                        0,  # кількість замовлень
                        "",  # останнє замовлення
                        0,   # середній чек
                        "активний",
                        datetime.now().strftime("%d.%m.%Y %H:%M")
                    ]
                    ws.append_row(new_row)
                    
                return True
                
            except Exception as e:
                # Якщо вкладка не існує, створюємо її
                if "not found" in str(e).lower():
                    ws = self.spreadsheet.add_worksheet(title="Користувачі", rows="1000", cols="7")
                    headers = ["User ID", "Ім'я", "Кількість замовлень", "Останнє замовлення", "Середній чек", "Статус", "Дата реєстрації"]
                    ws.append_row(headers)
                    
                    new_row = [
                        chat_id,
                        user_info.get("first_name", ""),
                        0, "", 0, "активний",
                        datetime.now().strftime("%d.%m.%Y %H:%M")
                    ]
                    ws.append_row(new_row)
                    return True
                else:
                    raise e
                    
        except Exception as e:
            logger.error(f"Error adding user data: {e}")
            return False
    
    def update_user_stats(self, chat_id, order_sum):
        """Оновлює статистику користувача після замовлення"""
        try:
            if not self.spreadsheet:
                if not self.init_connection():
                    return False
                    
            ws = self.spreadsheet.worksheet("Користувачі")
            users = ws.get_all_records()
            
            for i, user in enumerate(users, start=2):
                if str(user.get("User ID")) == str(chat_id):
                    current_orders = int(user.get("Кількість замовлень", 0))
                    current_total = float(user.get("Середній чек", 0)) * current_orders
                    
                    new_orders = current_orders + 1
                    new_average = (current_total + float(order_sum)) / new_orders
                    
                    # Оновлюємо дані
                    ws.update_cell(i, 3, new_orders)  # кількість замовлень
                    ws.update_cell(i, 4, datetime.now().strftime("%d.%m.%Y"))  # останнє замовлення
                    ws.update_cell(i, 5, round(new_average, 2))  # середній чек
                    
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error updating user stats: {e}")
            return False
    
    def create_dashboard_formulas(self):
        """Створює формули для дашборду статистики"""
        try:
            if not self.spreadsheet:
                if not self.init_connection():
                    return False
                    
            # Створюємо/оновлюємо вкладку Статистика
            try:
                ws = self.spreadsheet.worksheet("Статистика")
            except:
                ws = self.spreadsheet.add_worksheet(title="Статистика", rows="50", cols="10")
            
            # Заголовки та формули
            dashboard_data = [
                ["📊 DASHBOARD - FerrikFootBot", "", "", ""],
                ["", "", "", ""],
                ["🕐 Реальний час:", f"=NOW()", "", ""],
                ["📅 Сьогодні:", f"=TODAY()", "", ""],
                ["", "", "", ""],
                ["📈 ЗАМОВЛЕННЯ СЬОГОДНІ", "", "", ""],
                ["Всього замовлень:", '=COUNTIFS(Замовлення!B:B,">="&TODAY(),Замовлення!B:B,"<"&TODAY()+1)', "", ""],
                ["Нові:", '=COUNTIFS(Замовлення!B:B,">="&TODAY(),Замовлення!J:J,"Нове")', "", ""],
                ["В роботі:", '=COUNTIFS(Замовлення!B:B,">="&TODAY(),Замовлення!J:J,"В роботі")', "", ""],
                ["Виконані:", '=COUNTIFS(Замовлення!B:B,">="&TODAY(),Замовлення!J:J,"Доставлено")', "", ""],
                ["Скасовані:", '=COUNTIFS(Замовлення!B:B,">="&TODAY(),Замовлення!J:J,"Скасовано")', "", ""],
                ["", "", "", ""],
                ["💰 ФІНАНСИ СЬОГОДНІ", "", "", ""],
                ["Виручка:", '=SUMIFS(Замовлення!H:H,Замовлення!B:B,">="&TODAY(),Замовлення!J:J,"Доставлено")', "грн", ""],
                ["Середній чек:", '=AVERAGEIFS(Замовлення!H:H,Замовлення!B:B,">="&TODAY(),Замовлення!J:J,"Доставлено")', "грн", ""],
                ["", "", "", ""],
                ["👥 КОРИСТУВАЧІ", "", "", ""],
                ["Всього користувачів:", "=COUNTA(Користувачі!A:A)-1", "", ""],
                ["Активних сьогодні:", '=COUNTIFS(Замовлення!B:B,">="&TODAY(),Замовлення!C:C,"<>")', "", ""],
                ["", "", "", ""],
                ["🏆 ТОП-СТРАВИ МІСЯЦЯ", "", "", ""],
                ["(Оновлюється автоматично)", "", "", ""],
            ]
            
            # Очищуємо та заповнюємо
            ws.clear()
            for row_data in dashboard_data:
                ws.append_row(row_data)
            
            # Форматування (якщо потрібно)
            ws.format("A1:D1", {"backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0}})
            
            logger.info("Dashboard formulas created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating dashboard: {e}")
            return False
    
    def send_daily_report(self, operator_chat_id):
        """Відправляє щоденний звіт оператору"""
        try:
            stats = self.get_daily_stats()
            
            if not stats:
                return False
                
            report = f"📊 <b>Щоденний звіт - {datetime.now().strftime('%d.%m.%Y')}</b>\n\n"
            report += f"📦 <b>Замовлення:</b>\n"
            report += f"  • Всього: {stats['total_orders']}\n"
            report += f"  • Нові: {stats['new_orders']}\n"
            report += f"  • В роботі: {stats['in_progress']}\n"
            report += f"  • Виконані: {stats['completed']}\n"
            report += f"  • Скасовані: {stats['cancelled']}\n\n"
            report += f"💰 <b>Фінанси:</b>\n"
            report += f"  • Виручка: {stats['total_revenue']:.2f} грн\n"
            report += f"  • Середній чек: {stats['average_order']:.2f} грн\n\n"
            
            if stats['new_orders'] > 0:
                report += f"⚠️ Увага: {stats['new_orders']} нових замовлень потребують обробки!"
            
            tg_send_message(operator_chat_id, report)
            return True
            
        except Exception as e:
            logger.error(f"Error sending daily report: {e}")
            return False

# Глобальний екземпляр адмін-панелі
admin_panel = AdminPanel()

def update_order_status(order_id, status, operator=None):
    """Зручна функція для оновлення статусу замовлення"""
    return admin_panel.update_order_status(order_id, status, operator)

def track_user_activity(chat_id, user_info):
    """Відстежує активність користувача"""
    return admin_panel.add_user_data(chat_id, user_info)

def get_new_orders():
    """Отримує список нових замовлень"""
    return admin_panel.get_pending_orders()

def send_daily_stats(operator_chat_id):
    """Відправляє щоденну статистику"""
    return admin_panel.send_daily_report(operator_chat_id)