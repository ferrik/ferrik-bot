# main.py — Ferrik minimal in-memory bot (Part 1)
from flask import Flask, request, jsonify
import os
import requests
import json
import uuid
import logging

app = Flask(__name__)

# CONFIG from environment (set on Render)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # set this in Render env
TELEGRAM_SECRET_TOKEN = os.environ.get("TELEGRAM_SECRET_TOKEN", "Ferrik123!")  # set same when setWebhook
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ferrik_minimal")

# --- In-memory sample data (MVP) ---
RESTAURANTS = {
    "1": {
        "name": "Піцерія Наполі 🍕",
        "menu": [
            {"id": "1_1", "name": "Піца Маргарита", "price": 150},
            {"id": "1_2", "name": "Піца Пепероні", "price": 180}
        ]
    },
    "2": {
        "name": "Суші Майстер 🍣",
        "menu": [
            {"id": "2_1", "name": "Каліфорнія рол", "price": 220},
            {"id": "2_2", "name": "Філадельфія", "price": 250}
        ]
    }
}

# carts stored in memory: {telegram_id: [item_dict, ...]}
CARTS = {}

# --- Telegram helper functions ---
def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        # Telegram expects reply_markup as JSON string
        payload["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=8)
        logger.info("sendMessage status %s", r.status_code)
        return r.json()
    except Exception as e:
        logger.exception("send_message error: %s", e)
        return None

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(f"{API_URL}/editMessageText", json=payload, timeout=8)
        logger.info("editMessage status %s", r.status_code)
        return r.json()
    except Exception as e:
        logger.exception("edit_message error: %s", e)
        return None

def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    try:
        r = requests.post(f"{API_URL}/answerCallbackQuery", json=payload, timeout=5)
        return r.json()
    except Exception as e:
        logger.exception("answer_callback error: %s", e)
        return None

# helper to create inline keyboard from rows of buttons
def make_inline_keyboard(rows):
    return {"inline_keyboard": rows}

# --- Webhook endpoint ---
@app.route("/telegram/webhook", methods=["POST"])
def webhook():
    # verify secret header (Telegram sets X-Telegram-Bot-Api-Secret-Token when using secret_token)
    header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if TELEGRAM_SECRET_TOKEN and header != TELEGRAM_SECRET_TOKEN:
        logger.warning("Invalid secret header: %s", header)
        return jsonify({"ok": False, "error": "invalid secret"}), 403

    update = request.get_json(force=True)
    logger.info("Update received keys: %s", list(update.keys()))
    try:
        # handle message
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "").strip()
            user_name = msg.get("from", {}).get("first_name", "")
            handle_text(chat_id, text, user_name)

        # handle callback_query
        if "callback_query" in update:
            cq = update["callback_query"]
            handle_callback(cq)

        return jsonify({"ok": True})
    except Exception as e:
        logger.exception("Webhook processing failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

# --- Text handler (simple commands and free text) ---
def handle_text(chat_id, text, user_name):
    text_l = (text or "").lower()
    # start / greeting
    if text_l in ["/start", "start", "привіт", "hi", "hello"]:
        reply = (f"Привіт {user_name or ''}! 👋\n\n"
                 "Я — Ferrik 🍽️. Можу допомогти замовити їжу.\n\n"
                 "📌 Команди:\n"
                 "• /menu — Переглянути заклади\n"
                 "• 'кошик' — Показати мій кошик\n"
                 "• Напиши пошук: наприклад — \"піца з куркою до 200 грн\"\n\nБажаєш почати? 😊")
        send_message(chat_id, reply)
        return

    # show restaurants
    if text_l in ["/menu", "menu", "ресторани", "ресторани 🍽️", "ресторани🍽️"]:
        rows = []
        for rid, r in RESTAURANTS.items():
            rows.append([{"text": r["name"], "callback_data": f"rest_{rid}"}])
        send_message(chat_id, "Оберіть ресторан у Тернополі:", reply_markup=make_inline_keyboard(rows))
        return

    # show cart
    if text_l in ["кошик", "мій кошик", "cart"]:
        show_cart(chat_id)
        return

    # naive free-text handling (we'll replace with Gemini in Part 3)
    # simple keyword: if contains 'піца' show pizzas across restaurants
    if "піца" in text_l or "pizza" in text_l:
        # collect pizza dishes
        rows = []
        for rid, r in RESTAURANTS.items():
            for item in r["menu"]:
                if "піца" in item["name"].lower() or "pizza" in item["name"].lower() or "піца" in item.get("category", ""):
                    rows.append([{"text": f"{item['name']} — {item['price']} грн", "callback_data": f"add_{item['id']}"}])
        if rows:
            send_message(chat_id, "Знайдено позиції (піца):", reply_markup=make_inline_keyboard(rows))
            return

    # fallback: help
    send_message(chat_id, "Вибач, я не зрозумів. Спробуйте /menu або напишіть, що шукаєте (наприклад: 'піца').")

# --- Callback handler (inline buttons) ---
def handle_callback(cq):
    data = cq.get("data")
    callback_id = cq.get("id")
    message = cq.get("message") or {}
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    message_id = message.get("message_id")

    logger.info("Callback data: %s", data)

    if not data or not chat_id:
        answer_callback(callback_id)
        return

    # restaurant selected -> show menu
    if data.startswith("rest_"):
        rest_id = data.split("_", 1)[1]
        rest = RESTAURANTS.get(rest_id)
        if not rest:
            send_message(chat_id, "❗ Ресторан не знайдено.")
            answer_callback(callback_id)
            return
        rows = []
        for item in rest["menu"]:
            rows.append([{"text": f"{item['name']} — {item['price']} грн", "callback_data": f"add_{item['id']}"}])
        # extra buttons
        rows.append([{"text": "📥 Переглянути кошик", "callback_data": "view_cart"}])
        rows.append([{"text": "⬅️ Назад до закладів", "callback_data": "back_to_menu"}])
        edit_message(chat_id, message_id, f"Меню {rest['name']}:", reply_markup=make_inline_keyboard(rows))
        answer_callback(callback_id)
        return

    # add item to cart
    if data.startswith("add_"):
        item_id = data.split("_", 1)[1]  # e.g. "1_1"
        item = None
        for r in RESTAURANTS.values():
            for it in r["menu"]:
                if it["id"] == item_id:
                    item = it; break
            if item: break
        if not item:
            send_message(chat_id, "❗ Страву не знайдено.")
            answer_callback(callback_id)
            return
        # add to cart
        CARTS.setdefault(str(chat_id), []).append(item)
        send_message(chat_id, f"✅ Додано до кошика: {item['name']} — {item['price']} грн")
        answer_callback(callback_id, text="Додано до кошика ✅")
        return

    if data == "view_cart":
        show_cart(chat_id)
        answer_callback(callback_id)
        return

    if data == "clear_cart":
        CARTS[str(chat_id)] = []
        send_message(chat_id, "🗑️ Кошик очищено.")
        answer_callback(callback_id)
        return

    if data == "order_confirm":
        # create a simple fake order id
        items = CARTS.get(str(chat_id), [])
        if not items:
            send_message(chat_id, "Кошик порожній — немає чого замовляти.")
            answer_callback(callback_id)
            return
        total = sum(i["price"] for i in items)
        order_id = str(uuid.uuid4())[:8]
        CARTS[str(chat_id)] = []
        send_message(chat_id, f"✅ Ваше замовлення {order_id} прийнято!\nСума: {total} грн\nМи зв'яжемося для підтвердження. ☎️")
        logger.info("New order %s from %s total=%s", order_id, chat_id, total)
        answer_callback(callback_id)
        return

    if data == "back_to_menu":
        # simulate /menu
        rows = []
        for rid, r in RESTAURANTS.items():
            rows.append([{"text": r["name"], "callback_data": f"rest_{rid}"}])
        edit_message(chat_id, message_id, "Оберіть ресторан:", reply_markup=make_inline_keyboard(rows))
        answer_callback(callback_id)
        return

    # default
    answer_callback(callback_id)

# --- show_cart helper ---
def show_cart(chat_id):
    items = CARTS.get(str(chat_id), [])
    if not items:
        send_message(chat_id, "🛒 Ваш кошик порожній.")
        return
    lines = []
    total = 0
    for it in items:
        lines.append(f"• {it['name']} — {it['price']} грн")
        total += it["price"]
    text = "🛒 Ваш кошик:\n" + "\n".join(lines) + f"\n\n*Загалом: {total} грн*"
    rows = [
        [{"text": "📝 Підтвердити замовлення", "callback_data": "order_confirm"}],
        [{"text": "🗑 Очистити кошик", "callback_data": "clear_cart"}],
        [{"text": "⬅️ Продовжити вибір", "callback_data": "back_to_menu"}]
    ]
    send_message(chat_id, text, reply_markup=make_inline_keyboard(rows), parse_mode="Markdown")

# --- health ---
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# small index
@app.route("/")
def index():
    return "Ferrik minimal bot running."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting Ferrik minimal on port %s", port)
    app.run(host="0.0.0.0", port=port)
