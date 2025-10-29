"""💾 Simple In-Memory Cache"""
import time
from typing import Any, Optional

class SimpleCache:
    def __init__(self, ttl=300):  # 5 хвилин
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        self.cache[key] = (value, time.time())
    
    def clear(self):
        self.cache.clear()

# Глобальний кеш
ai_cache = SimpleCache(ttl=300)  # 5 хвилин
