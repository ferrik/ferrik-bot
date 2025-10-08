#!/usr/bin/env python3
# main.py — Flask + Telegram webhook, Google Sheets integration, simple cart

import os
import json
import logging
from decimal import Decimal
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, abort

# локальний bot_config (файл вище)
import bot_config as cfg

# Google Sheets
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Telegram send message
import requests

# Optional Redis for carts
redis_client = None
if cfg.REDIS_URL:
    try:
        import redis
        redis_client = redis.from_url(cfg.REDIS_URL)
    except Exception as e:
        logging.getLogger(__name__).warning("Redis init failed: %s", e)
        redis_client = None

app = Flask(__name__)

logger = logging.getLogger("hubsy")
logger.setLevel(cfg.LOG_LEVEL if hasattr(cfg, "LOG_LEVEL") else logging.INFO)

# In-memory cart fallback
IN_MEMORY_CARTS = {}  # {user_id: {item_id: qty, ...}}

# Menu cache
MENU_CACHE = {
    "items": [],
    "loaded_at": None
}

# -------------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------------
def require_secret(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if not header or not cfg.WEBHOOK_SECRET or header != cfg.WEBHOOK_SECRET:
            logger.warning("Invalid webhook secret header: %s", header)
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper

def telegram_send_message(chat_id: int, text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            logger.warning("Telegram send failed: %s %s", r.status_code, r.text)
        return r.json()
    except Exception as e:
        logger.exception("Telegram send exception: %s", e)
        return None

# -------------------------------------------------------------------------
# Google Sheets helpers
# -------------------------------------------------------------------------
def get_sheets_service():
    """
    Create Google Sheets service using credentials string in cfg.GOOGLE_CREDENTIALS_JSON
    """
    if not cfg.GOOGLE_CREDENTIALS_JSON:
        raise RuntimeError("Google credentials not provided")
    creds_info = json.loads(cfg.GOOGLE_CREDENTIALS_JSON)
    credentials = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=credentials, cache_discovery=False)
    return service

def load_menu_from_sheets(force=False):
    # cache for 5 minutes
    import time
    if MENU_CACHE["items"] and not force and MENU_CACHE["loaded_at"] and (time.time() - MENU_CACHE["loaded_at"] < 300):
        return MENU_CACHE["items"]
    try:
        svc = get_sheets_service()
        sheet = svc.spreadsheets()
        # Read first sheet named "Меню" or the first sheet
        resp = sheet.values().get(spreadsheetId=cfg.GOOGLE_SHEET_ID, range="Меню!A1:Z1000").execute()
        values = resp.get("values", [])
        if not values or len(values) < 2:
            MENU_CACHE["items"] = []
            MENU_CACHE["loaded_at"] = time.time()
            return []
        headers = values[0]
        items = []
        for row in values[1:]:
            # map row to dict
            row_dict = {}
            for i, h in enumerate(headers):
                row_dict[h] = row[i] if i < len(row) else ""
            try:
                price = Decimal(str(row_dict.get("Ціна", "0")).replace(",", "."))
            except Exception:
                price = Decimal("0")
            item = {
                "id": row_dict.get("ID") or row_dict.get("ID Страви") or row_dict.get("PZ001"),
                "name": row_dict.get("Страви") or row_dict.get("Назва") or row_dict.get("Назва Страви"),
                "category": row_dict.get("Категорія"),
                "description": row_dict.get("Опис", ""),
                "price": price,
                "restaurant": row_dict.get("Ресторан", ""),
                "active": (str(row_dict.get("Активний", "Так")).lower() in ["так", "yes", "true"])
            }
            if item["id"]:
                items.append(item)
        MENU_CACHE["items"] = items
        MENU_CACHE["loaded_at"] = time.time()
        logger.info("Loaded %d menu items from Google Sheets", len(items))
        return items
    except Exception as e:
        logger.exception("Failed to load menu from Sheets: %s", e)
        return MENU_CACHE.get("items", [])

def append_order_to_sheets(order_record: dict):
    """
    Append order_record as a new row to Orders sheet.
    order_record should include: order_id, telegram_id, time, items_json, sum, status
    """
    try:
        svc = get_sheets_service()
        sheet = svc.spreadsheets()
        row = [
            order_record.get("order_id"),
            str(order_record.get("telegram_id")),
            order_record.get("time"),
            json.dumps(order_record.get("items"), ensure_ascii=False),
            str(order_record.get("sum")),
            order_record.get("status")
        ]
        sheet.values().append(
            spreadsheetId=cfg.GOOGLE_SHEET_ID,
            range="Замовлення!A1:F1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]}
        ).execute()
        logger.info("Appended order %s to Sheets", order_record.get("order_id"))
        return True
    except Exception as e:
        logger.exception("Failed to append order to Sheets: %s", e)
        return False

# -------------------------------------------------------------------------
# Cart helpers
# -------------------------------------------------------------------------
def get_cart_key(user_id):
    return f"cart:{user_id}"

def get_cart(user_id):
    if redis_client:
        raw = redis_client.get(get_cart_key(user_id))
        if raw:
            try:
                return json.loads(raw)
            except:
                return {}
        return {}
    else:
        return IN_MEMORY_CARTS.setdefault(str(user_id), {})

def save_cart(user_id, cart):
    if redis_client:
        redis_client.setex(get_cart_key(user_id), cfg.CART_TTL_HOURS * 3600, json.dumps(cart, ensure_ascii=False))
    else:
        IN_MEMORY_CARTS[str(user_id)] = cart

def clear_cart(user_id):
    if redis_client:
        redis_client.delete(get_cart_key(user_id))
    else:
        IN_MEMORY_CARTS.pop(str(user_id), None)

# -------------------------------------------------------------------------
# Simple search (fallback if Gemini off)
# -------------------------------------------------------------------------
def simple_search(query):
    q = query.strip().lower()
    items = load_menu_from_sheets()
    results = []
    for it in items:
        if not it.get("active", True):
            continue
        text = f"{it.get('name','')} {it.get('description','')} {it.get('category','')}".lower()
        if q in text:
            results.append(it)
    return results

# -------------------------------------------------------------------------
# Telegram update handler
# -------------------------------------------------------------------------
@app.route("/webhook", methods=["POST"])
@require_secret
def webhook():
    data = request.get_json(force=True)
    logger.info("Received update: %s", data.get("update_id"))
    # handle different update types
    try:
        if "message" in data:
            handle_message(data["message"])
        elif "callback_query" in data:
            # optional: handle inline buttons if implemented
            logger.info("Callback query received")
        else:
            logger.info("Unknown update type")
    except Exception as e:
        logger.exception("Error handling update: %s", e)
    return jsonify({"ok": True})

def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "") or ""
    logger.info("Message from %s: %s", user_id, text)

    # Commands
    if text.strip().lower().startswith("/start"):
        send_welcome(chat_id)
        return

    if text.strip().lower() in ["меню", "menu"]:
        send_menu(chat_id)
        return

    if text.strip().lower() in ["кошик", "cart"]:
        send_cart(chat_id, user_id)
        return

    if text.strip().lower().startswith("додати "):
        # "Додати <ID> <qty>"
        parts = text.strip().split()
        if len(parts) >= 2:
            item_id = parts[1]
            qty = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 1
            add_to_cart(user_id, item_id, qty, chat_id)
            return

    if text.strip().lower().startswith("замовити"):
        place_order(user_id, chat_id)
        return

    # Otherwise, try search (AI or simple)
    results = simple_search(text)
    if results:
        reply = "Знайдено:\n"
        for it in results[:8]:
            reply += f"- {it['id'] or ''} | {it['name']} — {it['price']} грн\n"
        reply += '\nЩоб додати у корзину: "Додати <ID> [кількість]"'
        telegram_send_message(chat_id, reply)
    else:
        telegram_send_message(chat_id, "Нічого не знайдено. Спробуй інше запитання або напиши 'Меню'.")

def send_welcome(chat_id):
    text = "Вітаю! Я Hubsy — бот для замовлення їжі.\n\nКоманди:\n- Меню — подивитись меню\n- Кошик — переглянути корзину\n- Додати <ID> [qty] — додати товар\n- Замовити — оформити замовлення"
    keyboard = {
        "keyboard": [
            [{"text": "Меню"}],
            [{"text": "Кошик"}]
        ],
        "resize_keyboard": True
    }
    telegram_send_message(chat_id, text, reply_markup=keyboard)

def send_menu(chat_id):
    items = load_menu_from_sheets()
    if not items:
        telegram_send_message(chat_id, "Меню наразі порожнє.")
        return
    # send first N items as a short list
    text = "<b>Меню (вкорочено)</b>\n\n"
    for it in items[:20]:
        if not it.get("active", True):
            continue
        text += f"{it.get('id','')}: <b>{it.get('name')}</b>\n{it.get('description','')}\nЦіна: {it.get('price')} грн\n\n"
    text += 'Щоб додати у корзину: "Додати <ID> [кількість]"'
    telegram_send_message(chat_id, text)

def add_to_cart(user_id, item_id, qty, chat_id=None):
    items = load_menu_from_sheets()
    item = next((i for i in items if i.get("id") == item_id or i.get("id")==str(item_id)), None)
    if not item:
        if chat_id:
            telegram_send_message(chat_id, f"Товар з ID={item_id} не знайдено.")
        return False
    cart = get_cart(user_id)
    if len(cart.keys()) >= cfg.MAX_CART_ITEMS and item_id not in cart:
        telegram_send_message(chat_id, "Досягнуто максимуму товарів у корзині.")
        return False
    cart[item_id] = cart.get(item_id, 0) + int(qty)
    save_cart(user_id, cart)
    telegram_send_message(chat_id, f"Додано {qty}× {item.get('name')} у корзину.")
    return True

def send_cart(chat_id, user_id):
    cart = get_cart(user_id)
    if not cart:
        telegram_send_message(chat_id, "Кошик порожній.")
        return
    items = load_menu_from_sheets()
    total = Decimal("0")
    text = "<b>Твій кошик</b>\n\n"
    for item_id, qty in cart.items():
        it = next((i for i in items if i.get("id")==item_id), None)
        if not it:
            continue
        line_sum = it.get("price", Decimal("0")) * Decimal(qty)
        total += line_sum
        text += f"{it.get('id')}: {it.get('name')} — {qty} × {it.get('price')} = {line_sum} грн\n"
    text += f"\n<b>Разом: {total} грн</b>\n\nЩоб оформити: напиши 'Замовити'"
    telegram_send_message(chat_id, text)

def place_order(user_id, chat_id):
    cart = get_cart(user_id)
    if not cart:
        telegram_send_message(chat_id, "Кошик порожній.")
        return
    items = load_menu_from_sheets()
    total = Decimal("0")
    order_items = []
    for item_id, qty in cart.items():
        it = next((i for i in items if i.get("id")==item_id), None)
        if not it:
            continue
        line_sum = it.get("price", Decimal("0")) * Decimal(qty)
        total += line_sum
        order_items.append({
            "id": item_id,
            "name": it.get("name"),
            "qty": qty,
            "unit_price": str(it.get("price")),
            "sum": str(line_sum)
        })
    order_id = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{user_id}"
    order_record = {
        "order_id": order_id,
        "telegram_id": user_id,
        "time": datetime.utcnow().isoformat(),
        "items": order_items,
        "sum": str(total),
        "status": "Нове"
    }
    ok = append_order_to_sheets(order_record)
    if ok:
        telegram_send_message(chat_id, f"✅ Ваше замовлення {order_id} прийнято.\nСума: {total} грн")
        clear_cart(user_id)
        # notify operator if set
        if cfg.OPERATOR_CHAT_ID:
            telegram_send_message(cfg.OPERATOR_CHAT_ID, f"Нове замовлення {order_id} від {user_id}\nСума: {total} грн")
    else:
        telegram_send_message(chat_id, "❌ Помилка при збереженні замовлення. Спробуйте пізніше.")

# -------------------------------------------------------------------------
# Health check & admin endpoints
# -------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

# -------------------------------------------------------------------------
# Start up
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # Local debug run
    try:
        cfg.validate_config()
    except Exception as e:
        logger.exception("Config validation failed: %s", e)
        if cfg.IS_PRODUCTION:
            raise
    logger.info("Starting Flask (development) on port %s", cfg.PORT)
    app.run(host="0.0.0.0", port=cfg.PORT, debug=cfg.FLASK_DEBUG)
