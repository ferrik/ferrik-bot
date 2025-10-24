import os
import json
import psycopg2
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Завантажуємо змінні середовища ---
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# --- Авторизація Google Sheets API ---
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)
service = build('sheets', 'v4', credentials=creds)
sheet_api = service.spreadsheets().values()

# --- Підключення до PostgreSQL ---
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# --- Листи для синхронізації ---
SHEETS = {
    "Меню": "menu",
    "Замовлення": "orders",
    "Промокоди": "promo_codes",
    "Відгуки": "reviews",
    "Конфіг": "config",
    "Партнери": "partners"
}

def sanitize_column(col):
    """Підчищає назви стовпців під формат SQL."""
    return col.strip().replace(" ", "_").replace("(", "").replace(")", "").replace("%", "perc").replace("-", "_")

def create_table_if_not_exists(table_name, df):
    """Автоматично створює таблицю в PostgreSQL, якщо її ще немає."""
    cols = []
    for col in df.columns:
        col_name = sanitize_column(col)
        cols.append(f'"{col_name}" TEXT')
    create_sql = f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join(cols)});'
    cursor.execute(create_sql)
    conn.commit()

def sync_sheet(sheet_name, table_name):
    """Синхронізація одного листа."""
    print(f"🔄 Синхронізація листа: {sheet_name} → таблиця: {table_name}")
    try:
        result = sheet_api.get(spreadsheetId=GOOGLE_SHEET_ID, range=sheet_name).execute()
        values = result.get("values", [])
        if not values:
            print(f"⚠️ Порожній лист: {sheet_name}")
            return
        df = pd.DataFrame(values[1:], columns=values[0])
        create_table_if_not_exists(table_name, df)

        # Очищення таблиці перед оновленням
        cursor.execute(f"DELETE FROM {table_name};")

        # Вставка рядків
        for _, row in df.iterrows():
            cols = [sanitize_column(c) for c in df.columns]
            placeholders = ", ".join(["%s"] * len(cols))
            insert_sql = f'INSERT INTO {table_name} ({", ".join(cols)}) VALUES ({placeholders})'
            cursor.execute(insert_sql, tuple(row))
        conn.commit()
        print(f"✅ Успішно синхронізовано: {sheet_name}")
    except Exception as e:
        print(f"❌ Помилка при синхронізації {sheet_name}: {e}")

def main():
    for sheet_name, table_name in SHEETS.items():
        sync_sheet(sheet_name, table_name)
    cursor.close()
    conn.close()
    print("🎯 Усі листи синхронізовано!")

if __name__ == "__main__":
    main()
