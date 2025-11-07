"""
⚙️ Конфігурація додатку
"""
import os
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class TelegramConfig:
    """Налаштування Telegram бота"""
    bot_token: str
    webhook_url: Optional[str] = None
    admin_ids: list[int] = None
    
    def __post_init__(self):
        if self.admin_ids is None:
            self.admin_ids = []
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")


@dataclass
class GeminiConfig:
    """Налаштування Gemini AI"""
    api_key: str
    model_name: str = "gemini-1.5-flash"
    temperature: float = 0.7
    max_tokens: int = 1000
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")


@dataclass
class GoogleSheetsConfig:
    """Налаштування Google Sheets"""
    credentials_json: str
    spreadsheet_id: str
    menu_sheet_name: str = "Menu"
    orders_sheet_name: str = "Orders"
    
    def __post_init__(self):
        if not self.credentials_json:
            raise ValueError("GOOGLE_SHEETS_CREDENTIALS is required")
        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_ID is required")


@dataclass
class AppConfig:
    """Загальна конфігурація додатку"""
    # Режим роботи
    debug: bool = False
    environment: str = "production"
    
    # Flask
    host: str = "0.0.0.0"
    port: int = 5000
    
    # Логування
    log_level: str = "INFO"
    
    # Бізнес-логіка
    min_order_amount: float = 50.0  # Мінімальна сума замовлення
    max_order_items: int = 50  # Максимальна кількість товарів
    delivery_cost: float = 0.0  # Вартість доставки
    
    # Таймаути
    session_timeout: int = 3600  # 1 година
    ai_timeout: int = 30  # Таймаут для AI запитів
    
    # Повідомлення
    welcome_message: str = (
        "👋 Вітаю в FerrikFoot!\n\n"
        "Я допоможу вам замовити смачну їжу 🍕\n\n"
        "Використовуйте:\n"
        "🔹 /menu - переглянути меню\n"
        "🔹 /cart - переглянути кошик\n"
        "🔹 /order - оформити замовлення\n"
        "🔹 /help - допомога\n\n"
        "Або просто напишіть, що б ви хотіли замовити!"
    )
    
    def __post_init__(self):
        # Налаштування логування
        log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        level = log_levels.get(self.log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def load_config() -> tuple[TelegramConfig, GeminiConfig, GoogleSheetsConfig, AppConfig]:
    """
    Завантаження конфігурації з environment variables
    
    Returns:
        tuple: (telegram_config, gemini_config, sheets_config, app_config)
    """
    
    # Telegram
    telegram_config = TelegramConfig(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        webhook_url=os.getenv("WEBHOOK_URL"),
        admin_ids=[
            int(id.strip()) 
            for id in os.getenv("ADMIN_IDS", "").split(",") 
            if id.strip()
        ]
    )
    
    # Gemini AI
    gemini_config = GeminiConfig(
        api_key=os.getenv("GEMINI_API_KEY", ""),
        model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "1000"))
    )
    
    # Google Sheets
    sheets_config = GoogleSheetsConfig(
        credentials_json=os.getenv("GOOGLE_SHEETS_CREDENTIALS", ""),
        spreadsheet_id=os.getenv("GOOGLE_SHEETS_ID", ""),
        menu_sheet_name=os.getenv("MENU_SHEET_NAME", "Menu"),
        orders_sheet_name=os.getenv("ORDERS_SHEET_NAME", "Orders")
    )
    
    # App
    app_config = AppConfig(
        debug=os.getenv("DEBUG", "False").lower() == "true",
        environment=os.getenv("ENVIRONMENT", "production"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        min_order_amount=float(os.getenv("MIN_ORDER_AMOUNT", "50.0")),
        max_order_items=int(os.getenv("MAX_ORDER_ITEMS", "50")),
        delivery_cost=float(os.getenv("DELIVERY_COST", "0.0")),
        session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600")),
        ai_timeout=int(os.getenv("AI_TIMEOUT", "30"))
    )
    
    logger.info("✅ Configuration loaded successfully")
    logger.info(f"📍 Environment: {app_config.environment}")
    logger.info(f"🐛 Debug mode: {app_config.debug}")
    logger.info(f"🌐 Host: {app_config.host}:{app_config.port}")
    
    return telegram_config, gemini_config, sheets_config, app_config


# ============================================================================
# Environment variables template (.env)
# ============================================================================
"""
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://your-app.onrender.com
ADMIN_IDS=123456789,987654321

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TEMPERATURE=0.7
GEMINI_MAX_TOKENS=1000

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS={"type": "service_account", ...}
GOOGLE_SHEETS_ID=your_spreadsheet_id_here
MENU_SHEET_NAME=Menu
ORDERS_SHEET_NAME=Orders

# App Settings
DEBUG=False
ENVIRONMENT=production
PORT=5000
LOG_LEVEL=INFO
MIN_ORDER_AMOUNT=50.0
MAX_ORDER_ITEMS=50
DELIVERY_COST=0.0
SESSION_TIMEOUT=3600
AI_TIMEOUT=30
"""
