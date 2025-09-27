import os
from dotenv import load_dotenv

# Завантажуємо змінні з .env файлу (якщо є). 
# На Render використовується пряме завантаження з envVars.
load_dotenv()

# --- СТАНДАРТИЗАЦІЯ ЗМІННИХ СЕРЕДОВИЩА ---

# Telegram Bot Token (Використовуємо TELEGRAM_BOT_TOKEN для консистентності з render.yaml)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') 
if not BOT_TOKEN:
    # Залишаємо додаткову перевірку для локального запуску, якщо використовується старе ім'я
    BOT_TOKEN = os.environ.get('BOT_TOKEN') 
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

# Google Gemini API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

# Google Sheets Configuration
# Використовуємо GOOGLE_SHEET_ID для консистентності з render.yaml
SPREADSHEET_ID = os.environ.get('GOOGLE_SHEET_ID') 
if not SPREADSHEET_ID:
    SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
    if not SPREADSHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID environment variable is required")

# Google Service Account Credentials
GOOGLE_CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS_JSON')
CREDS_B64 = os.environ.get('CREDS_B64')

# Database Configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///bot_data.db')

# App Configuration
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

# Webhook URL для Render
WEBHOOK_URL = os.environ.get('WEBHOOK_URL') 
if not WEBHOOK_URL:
     # Використовуємо URL з render.yaml як fallback
    WEBHOOK_URL = 'https://ferrik-bot-zvev.onrender.com/webhook'


# Logging, Feature Flags, etc.
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
ENABLE_AI_RECOMMENDATIONS = os.environ.get('ENABLE_AI_RECOMMENDATIONS', 'True').lower() == 'true'
ENABLE_GOOGLE_SHEETS = os.environ.get('ENABLE_GOOGLE_SHEETS', 'True').lower() == 'true'
MENU_CACHE_TTL = int(os.environ.get('MENU_CACHE_TTL', 3600))
MAX_REQUESTS_PER_MINUTE = int(os.environ.get('MAX_REQUESTS_PER_MINUTE', 60))


# Експортуємо константи з уніфікованими назвами
TELEGRAM_BOT_TOKEN = BOT_TOKEN
GOOGLE_SHEET_ID = SPREADSHEET_ID
# ... інші експорти
