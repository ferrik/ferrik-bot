"""
Configuration для Telegram Bot
Всі environment variables та константи

ВАЖЛИВО:
- Завжди використовуйте .env файл для secrets
- Ніколи не комітьте реальні credentials
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Завантажити .env файл
load_dotenv()

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# TELEGRAM CONFIGURATION
# ============================================================================

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not set in environment!")
    raise ValueError("BOT_TOKEN is required")

WEBHOOK_URL = os.getenv('WEBHOOK_URL')
if not WEBHOOK_URL:
    logger.warning("⚠️  WEBHOOK_URL not set. Webhook mode won't work.")

WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
    logger.error("❌ WEBHOOK_SECRET not set in environment!")
    raise ValueError("WEBHOOK_SECRET is required (min 32 characters)")

if len(WEBHOOK_SECRET) < 32:
    logger.error(f"❌ WEBHOOK_SECRET too short: {len(WEBHOOK_SECRET)} chars (min 32)")
    raise ValueError("WEBHOOK_SECRET must be at least 32 characters")


# ============================================================================
# GOOGLE SHEETS CONFIGURATION
# ============================================================================

GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
if not GOOGLE_SHEET_ID:
    logger.error("❌ GOOGLE_SHEET_ID not set!")
    raise ValueError("GOOGLE_SHEET_ID is required")

# Google credentials можуть бути або JSON строкою або base64
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
GOOGLE_CREDS_B64 = os.getenv('GOOGLE_CREDS_B64')

if not GOOGLE_CREDENTIALS_JSON and not GOOGLE_CREDS_B64:
    logger.error("❌ Google credentials not set!")
    raise ValueError("Either GOOGLE_CREDENTIALS_JSON or GOOGLE_CREDS_B64 required")

# Декодувати base64 якщо використовується
if GOOGLE_CREDS_B64 and not GOOGLE_CREDENTIALS_JSON:
    import base64
    import json
    try:
        decoded = base64.b64decode(GOOGLE_CREDS_B64)
        GOOGLE_CREDENTIALS_JSON = decoded.decode('utf-8')
    except Exception as e:
        logger.error(f"❌ Failed to decode GOOGLE_CREDS_B64: {e}")
        raise


# ============================================================================
# GEMINI AI CONFIGURATION
# ============================================================================

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("⚠️  GEMINI_API_KEY not set. AI features will be disabled.")


# ============================================================================
# OPERATOR CONFIGURATION
# ============================================================================

OPERATOR_CHAT_ID = os.getenv('OPERATOR_CHAT_ID')
if not OPERATOR_CHAT_ID:
    logger.warning("⚠️  OPERATOR_CHAT_ID not set. Operator notifications disabled.")
else:
    try:
        OPERATOR_CHAT_ID = int(OPERATOR_CHAT_ID)
    except ValueError:
        logger.error(f"❌ Invalid OPERATOR_CHAT_ID: {OPERATOR_CHAT_ID}")
        OPERATOR_CHAT_ID = None


# ============================================================================
# REDIS CONFIGURATION (Optional)
# ============================================================================

REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    logger.info(f"✅ Redis URL configured: {REDIS_URL.split('@')[0]}...")
else:
    logger.warning("⚠️  REDIS_URL not set. Using in-memory storage (not suitable for production with multiple workers)")


# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================

# Environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'

# Debug mode (тільки для development!)
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
if FLASK_DEBUG and IS_PRODUCTION:
    logger.warning("⚠️  Debug mode enabled in production! This is dangerous!")

# Logging level
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.getLogger().setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Port
PORT = int(os.getenv('PORT', 5000))


# ============================================================================
# MENU FIELD NAMES (для backward compatibility)
# ============================================================================

# Константи для старого коду - поступово замінюйте на MenuField
KEY_NAME = "Назва Страви"
KEY_CATEGORY = "Категорія"
KEY_PRICE = "Ціна"
KEY_DESCRIPTION = "Опис"
KEY_ID = "ID"


# ============================================================================
# RATE LIMITING CONFIGURATION
# ============================================================================

# Максимум запитів на користувача
MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', 30))

# Максимум запитів до Telegram API
TELEGRAM_RATE_LIMIT = 30  # requests per second


# ============================================================================
# CART CONFIGURATION
# ============================================================================

# TTL для корзини (годин)
CART_TTL_HOURS = int(os.getenv('CART_TTL_HOURS', 24))

# Максимум товарів в корзині
MAX_CART_ITEMS = int(os.getenv('MAX_CART_ITEMS', 50))

# Максимальна кількість одного товару
MAX_ITEM_QUANTITY = int(os.getenv('MAX_ITEM_QUANTITY', 99))


# ============================================================================
# VALIDATION & SECURITY
# ============================================================================

# Мінімальна довжина номера телефону
MIN_PHONE_LENGTH = 10

# Мінімальна довжина адреси
MIN_ADDRESS_LENGTH = 10

# Дозволені символи в пошуковому запиті
ALLOWED_SEARCH_CHARS = r'^[а-яА-ЯіІїЇєЄa-zA-Z0-9\s\-,.\(\)]+$'


# ============================================================================
# STARTUP CHECKS
# ============================================================================

def validate_config():
    """
    Перевіряє що всі критичні змінні встановлені
    
    Викликається при старті додатку
    
    Raises:
        ValueError: якщо критичні змінні відсутні
    """
    errors = []
    
    # Критичні змінні
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN not set")
    
    if not WEBHOOK_SECRET:
        errors.append("WEBHOOK_SECRET not set")
    elif len(WEBHOOK_SECRET) < 32:
        errors.append(f"WEBHOOK_SECRET too short ({len(WEBHOOK_SECRET)} chars, need 32+)")
    
    if not GOOGLE_SHEET_ID:
        errors.append("GOOGLE_SHEET_ID not set")
    
    if not GOOGLE_CREDENTIALS_JSON:
        errors.append("Google credentials not set")
    
    # Попередження (не критично)
    warnings = []
    
    if not GEMINI_API_KEY:
        warnings.append("GEMINI_API_KEY not set - AI features disabled")
    
    if not OPERATOR_CHAT_ID:
        warnings.append("OPERATOR_CHAT_ID not set - notifications disabled")
    
    if not REDIS_URL and IS_PRODUCTION:
        warnings.append("REDIS_URL not set in production - using in-memory storage")
    
    # Вивести результати
    if errors:
        logger.error("❌ Configuration errors:")
        for error in errors:
            logger.error(f"   - {error}")
        raise ValueError(f"Configuration invalid: {'; '.join(errors)}")
    
    if warnings:
        logger.warning("⚠️  Configuration warnings:")
        for warning in warnings:
            logger.warning(f"   - {warning}")
    
    logger.info("✅ Configuration validated successfully")
    return True


def log_config():
    """
    Логує конфігурацію (без секретів!)
    """
    logger.info("=" * 60)
    logger.info("BOT CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Debug mode: {FLASK_DEBUG}")
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"Port: {PORT}")
    logger.info(f"Bot token: {BOT_TOKEN[:10]}***" if BOT_TOKEN else "Not set")
    logger.info(f"Webhook URL: {WEBHOOK_URL}" if WEBHOOK_URL else "Not set")
    logger.info(f"Webhook secret: {WEBHOOK_SECRET[:10]}***" if WEBHOOK_SECRET else "Not set")
    logger.info(f"Sheet ID: {GOOGLE_SHEET_ID}" if GOOGLE_SHEET_ID else "Not set")
    logger.info(f"Gemini API: {'Configured' if GEMINI_API_KEY else 'Not set'}")
    logger.info(f"Operator ID: {OPERATOR_CHAT_ID}" if OPERATOR_CHAT_ID else "Not set")
    logger.info(f"Redis URL: {'Configured' if REDIS_URL else 'In-memory mode'}")
    logger.info(f"Cart TTL: {CART_TTL_HOURS} hours")
    logger.info(f"Max cart items: {MAX_CART_ITEMS}")
    logger.info("=" * 60)


# ============================================================================
# INITIALIZATION
# ============================================================================

# Валідація при імпорті
try:
    validate_config()
    log_config()
except Exception as e:
    logger.error(f"❌ Configuration failed: {e}")
    if IS_PRODUCTION:
        # В production не запускаємося з невалідною конфігурацією
        sys.exit(1)
    else:
        # В development показуємо помилку але не падаємо
        logger.warning("⚠️  Running with invalid config in development mode")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Telegram
    'BOT_TOKEN',
    'WEBHOOK_URL',
    'WEBHOOK_SECRET',
    
    # Google Sheets
    'GOOGLE_SHEET_ID',
    'GOOGLE_CREDENTIALS_JSON',
    
    # Gemini
    'GEMINI_API_KEY',
    
    # Operator
    'OPERATOR_CHAT_ID',
    
    # Redis
    'REDIS_URL',
    
    # App
    'ENVIRONMENT',
    'IS_PRODUCTION',
    'FLASK_DEBUG',
    'LOG_LEVEL',
    'PORT',
    
    # Field names
    'KEY_NAME',
    'KEY_CATEGORY',
    'KEY_PRICE',
    'KEY_DESCRIPTION',
    'KEY_ID',
    
    # Limits
    'MAX_REQUESTS_PER_MINUTE',
    'TELEGRAM_RATE_LIMIT',
    'CART_TTL_HOURS',
    'MAX_CART_ITEMS',
    'MAX_ITEM_QUANTITY',
    
    # Functions
    'validate_config',
    'log_config',
]