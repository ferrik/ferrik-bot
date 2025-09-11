from flask import Flask, request
import os
import requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "Ferrik123!")

@app.route('/')
def home():
    return "Ferrik bot is running!"

@app.route(f"/webhook/{SECRET_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Received update:", data)
    # сюди пізніше додамо обробку повідомлень
    return {"ok": True}
