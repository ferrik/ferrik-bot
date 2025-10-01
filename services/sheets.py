import os
import gspread
from google.oauth2.service_account import Credentials
import logging
import json

logger = logging.getLogger("bonapp")
menu_cache = []

def init_gspread_client():
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not creds_json:
            logger.error("GOOGLE_CREDENTIALS_JSON is not set")
            return False
        creds_dict = json.loads(creds_json)
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        logger.info("Google Sheets client initialized")
        return client
    except Exception as e:
        logger.error(f"Error initializing Google Sheets: {str(e)}", exc_info=True)
        return False

def get_menu_from_sheet():
    try:
        client = init_gspread_client()
        if not client:
            return []
        sheet = client.open_by_key(os.environ.get("GOOGLE_SHEET_ID")).sheet1
        menu = sheet.get_all_records()
        logger.info(f"Menu loaded: {len(menu)} items")
        return menu
    except Exception as e:
        logger.error(f"Error loading menu: {str(e)}", exc_info=True)
        return []

def save_order_to_sheets(chat_id, cart):
    try:
        client = init_gspread_client()
        if not client:
            return False
        sheet = client.open_by_key(os.environ.get("GOOGLE_SHEET_ID")).worksheet("Orders")
        order_data = [chat_id, datetime.now().isoformat(), json.dumps(cart)]
        sheet.append_row(order_data)
        logger.info(f"Order saved for {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving order: {str(e)}", exc_info=True)
        return False

def is_sheets_connected():
    return bool(init_gspread_client())

def search_menu_items(query):
    try:
        menu = get_menu_from_sheet()
        query = query.lower()
        return [item for item in menu if query in item.get("Назва Страви", "").lower() or query in item.get("Категорія", "").lower()]
    except Exception as e:
        logger.error(f"Error searching menu: {str(e)}", exc_info=True)
        return []
