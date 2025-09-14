import os
import logging
from flask import Flask, request
import requests

# 🔹 Налаштування логів
logging.basicConfig(level=logging.INFO)

# 🔹 Токен бота з Render (через змінні середовища!)
TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# 🔹 Flask сервер
app = Flask(__name__)

# 📌 Головне меню (з емодзі)
MAIN_MENU = {
    "order_food": "🍔 Замовити їжу",
    "reserve_table": "📅 Забронювати столик",
    "offers": "💸 Акції та знижки",
    "my_profile": "🙋‍♂️ Мій профіль"
}


def send_message(chat_id, text, reply_markup=None):
    """Відправка повідомлення в Telegram"""
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)


def main_menu_keyboard():
    """Формуємо клавіатуру головного меню"""
    keyboard = [[{"text": v}] for v in MAIN_MENU.values()]
    return {"keyboard": keyboard, "resize_keyboard": True}


@app.route(f"/webhook/{os.getenv('WEBHOOK_SECRET')}", methods=["POST"])
def webhook():
    """Обробка повідомлень з Telegram"""
    data = request.get_json()
    logging.info(data)

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            send_message(
                chat_id,
                "👋 Вітаю! Я <b>FerrikBot</b> – твій помічник з доставки їжі та бронювання 🍕🍷",
                reply_markup=main_menu_keyboard()
            )
        elif text == MAIN_MENU["order_food"]:
            send_message(chat_id, "🍽 Що хочеш замовити? Напиши страву, я знайду для тебе 🧑‍🍳")
        elif text == MAIN_MENU["reserve_table"]:
            send_message(chat_id, "📅 Вкажи ресторан та час, я допоможу забронювати столик 🪑")
        elif text == MAIN_MENU["offers"]:
            send_message(chat_id, "💸 Ось актуальні знижки та акції від наших партнерів 🎉")
        elif text == MAIN_MENU["my_profile"]:
            send_message(chat_id, "🙋‍♂️ Тут буде твій профіль: ім’я, адреса, замовлення 🏠📞")
        else:
            send_message(chat_id, "🤖 Не розумію команду. Використай меню ⬇️", reply_markup=main_menu_keyboard())

    return {"ok": True}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
