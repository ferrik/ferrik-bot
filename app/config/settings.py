"""
⚙️ Конфігурація бота (покращена версія)

Автоматична валідація, типізація, безпечне завантаження
"""
import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

# ============================================================================
# Налаштування логування
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# Основна конфігурація
# ============================================================================

@dataclass
class BotConfig:
    """Основні налаштування бота"""
    
    # Telegram
    telegram_token: str
    webhook_secret: str
    
    # Google Sheets
    sheet_id: str
    google_credentials: Optional[str] = None
    
    # Deployment
    environment: str = "production"
    debug: bool = False
    port: int = 5000
    webhook_url: Optional[str] = None
    render_url: Optional[str] = None
    
    # Database
    database_url: str = "sqlite:///bot.db"
    redis_url: Optional[str] = None
    
    # Features
    min_order_amount: float = 100.0
    enable_commission: bool = True
    
    # Admin
    admin_token: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Завантажити конфігурацію з змінних середовища"""
        
        return cls(
            # Required
            telegram_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            webhook_secret=os.getenv('WEBHOOK_SECRET', 'default_secret'),
            sheet_id=os.getenv('GOOGLE_SHEET_ID', ''),
            
            # Optional - Google
            google_credentials=os.getenv('GOOGLE_CREDENTIALS'),
            
            # Optional - Deployment
            environment=os.getenv('ENVIRONMENT', 'production'),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            port=int(os.getenv('PORT', 5000)),
            webhook_url=os.getenv('WEBHOOK_URL'),
            render_url=os.getenv('RENDER_EXTERNAL_URL'),
            
            # Optional - Database
            database_url=os.getenv('DATABASE_URL', 'sqlite:///bot.db'),
            redis_url=os.getenv('REDIS_URL'),
            
            # Optional - Features
            min_order_amount=float(os.getenv('MIN_ORDER_AMOUNT', 100.0)),
            enable_commission=os.getenv('ENABLE_COMMISSION', 'true').lower() == 'true',
            
            # Optional - Admin
            admin_token=os.getenv('ADMIN_TOKEN'),
        )
    
    def validate(self) -> bool:
        """Перевірка коректності конфігурації"""
        errors = []
        
        if not self.telegram_token:
            errors.append("❌ TELEGRAM_BOT_TOKEN is required")
        
        if not self.sheet_id:
            errors.append("❌ GOOGLE_SHEET_ID is required")
        
        if not self.webhook_url and not self.render_url:
            errors.append("⚠️ Neither WEBHOOK_URL nor RENDER_EXTERNAL_URL is set")
        
        if errors:
            for error in errors:
                logger.error(error)
            return False
        
        logger.info("✅ Configuration validated successfully")
        return True
    
    def get_webhook_url(self) -> str:
        """Отримати URL для webhook"""
        base_url = self.webhook_url or self.render_url
        if not base_url:
            raise ValueError("No webhook URL configured")
        
        # Додаємо /webhook якщо немає
        if not base_url.endswith('/webhook'):
            base_url = f"{base_url.rstrip('/')}/webhook"
        
        return base_url
    
    def display(self):
        """Показати конфігурацію (приховуючи секрети)"""
        logger.info("=" * 60)
        logger.info("🤖 BOT CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Debug: {self.debug}")
        logger.info(f"Port: {self.port}")
        logger.info(f"Webhook URL: {self.get_webhook_url()}")
        logger.info(f"Sheet ID: {self.sheet_id[:8]}...")
        logger.info(f"Database: {self.database_url.split(':')[0]}://...")
        logger.info(f"Redis: {'ENABLED' if self.redis_url else 'DISABLED'}")
        logger.info(f"Min Order: {self.min_order_amount} грн")
        logger.info(f"Commission: {'ENABLED' if self.enable_commission else 'DISABLED'}")
        logger.info("=" * 60)


# ============================================================================
# Google Credentials Parser
# ============================================================================

def load_google_credentials() -> Optional[Dict[str, Any]]:
    """
    Завантажити Google credentials з різних форматів
    
    Підтримує:
    1. JSON-рядок в змінній середовища
    2. Шлях до файлу credentials.json
    3. None (якщо не налаштовано)
    """
    creds_str = os.getenv('GOOGLE_CREDENTIALS', '')
    
    if not creds_str:
        logger.warning("⚠️ GOOGLE_CREDENTIALS not set")
        return None
    
    # Спроба парсити як JSON
    try:
        creds_dict = json.loads(creds_str)
        logger.info("✅ Google credentials loaded from JSON string")
        return creds_dict
    except json.JSONDecodeError:
        pass
    
    # Спроба прочитати як файл
    if os.path.isfile(creds_str):
        try:
            with open(creds_str, 'r') as f:
                creds_dict = json.load(f)
            logger.info(f"✅ Google credentials loaded from file: {creds_str}")
            return creds_dict
