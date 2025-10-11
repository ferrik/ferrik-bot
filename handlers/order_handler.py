"""
Order Handler with Commission Processing
Обробка замовлень з розрахунком комісій
"""

import logging
import json
from datetime import datetime
from config import (
    COMMISSION_CONFIG,
    ORDER_EXTENSION_FIELDS,
    PROMO_FIELDS,
    format_commission_report
)
from services.commission_service import (
    CommissionProcessor,
    PromoCodeManager,
    PartnerAnalytics
)

logger = logging.getLogger('order_handler')


class OrderManager:
    """Управління замовленнями з комісіями"""
    
    def __init__(self, sheets_service, partners_data=None, promo_codes=None):
        """
        Args:
            sheets_service: сервіс для роботи з Google Sheets
            partners_data: список партнерів з таблиці
            promo_codes: список промокодів з таблиці
        """
        self.sheets = sheets_service
        self.partners_data = partners_data or []
        self.promo_codes = promo_codes or []
        self.commission_processor = CommissionProcessor()
        self.promo_manager = PromoCodeManager()
    
    def create_order_with_commission(self, user_id, items, partner_id, promo_code=None):
        """
        Створює замовлення та розраховує комісію
        
        Args:
            user_id: Telegram ID користувача
            items: список товарів [{id, name, price, quantity}, ...]
            partner_id: ID партнера (ресторану)
            promo_code: промокод (опціонально)
        
        Returns:
            {
                'order_id': str,
                'success': bool,
                'message': str,
                'commission_info': dict
            }
        """
        
        try:
            # Розраховуємо загальну суму
            order_total = sum(
                float(item.get('price', 0)) * int(item.get('quantity', 1))
                for item in items
            )
            
            if order_total < COMMISSION_CONFIG['min_order_value']:
                return {
                    'success': False,
                    'message': f"Мінімальна сума замовлення: {COMMISSION_CONFIG['min_order_value']} грн"
                }
            
            # Знаходимо дані партнера
            partner_data = next(
                (p for p in self.partners_data if p.get('id') == partner_id),
                None
            )
            
            if not partner_data:
                logger.warning(f"Partner {partner_id} not found")
                partner_data = {'id': partner_id, 'commission_rate': COMMISSION_CONFIG['default_rate']}
            
            # Перевіряємо промокод
            discount_amount = 0
            if promo_code:
                is_valid, discount_percent, error = self.promo_manager.validate_promo_code(
                    promo_code,
                    self.promo_codes
                )
                
                if not is_valid:
                    logger.warning(f"Invalid promo code: {promo_code} - {error}")
                    # Продовжуємо без промокода, але сповіщаємо користувача
                    promo_code = None
                else:
                    # Застосовуємо знижку
                    from config import apply_promo_discount
                    order_total, discount_amount = apply_promo_discount(order_total, discount_percent)
            
            # Розраховуємо комісію
            order_data = {
                'order_id': self._generate_order_id(),
                'partner_id': partner_id,
                'total_amount': order_total,
                'promo_code': promo_code
            }
            
            commission_info = self.commission_processor.process_order_commission(
                order_data,
                partner_data
            )
            
            # Формуємо замовлення для таблиці
            order_record = {
                'order_id': commission_info['order_id'],
                'user_id': user_id,
                'partner_id': partner_id,
                'items': json.dumps(items),  # JSON сериализация
                'total_amount': commission_info['original_amount'],
                'discount_amount': commission_info['discount_amount'],
                'final_amount': commission_info['final_amount'],
                'commission_rate': commission_info['commission_rate'],
                'commission_amount': commission_info['commission_amount'],
                'platform_revenue': commission_info['platform_revenue'],
                'promo_code': promo_code or '',
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            logger.info(f"Order {order_record['order_id']} created with commission {commission_info['commission_amount']} грн")
            
            return {
                'success': True,
                'order_id': commission_info['order_id'],
                'message': 'Замовлення оформлене',
                'commission_info': commission_info,
                'order_record': order_record
            }
        
        except Exception as e:
            logger.error(f"Error creating order: {e}", exc_info=True)
            return {
                'success': False,
                'message': 'Помилка при оформленні замовлення'
            }
    
    def get_order_summary(self, order_data):
        """
        Форматує резюме замовлення для користувача
        
        Returns:
            str - текст резюме для Telegram
        """
        
        summary = f"""
📋 РЕЗЮМЕ ЗАМОВЛЕННЯ

ID: {order_data.get('order_id')}

💰 Вартість:
• Сума товарів: {order_data.get('original_amount', 0)} грн
• Знижка: {order_data.get('discount_amount', 0)} грн
• До сплати: {order_data.get('final_amount', 0)} грн

📊 Деталі:
• Партнер: {order_data.get('partner_name', 'N/A')}
• Час доставки: {order_data.get('delivery_time', 'N/A')} хв
• Статус: {order_data.get('status', 'обробка')}

✅ Замовлення підтверджено
🚚 Чекайте на доставку
"""
        return summary
    
    def get_partner_commission_summary(self, partner_id, orders_list):
        """
        Отримує резюме комісій для партнера
        
        Returns:
            str - резюме для Telegram
        """
        
        partner_data = next(
            (p for p in self.partners_data if p.get('id') == partner_id),
            None
        )
        
        if not partner_data:
            return "Партнер не знайдений"
        
        # Фільтруємо замовлення партнера
        partner_orders = [o for o in orders_list if o.get('partner_id') == partner_id]
        
        # Розраховуємо статистику
        stats = CommissionProcessor.calculate_weekly_stats(partner_orders)
        
        partner_data.update(stats)
        
        return format_commission_report(partner_data)
    
    def _generate_order_id(self):
        """Генерує унікальний ID замовлення"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        import random
        random_part = random.randint(1000, 9999)
        return f"ORD-{timestamp}-{random_part}"


class PromoCodeHandler:
    """Обробка промокодів"""
    
    def __init__(self, sheets_service):
        self.sheets = sheets_service
        self.promo_manager = PromoCodeManager()
    
    def apply_promo_to_order(self, promo_code, order_total, promo_codes_list):
        """
        Застосовує промокод до замовлення
        
        Returns:
            {
                'success': bool,
                'new_total': float,
                'discount': float,
                'message': str
            }
        """
        
        is_valid, discount_percent, error = self.promo_manager.validate_promo_code(
            promo_code,
            promo_codes_list
        )
        
        if not is_valid:
            return {
                'success': False,
                'message': error or 'Промокод невалідний'
            }
        
        from config import apply_promo_discount
        new_total, discount = apply_promo_discount(order_total, discount_percent)
        
        return {
            'success': True,
            'new_total': new_total,
            'discount': discount,
            'discount_percent': discount_percent,
            'message': f"Знижка {discount_percent}% застосована: економія {discount} грн"
        }
    
    def create_promo_for_partner(self, partner_id, discount_percent, usage_limit=None, expiry_days=30):
        """
        Створює новий промокод для партнера
        
        Returns:
            dict з деталями промокода
        """
        
        code = self.promo_manager.generate_promo_code()
        
        from datetime import timedelta
        expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime('%Y-%m-%d')
        
        promo_data = {
            'code': code,
            'partner_id': partner_id,
            'discount_percent': discount_percent,
            'usage_limit': usage_limit or 0,  # 0 = неограниченно
            'usage_count': 0,
            'expiry_date': expiry_date,
            'status': 'active',
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f"Promo code created: {code} for partner {partner_id}")
        
        return promo_data


class OrderAnalytics:
    """Аналітика замовлень"""
    
    @staticmethod
    def get_order_completion_rate(orders_list):
        """
        Розраховує % завершених замовлень
        
        Returns:
            float - відсоток від 0 до 100
        """
        
        if not orders_list:
            return 0.0
        
        completed = len([o for o in orders_list if o.get('status') == 'completed'])
        return round((completed / len(orders_list)) * 100, 1)
    
    @staticmethod
    def get_average_order_value(orders_list):
        """
        Розраховує середню вартість замовлення
        
        Returns:
            float - середня сума
        """
        
        if not orders_list:
            return 0.0
        
        total = sum(float(o.get('final_amount', 0)) for o in orders_list)
        return round(total / len(orders_list), 2)
    
    @staticmethod
    def get_refund_rate(orders_list):
        """
        Розраховує % повернень коштів
        
        Returns:
            float - відсоток від 0 до 100
        """
        
        if not orders_list:
            return 0.0
        
        refunded = len([o for o in orders_list if o.get('refund_status') == 'refunded'])
        return round((refunded / len(orders_list)) * 100, 1)