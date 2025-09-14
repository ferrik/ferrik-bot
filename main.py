import os
import logging
import json
import uuid
from flask import Flask, request, jsonify
import requests

# ---- Конфігурація ----
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "Ferrik123!")  # повинен співпадати з тим, що в setWebhook
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ---- Логи ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ferrik")

# ---- Flask app (gunicorn шукає 'app') ----
app = Flask(__name__)

# ---- Тестові дані (MVP) ----
RESTAURANTS = {
    1: {
        "name": "Піцерія Наполі 🍕",
        "menu": [
            {"dish_id": 101, "name": "Маргарита", "price": 150},
            {"dish_id": 102, "name": "Пепероні", "price": 180},
        ],
    },
    2: {
        "name": "Суші Майстер 🍣",
        "menu": [
            {"dish_id": 201, "name": "Каліфорнія рол", "price": 220},
            {"dish_id": 202, "name": "Філадельфія", "price": 250},
        ],
    },
}

# у пам'яті кошики: {chat_id: [ {dish dict}, ... ] }
CARTS = {}

# ---- Telegram helper functions ----
def tg_send_message(chat_id: int, text: str, reply_markup: dict = None, parse_mode: str = "HTML"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        logger.info("sendMessage status=%s json=%s", r.status_code, r.text[:200])
        return r.json()
    except Exception as e:
        logger.exception("tg_send_message error: %s", e)
        return None

def tg_edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict = None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(f"{API_URL}/editMessageText", json=payload, timeout=10)
        logger.info("editMessageText status=%s", r.status_code)
        return r.json()
    except Exception as e:
        logger.exception("tg_edit_message error: %s", e)
        return None

def tg_answer_callback(callback_query_id: str, text: str = None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        r = requests.post(f"{API_URL}/answerCallbackQuery", json=payload, timeout=5)
        return r.json()
    except Exception as e:
        logger.exception("tg_answer_callback error: %s", e)
        return None

# ---- Utility: keyboards ----
def main_keyboard():
    # Reply keyboard (persistent)
    keyboard = [
        [{"text": "🍔 Замовити їжу"}, {"text": "📅 Забронювати столик"}],
        [{"text": "💸 Акції"}, {"text": "📦 Мій кошик"}],
    ]
    return {"keyboard": keyboard, "resize_keyboard": True, "one_time_keyboard": False}

def restaurants_inline_keyboard():
    rows = []
    for rid, r in RESTAURANTS.items():
        rows.append([{"text": r["name"], "callback_data": f"rest_{rid}"}])
    return {"inline_keyboard": rows}

def menu_inline_keyboard_for_restaurant(rest_id):
    rows = []
    for item in RESTAURANTS[rest_id]["menu"]:
        rows.append([{"text": f"{item['name']} — {item['price']} грн", "callback_data": f"add_{item['dish_id']}"}])
    rows.append([{"text": "📥 Переглянути кошик", "callback_data": "view_cart"}])
    return {"inline_keyboard": rows}

def cart_keyboard():
    return {"inline_keyboard": [[{"text":"📝 Оформити замовлення","callback_data":"order_confirm"}, {"text":"🗑 Очистити кошик","callback_data":"clear_cart"}]]}

# ---- Webhook endpoint ----
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    # optional header check (if you used secret token in setWebhook; adjust if you used secret in URL)
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_SECRET and header_secret and header_secret != WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret header: %s", header_secret)
        return jsonify({"ok": False, "error": "invalid secret"}), 403

    update = request.get_json(force=True)
    logger.info("Update received: %s", json.dumps(update)[:1000])

    # message (text)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        # Commands /start
        if text.lower() in ["/start", "start", "hi", "привіт", "hello"]:
            tg_send_message(chat_id,
                            "👋 Вітаю! Я — FerrikBot 🍽️\nВиберіть дію з меню ⬇️",
                            reply_markup=main_keyboard())
            return jsonify({"ok": True})

        # Main menu buttons
        if text == "🍔 Замовити їжу":
            tg_send_message(chat_id, "Ось доступні заклади у Тернополі:", reply_markup=restaurants_inline_keyboard())
            return jsonify({"ok": True})
        if text == "📦 Мій кошик" or text.lower() == "кошик":
            return _handle_show_cart(chat_id)
        if text == "💸 Акції":
            tg_send_message(chat_id, "🎉 Поки що акцій немає. Зовсім скоро будуть пропозиції!")
            return jsonify({"ok": True})
        if text == "📅 Забронювати столик":
            tg_send_message(chat_id, "📅 Напишіть, у якому ресторані та на який час ви бажаєте бронювати столик.")
            return jsonify({"ok": True})

        # Free text fallback: if user types dish name -> show popular (MVP)
        tg_send_message(chat_id, "🔎 Шукаю по запиту... Показую популярні страви:", reply_markup=restaurants_inline_keyboard())
        return jsonify({"ok": True})

    # callback_query (inline button pressed)
    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data", "")
        callback_id = cq.get("id")
        message = cq.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        # restaurant selected
        if data.startswith("rest_"):
            rest_id = int(data.split("_", 1)[1])
            if rest_id in RESTAURANTS:
                tg_edit_message(chat_id, message_id, f"Меню — {RESTAURANTS[rest_id]['name']}", reply_markup=menu_inline_keyboard_for_restaurant(rest_id))
                tg_answer_callback(callback_id)
                return jsonify({"ok": True})
            else:
                tg_answer_callback(callback_id, text="Ресторан не знайдено")
                return jsonify({"ok": True})

        # add dish
        if data.startswith("add_"):
            dish_id = int(data.split("_", 1)[1])
            # find dish
            dish = None
            for r in RESTAURANTS.values():
                for it in r["menu"]:
                    if it["dish_id"] == dish_id:
                        dish = it
                        break
                if dish:
                    break
            if not dish:
                tg_answer_callback(callback_id, text="Страва не знайдена")
                return jsonify({"ok": True})
            # add to cart
            CARTS.setdefault(chat_id, []).append(dish)
            tg_answer_callback(callback_id, text=f"✅ Додано: {dish['name']}")
            tg_send_message(chat_id, f"✅ Додано {dish['name']} — {dish['price']} грн")
            return jsonify({"ok": True})

        if data == "view_cart":
            tg_answer_callback(callback_id)
            return _handle_show_cart(chat_id)

        if data == "clear_cart":
            CARTS.pop(chat_id, None)
            tg_answer_callback(callback_id, text="Кошик очищено")
            tg_send_message(chat_id, "🗑️ Ваш кошик очищено")
            return jsonify({"ok": True})

        if data == "order_confirm":
            # create a fake order id and clear cart
            cart = CARTS.get(chat_id, [])
            if not cart:
                tg_answer_callback(callback_id, text="Кошик порожній")
                tg_send_message(chat_id, "Ваш кошик порожній 🛒")
                return jsonify({"ok": True})
            total = sum(item["price"] for item in cart)
            order_id = str(uuid.uuid4())[:8]
            CARTS.pop(chat_id, None)
            tg_answer_callback(callback_id, text="Замовлення оформлене")
            tg_send_message(chat_id, f"✅ Замовлення #{order_id} прийнято. Сума: {total} грн.\nМи зв'яжемося з вами для підтвердження.")
            logger.info("New order %s from chat %s total=%s", order_id, chat_id, total)
            return jsonify({"ok": True})

        # default
        tg_answer_callback(callback_id)
        return jsonify({"ok": True})

    # fallback
    return jsonify({"ok": True})

# ---- helper to show cart as separate function ----
def _handle_show_cart(chat_id):
    cart = CARTS.get(chat_id, [])
    if not cart:
        tg_send_message(chat_id, "🛒 Ваш кошик порожній.")
        return jsonify({"ok": True})
    lines = [f"• {it['name']} — {it['price']} грн" for it in cart]
    total = sum(it["price"] for it in cart)
    text = "🛒 Ваш кошик:\n" + "\n".join(lines) + f"\n\n<b>Загалом: {total} грн</b>"
    tg_send_message(chat_id, text, reply_markup=cart_keyboard())
    return jsonify({"ok": True})

# ---- health check ----
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# ---- Run (not used by gunicorn in prod, but useful locally) ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting local Flask server on port %s", port)
    app.run(host="0.0.0.0", port=port)
