"""
Bot configuration module
Wrapper around main config for backward compatibility
"""
import logging
from config import (
    BOT_TOKEN,
    TELEGRAM_BOT_TOKEN,
    OPERATOR_CHAT_ID,
    WEBHOOK_URL,
    WEBHOOK_SECRET,
    GOOGLE_SHEET_ID,
    GOOGLE_CREDENTIALS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    REDIS_URL,
    CART_TTL_HOURS,
    MAX_CART_ITEMS,
    ORDER_FIELDS,
    MENU_FIELDS,
    USER_FIELDS,
    SHEET_NAMES
)

logger = logging.getLogger('bot_config')

# Re-export all config variables
__all__ = [
    'BOT_TOKEN',
    'TELEGRAM_BOT_TOKEN',
    'OPERATOR_CHAT_ID',
    'WEBHOOK_URL',
    'WEBHOOK_SECRET',
    'GOOGLE_SHEET_ID',
    'GOOGLE_CREDENTIALS',
    'GEMINI_API_KEY',
    'GEMINI_MODEL',
    'REDIS_URL',
    'CART_TTL_HOURS',
    'MAX_CART_ITEMS',
    'ORDER_FIELDS',
    'MENU_FIELDS',
    'USER_FIELDS',
    'SHEET_NAMES'
]

# Validation
if not BOT_TOKEN:
    logger.error("Bot token not configured!")

if OPERATOR_CHAT_ID:
    logger.info(f"Operator notifications enabled for chat: {OPERATOR_CHAT_ID}")
else:
    logger.warning("Invalid OPERATOR_CHAT_ID, ignoring")