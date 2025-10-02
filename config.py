import os
import logging

# Налаштування логування
logger = logging.getLogger('config')

# Зробимо dotenv необов'язковим для розгортання, де змінні встановлюються напряму.
# Вирішує помилку 'No module named 'dotenv'' під час імпорту.
try:
    from dotenv import load_dotenv
    # Завантажуємо змінні з .env файлу (якщо є). Тільки для локального запуску.
    load_dotenv()
    logger.info("✅ python-dotenv imported and .env loaded (if present).")
except ImportError:
    logger.warning("⚠️ python-dotenv not found. Relying solely on environment variables.")


# Telegram Bot Token
BOT_TOKEN = os.environ.get('BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.warning("⚠️ BOT_TOKEN not found, bot will not work properly")

# Google Gemini API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY not found, AI features will be disabled")

# Google Sheets Configuration
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID') or os.environ.get('GOOGLE_SHEET_ID')
if not SPREADSHEET_ID:
    logger.warning("⚠️ SPREADSHEET_ID not found, Google Sheets features will be disabled")

# Google Service Account Credentials
GOOGLE_CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS_JSON')
CREDS_B64 = os.environ.get('CREDS_B64')

if not GOOGLE_CREDENTIALS_JSON and not CREDS_B64:
    logger.warning("⚠️ Neither GOOGLE_CREDENTIALS_JSON nor CREDS_B64 found")

# Operator chat ID (конвертуємо в int, якщо задано)
OPERATOR_CHAT_ID_RAW = os.environ.get('OPERATOR_CHAT_ID', '')
OPERATOR_CHAT_ID = int(OPERATOR_CHAT_ID_RAW) if OPERATOR_CHAT_ID_RAW and OPERATOR_CHAT_ID_RAW.isdigit() else None

if not OPERATOR_CHAT_ID:
    logger.warning("⚠️ OPERATOR_CHAT_ID not set or invalid")

# Webhook Configuration
# WEBHOOK_URL - це повний шлях до вебхука, включаючи /webhook або таємний шлях
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com/webhook')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'Ferrik123')

# RENDER_URL - це базова URL для health check та setWebhook
# Більш безпечний спосіб отримати базову URL
if WEBHOOK_URL:
    # Видаляємо все після домену + порту
    from urllib.parse import urlparse
    parsed = urlparse(WEBHOOK_URL)
    RENDER_URL = f"{parsed.scheme}://{parsed.netloc}"
else:
    RENDER_URL = 'https://ferrik-bot-zvev.onrender.com'

# App Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))
TIMEZONE_NAME = os.environ.get('TIMEZONE_NAME', 'Europe/Kiev')  # Для коректного часу доби

# Feature Flags
ENABLE_AI_RECOMMENDATIONS = os.environ.get('ENABLE_AI_RECOMMENDATIONS', 'True').lower() == 'true'
GEMINI_MODEL_NAME = os.environ.get('GEMINI_MODEL_NAME', 'gemini-1.5-flash')
MIN_DELIVERY_AMOUNT = int(os.environ.get('MIN_DELIVERY_AMOUNT', 300))

# Cache Configuration
MENU_CACHE_TTL = int(os.environ.get('MENU_CACHE_TTL', 3600))  # 1 hour

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = int(os.environ.get('MAX_REQUESTS_PER_MINUTE', 60))

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

# Validate configuration
def validate_config():
    """Валідація конфігурації при запуску"""
    issues = []
    
    if not BOT_TOKEN:
        issues.append("BOT_TOKEN is missing - Bot cannot communicate with Telegram")
    
    # AI/Sheets validation is soft (features are disabled if missing)
    if not GEMINI_API_KEY and ENABLE_AI_RECOMMENDATIONS:
        issues.append("GEMINI_API_KEY is missing, but ENABLE_AI_RECOMMENDATIONS=True - AI features will fail")
    
    if not SPREADSHEET_ID:
        issues.append("SPREADSHEET_ID is missing - Google Sheets features disabled")
    
    if not GOOGLE_CREDENTIALS_JSON and not CREDS_B64:
        issues.append("Google credentials missing - cannot access Google Sheets")
    
    if issues:
        logger.warning("⚠️ Configuration issues detected:")
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
    logger.info(f"  GOOGLE_CREDENTIALS_JSON: {'✅ Set' if GOOGLE_CREDENTIALS_JSON else '❌ Missing'}")
    logger.info(f"  CREDS_B64: {'✅ Set' if CREDS_B64 else '❌ Missing'}")
    logger.info(f"  OPERATOR_CHAT_ID: {'✅ Set' if OPERATOR_CHAT_ID else '⚠️ Not set'}")
    logger.info(f"  WEBHOOK_URL: {WEBHOOK_URL}")
    logger.info(f"  RENDER_URL (Base): {RENDER_URL}")
    logger.info(f"  WEBHOOK_SECRET: {'✅ Set' if WEBHOOK_SECRET else '❌ Missing'}")
    logger.info(f"  TIMEZONE_NAME: {TIMEZONE_NAME}")
    logger.info(f"  MIN_DELIVERY_AMOUNT: {MIN_DELIVERY_AMOUNT}")
    logger.info(f"  ENABLE_AI_RECOMMENDATIONS: {ENABLE_AI_RECOMMENDATIONS}")
    logger.info(f"  DEBUG: {DEBUG}")
    logger.info(f"  PORT: {PORT}")
    logger.info("=" * 50)