import os
from dotenv import load_dotenv

load_dotenv()

# ============= TELEGRAM =============
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
OPERATOR_CHAT_ID = os.getenv('OPERATOR_CHAT_ID')

# ============= GOOGLE =============
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# ============= DATABASE =============
DATABASE_URL = os.getenv('DATABASE_URL')
DB_NAME = os.getenv('DATABASE_NAME', 'ferrik_bot_db')

# ============= SERVER =============
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
FLASK_ENV = os.getenv('FLASK_ENV', 'production')

# ============= BUSINESS LOGIC =============
DELIVERY_COST = float(os.getenv('DELIVERY_COST', 30))  # 30₴
MIN_ORDER_AMOUNT = float(os.getenv('MIN_ORDER_AMOUNT', 100))  # 100₴
COMMISSION_RATE = float(os.getenv('COMMISSION_RATE', 15))  # 15% за замовчуванням

# ============= LOCATION =============
CITY = os.getenv('CITY', 'Тернопіль')
DELIVERY_ZONE = os.getenv('DELIVERY_ZONE', 'центр')  # центр
DELIVERY_RADIUS_KM = int(os.getenv('DELIVERY_RADIUS_KM', 7))  # 7 км

# ============= LOGGING =============
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Валідація
assert BOT_TOKEN, "❌ BOT_TOKEN не встановлена"
assert DATABASE_URL, "❌ DATABASE_URL не встановлена"
assert GEMINI_API_KEY, "❌ GEMINI_API_KEY не встановлена"
