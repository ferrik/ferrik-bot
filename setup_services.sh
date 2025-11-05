#!/bin/bash
# Автоматичне встановлення відсутніх сервісів для Ferrik Bot
# Запуск: bash setup_services.sh

set -e  # Зупинка при помилці

echo "🚀 Ferrik Bot - Автоматичне встановлення сервісів"
echo "=================================================="
echo ""

# Кольори для виводу
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функція для виводу
print_step() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Крок 1: Перевірка директорії
echo "Крок 1/8: Перевірка директорії проекту..."
if [ ! -f "main.py" ]; then
    print_error "main.py не знайдено. Переконайся що ти в директорії ferrik-bot"
    exit 1
fi
print_step "Директорія коректна"
echo ""

# Крок 2: Створення структури
echo "Крок 2/8: Створення структури директорій..."
mkdir -p services models storage handlers utils tests scripts
touch services/__init__.py
touch models/__init__.py
touch storage/__init__.py
touch handlers/__init__.py
touch utils/__init__.py
print_step "Структура створена"
echo ""

# Крок 3: Backup існуючих файлів
echo "Крок 3/8: Backup існуючих файлів..."
if [ -d "services" ] && [ "$(ls -A services)" ]; then
    BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    cp -r services "$BACKUP_DIR/" 2>/dev/null || true
    print_step "Backup створено: $BACKUP_DIR"
else
    print_step "Backup не потрібен (немає існуючих файлів)"
fi
echo ""

# Крок 4: Створення services/telegram.py
echo "Крок 4/8: Створення services/telegram.py..."
cat > services/telegram.py << 'TELEGRAM_EOF'
"""
Telegram API Wrapper
Обгортка для роботи з Telegram Bot API
"""
import logging
import requests
from typing import Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

# Base URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{config.BOT_TOKEN}"


def tg_send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: Optional[Dict] = None,
    disable_web_page_preview: bool = True
) -> bool:
    """Відправити повідомлення в Telegram"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            logger.info(f"✅ Message sent to {chat_id}")
            return True
        else:
            logger.error(f"❌ Telegram API error: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return False


def tg_send_photo(
    chat_id: int,
    photo_url: str,
    caption: str = "",
    reply_markup: Optional[Dict] = None
) -> bool:
    """Відправити фото в Telegram"""
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            logger.info(f"✅ Photo sent to {chat_id}")
            return True
        else:
            logger.error(f"❌ Telegram API error: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return False


def tg_answer_callback(
    callback_query_id: str,
    text: str = "",
    show_alert: bool = False
) -> bool:
    """Відповісти на callback query"""
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        return result.get("ok", False)
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Answer callback failed: {e}")
        return False


def test_telegram_connection() -> bool:
    """Тест з'єднання з Telegram API"""
    url = f"{TELEGRAM_API_URL}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            bot_info = result.get("result", {})
            logger.info(f"✅ Bot connected: @{bot_info.get('username')}")
            return True
        else:
            logger.error(f"❌ Telegram API error: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False
TELEGRAM_EOF

print_step "services/telegram.py створено"
echo ""

# Крок 5: Створення services/gemini.py
echo "Крок 5/8: Створення services/gemini.py..."
cat > services/gemini.py << 'GEMINI_EOF'
"""
Gemini AI Integration
Інтеграція з Google Gemini для розумного пошуку та рекомендацій
"""
import logging
from typing import List, Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

# Перевірка наявності Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    
    if config.GEMINI_API_KEY:
        genai.configure(api_key=config.GEMINI_API_KEY)
        logger.info("✅ Gemini AI configured")
    else:
        logger.warning("⚠️ GEMINI_API_KEY not set")
        GEMINI_AVAILABLE = False
        
except ImportError:
    logger.error("❌ google-generativeai not installed")
    GEMINI_AVAILABLE = False


def search_menu(query: str, menu_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Розумний пошук у меню через AI"""
    if not GEMINI_AVAILABLE or not menu_data:
        return simple_search(query, menu_data)
    
    try:
        menu_text = "\n".join([
            f"{i+1}. {item.get('Страви', item.get('Назва Страви', 'N/A'))} - "
            f"{item.get('Опис', '')} ({item.get('Ціна', 0)} грн)"
            for i, item in enumerate(menu_data[:30])
        ])
        
        prompt = f"""Ти асистент для пошуку страв у ресторані.

МЕНЮ:
{menu_text}

ЗАПИТ: "{query}"

Знайди 3-5 страв з меню, які найбільше підходять під запит.
Відповідай ТІЛЬКИ номерами страв через кому (наприклад: 1, 5, 12).
Якщо нічого не підходить, відповідай: НІЧОГО"""
        
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        
        answer = response.text.strip()
        
        if "НІЧОГО" in answer.upper():
            return []
        
        indices = []
        for part in answer.split(','):
            try:
                idx = int(part.strip()) - 1
                if 0 <= idx < len(menu_data):
                    indices.append(idx)
            except ValueError:
                continue
        
        results = [menu_data[i] for i in indices[:5]]
        
        logger.info(f"✅ AI search: '{query}' → {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"❌ AI search failed: {e}")
        return simple_search(query, menu_data)


def simple_search(query: str, menu_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Простий пошук по назві (fallback)"""
    query_lower = query.lower()
    results = []
    
    for item in menu_data:
        name = item.get('Страви', item.get('Назва Страви', '')).lower()
        description = item.get('Опис', '').lower()
        category = item.get('Категорія', '').lower()
        
        if (query_lower in name or 
            query_lower in description or 
            query_lower in category):
            results.append(item)
    
    logger.info(f"✅ Simple search: '{query}' → {len(results)} results")
    return results[:5]


def get_ai_response(query: str, menu_data: List[Dict[str, Any]]) -> Optional[str]:
    """Отримати AI коментар/пораду"""
    if not GEMINI_AVAILABLE:
        return None
    
    try:
        menu_categories = set()
        for item in menu_data:
            cat = item.get('Категорія', 'Інше')
            menu_categories.add(cat)
        
        categories_text = ", ".join(menu_categories)
        
        prompt = f"""Ти дружній асистент ресторану в Тернополі.

ДОСТУПНІ КАТЕГОРІЇ: {categories_text}

ЗАПИТ КОРИСТУВАЧА: "{query}"

Дай коротку (2-3 речення) пораду або коментар українською мовою.
Будь дружнім та корисним. Використовуй емодзі 😊"""
        
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        
        answer = response.text.strip()
        logger.info(f"✅ AI response generated")
        
        return answer
        
    except Exception as e:
        logger.error(f"❌ AI response failed: {e}")
        return None


def test_gemini_connection() -> bool:
    """Тест підключення до Gemini"""
    if not GEMINI_AVAILABLE:
        logger.warning("⚠️ Gemini not available")
        return False
    
    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = model.generate_content("Скажи 'OK' якщо працює")
        
        answer = response.text.strip()
        logger.info(f"✅ Gemini test: {answer}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Gemini test failed: {e}")
        return False
GEMINI_EOF

print_step "services/gemini.py створено"
echo ""

# Крок 6: Створення services/sheets.py
echo "Крок 6/8: Створення services/sheets.py..."
cat > services/sheets.py << 'SHEETS_EOF'
"""
Google Sheets Integration
Робота з Google Sheets як базою даних
"""
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import config

logger = logging.getLogger(__name__)

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    logger.error("❌ gspread not installed")
    GSPREAD_AVAILABLE = False

_sheet_client = None
_menu_cache = []
_menu_cache_time = None
CACHE_TTL = 300


def get_sheet_client():
    """Отримати клієнт Google Sheets"""
    global _sheet_client
    
    if _sheet_client:
        return _sheet_client
    
    if not GSPREAD_AVAILABLE:
        logger.error("❌ gspread not available")
        return None
    
    if not config.GOOGLE_SHEET_ID:
        logger.error("❌ GOOGLE_SHEET_ID not set")
        return None
    
    if not config.GOOGLE_CREDENTIALS:
        logger.error("❌ GOOGLE_CREDENTIALS not set")
        return None
    
    try:
        creds_dict = json.loads(config.GOOGLE_CREDENTIALS)
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=scopes
        )
        
        _sheet_client = gspread.authorize(credentials)
        logger.info("✅ Google Sheets client authorized")
        
        return _sheet_client
        
    except Exception as e:
        logger.error(f"❌ Failed to authorize Google Sheets: {e}")
        return None


def get_menu_from_sheet() -> List[Dict[str, Any]]:
    """Завантажити меню з Google Sheets"""
    global _menu_cache, _menu_cache_time
    
    if _menu_cache and _menu_cache_time:
        age = (datetime.now() - _menu_cache_time).total_seconds()
        if age < CACHE_TTL:
            logger.info(f"✅ Menu from cache ({len(_menu_cache)} items)")
            return _menu_cache
    
    client = get_sheet_client()
    if not client:
        logger.error("❌ Cannot get sheet client")
        return []
    
    try:
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        menu_sheet = sheet.worksheet(config.SHEET_NAMES.get('menu', 'Меню'))
        records = menu_sheet.get_all_records()
        
        active_items = []
        for item in records:
            is_active = str(item.get('Активний', 'TRUE')).upper()
            
            if is_active in ['TRUE', 'ТАК', '1', 'YES']:
                active_items.append(item)
        
        _menu_cache = active_items
        _menu_cache_time = datetime.now()
        
        logger.info(f"✅ Menu loaded: {len(active_items)} items")
        return active_items
        
    except Exception as e:
        logger.error(f"❌ Failed to load menu: {e}")
        return _menu_cache


def save_order_to_sheet(order_data: Dict[str, Any]) -> bool:
    """Зберегти замовлення в Google Sheets"""
    client = get_sheet_client()
    if not client:
        return False
    
    try:
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        orders_sheet = sheet.worksheet(config.SHEET_NAMES.get('orders', 'Замовлення'))
        
        row = [
            order_data.get('order_id', ''),
            order_data.get('user_id', ''),
            order_data.get('username', ''),
            order_data.get('timestamp', datetime.now().isoformat()),
            json.dumps(order_data.get('items', []), ensure_ascii=False),
            order_data.get('total', 0),
            order_data.get('status', 'new'),
            order_data.get('phone', ''),
            order_data.get('address', ''),
            order_data.get('notes', '')
        ]
        
        orders_sheet.append_row(row)
        
        logger.info(f"✅ Order saved: {order_data.get('order_id')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save order: {e}")
        return False


def test_sheets_connection() -> bool:
    """Тест підключення до Google Sheets"""
    client = get_sheet_client()
    if not client:
        return False
    
    try:
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        title = sheet.title
        
        logger.info(f"✅ Connected to sheet: {title}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False
SHEETS_EOF

print_step "services/sheets.py створено"
echo ""

# Крок 7: Створення services/database.py
echo "Крок 7/8: Створення services/database.py..."
cat > services/database.py << 'DATABASE_EOF'
"""
Simple SQLite Database for activity logging
"""
import logging
import sqlite3
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("ferrik_bot.db")


def get_connection() -> Optional[sqlite3.Connection]:
    """Отримати з'єднання з БД"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None


def init_database() -> bool:
    """Ініціалізувати базу даних"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT,
                items TEXT NOT NULL,
                total REAL NOT NULL,
                status TEXT DEFAULT 'new',
                phone TEXT,
                address TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dish_popularity (
                dish_name TEXT PRIMARY KEY,
                order_count INTEGER DEFAULT 0,
                last_ordered DATETIME
            )
        """)
        
        conn.commit()
        logger.info("✅ Database initialized")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ Database init failed: {e}")
        return False
    finally:
        conn.close()


def log_activity(user_id: int, action: str, details: Dict[str, Any] = None) -> bool:
    """Логувати активність користувача"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        details_json = json.dumps(details) if details else None
        
        cursor.execute("""
            INSERT INTO activity_log (user_id, action, details)
            VALUES (?, ?, ?)
        """, (user_id, action, details_json))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ Log activity failed: {e}")
        return False
    finally:
        conn.close()


def save_order(
    order_id: str,
    user_id: int,
    username: str,
    items: List[Dict[str, Any]],
    total: float,
    phone: str = "",
    address: str = "",
    notes: str = ""
) -> bool:
    """Зберегти замовлення в локальну БД"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        items_json = json.dumps(items, ensure_ascii=False)
        
        cursor.execute("""
            INSERT OR REPLACE INTO orders 
            (id, user_id, username, items, total, phone, address, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, user_id, username, items_json, total, phone, address, notes))
        
        for item in items:
            dish_name = item.get('name', '')
            if dish_name:
                cursor.execute("""
                    INSERT INTO dish_popularity (dish_name, order_count, last_ordered)
                    VALUES (?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(dish_name) DO UPDATE SET
                        order_count = order_count + 1,
                        last_ordered = CURRENT_TIMESTAMP
                """, (dish_name,))
        
        conn.commit()
        logger.info(f"✅ Order saved to DB: {order_id}")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ Save order failed: {e}")
        return False
    finally:
        conn.close()


def get_user_orders(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Отримати історію замовлень користувача"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        
        orders = []
        for row in rows:
            orders.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'username': row['username'],
                'items': json.loads(row['items']),
                'total': row['total'],
                'status': row['status'],
                'phone': row['phone'],
                'address': row['address'],
                'notes': row['notes'],
                'created_at': row['created_at']
            })
        
        return orders
        
    except sqlite3.Error as e:
        logger.error(f"❌ Get user orders failed: {e}")
        return []
    finally:
        conn.close()


def get_popular_items(limit: int = 5) -> List[Tuple[str, int]]:
    """Отримати топ популярних страв"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT dish_name, order_count
            FROM dish_popularity
            ORDER BY order_count DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        return [(row['dish_name'], row['order_count']) for row in rows]
        
    except sqlite3.Error as e:
        logger.error(f"❌ Get popular items failed: {e}")
        return []
    finally:
        conn.close()


def test_connection() -> Tuple[bool, str]:
    """Тест підключення до БД"""
    conn = get_connection()
    if not conn:
        return False, "Cannot connect to database"
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        orders_count = cursor.fetchone()[0]
        
        return True, f"SQLite {version}, {orders_count} orders"
        
    except sqlite3.Error as e:
        return False, str(e)
    finally:
        conn.close()
DATABASE_EOF

print_step "services/database.py створено"
echo ""

# Крок 8: Оновлення requirements.txt
echo "Крок 8/8: Оновлення requirements.txt..."

# Перевірка чи є gspread
if ! grep -q "gspread" requirements.txt; then
    echo "gspread==5.12.0" >> requirements.txt
    print_step "Додано gspread в requirements.txt"
else
    print_step "gspread вже є в requirements.txt"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}✅ ВСТАНОВЛЕННЯ ЗАВЕРШЕНО!${NC}"
echo "=================================================="
echo ""
echo "Створені файли:"
echo "  ✓ services/telegram.py"
echo "  ✓ services/gemini.py"
echo "  ✓ services/sheets.py"
echo "  ✓ services/database.py"
echo "  ✓ services/__init__.py"
echo ""
echo "Наступні кроки:"
echo "  1. pip install -r requirements.txt"
echo "  2. python test_imports.py"
echo "  3. python main.py"
echo ""
echo "Для тестування запусти:"
echo "  python -c \"from services import telegram, gemini, sheets, database; print('✅ All OK')\""
echo ""
