import os
import logging
from urllib.parse import urlparse

logger = logging.getLogger('config')

# Dotenv (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ .env loaded")
except ImportError:
    logger.warning("⚠️ python-dotenv not found")

# Telegram Bot Token
BOT_TOKEN = os.environ.get('BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.critical("❌ BOT_TOKEN not set")

# Google Gemini API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY not set")

# Google Sheets
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID') or os.environ.get('GOOGLE_SHEET_ID')
if not SPREADSHEET_ID:
    logger.warning("⚠️ SPREADSHEET_ID not set")

# Google Credentials
GOOGLE_CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS_JSON')
CREDS_B64 = os.environ.get('CREDS_B64')

if not GOOGLE_CREDENTIALS_JSON and not CREDS_B64:
    logger.warning("⚠️ Google credentials not set")

# Operator
OPERATOR_CHAT_ID_RAW = os.environ.get('OPERATOR_CHAT_ID', '')
OPERATOR_CHAT_ID = int(OPERATOR_CHAT_ID_RAW) if OPERATOR_CHAT_ID_RAW and OPERATOR_CHAT_ID_RAW.isdigit() else None

# Webhook Configuration
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com/webhook')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')

if not WEBHOOK_SECRET:
    logger.critical("❌ WEBHOOK_SECRET not set - SECURITY RISK!")
    raise RuntimeError("WEBHOOK_SECRET must be set")

# RENDER_URL - базова URL
if WEBHOOK_URL:
    parsed = urlparse(WEBHOOK_URL)
    RENDER_URL = f"{parsed.scheme}://{parsed.netloc}"
else:
    RENDER_URL = 'https://ferrik-bot-zvev.onrender.com'

# App Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))
TIMEZONE_NAME = os.environ.get('TIMEZONE_NAME', 'Europe/Kiev')

# Features
ENABLE_AI_RECOMMENDATIONS = os.environ.get('ENABLE_AI_RECOMMENDATIONS', 'True').lower() == 'true'
GEMINI_MODEL_NAME = os.environ.get('GEMINI_MODEL_NAME', 'gemini-1.5-flash')
MIN_DELIVERY_AMOUNT = int(os.environ.get('MIN_DELIVERY_AMOUNT', 300))

# Cache
MENU_CACHE_TTL = int(os.environ.get('MENU_CACHE_TTL', 3600))

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = int(os.environ.get('MAX_REQUESTS_PER_MINUTE', 60))

# Messages
ERROR_MESSAGES = {
    'generic': 'Виникла помилка. Спробуйте пізніше.',
    'ai_unavailable': 'AI недоступний.',
    'menu_unavailable': 'Меню недоступне.',
    'sheets_error': 'Помилка Google Sheets.'
}

SUCCESS_MESSAGES = {
    'order_created': 'Замовлення створено!',
    'user_registered': 'Ви зареєстровані!'
}

def validate_config():
    """Валідація конфігурації"""
    issues = []
    
    if not BOT_TOKEN:
        issues.append("BOT_TOKEN missing")
    
    if not GEMINI_API_KEY and ENABLE_AI_RECOMMENDATIONS:
        issues.append("GEMINI_API_KEY missing but AI enabled")
    
    if not SPREADSHEET_ID:
        issues.append("SPREADSHEET_ID missing")
    
    if not GOOGLE_CREDENTIALS_JSON and not CREDS_B64:
        issues.append("Google credentials missing")
    
    if issues:
        logger.warning("⚠️ Configuration issues:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        return False
    
    logger.info("✅ Config valid")
    return True

def log_config():
    """Логування конфігурації"""
    logger.info("=" * 50)
    logger.info("Configuration:")
    logger.info(f"  BOT_TOKEN: {'✅' if BOT_TOKEN else '❌'}")
    logger.info(f"  GEMINI_API_KEY: {'✅' if GEMINI_API_KEY else '❌'}")
    logger.info(f"  SPREADSHEET_ID: {'✅' if SPREADSHEET_ID else '❌'}")
    logger.info(f"  GOOGLE_CREDENTIALS: {'✅' if GOOGLE_CREDENTIALS_JSON else '❌'}")
    logger.info(f"  WEBHOOK_SECRET: {'✅' if WEBHOOK_SECRET else '❌'}")
    logger.info(f"  RENDER_URL: {RENDER_URL}")
    logger.info(f"  DEBUG: {DEBUG}")
    logger.info(f"  PORT: {PORT}")
    logger.info("=" * 50)
