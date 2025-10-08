"""
Модуль сервісів.

Надає доступ до всіх основних сервісів бота:
- telegram: взаємодія з Telegram Bot API.
- sheets: робота з Google Sheets.
- database: локальна база даних SQLite.
- gemini: (опціонально) інтеграція з Gemini API.
"""

from . import telegram
from . import sheets
from . import database

# Опціональний імпорт Gemini, щоб бот працював і без нього
try:
    from . import gemini
except ImportError:
    gemini = None

__all__ = [
    'telegram',
    'sheets',
    'database',
    'gemini'
]


