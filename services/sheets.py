import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    import gspread
except Exception as e:
    logger.exception("gspread не доступний: %s. Додай до requirements.txt 'gspread'.", e)
    raise

from config import SPREADSHEET_ID, get_google_creds_dict, MIN_DELIVERY_AMOUNT

_gc = None
_sheet = None

def init_gspread_client(force: bool = False):
    """
    Ініціалізувати клієнт gspread та встановити об'єкт sheet у _sheet.
    Якщо SPREADSHEET_ID або креденшали відсутні, повертає None.
    """
    global _gc, _sheet
    if _gc is not None and not force:
        return _sheet

    creds = get_google_creds_dict()
    if not creds:
        logger.warning("Google credentials не налаштовані. init_sheet_client повертає None.")
        return None

    if not SPREADSHEET_ID:
        logger.warning("SPREADSHEET_ID не задано. init_sheet_client повертає None.")
        return None

    try:
        _gc = gspread.service_account_from_dict(creds)
        wb = _gc.open_by_key(SPREADSHEET_ID)
        # За замовчуванням беремо перший лист; за потреби вказати назву
        _sheet = wb.sheet1
        logger.info("Google Sheets клієнт ініціалізовано успішно.")
        return _sheet
    except Exception as e:
        logger.exception("Помилка при ініціалізації Google Sheets: %s", e)
        return None


def get_all_records() -> List[Dict]:
    """
    Повертає всі записи з листа у вигляді list[dict].
    Повертає порожній список, якщо неможливо зчитати.
    """
    sh = init_gspread_client()
    if not sh:
        return []
    try:
        return sh.get_all_records()
    except Exception as e:
        logger.exception("Не вдалося отримати всі записи з Sheets: %s", e)
        return []


def get_item_by_id(item_id: str, id_column: str = "id") -> Optional[Dict]:
    """
    Знаходить товар по item_id у колонці id_column (за замовчуванням 'id').
    Повертає словник рядка або None.
    """
    if item_id is None:
        return None

    records = get_all_records()
    for row in records:
        # переводимо в str для порівняння, бо Google повертає все як str/number
        try:
            if str(row.get(id_column)) == str(item_id):
                return row
        except Exception:
            continue
    return None


def get_min_delivery_amount(default_from_env: Optional[str] = MIN_DELIVERY_AMOUNT, fallback_cell: tuple = (2, 5)) -> float:
    """
    Повертає мінімальну суму доставки:
    - спочатку читає з ENV (MIN_DELIVERY_AMOUNT якщо задано)
    - інакше читає з конкретної клітинки (рядок, колонка) за fallback_cell (рядок, колонка),
      за замовчуванням (2,5) = E2.
    - якщо нічого нема — повертає 0.0
    """
    # 1) ENV
    if default_from_env:
        try:
            return float(default_from_env)
        except Exception:
            logger.warning("MIN_DELIVERY_AMOUNT з ENV не є числом: %s", default_from_env)

    # 2) Google Sheet
    sh = init_gspread_client()
    if sh:
        try:
            r, c = fallback_cell
            value = sh.cell(r, c).value
            if value:
                return float(value)
        except Exception as e:
            logger.exception("Не вдалося зчитати мінімальну сумму з клітинки: {e}")

    return 0.0

def get_menu_from_sheet(force=False):
    """Завантажує меню з Google Sheets"""
    sh = init_gspread_client(force=force)
    if not sh:
        return []
    try:
        # Припускаємо, що меню в листі 'Menu'
        ws = sh.get_worksheet(0)  # або sh.worksheet('Menu')
        records = ws.get_all_records()
        menu = [item for item in records if item.get('active', True)]
        return menu
    except Exception as e:
        logger.error(f"Error fetching menu: {e}")
        return []

def save_order_to_sheets(order_data):
    """Зберігає замовлення в Google Sheets"""
    sh = init_gspread_client()
    if not sh:
        return None
    try:
        ws = sh.worksheet("Замовлення")  # Припускаємо лист "Замовлення"
        row = [datetime.now().strftime('%Y-%m-%d %H:%M'), order_data['chat_id'], order_data['total'], 'Нове']  # Приклад полів
        ws.append_row(row)
        return len(ws.get_all_records())  # Повертає ID як номер рядка
    except Exception as e:
        logger.error(f"Error saving order: {e}")
        return None