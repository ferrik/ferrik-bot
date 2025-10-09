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

# Environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Server
PORT = int(os.getenv('PORT', 10000))

# ============================================================
# TELEGRAM
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
BOT_TOKEN = TELEGRAM_BOT_TOKEN  # Аліас для зворотної сумісності

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not set!")

# Webhook configuration
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
RENDER_URL = os.getenv('RENDER_EXTERNAL_URL', '')  # ⭐ ДОДАНО ЦЮ ЗМІННУ

# Operator chat ID (має бути числом, не hash)
OPERATOR_CHAT_ID_STR = os.getenv('OPERATOR_CHAT_ID', '')
OPERATOR_CHAT_ID: Optional[int] = None

if OPERATOR_CHAT_ID_STR:
    try:
        OPERATOR_CHAT_ID = int(OPERATOR_CHAT_ID_STR)
    except ValueError:
        logger.error(f"❌ Invalid OPERATOR_CHAT_ID: {OPERATOR_CHAT_ID_STR}")
        logger.info("💡 OPERATOR_CHAT_ID має бути числом (наприклад: 123456789)")

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

# Cart settings
CART_TTL_HOURS = int(os.getenv('CART_TTL_HOURS', 24))
MAX_CART_ITEMS = int(os.getenv('MAX_CART_ITEMS', 50))

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

# ============================================================
# DISPLAY CONFIG (for debugging)
# ============================================================

def display_config():
    """Показати конфігурацію (без секретів)"""
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