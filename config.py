import os
import base64
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def load_env_var(name, required=False, default=None):
    value = os.getenv(name, default)
    if required and not value:
        logger.error(f"{name} environment variable is required")
        raise ValueError(f"{name} environment variable is required")
    return value

BOT_TOKEN = load_env_var("BOT_TOKEN", required=True)
SPREADSHEET_ID = load_env_var("SPREADSHEET_ID", required=True)
CREDS_B64 = load_env_var("CREDS_B64")
GOOGLE_CREDENTIALS_JSON = load_env_var("GOOGLE_CREDENTIALS_JSON")  # Зроблено необов’язковим
GEMINI_API_KEY = load_env_var("GEMINI_API_KEY", required=True)
GEMINI_MODEL_NAME = load_env_var("GEMINI_MODEL_NAME", default="gemini-1.5-flash")
ENABLE_AI_RECOMMENDATIONS = load_env_var("ENABLE_AI_RECOMMENDATIONS", default="true").lower() == "true"
ERROR_MESSAGES = {
    'ai_unavailable': "AI недоступний",
    'generic': "Помилка"
}
ADMIN_CHAT_ID = load_env_var("ADMIN_CHAT_ID")
MIN_DELIVERY_AMOUNT = load_env_var("MIN_DELIVERY_AMOUNT", default="300")

if not GOOGLE_CREDENTIALS_JSON and CREDS_B64:
    try:
        GOOGLE_CREDENTIALS_JSON = base64.b64decode(CREDS_B64).decode("utf-8")
        logger.info("CREDS_B64 decoded successfully")
    except Exception as e:
        logger.error(f"Failed to decode CREDS_B64: {e}")
        raise ValueError("Invalid CREDS_B64")
elif not GOOGLE_CREDENTIALS_JSON:
    logger.warning("Neither GOOGLE_CREDENTIALS_JSON nor CREDS_B64 provided. Google Sheets integration will fail.")

def get_google_creds_dict():
    if not GOOGLE_CREDENTIALS_JSON:
        logger.warning("GOOGLE_CREDENTIALS_JSON is not set")
        return None
    try:
        return json.loads(GOOGLE_CREDENTIALS_JSON)
    except Exception as e:
        logger.error(f"Failed to parse GOOGLE_CREDENTIALS_JSON: {e}")
        return None