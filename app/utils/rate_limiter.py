"""
⏱️ Rate Limiter для API викликів
Обмежує частоту запитів до API (Gemini, Sheets тощо)
"""

import time
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Обмежувач частоти запитів"""
    
    def __init__(self, cooldown: int = 30):
        """
        Args:
            cooldown: Час очікування між запитами (секунди)
        """
        self.cooldown = cooldown
        self.last_call: Dict[str, float] = {}
    
    def can_call(self, user_id: int, api_name: str) -> bool:
        """
        Перевірка чи можна виконати запит
        
        Args:
            user_id: ID користувача
            api_name: Назва API (gemini, sheets, etc)
        
        Returns:
            bool: True якщо можна викликати
        """
        key = f"{user_id}:{api_name}"
        now = time.time()
        
        if key in self.last_call:
            elapsed = now - self.last_call[key]
            if elapsed < self.cooldown:
                remaining = int(self.cooldown - elapsed)
                logger.warning(
                    f"⏱️ Rate limit for {api_name}: user {user_id}, "
                    f"wait {remaining}s"
                )
                return False
        
        self.last_call[key] = now
        return True
    
    def reset(self, user_id: int, api_name: str):
        """Скинути лічильник для користувача"""
        key = f"{user_id}:{api_name}"
        if key in self.last_call:
            del self.last_call[key]
            logger.info(f"✅ Rate limit reset for {api_name}: user {user_id}")
    
    def get_remaining_time(self, user_id: int, api_name: str) -> int:
        """Отримати час очікування (секунди)"""
        key = f"{user_id}:{api_name}"
        now = time.time()
        
        if key in self.last_call:
            elapsed = now - self.last_call[key]
            if elapsed < self.cooldown:
                return int(self.cooldown - elapsed)
        
        return 0


# Глобальні екземпляри для різних API
gemini_limiter = RateLimiter(cooldown=60)   # 1 хвилина для AI
sheets_limiter = RateLimiter(cooldown=30)   # 30 секунд для Sheets
general_limiter = RateLimiter(cooldown=10)  # 10 секунд для загальних запитів