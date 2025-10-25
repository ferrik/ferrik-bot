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
        except Exception as e:
            logger.error(f"❌ Error reading credentials file: {e}")
            return None
    
    logger.warning("⚠️ GOOGLE_CREDENTIALS format not recognized")
    return None


# ============================================================================
# Константи та словники
# ============================================================================

# Стани користувача
class UserState:
    IDLE = 'STATE_IDLE'
    AWAITING_PHONE = 'STATE_AWAITING_PHONE'
    AWAITING_ADDRESS = 'STATE_AWAITING_ADDRESS'
    AWAITING_FEEDBACK = 'STATE_AWAITING_FEEDBACK'

# Статуси замовлень
class OrderStatus:
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    IN_PROGRESS = 'in_progress'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'

ORDER_STATUS_NAMES = {
    OrderStatus.PENDING: '⏳ Очікує підтвердження',
    OrderStatus.CONFIRMED: '✅ Підтверджено',
    OrderStatus.IN_PROGRESS: '🚚 В дорозі',
    OrderStatus.DELIVERED: '📦 Доставлено',
    OrderStatus.CANCELLED: '❌ Скасовано'
}

# Рівні партнерів
PREMIUM_LEVELS = {
    'bronze': {'name': '🥉 Бронза', 'discount': 5},
    'silver': {'name': '🥈 Срібло', 'discount': 10},
    'gold': {'name': '🥇 Золото', 'discount': 15},
    'platinum': {'name': '💎 Платина', 'discount': 20}
}

# Статуси партнерів
PARTNER_STATUSES = {
    'active': '✅ Активний',
    'pending': '⏳ На розгляді',
    'suspended': '⚠️ Призупинено',
    'blocked': '🚫 Заблоковано'
}

# Конфігурація комісій
COMMISSION_CONFIG = {
    'default_rate': 0.10,  # 10%
    'min_rate': 0.05,      # 5%
    'max_rate': 0.25,      # 25%
    'enable': True
}

# Маппінг полів Google Sheets
SHEET_FIELDS = {
    'menu': {
        'id': 'ID',
        'name': 'Назва',
        'price': 'Ціна',
        'category': 'Категорія',
        'description': 'Опис',
        'image_url': 'Фото',
        'available': 'Доступно'
    },
    'orders': {
        'id': 'ID',
        'user_id': 'User ID',
        'username': 'Username',
        'phone': 'Телефон',
        'address': 'Адреса',
        'items': 'Товари',
        'total': 'Сума',
        'status': 'Статус',
        'created_at': 'Дата створення'
    },
    'partners': {
        'id': 'ID',
        'name': "Ім'я",
        'phone': 'Телефон',
        'level': 'Рівень',
        'commission_rate': 'Комісія',
        'status': 'Статус',
        'total_revenue': 'Загальний дохід',
        'rating': 'Рейтинг'
    },
    'reviews': {
        'id': 'ID',
        'user_id': 'User ID',
        'username': 'Username',
        'rating': 'Оцінка',
        'comment': 'Коментар',
        'created_at': 'Дата'
    }
}


# ============================================================================
# Ініціалізація глобальної конфігурації
# ============================================================================

# Створюємо глобальний екземпляр конфігу
config = BotConfig.from_env()

# Завантажуємо Google Credentials
GOOGLE_CREDENTIALS_DICT = load_google_credentials()

# Експортуємо для backward compatibility зі старим кодом
TELEGRAM_BOT_TOKEN = config.telegram_token
WEBHOOK_SECRET = config.webhook_secret
GOOGLE_SHEET_ID = config.sheet_id
GOOGLE_CREDENTIALS = config.google_credentials
ENVIRONMENT = config.environment
DEBUG = config.debug
PORT = config.port
WEBHOOK_URL = config.webhook_url
RENDER_URL = config.render_url
DATABASE_URL = config.database_url
REDIS_URL = config.redis_url
MIN_ORDER_AMOUNT = config.min_order_amount
ADMIN_TOKEN = config.admin_token


# ============================================================================
# Утилітні функції
# ============================================================================

def get_webhook_url() -> str:
    """Отримати повний URL webhook"""
    return config.get_webhook_url()

def is_production() -> bool:
    """Перевірка чи працюємо в production"""
    return config.environment.lower() == 'production'

def is_debug() -> bool:
    """Перевірка режиму debug"""
    return config.debug


# ============================================================================
# Валідація при імпорті (опціонально)
# ============================================================================

if __name__ != "__main__":
    # Валідуємо конфіг при імпорті (але не виводимо помилки в продакшні)
    if not config.telegram_token or not config.sheet_id:
        if is_debug():
            logger.warning("⚠️ Configuration incomplete - some features may not work")


# ============================================================================
# Якщо запускається як скрипт - показати конфігурацію
# ============================================================================

if __name__ == "__main__":
    # Валідація
    is_valid = config.validate()
    
    # Показ конфігу
    config.display()
    
    # Перевірка Google Credentials
    if GOOGLE_CREDENTIALS_DICT:
        logger.info(f"✅ Google Credentials: {len(GOOGLE_CREDENTIALS_DICT)} keys loaded")
        logger.info(f"   Type: {GOOGLE_CREDENTIALS_DICT.get('type', 'unknown')}")
        logger.info(f"   Project: {GOOGLE_CREDENTIALS_DICT.get('project_id', 'unknown')[:20]}...")
    else:
        logger.warning("⚠️ Google Credentials not loaded")
    
    # Фінальний статус
    if is_valid:
        logger.info("🎉 Configuration is valid and ready to use!")
    else:
        logger.error("💥 Configuration validation failed!")
        exit(1)
