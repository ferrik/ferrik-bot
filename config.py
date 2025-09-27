import os
from dotenv import load_dotenv

# Завантажуємо змінні з .env файлу (якщо є)
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Google Gemini API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

# Google Sheets Configuration
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
if not SPREADSHEET_ID:
    raise ValueError("SPREADSHEET_ID environment variable is required")

# Google Service Account Credentials
GOOGLE_CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS_JSON')
CREDS_B64 = os.environ.get('CREDS_B64')

if not GOOGLE_CREDENTIALS_JSON and not CREDS_B64:
    raise ValueError("Either GOOGLE_CREDENTIALS_JSON or CREDS_B64 environment variable is required")

# Database Configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///bot.db')

# App Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

# Webhook URL для Render
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com/webhook')

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

# Feature Flags
ENABLE_AI_RECOMMENDATIONS = os.environ.get('ENABLE_AI_RECOMMENDATIONS', 'True').lower() == 'true'
ENABLE_GOOGLE_SHEETS = os.environ.get('ENABLE_GOOGLE_SHEETS', 'True').lower() == 'true'

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
    required_vars = ['BOT_TOKEN', 'GEMINI_API_KEY', 'SPREADSHEET_ID']
    missing_vars = []
    
    for var in required_vars:
        if not globals().get(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True

# Запуск валідації при імпорті
validate_config()
