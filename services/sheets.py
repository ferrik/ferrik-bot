import logging
import json
import gspread
from google.oauth2.service_account import Credentials
from config import SPREADSHEET_ID, get_google_creds_dict, MIN_DELIVERY_AMOUNT

logger = logging.getLogger("ferrik")
logging.basicConfig(level=logging.INFO)

def init_gspread_client():
    """Ініціалізація клієнта Google Sheets."""
    try:
        creds_dict = get_google_creds_dict()
        if not creds_dict:
            logger.error("Failed to initialize Google Sheets client: No credentials provided")
            return None
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        logger.info("Google Sheets client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {str(e)}")
        return None

def get_menu_from_sheet():
    """Отримує меню з аркуша 'Меню' Google Sheets."""
    try:
        client = init_gspread_client()
        if not client:
            logger.error("Cannot fetch menu: Google Sheets client not initialized")
            return {}
        
        logger.info(f"Attempting to access spreadsheet with ID: {SPREADSHEET_ID}")
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        try:
            sheet = spreadsheet.worksheet("Меню")
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet 'Меню' not found in spreadsheet {SPREADSHEET_ID}")
            return {}
        
        records = sheet.get_all_records()
        if not records:
            logger.warning(f"No records found in 'Меню' worksheet")
        
        menu = {}
        for record in records:
            if record.get("Активний", "").lower() in ["так", "true", "1"]:  # Фільтруємо активні страви
                item_id = str(record.get("ID", ""))
                if item_id:
                    menu[item_id] = {
                        "id": item_id,
                        "category": record.get("Категорія", ""),
                        "name": record.get("Страви", ""),
                        "description": record.get("Опис", ""),
                        "price": float(record.get("Ціна", 0)),
                        "restaurant": record.get("Ресторан", ""),
                        "delivery_time_min": int(record.get("Час Доставки (хв)", 0)),
                        "photo_url": record.get("Фото URL", ""),
                        "prep_time_min": int(record.get("Час_приготування", 0)),
                        "allergens": record.get("Аллергени", ""),
                        "rating": float(record.get("Рейтинг", 0))
                    }
                else:
                    logger.warning(f"Skipping menu item with missing ID: {record}")
        
        logger.info(f"Fetched {len(menu)} active menu items from Google Sheets")
        return menu
    except gspread.exceptions.APIError as e:
        logger.error(f"Google Sheets API error: {str(e)} (HTTP {e.response.status_code if e.response else 'unknown'})")
        return {}
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet with ID {SPREADSHEET_ID} not found or inaccessible")
        return {}
    except Exception as e:
        logger.error(f"Error fetching menu from Google Sheets: {str(e)}")
        return {}

def get_item_by_id(item_id: str):
    """Отримує елемент меню за ID."""
    menu = get_menu_from_sheet()
    return menu.get(item_id)

def get_min_delivery_amount():
    """Повертає мінімальну суму доставки з конфігурації."""
    return float(MIN_DELIVERY_AMOUNT)

def get_config():
    """Отримує конфігурацію з аркуша 'Конфіг'."""
    try:
        client = init_gspread_client()
        if not client:
            logger.error("Cannot fetch config: Google Sheets client not initialized")
            return {}
        
        logger.info(f"Attempting to access spreadsheet with ID: {SPREADSHEET_ID}")
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        try:
            sheet = spreadsheet.worksheet("Конфіг")
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet 'Конфіг' not found in spreadsheet {SPREADSHEET_ID}")
            return {}
        
        records = sheet.get_all_records()
        if not records:
            logger.warning(f"No records found in 'Конфіг' worksheet")
        
        config = {}
        for record in records:
            key = record.get("Ключ", "")
            if key:
                config[key] = {
                    "value": record.get("Значення", ""),
                    "open_hour": int(record.get("OPEN_HOUR", 9)),
                    "close_hour": int(record.get("CLOSE_HOUR", 22))
                }
            else:
                logger.warning(f"Skipping config entry with missing key: {record}")
        
        logger.info(f"Fetched {len(config)} config entries from Google Sheets")
        return config
    except gspread.exceptions.APIError as e:
        logger.error(f"Google Sheets API error: {str(e)} (HTTP {e.response.status_code if e.response else 'unknown'})")
        return {}
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet with ID {SPREADSHEET_ID} not found or inaccessible")
        return {}
    except Exception as e:
        logger.error(f"Error fetching config from Google Sheets: {str(e)}")
        return {}

def save_order(order_data: dict):
    """Зберігає замовлення в аркуш 'Замовлення'."""
    try:
        client = init_gspread_client()
        if not client:
            logger.error("Cannot save order: Google Sheets client not initialized")
            return False
        
        logger.info(f"Attempting to access spreadsheet with ID: {SPREADSHEET_ID}")
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        try:
            sheet = spreadsheet.worksheet("Замовлення")
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet 'Замовлення' not found in spreadsheet {SPREADSHEET_ID}")
            return False
        
        row = [
            order_data.get("order_id", ""),
            order_data.get("user_id", ""),
            order_data.get("order_time", ""),
            json.dumps(order_data.get("items", []), ensure_ascii=False),
            order_data.get("total_amount", 0.0),
            order_data.get("address", ""),
            order_data.get("phone", ""),
            order_data.get("payment_method", ""),
            order_data.get("status", "Нове"),
            order_data.get("channel", "Telegram"),
            order_data.get("delivery_cost", 0.0),
            order_data.get("total_with_delivery", 0.0),
            order_data.get("delivery_type", ""),
            order_data.get("delivery_time", ""),
            order_data.get("operator", ""),
            order_data.get("notes", "")
        ]
        sheet.append_row(row)
        logger.info(f"Saved order {order_data.get('order_id')} to Google Sheets")
        return True
    except gspread.exceptions.APIError as e:
        logger.error(f"Google Sheets API error when saving order: {str(e)} (HTTP {e.response.status_code if e.response else 'unknown'})")
        return False
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet with ID {SPREADSHEET_ID} not found or inaccessible")
        return False
    except Exception as e:
        logger.error(f"Error saving order to Google Sheets: {str(e)}")
        return False 