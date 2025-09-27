"""
Google Sheets service для роботи з таблицями
"""

import gspread
import json
import base64
import logging
from io import BytesIO
from config import SPREADSHEET_ID, GOOGLE_CREDENTIALS_JSON, CREDS_B64

logger = logging.getLogger(__name__)

def init_sheets():
    """Ініціалізація підключення до Google Sheets"""
    try:
        # Спробуємо використати CREDS_B64
        if CREDS_B64:
            logger.info("Using CREDS_B64 from env")
            credentials_data = base64.b64decode(CREDS_B64).decode('utf-8')
            credentials_dict = json.loads(credentials_data)
            logger.info("Successfully loaded credentials from CREDS_B64")
        elif GOOGLE_CREDENTIALS_JSON:
            logger.info("Using GOOGLE_CREDENTIALS_JSON from env")
            credentials_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        else:
            # Спробуємо прочитати з файлу
            logger.info("Trying to load from creds.json file")
            with open('creds.json', 'r') as f:
                credentials_dict = json.load(f)
        
        # Підключення до Google Sheets
        gc = gspread.service_account_from_dict(credentials_dict)
        sheet = gc.open_by_key(SPREADSHEET_ID)
        
        logger.info(f"Connected to Google Sheet: {SPREADSHEET_ID}")
        return sheet
        
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        return None

def get_menu_from_sheets():
    """Завантаження меню з Google Sheets"""
    try:
        sheet = init_sheets()
        if not sheet:
            logger.error("No sheet connection available")
            return {}
        
        # Спробуємо знайти worksheet з меню
        try:
            menu_worksheet = sheet.worksheet("Menu")
        except:
            try:
                menu_worksheet = sheet.worksheet("Меню")
            except:
                # Використаємо перший worksheet
                menu_worksheet = sheet.get_worksheet(0)
        
        # Отримуємо всі записи
        records = menu_worksheet.get_all_records()
        
        menu_cache = {}
        active_count = 0
        
        for i, record in enumerate(records):
            # Гнучка перевірка колонок
            item_id = record.get('id') or record.get('ID') or str(i + 1)
            name = record.get('name') or record.get('Name') or record.get('назва') or record.get('Назва')
            price = record.get('price') or record.get('Price') or record.get('ціна') or record.get('Ціна')
            description = record.get('description') or record.get('Description') or record.get('опис') or record.get('Опис') or ''
            active = record.get('active') or record.get('Active') or record.get('активний') or record.get('Активний')
            
            # Перевірка активності
            is_active = True
            if active is not None:
                if isinstance(active, str):
                    is_active = active.lower() in ['true', '1', 'yes', 'так', 'активний']
                else:
                    is_active = bool(active)
            
            if name and price:
                try:
                    price_value = float(str(price).replace(',', '.'))
                    menu_cache[str(item_id)] = {
                        'id': str(item_id),
                        'name': str(name),
                        'price': price_value,
                        'description': str(description),
                        'active': is_active
                    }
                    if is_active:
                        active_count += 1
                except ValueError:
                    logger.warning(f"Invalid price for item {name}: {price}")
        
        logger.info(f"Menu loaded: {active_count} active items from {len(menu_cache)} total")
        return menu_cache
        
    except Exception as e:
        logger.error(f"Error loading menu from sheets: {e}")
        return {}

def add_user_data(user_id, username, action="User interaction"):
    """Додавання даних користувача в Google Sheets"""
    try:
        sheet = init_sheets()
        if not sheet:
            logger.error("No sheet connection available")
            return False
        
        # Спробуємо знайти worksheet для користувачів
        try:
            users_worksheet = sheet.worksheet("Users")
        except:
            try:
                users_worksheet = sheet.worksheet("Statistics")
            except:
                # Створимо новий worksheet
                users_worksheet = sheet.add_worksheet("Users", rows=1000, cols=5)
                users_worksheet.append_row(["Date", "User ID", "Username", "Action", "Timestamp"])
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        users_worksheet.append_row([
            timestamp,
            str(user_id),
            str(username),
            str(action),
            timestamp
        ])
        
        logger.info(f"User data added for {user_id}: {action}")
        return True
        
    except Exception as e:
        logger.error(f"Error adding user data: {e}")
        return False

def get_statistics():
    """Отримання статистики з Google Sheets"""
    try:
        sheet = init_sheets()
        if not sheet:
            return {}
        
        try:
            stats_worksheet = sheet.worksheet("Statistics")
            records = stats_worksheet.get_all_records()
            
            # Базова статистика
            total_users = len(set(record.get('User ID') for record in records if record.get('User ID')))
            total_actions = len(records)
            
            return {
                'total_users': total_users,
                'total_actions': total_actions,
                'recent_actions': records[-10:] if records else []
            }
        except:
            return {}
            
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {}
