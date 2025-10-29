"""
⏱️ RATE LIMITER - Для Gemini API
"""
import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Простий in-memory rate limiter"""
    
    def __init__(self, max_requests=5, time_window=60):
        """
        max_requests: 5 запитів
        time_window: за 60 секунд
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> bool:
        """Перевірити чи дозволено користувачу робити запит"""
        now = time.time()
        
        # Видалити старі запити
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
        """Скільки секунд чекати до наступного запиту"""
        if not self.requests[user_id]:
            return 0
        
        oldest = self.requests[user_id][0]
        wait = int(self.time_window - (time.time() - oldest)) + 1
        return max(0, wait)


# Глобальний instance
ai_rate_limiter = RateLimiter(
    max_requests=5,      # 5 запитів
    time_window=60       # за 60 секунд
)

# Для промокодів та адмін-операцій (менш жорсткий)
admin_rate_limiter = RateLimiter(
    max_requests=50,
    time_window=60
)
