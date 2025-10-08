"""
Configuration для Telegram Bot
(адаптовано під Render / webhook)
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Завантажити .env файл (Render встановлює env vars в середовищі)
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

WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # optional, used for logging
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

if not WEBHOOK_SECRET:
    logger.error("❌ WEBHOOK_SECRET not set in environment!")

# ============================================================================
# GOOGLE SHEETS CONFIGURATION
# ============================================================================

GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
GOOGLE_CREDS_B64 = os.getenv('GOOGLE_CREDS_B64')

# If base64 provided, decode to JSON string
if GOOGLE_CREDS_B64 and not GOOGLE_CREDENTIALS_JSON:
    import base64
    try:
        GOOGLE_CREDENTIALS_JSON = base64.b64decode(GOOGLE_CREDS_B64).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decode GOOGLE_CREDS_B64: {e}")
        GOOGLE_CREDENTIALS_JSON = None

# ============================================================================
# GEMINI AI CONFIGURATION (optional)
# ============================================================================

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', None)

# ============================================================================
# OPERATOR CONFIGURATION
# ============================================================================

OPERATOR_CHAT_ID = os.getenv('OPERATOR_CHAT_ID')
if OPERATOR_CHAT_ID:
    try:
        OPERATOR_CHAT_ID = int(OPERATOR_CHAT_ID)
    except Exception:
        logger.warning("Invalid OPERATOR_CHAT_ID, ignoring")
        OPERATOR_CHAT_ID = None

# ============================================================================
# REDIS CONFIGURATION (optional)
# ============================================================================

REDIS_URL = os.getenv('REDIS_URL')  # e.g. redis://:password@host:port/0

# ============================================================================
# APP CONFIG
# ============================================================================

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
import logging as _logging
_logging.getLogger().setLevel(getattr(_logging, LOG_LEVEL, _logging.INFO))
PORT = int(os.getenv('PORT', 5000))

# ============================================================================
# Limits / Defaults
# ============================================================================

MAX_CART_ITEMS = int(os.getenv('MAX_CART_ITEMS', 50))
CART_TTL_HOURS = int(os.getenv('CART_TTL_HOURS', 24))

# ============================================================================
# Minimal validation called by main.py
# ============================================================================

def validate_config():
    errors = []
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN not set")
    if not WEBHOOK_SECRET:
        errors.append("WEBHOOK_SECRET not set")
    if not GOOGLE_SHEET_ID:
        errors.append("GOOGLE_SHEET_ID not set")
    if not (GOOGLE_CREDENTIALS_JSON):
        errors.append("Google credentials not set (GOOGLE_CREDENTIALS_JSON or GOOGLE_CREDS_B64)")
    if errors:
        for e in errors:
            logger.error("Config error: %s", e)
        raise ValueError("; ".join(errors))
    logger.info("Config validation passed")

def log_config():
    logger.info("==== BOT CONFIG ====")
    logger.info("ENVIRONMENT: %s", ENVIRONMENT)
    logger.info("WEBHOOK_URL: %s", WEBHOOK_URL if WEBHOOK_URL else "Not set")
    logger.info("GOOGLE_SHEET_ID: %s", GOOGLE_SHEET_ID if GOOGLE_SHEET_ID else "Not set")
    logger.info("GEMINI_API_KEY: %s", "Set" if GEMINI_API_KEY else "Not set")
    logger.info("=====================")

