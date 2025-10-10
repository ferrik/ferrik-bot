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
BOT_TOKEN = TELEGRAM_BOT_TOKEN  # Аліас

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

if not GOOGLE_SHEET_ID:
    logger.warning("⚠️  GOOGLE_SHEET_ID not set")

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
# FIELD MAPPING - Google Sheets columns
# ============================================================

# Order sheet columns
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
    'name': 'B',
    'description': 'C',
    'price': 'D',
    'category': 'E',
    'available': 'F',
    'image_url': 'G'
}

# User data columns
USER_FIELDS = {
    'user_id': 'A',
    'username': 'B',
    'phone': 'C',
    'address': 'D',
    'registered': 'E'
}

# Sheet names
SHEET_NAMES = {
    'orders': 'Orders',
    'menu': 'Menu',
    'users': 'Users'
}

# Field mapping class для сумісності з config.field_mapping
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
# HELPER FUNCTIONS
# ============================================================

def normalize_menu_list(menu_data):
    """
    Normalize menu data from Google Sheets
    
    Args:
        menu_data: Raw menu data from sheets
        
    Returns:
        Normalized list of menu items
    """
    if not menu_data:
        return []
    
    normalized = []
    for item in menu_data:
        if isinstance(item, dict):
            normalized_item = {
                'id': item.get('id', ''),
                'name': item.get('name', ''),
                'description': item.get('description', ''),
                'price': float(item.get('price', 0)) if item.get('price') else 0,
                'category': item.get('category', 'Інше'),
                'available': bool(item.get('available', True)),
                'image_url': item.get('image_url', '')
            }
            normalized.append(normalized_item)
    
    return normalized

def create_legacy_compatible_item(item_data):
    """
    Create legacy compatible item format
    
    Args:
        item_data: Item data dict
        
    Returns:
        Legacy formatted item
    """
    if not item_data:
        return None
    
    return {
        'id': str(item_data.get('id', '')),
        'name': str(item_data.get('name', '')),
        'description': str(item_data.get('description', '')),
        'price': float(item_data.get('price', 0)),
        'category': str(item_data.get('category', 'Інше')),
        'available': bool(item_data.get('available', True)),
        'image_url': str(item_data.get('image_url', ''))
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

# ============================================================
# VALIDATION
# ============================================================

def validate_config():
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