"""
Partner Management Handler
Управління партнерами та їх аналітикою
"""

import logging
from datetime import datetime, timedelta
from config import (
    PREMIUM_LEVELS,
    PARTNER_STATUSES,
    COMMISSION_CONFIG,
    is_premium_active,
    format_commission_report
)
from services.commission_service import PartnerAnalytics

logger = logging.getLogger('partner_management')


class PartnerManager:
    """Управління партнерами"""
    
    def __init__(self, sheets_service, partners_data=None):
        self.sheets = sheets_service
        self.partners_data = partners_data or []
    
    def get_partner_profile(self, partner_id):
        """
        Отримує профіль партнера
        
        Returns:
            dict з інформацією про партнера
        """
        
        partner = next(
            (p for p in self.partners_data if p.get('id') == partner_id),
            None
        )
        
        if not partner:
            logger.warning(f"Partner {partner_id} not found")
            return None
        
        # Перевіраємо статус преміум
        is_premium = is_premium_active(partner.get('premium_until', ''))
        premium_level = partner.get('premium_level') if is_premium else 'standard'
        
        profile = {
            'id': partner.get('id'),
            'name': partner.get('name'),
            'category': partner.get('category'),
            'phone': partner.get('phone'),
            'commission_rate': partner.get('commission_rate', COMMISSION_CONFIG['default_rate']),
            'premium_level': premium_level,
            'is_premium_active': is_premium,
            'status': partner.get('status', 'pending'),
            'rating': partner.get('rating', 0),
            'weekly_orders': partner.get('active_orders_week', 0),
            'weekly_revenue': partner.get('revenue_week', 0)
        }
        
        return profile
    
    def get_all_active_partners(self):
        """
        Отримує список активних партнерів
        
        Returns:
            list - активні партнери відсортовані за преміум рівнем
        """
        
        active_partners = []
        
        for partner in self.partners_data:
            if partner.get('status') == 'active':
                is_premium = is_premium_active(partner.get('premium_until', ''))
                premium_level = partner.get('premium_level') if is_premium else 'standard'
                
                active_partners.append({
                    'id': partner.get('id'),
                    'name': partner.get('name'),
                    'category': partner.get('category'),
                    'premium_level': premium_level,
                    'rating': partner.get('rating', 0),
                    'order_position': self._calculate_position(partner)
                })
        
        # Сортуємо: спочатку premium, потім за рейтингом
        active_partners.sort(key=lambda x: (
            0 if x['premium_level'] != 'standard' else 1,
            -float(x['rating'] or 0)
        ))
        
        return active_partners
    
    def upgrade_partner_premium(self, partner_id, premium_level, months=1):
        """
        Оновлює преміум статус партнера
        
        Args:
            partner_id: ID партнера
            premium_level: 'standard', 'premium' або 'exclusive'
            months: кількість місяців
        
        Returns:
            {
                'success': bool,
                'message': str,
                'new_expiry': str
            }
        """
        
        if premium_level not in PREMIUM_LEVELS:
            return {
                'success': False,
                'message': f"Невідомий рівень преміум: {premium_level}"
            }
        
        if premium_level == 'standard':
            # Скасування преміум
            new_expiry = datetime.now().strftime('%Y-%m-%d')
            message = "Преміум скасовано"
        else:
            new_expiry = (datetime.now() + timedelta(days=30 * months)).strftime('%Y-%m-%d')
            premium_info = PREMIUM_LEVELS[premium_level]
            message = f"Преміум {premium_info['name']} активовано до {new_expiry}"
        
        logger.info(f"Partner {partner_id} premium upgraded to {premium_level}")
        
        return {
            'success': True,
            'premium_level': premium_level,
            'new_expiry': new_expiry,
            'message': message,
            'price': PREMIUM_LEVELS[premium_level]['price'] if premium_level != 'standard' else 0
        }
    
    def update_partner_commission_rate(self, partner_id, new_rate):
        """
        Оновлює ставку комісії для партнера
        
        Returns:
            dict з результатом
        """
        
        if new_rate < 0 or new_rate > 100:
            return {
                'success': False,
                'message': "Ставка комісії повинна бути від 0 до 100%"
            }
        
        partner = next(
            (p for p in self.partners_data if p.get('id') == partner_id),
            None
        )
        
        if not partner:
            return {
                'success': False,
                'message': "Партнер не знайдений"
            }
        
        old_rate = partner.get('commission_rate')
        partner['commission_rate'] = new_rate
        
        logger.info(f"Partner {partner_id} commission rate changed: {old_rate}% -> {new_rate}%")
        
        return {
            'success': True,
            'old_rate': old_rate,
            'new_rate': new_rate,
            'message': f"Ставка комісії оновлена: {old_rate}% -> {new_rate}%"
        }
    
    def suspend_partner(self, partner_id, reason=""):
        """
        Призупиняє роботу партнера
        
        Returns:
            dict з результатом
        """
        
        partner = next(
            (p for p in self.partners_data if p.get('id') == partner_id),
            None
        )
        
        if not partner:
            return {
                'success': False,
                'message': "Партнер не знайдений"
            }
        
        partner['status'] = 'suspended'
        
        logger.warning(f"Partner {partner_id} suspended. Reason: {reason}")
        
        return {
            'success': True,
            'message': f"Партнер призупинений",
            'reason': reason
        }
    
    def reactivate_partner(self, partner_id):
        """
        Активує партнера знову
        
        Returns:
            dict з результатом
        """
        
        partner = next(
            (p for p in self.partners_data if p.get('id') == partner_id),
            None
        )
        
        if not partner:
            return {
                'success': False,
                'message': "Партнер не знайдений"
            }
        
        partner['status'] = 'active'
        
        logger.info(f"Partner {partner_id} reactivated")
        
        return {
            'success': True,
            'message': "Партнер активований"
        }
    
    def _calculate_position(self, partner):
        """
        Розраховує позицію партнера у списку
        На основі: преміум рівень, рейтинг, кількість замовлень
        """
        
        premium_level = partner.get('premium_level', 'standard')
        rating = float(partner.get('rating', 0))
        orders = int(partner.get('active_orders_week', 0))
        
        # Вага для сортування
        score = 0
        
        # Преміум рівень
        if premium_level == 'exclusive':
            score += 1000
        elif premium_level == 'premium':
            score += 500
        
        # Рейтинг
        score += rating * 100
        
        # Кількість замовлень
        score += orders * 10
        
        return score


class PartnerAnalyticsHandler:
    """Аналітика для партнерів"""
    
    def __init__(self, sheets_service):
        self.sheets = sheets_service
    
    def get_partner_dashboard(self, partner_id, orders_list, reviews_list=None):
        """
        Генерує дашборд для партнера
        
        Returns:
            dict з основною інформацією для партнера
        """
        
        # Фільтруємо замовлення партнера
        partner_orders = [o for o in orders_list if o.get('partner_id') == partner_id]
        
        if not partner_orders:
            return {
                'orders_total': 0,
                'revenue_total': 0,
                'commission_total': 0,
                'avg_order_value': 0,
                'rating': 0,
                'message': 'Немає даних про замовлення'
            }
        
        # Розраховуємо основні метрики
        total_revenue = sum(float(o.get('final_amount', 0)) for o in partner_orders)
        total_commission = sum(float(o.get('commission_amount', 0)) for o in partner_orders)
        
        dashboard = {
            'orders_total': len(partner_orders),
            'revenue_total': round(total_revenue, 2),
            'commission_total': round(total_commission, 2),
            'avg_order_value': round(total_revenue / len(partner_orders), 2) if partner_orders else 0,
            'completed_orders': len([o for o in partner_orders if o.get('status') == 'completed']),
            'pending_orders': len([o for o in partner_orders if o.get('status') == 'pending']),
            'rating': self._calculate_rating(reviews_list) if reviews_list else 0
        }
        
        return dashboard
    
    def get_partner_commission_report(self, partner_id, orders_list, period_days=7):
        """
        Генерує звіт комісії для партнера за період
        
        Returns:
            str - форматований звіт для Telegram
        """
        
        from datetime import timedelta
        
        # Фільтруємо замовлення за період
        start_date = datetime.now() - timedelta(days=period_days)
        partner_orders = [
            o for o in orders_list
            if o.get('partner_id') == partner_id and
            datetime.fromisoformat(o.get('created_at', '')) >= start_date
        ]
        
        if not partner_orders:
            return f"Немає замовлень за останні {period_days} днів"
        
        total_commission = sum(float(o.get('commission_amount', 0)) for o in partner_orders)
        total_revenue = sum(float(o.get('final_amount', 0)) for o in partner_orders)
        
        report = f"""
💰 ЗВІТ КОМІСІЇ ЗА {period_days} ДНІВ

📊 Метрики:
• Замовлень: {len(partner_orders)}
• Сума замовлень: {round(total_revenue, 2)} грн
• Ваша комісія: {round(total_commission, 2)} грн
• На замовлення: {round(total_commission / len(partner_orders), 2)} грн

📈 Тренд:
• Середнє на день: {round(total_commission / period_days, 2)} грн
• Статус: {'📈 Зростання' if total_commission > 0 else '📉 Спад'}

✅ Звіт готовий для огляду
"""
        return report
    
    @staticmethod
    def _calculate_rating(reviews_list):
        """Розраховує рейтинг на основі відгуків"""
        
        if not reviews_list:
            return 0.0
        
        ratings = [
            float(r.get('rating', 0))
            for r in reviews_list
            if r.get('rating')
        ]
        
        if not ratings:
            return 0.0
        
        return round(sum(ratings) / len(ratings), 1)


class PremiumFeatureManager:
    """Управління преміум функціями"""
    
    @staticmethod
    def get_premium_benefits(premium_level):
        """
        Отримує переваги для преміум рівня
        
        Returns:
            str - список переваг для Telegram
        """
        
        level_info = PREMIUM_LEVELS.get(premium_level)
        
        if not level_info:
            return "Рівень преміум не знайдений"
        
        benefits = f"""
⭐ {level_info['name'].upper()}

Переваги:
"""
        for feature in level_info['features']:
            benefits += f"✓ {feature}\n"
        
        benefits += f"\n💰 Ціна: {level_info['price']} грн/місяць"
        
        return benefits
    
    @staticmethod
    def format_premium_promo():
        """
        Форматує промо для преміум розширення
        
        Returns:
            str - текст для Telegram
        """
        
        promo = """
🌟 РОЗШИРТЕ ВАШІ МОЖЛИВОСТІ

Виберіть оптимальний рівень преміум:

🔹 Standard (Безкоштовно)
   • Базовий список меню
   • Стандартна комісія

🔹 Premium (250 грн/месяц)
   • ⭐ Топ у списку міста
   • Спеціальний бадж
   • Показ рейтингу
   • -2% комісія

🔹 Exclusive (1000 грн/месяц)
   • ⭐⭐ Перше місце в списку
   • Персональний банер
   • Персональні підбірки
   • Рекомендації дня
   • -5% комісія

📞 Контактуйте нас для деталей
"""
        return promo