# ============================================================
# MONETIZATION CONFIGURATION
# ============================================================

# Sheet names with Ukrainian support
SHEET_NAMES = {
    'menu': 'Меню',
    'orders': 'Замовлення',
    'partners': 'Партнери',
    'promo_codes': 'Промокоди',
    'reviews': 'Відгуки',
    'analytics': 'Аналітика'
}

# Partners sheet field mapping
PARTNERS_FIELDS = {
    'id': 'A',
    'name': 'B',
    'category': 'C',
    'commission_rate': 'D',
    'premium_level': 'E',
    'premium_until': 'F',
    'status': 'G',
    'phone': 'H',
    'active_orders_week': 'I',
    'revenue_week': 'J',
    'rating': 'K'
}

# Orders extension fields (добавляют к существующим)
ORDER_EXTENSION_FIELDS = {
    'partner_id': 'Q',
    'commission_amount': 'R',
    'commission_paid': 'S',
    'payment_status': 'T',
    'platform_revenue': 'U',
    'promo_code': 'V',
    'discount_applied': 'W',
    'refund_status': 'X'
}

# Promo codes sheet
PROMO_FIELDS = {
    'code': 'A',
    'partner_id': 'B',
    'discount_percent': 'C',
    'usage_limit': 'D',
    'usage_count': 'E',
    'expiry_date': 'F',
    'status': 'G',
    'created_by': 'H'
}

# Reviews sheet
REVIEWS_FIELDS = {
    'review_id': 'A',
    'partner_id': 'B',
    'user_id': 'C',
    'rating': 'D',
    'comment': 'E',
    'order_id': 'F',
    'date': 'G',
    'helpful_count': 'H'
}

# Commission configuration
COMMISSION_CONFIG = {
    'default_rate': 5,  # 5% за замовчуванням
    'min_order_value': 50,  # мінімум 50 грн для комісії
    'premium_discount_rate': 2,  # -2% для premium партнерів
    'promo_commission': 15  # 15% з використаних промокодів
}

# Premium levels
PREMIUM_LEVELS = {
    'standard': {
        'name': 'Стандарт',
        'price': 0,
        'discount': 0,
        'features': ['базовий список']
    },
    'premium': {
        'name': 'Преміум',
        'price': 250,
        'discount': 2,
        'features': ['топ списку', 'бадж ⭐', 'рейтинг']
    },
    'exclusive': {
        'name': 'Екслюзив',
        'price': 1000,
        'discount': 5,
        'features': ['топ списку', 'банер', 'персональні підбірки']
    }
}

# Partner statuses
PARTNER_STATUSES = {
    'active': 'активний',
    'inactive': 'неактивний',
    'suspended': 'призупинений',
    'pending': 'очікування'
}

# Payment statuses
PAYMENT_STATUSES = {
    'pending': 'очікування',
    'processing': 'обробка',
    'completed': 'завершено',
    'failed': 'помилка',
    'refunded': 'повернено'
}

# Analytics retention (дні)
ANALYTICS_RETENTION_DAYS = 90

# Commission payment schedule (день місяця)
COMMISSION_PAYMENT_DAY = 5

def get_commission_amount(order_total, partner_id=None, commission_rate=None):
    """
    Розраховує розмір комісії
    
    Args:
        order_total: Сума замовлення
        partner_id: ID партнера (для отримання його ставки)
        commission_rate: Кастомна ставка комісії (%)
    
    Returns:
        Розмір комісії в грн
    """
    if order_total < COMMISSION_CONFIG['min_order_value']:
        return 0
    
    rate = commission_rate or COMMISSION_CONFIG['default_rate']
    return round(order_total * rate / 100, 2)

def get_platform_revenue(order_total, commission_amount):
    """
    Розраховує дохід платформи
    
    Returns:
        Дохід платформи після комісії партнеру
    """
    return round(order_total - commission_amount, 2)

def apply_promo_discount(order_total, discount_percent):
    """
    Застосовує промокод знижку
    
    Returns:
        (нова_сума, розмір_знижки)
    """
    if discount_percent > 100:
        discount_percent = 100
    
    discount_amount = round(order_total * discount_percent / 100, 2)
    new_total = round(order_total - discount_amount, 2)
    
    return new_total, discount_amount

def is_premium_active(premium_until_date):
    """
    Перевіряє чи активний преміум статус
    
    Args:
        premium_until_date: Дата закінчення преміум (YYYY-MM-DD)
    
    Returns:
        True/False
    """
    from datetime import datetime
    
    try:
        expiry = datetime.strptime(premium_until_date, '%Y-%m-%d')
        return datetime.now() < expiry
    except (ValueError, TypeError):
        return False

def get_premium_level_info(level_name):
    """
    Отримує інформацію про преміум рівень
    
    Args:
        level_name: Назва рівня (standard, premium, exclusive)
    
    Returns:
        dict з інформацією про рівень або None
    """
    return PREMIUM_LEVELS.get(level_name)

def format_commission_report(partner_data):
    """
    Форматує звіт комісії для партнера
    
    Returns:
        Красивий текст для Telegram
    """
    total_orders = partner_data.get('active_orders_week', 0)
    revenue = partner_data.get('revenue_week', 0)
    commission_rate = partner_data.get('commission_rate', COMMISSION_CONFIG['default_rate'])
    
    total_commission = get_commission_amount(revenue, commission_rate=commission_rate)
    
    report = f"""
📊 ЗВІТ КОМІСІЇ

Партнер: {partner_data.get('name', 'N/A')}
Період: цей тиждень

Замовлення: {total_orders}
Сума замовлень: {revenue} грн
Ставка комісії: {commission_rate}%
Комісія до сплати: {total_commission} грн

Рейтинг: {partner_data.get('rating', 'N/A')} ⭐
Статус: {PARTNER_STATUSES.get(partner_data.get('status'), 'невідомо')}
"""
    return report