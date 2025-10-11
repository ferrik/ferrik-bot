import os
import logging
from typing import Optional

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('config')

# ============================================================
# ОСНОВНІ НАЛАШТУВАННЯ
# ============================================================

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
PORT = int(os.getenv('PORT', 10000))

# ============================================================
# TELEGRAM
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
BOT_TOKEN = TELEGRAM_BOT_TOKEN  # Аліас для сумісності

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not set!")

WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
RENDER_URL = os.getenv('RENDER_EXTERNAL_URL', '')

OPERATOR_CHAT_ID_STR = os.getenv('OPERATOR_CHAT_ID', '')
OPERATOR_CHAT_ID: Optional[int] = None

if OPERATOR_CHAT_ID_STR:
    try:
        OPERATOR_CHAT_ID = int(OPERATOR_CHAT_ID_STR)
    except ValueError:
        logger.error(f"❌ Invalid OPERATOR_CHAT_ID: {OPERATOR_CHAT_ID_STR}")
        logger.info("💡 OPERATOR_CHAT_ID має бути числом")

# ============================================================
# GOOGLE SHEETS
# ============================================================

GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS', '')
GOOGLE_CREDENTIALS_JSON = GOOGLE_CREDENTIALS  # ⭐ ВИПРАВЛЕННЯ для сумісності з sheets.py

if not GOOGLE_SHEET_ID:
    logger.warning("⚠️  GOOGLE_SHEET_ID not set")

if not GOOGLE_CREDENTIALS:
    logger.warning("⚠️  GOOGLE_CREDENTIALS not set")

# ============================================================
# GEMINI AI
# ============================================================

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-pro')

# ============================================================
# REDIS / STORAGE
# ============================================================

REDIS_URL = os.getenv('REDIS_URL', '')
if not REDIS_URL:
    logger.warning("⚠️  REDIS_URL not set. Using in-memory storage (not suitable for production with multiple workers)")

CART_TTL_HOURS = int(os.getenv('CART_TTL_HOURS', 24))
MAX_CART_ITEMS = int(os.getenv('MAX_CART_ITEMS', 50))

# ============================================================
# GOOGLE SHEETS STRUCTURE (基本)
# ============================================================

# Order sheet columns (базові)
ORDER_FIELDS = {
    'order_id': 'A',
    'user_id': 'B',
    'username': 'C',
    'timestamp': 'D',
    'items': 'E',
    'total': 'F',
    'status': 'G',
    'phone': 'H',
    'address': 'I',
    'notes': 'J'
}

# Menu/Product sheet columns
MENU_FIELDS = {
    'id': 'A',
    'category': 'B',
    'name': 'C',
    'description': 'D',
    'price': 'E',
    'restaurant': 'F',
    'delivery_time': 'G',
    'image_url': 'H',
    'available': 'I',
    'cook_time': 'J',
    'allergens': 'K',
    'rating': 'L'
}

# User data columns
USER_FIELDS = {
    'user_id': 'A',
    'username': 'B',
    'phone': 'C',
    'address': 'D',
    'registered': 'E'
}

# Sheet names with Ukrainian support
SHEET_NAMES = {
    'menu': 'Меню',
    'orders': 'Замовлення',
    'partners': 'Партнери',
    'promo_codes': 'Промокоди',
    'reviews': 'Відгуки'
}

# Field mapping class для сумісності
class field_mapping:
    ORDER_FIELDS = ORDER_FIELDS
    MENU_FIELDS = MENU_FIELDS
    USER_FIELDS = USER_FIELDS
    SHEET_NAMES = SHEET_NAMES
    
    @staticmethod
    def get_column_letter(field_name, field_type='order'):
        mapping = {
            'order': ORDER_FIELDS,
            'menu': MENU_FIELDS,
            'user': USER_FIELDS
        }
        return mapping.get(field_type, {}).get(field_name, 'A')
    
    @staticmethod
    def get_sheet_name(sheet_type):
        return SHEET_NAMES.get(sheet_type, 'Sheet1')

# ============================================================
# MONETIZATION - PARTNERS
# ============================================================

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

# Commission configuration
COMMISSION_CONFIG = {
    'default_rate': 5,
    'min_order_value': 50,
    'premium_discount_rate': 2,
    'promo_commission': 15
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

# ============================================================
# MONETIZATION - PROMO CODES
# ============================================================

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

# ============================================================
# MONETIZATION - REVIEWS
# ============================================================

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

# ============================================================
# ORDER EXTENSION FIELDS (для монетизації)
# ============================================================

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

# ============================================================
# HELPER FUNCTIONS - BASIC
# ============================================================

def normalize_menu_list(menu_data):
    """Normalize menu data from Google Sheets"""
    if not menu_data:
        return []
    
    normalized = []
    for item in menu_data:
        if isinstance(item, dict):
            normalized_item = {
                'id': item.get('id', ''),
                'name': item.get('name', ''),
                'category': item.get('category', 'Інше'),
                'description': item.get('description', ''),
                'price': float(item.get('price', 0)) if item.get('price') else 0,
                'restaurant': item.get('restaurant', ''),
                'delivery_time': item.get('delivery_time', 0),
                'image_url': item.get('image_url', ''),
                'available': bool(item.get('available', True)),
                'cook_time': item.get('cook_time', 0),
                'allergens': item.get('allergens', ''),
                'rating': float(item.get('rating', 0)) if item.get('rating') else 0
            }
            normalized.append(normalized_item)
    
    return normalized

def create_legacy_compatible_item(item_data):
    """Create legacy compatible item format"""
    if not item_data:
        return None
    
    return {
        'id': str(item_data.get('id', '')),
        'name': str(item_data.get('name', '')),
        'category': str(item_data.get('category', 'Інше')),
        'description': str(item_data.get('description', '')),
        'price': float(item_data.get('price', 0)),
        'restaurant': str(item_data.get('restaurant', '')),
        'delivery_time': int(item_data.get('delivery_time', 0)),
        'image_url': str(item_data.get('image_url', '')),
        'available': bool(item_data.get('available', True)),
        'cook_time': int(item_data.get('cook_time', 0)),
        'allergens': str(item_data.get('allergens', '')),
        'rating': float(item_data.get('rating', 0))
    }

def format_price(price):
    """Format price for display"""
    try:
        return f"{float(price):.2f} грн"
    except (ValueError, TypeError):
        return "0.00 грн"

def validate_order_item(item):
    """Validate order item structure"""
    required_fields = ['id', 'name', 'price', 'quantity']
    return all(field in item for field in required_fields)

def calculate_order_total(items):
    """Calculate total order price"""
    total = 0
    for item in items:
        try:
            price = float(item.get('price', 0))
            quantity = int(item.get('quantity', 1))
            total += price * quantity
        except (ValueError, TypeError):
            continue
    return total

def parse_cart_item(item_str):
    """Parse cart item from string format"""
    try:
        parts = item_str.split('|')
        return {
            'id': parts[0] if len(parts) > 0 else '',
            'name': parts[1] if len(parts) > 1 else '',
            'price': float(parts[2]) if len(parts) > 2 else 0,
            'quantity': int(parts[3]) if len(parts) > 3 else 1
        }
    except (ValueError, IndexError):
        return None

def format_cart_item(item):
    """Format cart item to string"""
    return f"{item.get('id', '')}|{item.get('name', '')}|{item.get('price', 0)}|{item.get('quantity', 1)}"

# ============================================================
# HELPER FUNCTIONS - MONETIZATION
# ============================================================

def get_commission_amount(order_total, partner_id=None, commission_rate=None):
    """Розраховує розмір комісії"""
    if order_total < COMMISSION_CONFIG['min_order_value']:
        return 0
    
    rate = commission_rate or COMMISSION_CONFIG['default_rate']
    return round(order_total * rate / 100, 2)

def get_platform_revenue(order_total, commission_amount):
    """Розраховує дохід платформи"""
    return round(order_total - commission_amount, 2)

def apply_promo_discount(order_total, discount_percent):
    """Застосовує промокод знижку"""
    if discount_percent > 100:
        discount_percent = 100
    
    discount_amount = round(order_total * discount_percent / 100, 2)
    new_total = round(order_total - discount_amount, 2)
    
    return new_total, discount_amount

def is_premium_active(premium_until_date):
    """Перевіряє чи активний преміум статус"""
    from datetime import datetime
    
    try:
        expiry = datetime.strptime(premium_until_date, '%Y-%m-%d')
        return datetime.now() < expiry
    except (ValueError, TypeError):
        return False

def get_premium_level_info(level_name):
    """Отримує інформацію про преміум рівень"""
    return PREMIUM_LEVELS.get(level_name)

def format_commission_report(partner_data):
    """Форматує звіт комісії для партнера"""
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

# ============================================================
# VALIDATION
# ============================================================

def validate_config():
    """Перевірка конфігурації"""
    warnings = []
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is required")
    
    if not WEBHOOK_URL:
        warnings.append("WEBHOOK_URL not set. Webhook mode won't work.")
    
    if not OPERATOR_CHAT_ID:
        warnings.append("OPERATOR_CHAT_ID not set - notifications disabled")
    
    if not REDIS_URL:
        warnings.append("REDIS_URL not set - using in-memory storage")
    
    if warnings:
        logger.warning("⚠️  Configuration warnings:")
        for w in warnings:
            logger.warning(f"   - {w}")
    
    if errors:
        logger.error("❌ Configuration errors:")
        for e in errors:
            logger.error(f"   - {e}")
        raise ValueError("Configuration validation failed")
    
    logger.info("✅ Configuration validated successfully")

def display_config():
    """Показити конфігурацію (без секретів)"""
    logger.info("=" * 60)
    logger.info("BOT CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"Port: {PORT}")
    logger.info(f"Bot token: {TELEGRAM_BOT_TOKEN[:15]}***" if TELEGRAM_BOT_TOKEN else "Not set")
    logger.info(f"Webhook URL: {WEBHOOK_URL if WEBHOOK_URL else 'Not set'}")
    logger.info(f"Webhook secret: {WEBHOOK_SECRET[:10]}***" if WEBHOOK_SECRET else "Not set")
    logger.info(f"Sheet ID: {GOOGLE_SHEET_ID if GOOGLE_SHEET_ID else 'Not set'}")
    logger.info(f"Gemini API: {'Configured' if GEMINI_API_KEY else 'Not set'}")
    logger.info(f"Operator chat: {OPERATOR_CHAT_ID if OPERATOR_CHAT_ID else 'Not set'}")
    logger.info(f"Redis URL: {REDIS_URL if REDIS_URL else 'In-memory mode'}")
    logger.info(f"Cart TTL: {CART_TTL_HOURS} hours")
    logger.info(f"Max cart items: {MAX_CART_ITEMS}")
    logger.info("=" * 60)

# Run validation on import
try:
    validate_config()
    display_config()
except Exception as e:
    logger.critical(f"❌ Configuration failed: {e}")
    raise