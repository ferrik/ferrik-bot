import os
import logging
import json
import re
from flask import Flask, request, jsonify
import requests
from handlers.cart import show_cart, add_item_to_cart
from handlers.order import start_checkout_process
from handlers.geo import check_delivery_availability
from services.sheets import init_gspread_client, update_menu_cache, get_item_by_id, test_gspread_connection
from services.gemini import get_gemini_recommendation
from services.telegram import tg_send_message, tg_send_photo, tg_answer_callback, tg_edit_message
from models.user import init_db, get_state, set_state, get_cart, set_cart
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    logging.warning("zoneinfo not found. Using naive datetime.")
    ZoneInfo = None

app = Flask(__name__)

# Налаштування логів
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)
logger = logging.getLogger("ferrik")

# Змінні середовища
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "Ferrik123").strip()
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "").strip()
OPERATOR_CHAT_ID = os.environ.get("OPERATOR_CHAT_ID", "").strip()
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Тернопіль").strip()
TIMEZONE_NAME = os.environ.get("TIMEZONE", "Europe/Kyiv").strip()

# Стани користувача
STATE_NORMAL = "normal"
STATE_AWAITING_PHONE = "awaiting_phone"
STATE_AWAITING_PHONE_CONFIRM = "awaiting_phone_confirm"
STATE_AWAITING_ADDRESS = "awaiting_address"
STATE_AWAITING_PAYMENT_METHOD = "awaiting_payment_method"
STATE_AWAITING_DELIVERY_TYPE = "awaiting_delivery_type"
STATE_AWAITING_DELIVERY_TIME = "awaiting_delivery_time"
STATE_AWAITING_CONFIRMATION = "awaiting_confirmation"
STATE_AWAITING_FEEDBACK = "awaiting_feedback"
STATE_AWAITING_OPERATOR_MESSAGE = "awaiting_operator_message"

# Webhook з обробкою помилок
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_SECRET and header_secret != WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret header: %s", header_secret)
        return jsonify({"ok": False, "error": "invalid secret"}), 403

    update = request.get_json(silent=True)
    if not update:
        logger.warning("Webhook received empty data.")
        return jsonify({"status": "empty"}), 200

    try:
        # Обробка повідомлень
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "").strip()
            user_state = get_state(chat_id)

            if text == "/start":
                greeting = generate_personalized_greeting(msg.get("from", {}).get("first_name", "Друже"))
                tg_send_message(chat_id, greeting, reply_markup=main_keyboard())
                set_state(chat_id, STATE_NORMAL)
            elif text == "/cart":
                show_cart(chat_id)
            elif text.startswith("/add_"):
                item_id = text.replace("/add_", "")
                add_item_to_cart(chat_id, item_id)
            elif user_state == STATE_AWAITING_PHONE:
                phone_number = re.sub(r'[^\d+]', '', text)
                if re.match(r'^\+?3?8?0\d{9}$', phone_number):
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "✅ Вірний номер", "callback_data": f"confirm_phone
