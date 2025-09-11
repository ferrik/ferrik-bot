from flask import Flask, request
import requests
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8245370711:AAGeaVdip9vedm5jPDeX7toDkFRCUCkFRfg")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

@app.route("/")
def home():
    return "Ferrik-bot is running!"

@app.route("/webhook/Ferrik123!", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        reply_text = f"Привіт 👋, я Ferrik-бот! Ти написав: {text}"

        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": reply_text}
        )

    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
