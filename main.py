import os
import logging
import json
import uuid
from flask import Flask, request, jsonify
import requests
from google.oauth2 import service_account
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import re
import sqlite3

try:
    from zoneinfo import ZoneInfo
except ImportError:
    logging.warning("zoneinfo module not found. Using pytz if available, otherwise naive datetime.")
    try:
        from pytz import timezone
        ZoneInfo = lambda tz: timezone(tz)
    except ImportError:
        ZoneInfo = None

import google.generativeai as genai

from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# Геолокація
geolocator = Nominatim(user_agent="ferrikfoot_bot")
RESTAURANT_LOCATION = (49.553517, 25.594767)  # Центр Тернополя
DELIVERY_RADIUS_KM = 7
# Тимчасові дані
user_addresses = {}  # {user_id: {"coords": (lat, lon), "address": "..."}}

# ---------- APP ----------
app = Flask(__name__)

# ---------- CONFIG ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
REQUESTS_TIMEOUT = 10
EXECUTOR = ThreadPoolExecutor(max_workers=5)

# ---------- ENV VARIABLES ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
SERVICE_ACCOUNT_KEY_PATH = os.environ.get("SERVICE_ACCOUNT_KEY_PATH", "").strip()
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "").strip()
OPERATOR_CHAT_ID_STR = os.environ.get("OPERATOR_CHAT_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Default values, can be overridden by Google Sheet config
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Тернопіль").strip()
TIMEZONE_NAME = os.environ.get("TIMEZONE", "Europe/Kyiv").strip()
RESTAURANT_OPEN_HOUR = int(os.environ.get("RESTAURANT_OPEN_HOUR", "9"))
RESTAURANT_CLOSE_HOUR = int(os.environ.get("RESTAURANT_CLOSE_HOUR", "22"))
DELIVERY_FEE = float(os.environ.get("DELIVERY_FEE", "50.0"))
MIN_ORDER_FOR_DELIVERY = float(os.environ.get("MIN_ORDER_FOR_DELIVERY", "300.0"))
RESTAURANT_ADDRESS = os.environ.get("RESTAURANT_ADDRESS", f"вул. Головна, 123, м. {DEFAULT_CITY}").strip()
CACHE_TIMEOUT_SECONDS = int(os.environ.get("CACHE_TIMEOUT_SECONDS", "900"))  # 15 хвилин

OPERATOR_CHAT_ID = None
try:
    if OPERATOR_CHAT_ID_STR:
        OPERATOR_CHAT_ID = int(OPERATOR_CHAT_ID_STR)
except ValueError:
    logging.warning(f"OPERATOR_CHAT_ID '{OPERATOR_CHAT_ID_STR}' is not an integer. Using None.")
except Exception as e:
    logging.warning(f"Error converting OPERATOR_CHAT_ID: {e}")

logging.info(f"ENV: TELEGRAM_BOT_TOKEN loaded: {bool(TELEGRAM_BOT_TOKEN)}")
logging.info(f"ENV: SERVICE_ACCOUNT_KEY_PATH loaded: {bool(SERVICE_ACCOUNT_KEY_PATH and os.path.exists(SERVICE_ACCOUNT_KEY_PATH))}")
logging.info(f"ENV: GOOGLE_SHEET_ID loaded: {bool(GOOGLE_SHEET_ID)}")
logging.info(f"ENV: OPERATOR_CHAT_ID loaded: {bool(OPERATOR_CHAT_ID)} (value: {OPERATOR_CHAT_ID})")
logging.info(f"ENV: GEMINI_API_KEY loaded: {bool(GEMINI_API_KEY)}")
logging.info(f"ENV: DEFAULT_CITY: {DEFAULT_CITY}")
logging.info(f"ENV: TIMEZONE: {TIMEZONE_NAME}")

# ---------- SQLite Database Setup ----------
DATABASE_PATH = "bot_data.db"  # Шлях до файлу бази даних

def init_db():
    """Ініціалізація бази даних SQLite для стану та кошиків."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    chat_id INTEGER PRIMARY KEY,
                    state TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_carts (
                    chat_id INTEGER PRIMARY KEY,
                    cart_data TEXT NOT NULL
                )
            """)
            conn.commit()
        logging.info("SQLite database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error initializing SQLite database: {e}")

init_db()

# ---------- User States Definitions ----------
STATE_NORMAL = "normal"
STATE_AWAITING_PHONE = "awaiting_phone"
STATE_AWAITING_PHONE_CONFIRM = "awaiting_phone_confirm"
STATE_AWAITING_ADDRESS = "awaiting_address"
STATE_AWAITING_PAYMENT_METHOD_CHOICE = "awaiting_payment_method_choice"
STATE_AWAITING_DELIVERY_TYPE_CHOICE = "awaiting_delivery_type_choice"
STATE_AWAITING_DELIVERY_TIME_CHOICE = "awaiting_delivery_time_choice"
STATE_AWAITING_FINAL_CONFIRMATION = "awaiting_final_confirmation"
STATE_AWAITING_OPERATOR_MESSAGE = "awaiting_operator_message"
STATE_AWAITING_SEARCH_QUERY = "awaiting_search_query"
STATE_AWAITING_FEEDBACK = "awaiting_feedback"

# ---------- Google Sheets Integration ----------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
gc = None
spreadsheet = None
menu_cache = []
last_menu_cache_time = None

def init_gspread_client():
    """Initializes the gspread client for Google Sheets."""
    global gc, spreadsheet
    logging.info("init_gspread_client: attempting to connect...")
    try:
        if not SERVICE_ACCOUNT_KEY_PATH or not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
            logging.error(f"Service account key file not found at: {SERVICE_ACCOUNT_KEY_PATH}")
            return False
        if not GOOGLE_SHEET_ID:
            logging.error("GOOGLE_SHEET_ID is not set.")
            return False

        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY_PATH, scopes=SCOPE)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
        logging.info("init_gspread_client: connected to Google Sheets successfully.")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        logging.error(f"Google Sheet with ID '{GOOGLE_SHEET_ID}' not found. Check ID and access permissions.")
        gc = spreadsheet = None
        return False
    except Exception as e:
        logging.exception(f"init_gspread_client error: {e}")
        gc = spreadsheet = None
        return False

def update_menu_cache(force=False):
    """
    Loads and normalizes menu data from the 'Меню' sheet into cache.
    Uses caching to reduce Google Sheets API requests.
    """
    global menu_cache, last_menu_cache_time
    try:
        if not spreadsheet and not init_gspread_client():
            logging.warning("update_menu_cache: could not connect to Google Sheets.")
            return

        if not force and last_menu_cache_time and (datetime.now() - last_menu_cache_time).total_seconds() < CACHE_TIMEOUT_SECONDS:
            logging.debug("update_menu_cache: using cached menu.")
            return
        
        logging.info("update_menu_cache: updating menu cache from Google Sheet...")
        ws = spreadsheet.worksheet("Меню")
        records = ws.get_all_records()
        processed = []
        for rec in records:
            item = {k: v for k, v in rec.items() if k} # Filter out empty keys
            
            item['Назва Страви'] = str(item.get('Назва Страви') or item.get('Назва', '')).strip()
            
            if not item['Назва Страви']:
                logging.warning(f"update_menu_cache: skipped item without a name: {rec}")
                continue

            item['Активний'] = str(item.get('Активний', 'Так')).strip()
            item['ID'] = str(item.get('ID')) if item.get('ID') is not None else None

            if item['ID'] is None:
                logging.warning(f"update_menu_cache: skipped item '{item['Назва Страви']}' without an ID.")
                continue

            try:
                price_str = str(item.get('Ціна', '0')).strip().replace(',', '.')
                item['Ціна'] = float(price_str) if price_str else 0.0
            except (ValueError, TypeError):
                logging.warning(f"update_menu_cache: invalid price '{item.get('Ціна')}' for '{item['Назва Страви']}'. Setting to 0.0.")
                item['Ціна'] = 0.0
            
            item.setdefault('Опис', '').strip()
            item.setdefault('Категорія', 'Без категорії').strip()
            item.setdefault('Фото URL', '').strip()
            processed.append(item)
        
        menu_cache = processed
        last_menu_cache_time = datetime.now()
        logging.info(f"update_menu_cache: cached {len(menu_cache)} menu items.")
    except gspread.exceptions.WorksheetNotFound:
        logging.error("update_menu_cache: worksheet 'Меню' not found in Google Sheet.")
        menu_cache = []
    except Exception as e:
        logging.exception(f"update_menu_cache error: {e}")
        menu_cache = []

def load_config_from_sheet():
    """Loads configuration from the 'Конфіг' sheet."""
    global RESTAURANT_OPEN_HOUR, RESTAURANT_CLOSE_HOUR, DELIVERY_FEE, MIN_ORDER_FOR_DELIVERY, \
           RESTAURANT_ADDRESS, CACHE_TIMEOUT_SECONDS, DEFAULT_CITY, TIMEZONE_NAME, OPERATOR_CHAT_ID

    logging.info("load_config_from_sheet: loading configuration from Google Sheet...")
    try:
        if not spreadsheet:
            logging.warning("load_config_from_sheet: Google Sheets client not available, skipping config load.")
            return False
        
        try:
            ws = spreadsheet.worksheet("Конфіг")
        except gspread.exceptions.WorksheetNotFound:
            logging.warning("load_config_from_sheet: worksheet 'Конфіг' not found. Using default environment variables.")
            return False

        rows = ws.get_all_values()
        if not rows or len(rows) < 1:
            logging.warning("load_config_from_sheet: no rows found in 'Конфіг' sheet. Using default environment variables.")
            return False

        config = {}
        for r_idx, r in enumerate(rows[1:], start=2): # Skip header row
            if not r or len(r) < 2:
                logging.warning(f"load_config_from_sheet: skipped invalid row {r_idx} in 'Конфіг': {r}")
                continue
            key = str(r[0]).strip().lower()
            val = str(r[1]).strip()
            if not key:
                logging.warning(f"load_config_from_sheet: skipped row {r_idx} with empty key in 'Конфіг'.")
                continue
            config[key] = val

        # Helper to get typed config values with fallback to current global vars
        def get_float_config(keys, default_val):
            for k in keys:
                if k in config:
                    try: return float(config[k].replace(',', '.'))
                    except ValueError: logging.warning(f"Invalid float config value for '{k}': '{config[k]}'. Using default {default_val}.")
            return default_val

        def get_int_config(keys, default_val):
            for k in keys:
                if k in config:
                    try: return int(float(config[k].replace(',', '.'))) # Handles "9.0"
                    except ValueError: logging.warning(f"Invalid int config value for '{k}': '{config[k]}'. Using default {default_val}.")
            return default_val
        
        def get_str_config(keys, default_val):
            for k in keys:
                if k in config and config[k]: return config[k]
            return default_val

        MIN_ORDER_FOR_DELIVERY = get_float_config(['мінімальна сума доставки', 'min_order_for_delivery'], MIN_ORDER_FOR_DELIVERY)
        DELIVERY_FEE = get_float_config(['вартість доставки', 'delivery_fee'], DELIVERY_FEE)
        RESTAURANT_OPEN_HOUR = get_int_config(['година відкриття', 'restaurant_open_hour'], RESTAURANT_OPEN_HOUR)
        RESTAURANT_CLOSE_HOUR = get_int_config(['година закриття', 'restaurant_close_hour'], RESTAURANT_CLOSE_HOUR)
        CACHE_TIMEOUT_SECONDS = get_int_config(['кеш тайм-аут', 'cache_timeout_seconds'], CACHE_TIMEOUT_SECONDS)
        RESTAURANT_ADDRESS = get_str_config(['адреса ресторану', 'restaurant_address'], RESTAURANT_ADDRESS)
        DEFAULT_CITY = get_str_config(['місто за замовчуванням', 'default_city'], DEFAULT_CITY)
        TIMEZONE_NAME = get_str_config(['часова зона', 'timezone'], TIMEZONE_NAME)

        operator_chat_id_from_sheet = get_str_config(['чат id оператора', 'operator_chat_id'], '')
        if operator_chat_id_from_sheet:
            try:
                OPERATOR_CHAT_ID = int(operator_chat_id_from_sheet)
                logging.info(f"OPERATOR_CHAT_ID set from sheet: {OPERATOR_CHAT_ID}")
            except ValueError:
                logging.warning(f"Invalid OPERATOR_CHAT_ID from sheet: '{operator_chat_id_from_sheet}'.")

        logging.info(f"Config loaded. Open: {RESTAURANT_OPEN_HOUR}, Close: {RESTAURANT_CLOSE_HOUR}, Delivery Fee: {DELIVERY_FEE}, Min Order: {MIN_ORDER_FOR_DELIVERY}, Cache Timeout: {CACHE_TIMEOUT_SECONDS}, City: {DEFAULT_CITY}, Timezone: {TIMEZONE_NAME}")
        return True
    except Exception as e:
        logging.exception(f"load_config_from_sheet error: {e}")
        return False

# ---------- Time and Currency Helpers ----------
def now(tz_name=TIMEZONE_NAME):
    """Returns current datetime in specified timezone, or naive if zoneinfo/pytz not available."""
    try:
        if ZoneInfo:
            return datetime.now(ZoneInfo(tz_name))
    except Exception:
        logging.debug(f'ZoneInfo failed for {tz_name}, fallback to naive datetime.')
    return datetime.now()

def format_currency(value):
    """Formats a numeric value as a currency string."""
    try:
        return f"{float(value):.2f} грн"
    except (ValueError, TypeError):
        return f"{value} грн"

# ---------- Personalized Greeting Function ----------
def generate_personalized_greeting(user_name="Друже"):
    """Generates a personalized greeting based on time of day, season, and holidays."""
    user_name = (user_name or '').strip() or 'Друже'
    current = now()
    hour = current.hour
    
    # Time of day greetings
    if 6 <= hour < 12: greeting = f"Доброго ранку, {user_name}!"
    elif 12 <= hour < 18: greeting = f"Доброго дня, {user_name}!"
    else: greeting = f"Доброго вечора, {user_name}!"
    
    # Restaurant status message
    open_time = f"{RESTAURANT_OPEN_HOUR:02d}:00"
    close_time = f"{RESTAURANT_CLOSE_HOUR:02d}:00"
    if is_restaurant_open():
        status = f"Ресторан відкритий до {close_time}. Будемо раді вашим замовленням! 😊"
    else:
        status = f"Ресторан зараз закритий. 😔 Працюємо з {open_time} до {close_time}. Чекаємо на вас!"
    
    return f"{greeting}\n\n{status}\n\nЯ ваш помічник для замовлення їжі! 🍔🍕"


def is_restaurant_open():
    """Checks if the restaurant is open based on configured hours."""
    current_hour = now().hour
    if RESTAURANT_OPEN_HOUR <= RESTAURANT_CLOSE_HOUR:
        return RESTAURANT_OPEN_HOUR <= current_hour < RESTAURANT_CLOSE_HOUR
    else: # Overnight operation, e.g., 22:00 - 02:00
        return (current_hour >= RESTAURANT_OPEN_HOUR) or (current_hour < RESTAURANT_CLOSE_HOUR)

# ---------- Startup Initialization ----------
with app.app_context():
    logging.info("Bot initialization started.")
    try:
        init_db() # Ініціалізуємо SQLite базу даних при старті
        if init_gspread_client():
            load_config_from_sheet() # Load config first to get correct CACHE_TIMEOUT_SECONDS, etc.
            update_menu_cache(force=True)
            logging.info("Bot initialized successfully and cache updated.")
        else:
            logging.error("Bot initialization failed: Google Sheets client could not be initialized. Bot may not function correctly.")
    except Exception as e:
        logging.exception(f"Startup error during bot initializatio

# (Код обрізаний через обмеження довжини, але я надішлю повну версію нижче)
```

**Повний код**: Через обмеження довжини повідомлення, я надішлю повний код як artifact.

<xaiArtifact artifact_id="1e92d4e0-e6e4-46cb-9e04-a1c27f902bc5" artifact_version_id="50d09f8e-d3d8-4e22-af30-5d1f4a39ccb1" title="main.py" contentType="text/python">
