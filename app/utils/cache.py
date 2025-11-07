"""
💾 CACHE - In-Memory кешування результатів
Скорочує повторні запити до API
"""

import time
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Простий in-memory кеш з TTL (Time To Live)
    
    Кешує результати для зменшення повторних запитів
    """
    
    def __init__(self, ttl: int = 300):
        """
        Ініціалізація кешу
        
        Args:
            ttl: Time To Live в секундах (за замовчуванням 5 хвилин)
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
        
        logger.info(f"📦 Cache initialized with TTL={ttl}s")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Отримати значення з кешу
        
        Args:
            key: Ключ кешу
        
        Returns:
            Значення якщо знайдено і не застаріло, інакше None
        """
        if key in self.cache:
            value, timestamp = self.cache[key]
            
            # Перевірити чи не застарів
            if time.time() - timestamp < self.ttl:
                self.hits += 1
                logger.debug(f"💾 Cache HIT: {key}")
                return value
            else:
                # Видалити застарілу запис
                del self.cache[key]
                logger.debug(f"⏰ Cache EXPIRED: {key}")
        
        self.misses += 1
        logger.debug(f"❌ Cache MISS: {key}")
        return None
    
    def set(self, key: str, value: Any):
        """
        Зберегти значення в кеш
        
        Args:
            key: Ключ кешу
            value: Значення для зберігання
        """
        self.cache[key] = (value, time.time())
        logger.debug(f"✅ Cache SET: {key}")
    
    def delete(self, key: str):
        """Видалити значення з кешу"""
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"🗑️ Cache DELETE: {key}")
    
    def clear(self):
        """Очистити весь кеш"""
        self.cache.clear()
        logger.info("🧹 Cache cleared")
    
    def get_stats(self) -> dict:
        """Отримати статистику кешу"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total': total,
            'hit_rate': f"{hit_rate:.1f}%",
            'cached_items': len(self.cache),
            'ttl': self.ttl
        }


# ============================================================================
# ГЛОБАЛЬНІ INSTANCES
# ============================================================================

# Кеш для AI відповідей (5 хвилин)
ai_cache = SimpleCache(ttl=300)

# Кеш для меню (30 хвилин)
menu_cache = SimpleCache(ttl=1800)

# Кеш для користувацьких дані (10 хвилин)
user_cache = SimpleCache(ttl=600
