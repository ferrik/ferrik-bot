"""
⏱️ RATE LIMITER - Захист від спаму та DDoS
Керує частотою API запитів користувачів
"""

import time
import logging
from collections import defaultdict
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Простий in-memory rate limiter
    
    Обмежує кількість запитів на користувача за визначений період часу
    """
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        """
        Ініціалізація rate limiter
        
        Args:
            max_requests: Максимум запитів (за замовчуванням 5)
            time_window: Часовий період в секундах (за замовчуванням 60)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
        
        logger.info(f"📊 RateLimiter initialized: {max_requests} requests per {time_window}s")
    
    def is_allowed(self, user_id: int) -> bool:
        """
        Перевірити чи дозволено користувачу робити запит
        
        Args:
            user_id: ID користувача
        
        Returns:
            True якщо дозволено, False якщо перевищено ліміт
        """
        now = time.time()
        
        # Видалити старі запити за межами часового вікна
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < self.time_window
        ]
        
        # Перевірити ліміт
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(now)
            return True
        
        return False
    
    def get_wait_time(self, user_id: int) -> int:
        """
        Дізнатися скільки секунд чекати до наступного запиту
        
        Args:
            user_id: ID користувача
        
        Returns:
            Кількість секунд очікування (0 якщо можна робити запит)
        """
        if not self.requests[user_id]:
            return 0
        
        oldest = self.requests[user_id][0]
        wait = int(self.time_window - (time.time() - oldest)) + 1
        return max(0, wait)
    
    def reset(self, user_id: int):
        """Скинути лічильник для користувача"""
        if user_id in self.requests:
            del self.requests[user_id]
    
    def reset_all(self):
        """Скинути всі лічильники"""
        self.requests.clear()
        logger.info("🔄 All rate limits reset")


# ============================================================================
# ГЛОБАЛЬНІ INSTANCES
# ============================================================================

# Для AI запитів (суворий ліміт)
ai_rate_limiter = RateLimiter(
    max_requests=5,      # 5 запитів
    time_window=60       # за 60 секунд
)

# Для адмін-операцій (м'якший ліміт)
admin_rate_limiter = RateLimiter(
    max_requests=50,     # 50 запитів
    time_window=60       # за 60 секунд
)

# Для замовлень (середній ліміт)
order_rate_limiter = RateLimiter(
    max_requests=10,     # 10 замовлень
    time_window=3600     # за годину
)
