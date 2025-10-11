"""
Commission Processing Service
Обработка комісій та аналітики для платформи
"""

import logging
from datetime import datetime
from config import (
    COMMISSION_CONFIG,
    PREMIUM_LEVELS,
    PAYMENT_STATUSES,
    get_commission_amount,
    get_platform_revenue,
    apply_promo_discount,
    is_premium_active
)

logger = logging.getLogger('commission_service')

class CommissionProcessor:
    """Обробка комісій для замовлень"""
    
    @staticmethod
    def process_order_commission(order_data, partner_data=None):
        """
        Розраховує комісію для замовлення
        
        Args:
            order_data: {
                'order_id': str,
                'total_amount': float,
                'partner_id': str,
                'promo_code': str (optional)
            }
            partner_data: дані партнера з таблиці
        
        Returns:
            {
                'order_id': str,
                'partner_id': str,
                'original_amount': float,
                'discount_amount': float,
                'final_amount': float,
                'commission_amount': float,
                'platform_revenue': float,
                'commission_rate': float,
                'payment_status': str
            }
        """
        
        order_id = order_data.get('order_id')
        partner_id = order_data.get('partner_id')
        original_amount = float(order_data.get('total_amount', 0))
        promo_code = order_data.get('promo_code')
        
        # За замовчуванням комісія
        commission_rate = COMMISSION_CONFIG['default_rate']
        discount_amount = 0
        final_amount = original_amount
        
        # Якщо є дані партнера, використовуємо його ставку
        if partner_data:
            commission_rate = float(partner_data.get('commission_rate', commission_rate))
            
            # Знижка для premium партнерів
            if partner_data.get('premium_level') and is_premium_active(
                partner_data.get('premium_until')
            ):
                premium_info = PREMIUM_LEVELS.get(partner_data.get('premium_level'))
                if premium_info:
                    commission_rate = max(0, commission_rate - premium_info['discount'])
        
        # Застосовуємо промокод якщо є
        if promo_code:
            # Тут можна додати логіку перевірки промокода
            # На початку припускаємо що скидка 10%
            final_amount, discount_amount = apply_promo_discount(original_amount, 10)
            logger.info(f"Promo code {promo_code} applied: {discount_amount} грн discount")
        
        # Розраховуємо комісію на основі фінальної суми
        commission_amount = get_commission_amount(final_amount, commission_rate=commission_rate)
        platform_revenue = get_platform_revenue(final_amount, commission_amount)
        
        result = {
            'order_id': order_id,
            'partner_id': partner_id,
            'original_amount': round(original_amount, 2),
            'discount_amount': round(discount_amount, 2),
            'final_amount': round(final_amount, 2),
            'commission_amount': round(commission_amount, 2),
            'platform_revenue': round(platform_revenue, 2),
            'commission_rate': commission_rate,
            'payment_status': PAYMENT_STATUSES['pending'],
            'processed_at': datetime.now().isoformat()
        }
        
        logger.info(f"Commission processed for order {order_id}: {commission_amount} грн")
        return result
    
    @staticmethod
    def calculate_weekly_stats(orders_list):
        """
        Розраховує статистику за тиждень для партнера
        
        Args:
            orders_list: список замовлень партнера за тиждень
        
        Returns:
            {
                'total_orders': int,
                'total_revenue': float,
                'total_commissions': float,
                'avg_order_value': float,
                'platform_revenue': float
            }
        """
        
        if not orders_list:
            return {
                'total_orders': 0,
                'total_revenue': 0.0,
                'total_commissions': 0.0,
                'avg_order_value': 0.0,
                'platform_revenue': 0.0
            }
        
        total_revenue = sum(float(order.get('final_amount', 0)) for order in orders_list)
        total_commissions = sum(float(order.get('commission_amount', 0)) for order in orders_list)
        platform_revenue = sum(float(order.get('platform_revenue', 0)) for order in orders_list)
        
        return {
            'total_orders': len(orders_list),
            'total_revenue': round(total_revenue, 2),
            'total_commissions': round(total_commissions, 2),
            'avg_order_value': round(total_revenue / len(orders_list), 2) if orders_list else 0,
            'platform_revenue': round(platform_revenue, 2)
        }
    
    @staticmethod
    def generate_commission_invoice(partner_id, period_stats):
        """
        Генерує рахунок комісії для партнера
        
        Args:
            partner_id: ID партнера
            period_stats: статистика за період
        
        Returns:
            dict з деталями рахунку
        """
        
        invoice = {
            'partner_id': partner_id,
            'invoice_date': datetime.now().isoformat(),
            'period_start': None,  # Можна передати з аргументів
            'period_end': None,
            'total_orders': period_stats.get('total_orders', 0),
            'total_revenue': period_stats.get('total_revenue', 0),
            'commission_amount': period_stats.get('total_commissions', 0),
            'platform_revenue': period_stats.get('platform_revenue', 0),
            'payment_status': PAYMENT_STATUSES['pending'],
            'due_date': None
        }
        
        logger.info(f"Invoice generated for partner {partner_id}: {invoice['commission_amount']} грн")
        return invoice


class PromoCodeManager:
    """Управління промокодами"""
    
    @staticmethod
    def validate_promo_code(code, promo_codes_list):
        """
        Перевіряє валідність промокода
        
        Returns:
            (is_valid: bool, discount_percent: float, error: str)
        """
        
        for promo in promo_codes_list:
            if promo.get('code') != code:
                continue
            
            # Перевіраємо статус
            if promo.get('status') != 'active':
                return False, 0, "Промокод неактивний"
            
            # Перевіраємо ліміт використання
            usage_count = int(promo.get('usage_count', 0))
            usage_limit = int(promo.get('usage_limit', 0))
            
            if usage_limit > 0 and usage_count >= usage_limit:
                return False, 0, "Промокод вичерпав ліміт використання"
            
            # Перевіраємо дату закінчення
            expiry_date = promo.get('expiry_date')
            if expiry_date:
                try:
                    expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
                    if datetime.now() > expiry:
                        return False, 0, "Промокод закінчився"
                except ValueError:
                    pass
            
            discount = float(promo.get('discount_percent', 0))
            return True, discount, None
        
        return False, 0, "Промокод не знайдений"
    
    @staticmethod
    def generate_promo_code(length=6):
        """
        Генерує новий промокод
        
        Returns:
            str - промокод
        """
        import random
        import string
        
        characters = string.ascii_uppercase + string.digits
        code = ''.join(random.choice(characters) for _ in range(length))
        
        logger.info(f"Generated promo code: {code}")
        return code


class PartnerAnalytics:
    """Аналітика для партнерів"""
    
    @staticmethod
    def calculate_partner_rating(reviews_list):
        """
        Розраховує рейтинг партнера на основі відгуків
        
        Returns:
            float - рейтинг від 1 до 5
        """
        
        if not reviews_list:
            return 0.0
        
        ratings = [float(review.get('rating', 0)) for review in reviews_list if review.get('rating')]
        
        if not ratings:
            return 0.0
        
        avg_rating = sum(ratings) / len(ratings)
        return round(min(5.0, max(1.0, avg_rating)), 1)
    
    @staticmethod
    def get_partner_performance(partner_stats):
        """
        Аналізує продуктивність партнера
        
        Returns:
            dict з рекомендаціями
        """
        
        total_orders = partner_stats.get('total_orders', 0)
        avg_order_value = partner_stats.get('avg_order_value', 0)
        
        performance = {
            'order_volume': 'low' if total_orders < 20 else 'medium' if total_orders < 100 else 'high',
            'revenue': 'low' if avg_order_value < 100 else 'medium' if avg_order_value < 300 else 'high',
            'recommendations': []
        }
        
        # Рекомендації
        if total_orders < 20:
            performance['recommendations'].append("Збільшіть кількість замовлень через промо")
        
        if avg_order_value < 100:
            performance['recommendations'].append("Спробуйте запропонувати комбо-набори")
        
        if total_orders > 100 and avg_order_value > 300:
            performance['recommendations'].append("Розгляньте преміум-рівень для більшої видимості")
        
        return performance