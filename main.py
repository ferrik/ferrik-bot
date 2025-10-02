import os
import logging
import base64
import json

# Налаштування логування
logger = logging.getLogger('config')

# .env необов'язковий
try:
    from dotenv import load_dotenv
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

# Якщо задано CREDS_B64 — пробуємо розкодувати та перевірити JSON
GOOGLE_CREDENTIALS_DICT = None
if CREDS_B64 and not GOOGLE_CREDENTIALS_JSON:
    try:
        decoded = base64.b64decode(CREDS_B64)
        GOOGLE_CREDENTIALS_DICT = json.loads(decoded)
        logger.info("✅ CREDS_B64 decoded successfully")
    except Exception:
        logger.exception("❌ Failed to decode CREDS_B64; ignoring")

if not GOOGLE_CREDENTIALS_JSON and not GOOGLE_CREDENTIALS_DICT:
    logger.warning("⚠️ Neither GOOGLE_CREDENTIALS_JSON nor valid CREDS_B64 found")

# Operator chat ID (конвертуємо в int, якщо задано)
OPERATOR_CHAT_ID_RAW = os.environ.get('OPERATOR_CHAT_ID', '')
OPERATOR_CHAT_ID = None
if OPERATOR_CHAT_ID_RAW:
    try:
        OPERATOR_CHAT_ID = int(OPERATOR_CHAT_ID_RAW)
    except Exception:
        logger.warning("⚠️ OPERATOR_CHAT_ID provided but invalid (not int)")

if not OPERATOR_CHAT_ID:
    logger.warning("⚠️ OPERATOR_CHAT_ID not set or invalid")

# Webhook Configuration
# WEBHOOK_URL - може бути None; не ставимо production дефолтів в коді
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

# CRITICAL: WEBHOOK_SECRET має бути складним і унікальним
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
    logger.critical("WEBHOOK_SECRET not set - this is a security risk!")
    # В production зупиняємо запуск
    raise RuntimeError("WEBHOOK_SECRET must be set in environment variables")

# RENDER_URL (базова URL для setWebhook) — намагаємося визначити з WEBHOOK_URL
if WEBHOOK_URL:
    from urllib.parse import urlparse
    parsed = urlparse(WEBHOOK_URL)
    RENDER_URL = f"{parsed.scheme}://{parsed.netloc}"
else:
    RENDER_URL = None

# App Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))
TIMEZONE_NAME = os.environ.get('TIMEZONE_NAME', 'Europe/Kyiv')  # Виправлено на Kyiv

# Feature Flags
ENABLE_AI_RECOMMENDATIONS = os.environ.get('ENABLE_AI_RECOMMENDATIONS', 'True').lower() == 'true'
GEMINI_MODEL_NAME = os.environ.get('GEMINI_MODEL_NAME', 'gemini-1.5-flash')
MIN_DELIVERY_AMOUNT = int(os.environ.get('MIN_DELIVERY_AMOUNT', 300))

# Cache Configuration
MENU_CACHE_TTL = int(os.environ.get('MENU_CACHE_TTL', 3600))  # 1 hour

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = int(os.environ.get('MAX_REQUESTS_PER_MINUTE', 60))

# Error / Success messages
ERROR_MESSAGES = {
    'generic': 'Виникла помилка. Спробуйте пізніше.',
    'ai_unavailable': 'AI рекомендації тимчасово недоступні.',
    'menu_unavailable': 'Меню тимчасово недоступне.',
    'sheets_error': 'Помилка підключення до Google Sheets.'
}

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

    if not GEMINI_API_KEY and ENABLE_AI_RECOMMENDATIONS:
        issues.append("GEMINI_API_KEY is missing, but ENABLE_AI_RECOMMENDATIONS=True - AI features will fail")

    if not SPREADSHEET_ID:
        issues.append("SPREADSHEET_ID is missing - Google Sheets features disabled")

    if not GOOGLE_CREDENTIALS_JSON and not GOOGLE_CREDENTIALS_DICT:
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
    logger.info(f"  WEBHOOK_URL: {WEBHOOK_URL or '❌ Missing'}")
    logger.info(f"  RENDER_URL (Base): {RENDER_URL or '❌ Missing'}")
    logger.info(f"  WEBHOOK_SECRET: {'✅ Set' if WEBHOOK_SECRET else '❌ Missing'}")
    logger.info(f"  TIMEZONE_NAME: {TIMEZONE_NAME}")
    logger.info(f"  MIN_DELIVERY_AMOUNT: {MIN_DELIVERY_AMOUNT}")
    logger.info(f"  ENABLE_AI_RECOMMENDATIONS: {ENABLE_AI_RECOMMENDATIONS}")
    logger.info(f"  DEBUG: {DEBUG}")
    logger.info(f"  PORT: {PORT}")
    logger.info("=" * 50)