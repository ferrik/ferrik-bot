"""
Analytics Service
Аналітика та звіти для платформи
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger('analytics_service')


class PlatformAnalytics:
    """Основна аналітика платформи"""
    
    @staticmethod
    def get_daily_revenue(orders_list, date_str=None):
        """
        Розраховує дохід за день
        
        Args:
            orders_list: список всіх замовлень
            date_str: дата в форматі YYYY-MM-DD (за замовчуванням - сьогодні)
        
        Returns:
            {
                'date': str,
                'orders_count': int,
                'total_amount': float,
                'commission_revenue': float,
                'platform_revenue': float
            }
        """
        
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        daily_stats = {
            'date': date_str,
            'orders_count': 0,
            'total_amount': 0.0,
            'commission_revenue': 0.0,
            'platform_revenue': 0.0
        }
        
        for order in orders_list:
            order_date = order.get('date', '')[:10]  # Беремо тільки дату
            
            if order_date == date_str:
                daily_stats['orders_count'] += 1
                daily_stats['total_amount'] += float(order.get('final_amount', 0))
                daily_stats['commission_revenue'] += float(order.get('commission_amount', 0))
                daily_stats['platform_revenue'] += float(order.get('platform_revenue', 0))
        
        # Округлюємо
        daily_stats['total_amount'] = round(daily_stats['total_amount'], 2)
        daily_stats['commission_revenue'] = round(daily_stats['commission_revenue'], 2)
        daily_stats['platform_revenue'] = round(daily_stats['platform_revenue'], 2)
        
        return daily_stats
    
    @staticmethod
    def get_monthly_revenue(orders_list, year=None, month=None):
        """
        Розраховує дохід за місяць
        
        Returns:
            dict з місячною статистикою
        """
        
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month
        
        monthly_stats = {
            'year': year,
            'month': month,
            'orders_count': 0,
            'total_amount': 0.0,
            'commission_revenue': 0.0,
            'platform_revenue': 0.0,
            'daily_breakdown': {}
        }
        
        for order in orders_list:
            try:
                order_date = datetime.strptime(order.get('date', '')[:10], '%Y-%m-%d')
                
                if order_date.year == year and order_date.month == month:
                    day_key = order_date.strftime('%Y-%m-%d')
                    
                    monthly_stats['orders_count'] += 1
                    monthly_stats['total_amount'] += float(order.get('final_amount', 0))
                    monthly_stats['commission_revenue'] += float(order.get('commission_amount', 0))
                    monthly_stats['platform_revenue'] += float(order.get('platform_revenue', 0))
                    
                    if day_key not in monthly_stats['daily_breakdown']:
                        monthly_stats['daily_breakdown'][day_key] = 0.0
                    
                    monthly_stats['daily_breakdown'][day_key] += float(order.get('commission_amount', 0))
            
            except (ValueError, TypeError):
                continue
        
        # Округлюємо
        monthly_stats['total_amount'] = round(monthly_stats['total_amount'], 2)
        monthly_stats['commission_revenue'] = round(monthly_stats['commission_revenue'], 2)
        monthly_stats['platform_revenue'] = round(monthly_stats['platform_revenue'], 2)
        
        return monthly_stats
    
    @staticmethod
    def get_partner_leaderboard(orders_list, partners_list, limit=10):
        """
        Видає рейтинг партнерів за дохідом
        
        Returns:
            list - топ партнерів з доходом
        """
        
        partner_revenue = defaultdict(float)
        partner_orders = defaultdict(int)
        
        for order in orders_list:
            partner_id = order.get('partner_id')
            if partner_id:
                partner_revenue[partner_id] += float(order.get('commission_amount', 0))
                partner_orders[partner_id] += 1
        
        # Створюємо список з інформацією про партнерів
        leaderboard = []
        for partner in partners_list:
            partner_id = partner.get('id')
            revenue = partner_revenue.get(partner_id, 0)
            orders = partner_orders.get(partner_id, 0)
            
            if revenue > 0 or orders > 0:  # Тільки активні партнери
                leaderboard.append({
                    'partner_id': partner_id,
                    'name': partner.get('name', 'N/A'),
                    'revenue': round(revenue, 2),
                    'orders': orders,
                    'avg_order': round(revenue / orders, 2) if orders > 0 else 0,
                    'rating': partner.get('rating', 0)
                })
        
        # Сортуємо за доходом
        leaderboard.sort(key=lambda x: x['revenue'], reverse=True)
        
        return leaderboard[:limit]
    
    @staticmethod
    def get_category_analysis(orders_list, menu_list):
        """
        Аналізує продажи за категоріями
        
        Returns:
            dict - статистика по категоріям
        """
        
        category_stats = defaultdict(lambda: {
            'orders': 0,
            'total_revenue': 0.0,
            'items_sold': 0
        })
        
        # Побудова mapping від item_id до категорії
        category_map = {}
        for item in menu_list:
            category_map[item.get('id')] = item.get('category', 'Інше')
        
        # Обробка замовлень
        for order in orders_list:
            # Припускаємо що товари в JSON форматі
            items = order.get('items', [])
            
            if isinstance(items, str):
                # Якщо JSON рядок, спробуємо распарсити
                import json
                try:
                    items = json.loads(items)
                except:
                    items = []
            
            for item in items:
                item_id = item.get('id')
                category = category_map.get(item_id, 'Інше')
                quantity = int(item.get('quantity', 1))
                price = float(item.get('price', 0))
                
                category_stats[category]['orders'] += 1
                category_stats[category]['total_revenue'] += price * quantity
                category_stats[category]['items_sold'] += quantity
        
        # Форматування результатів
        result = {}
        for category, stats in category_stats.items():
            result[category] = {
                'orders': stats['orders'],
                'total_revenue': round(stats['total_revenue'], 2),
                'items_sold': stats['items_sold'],
                'avg_order_value': round(
                    stats['total_revenue'] / stats['orders'], 2
                ) if stats['orders'] > 0 else 0
            }
        
        return result


class ReportGenerator:
    """Генератор звітів для адміністратора"""
    
    @staticmethod
    def generate_daily_report(analytics_data, date_str=None):
        """
        Генерує щоденний звіт
        
        Returns:
            str - форматований звіт для Telegram
        """
        
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        report = f"""
📊 ЩОДЕННИЙ ЗВІТ
Дата: {date_str}

📈 Основні метрики:
• Замовлень: {analytics_data.get('orders_count', 0)}
• Загальна сума: {analytics_data.get('total_amount', 0)} грн
• Комісія платформи: {analytics_data.get('commission_revenue', 0)} грн
• Дохід платформи: {analytics_data.get('platform_revenue', 0)} грн

✅ Звіт готов для огляду
"""
        return report
    
    @staticmethod
    def generate_monthly_report(analytics_data):
        """
        Генерує щомісячний звіт
        
        Returns:
            str - форматований звіт
        """
        
        year = analytics_data.get('year')
        month = analytics_data.get('month')
        
        report = f"""
📊 ЩОМІСЯЧНИЙ ЗВІТ
Період: {month}/{year}

📈 Основні метрики:
• Замовлень: {analytics_data.get('orders_count', 0)}
• Загальна сума: {analytics_data.get('total_amount', 0)} грн
• Комісія партнерам: {analytics_data.get('commission_revenue', 0)} грн
• Дохід платформи: {analytics_data.get('platform_revenue', 0)} грн

📅 Середнє на день: {round(analytics_data.get('commission_revenue', 0) / 30, 2)} грн

✅ Звіт готов для передачі інвесторам
"""
        return report
    
    @staticmethod
    def generate_partner_report(partner_data, period_stats):
        """
        Генерує звіт для партнера
        
        Returns:
            str - персоналізований звіт
        """
        
        report = f"""
💰 ЗВІТ ПАРТНЕРА

Партнер: {partner_data.get('name', 'N/A')}

📊 За період:
• Замовлень: {period_stats.get('total_orders', 0)}
• Сума замовлень: {period_stats.get('total_revenue', 0)} грн
• Ваша комісія: {period_stats.get('total_commissions', 0)} грн
• Дохід платформи: {period_stats.get('platform_revenue', 0)} грн

📈 Середнє значення:
• На замовлення: {period_stats.get('avg_order_value', 0)} грн

⭐ Рейтинг: {partner_data.get('rating', 'N/A')}
📍 Статус: {'Активний' if partner_data.get('status') == 'active' else 'Неактивний'}

💳 Наступна сплата: за графіком

✅ Спасибі за співпрацю!
"""
        return report