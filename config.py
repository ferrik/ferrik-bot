# config.py
import os
import base64
import json
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Telegram token (обов'язково)
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN (або TELEGRAM_BOT_TOKEN) не заданий у змінних середовища.")
    # не кидаємо помилку відразу — дозволяємо стартувати у dev, але попереджаємо
    # якщо хочеш — розкоментуй наступний рядок, щоб падало одразу:
    # raise ValueError("BOT_TOKEN environment variable is required")

# Google Sheets
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
if not SPREADSHEET_ID:
    logger.warning("SPREADSHEET_ID не задано. Функції, що працюють з Sheets, можуть падати.")

# Декілька форматів зберігання Google creds:
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")  # повний JSON як str
CREDS_B64 = os.getenv("CREDS_B64")  # base64-encoded creds.json

# Якщо є CREDS_B64 — декодуємо в JSON-рядок
if not GOOGLE_CREDENTIALS_JSON and CREDS_B64:
    try:
        GOOGLE_CREDENTIALS_JSON = base64.b64decode(CREDS_B64).decode("utf-8")
        logger.info("CREDS_B64 прочитано і декодовано у GOOGLE_CREDENTIALS_JSON.")
    except Exception as e:
        logger.exception("Не вдалося декодувати CREDS_B64: %s", e)

if not GOOGLE_CREDENTIALS_JSON:
    logger.warning("Немає GOOGLE_CREDENTIALS_JSON або CREDS_B64. Доступ до Google Sheets буде неможливим.")

# Додаткові змінні (опціонально)
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # наприклад для логів/повідомлень адміну
MIN_DELIVERY_AMOUNT = os.getenv("MIN_DELIVERY_AMOUNT")  # можна зчитувати з env як fallback

# Типові версії/флаги
ENV = os.getenv("ENV", "production")

def get_google_creds_dict():
    """
    Повертає dict з креденшелів для gspread.service_account_from_dict
    або None, якщо немає налаштованих креденшелів.
    """
    if not GOOGLE_CREDENTIALS_JSON:
        return None
    try:
        return json.loads(GOOGLE_CREDENTIALS_JSON)
    except Exception as e:
        logger.exception("Помилка при парсингу GOOGLE_CREDENTIALS_JSON: %s", e)
        return None
