import os
import logging
from dotenv import load_dotenv

# Завантажуємо змінні з .env файлу (якщо є)
load_dotenv()

# Налаштування логування
logger = logging.getLogger('config')

# Telegram Bot Token
BOT_TOKEN = os.environ.get('BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.warning("BOT_TOKEN not found, bot will not work properly")

# Google Gemini API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found, AI features will be disabled")

# Google Sheets Configuration
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID') or os.environ.get('GOOGLE_SHEET_ID')
if not SPREADSHEET_ID:
    logger.warning("SPREADSHEET_ID not found, Google Sheets features will be disabled")

# Google Service Account Credentials
GOOGLE_CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS_JSON')
CREDS_B64 = os.environ.get('CREDS_B64')

if not GOOGLE_CREDENTIALS_JSON and not CREDS_B64:
    logger.warning("Neither GOOGLE_CREDENTIALS_JSON nor CREDS_B64 found")

# Operator chat ID
OPERATOR_CHAT_ID = os.environ.get('OPERATOR_CHAT_ID', '')

# Webhook Configuration
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com/webhook')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', '')

# App Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

# Feature Flags
ENABLE_AI_RECOMMENDATIONS = os.environ.get('ENABLE_AI_RECOMMENDATIONS', 'True').lower() == 'true'
ENABLE_GOOGLE_SHEETS = os.environ.get('ENABLE_GOOGLE_SHEETS', 'True').lower() == 'true'

# Cache Configuration
MENU_CACHE_TTL = int(os.environ.get('MENU_CACHE_TTL', 3600))  # 1 hour

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = int(os.environ.get('MAX_REQUESTS_PER_MINUTE', 60))

# Delivery Configuration
MIN_DELIVERY_AMOUNT = float(os.environ.get('MIN_DELIVERY_AMOUNT', 200))
DELIVERY_COST = float(os.environ.get('DELIVERY_COST', 50))
DELIVERY_RADIUS_KM = float(os.environ.get('DELIVERY_RADIUS_KM', 7))

# Error Messages
ERROR_MESSAGES = {
    'generic': 'Виникла помилка. Спробуйте пізніше.',
    'ai_unavailable': 'AI рекомендації тимчасово недоступні.',
    'menu_unavailable': 'Меню тимчасово недоступне.',
    'sheets_error': 'Помилка підключення до Google Sheets.'
}

# Success Messages
SUCCESS_MESSAGES = {
    'order_created': 'Замовлення успішно створено!',
    'user_registered': 'Ви успішно зареєстровані!'
}

# Валідація конфігурації
def validate_config():
    """Валідація конфігурації при запуску"""
    issues = []
    
    if not BOT_TOKEN:
        issues.append("BOT_TOKEN is missing - bot will not function")
    
    if not GEMINI_API_KEY:
        issues.append("GEMINI_API_KEY is missing - AI features disabled")
    
    if not SPREADSHEET_ID:
        issues.append("SPREADSHEET_ID is missing - Google Sheets features disabled")
    
    if not GOOGLE_CREDENTIALS_JSON and not CREDS_B64:
        issues.append("Google credentials missing - cannot access Google Sheets")
    
    if issues:
        logger.warning("Configuration issues detected:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        return False
    
    logger.info("✅ All required configuration present")
    return True

# Логування конфігурації (без чутливих даних)
def log_config():
    """Логування поточної конфігурації"""
    logger.info("=" * 50)
    logger.info("Configuration Summary:")
    logger.info(f"  BOT_TOKEN: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
    logger.info(f"  GEMINI_API_KEY: {'✅ Set' if GEMINI_API_KEY else '❌ Missing'}")
    logger.info(f"  SPREADSHEET_ID: {'✅ Set' if SPREADSHEET_ID else '❌ Missing'}")
    logger.info(f"  CREDS_B64: {'✅ Set' if CREDS_B64 else '❌ Missing'}")
    logger.info(f"  OPERATOR_CHAT_ID: {'✅ Set' if OPERATOR_CHAT_ID else '⚠️ Not set'}")
    logger.info(f"  WEBHOOK_URL: {WEBHOOK_URL}")
    logger.info(f"  DEBUG: {DEBUG}")
    logger.info(f"  PORT: {PORT}")
    logger.info("=" * 50)

# Запуск валідації та логування при імпорті
try:
    validate_config()
    log_config()
except Exception as e:
    logger.error(f"Error during config validation: {e}")