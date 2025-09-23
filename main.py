import os
import logging
import json
import re
from flask import Flask, request, jsonify
import requests
from handlers.cart import show_cart, add_item_to_cart
from handlers.order import start_checkout_process
from handlers.geo import check_delivery_availability
from services.sheets import init_gspread_client, get_menu_from_sheet, get_item_by_id
from services.gemini import get_gemini_recommendation
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
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Тернопіль")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Зберігання стану в пам'яті
bot_state = {}

# Ініціалізуємо клієнт Google Sheets
gspread_client = init_gspread_client()

# Функція відправки повідомлень у Telegram
def tg_send_message(chat_id, text, reply_markup=None):
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)

    response = requests.post(f"{API_URL}/sendMessage", json=payload)
    return response.json()

# Функція відправки відповіді на callback
def tg_answer_callback(callback_id, text):
    payload = {
        'callback_query_id': callback_id,
        'text': text,
        'show_alert': False
    }
    requests.post(f"{API_URL}/answerCallbackQuery", json=payload)

# === ПОКРАЩЕННЯ 1: ВИНОСИМО ПРОМПТ В ОКРЕМУ ЗМІННУ ===
# Це робить код чистішим і дозволяє легко редагувати промпт
GEMINI_PROMPT_TEMPLATE = """
Ти — чат-бот для кафе. Твоє ім'я FerrikFootBot.
Твоя головна мета — допомагати клієнтам, надаючи інформацію про меню та відповідаючи на їхні запитання.

# Контекст
Ось наше актуальне меню у форматі JSON. Відповідай, використовуючи лише цю інформацію. НЕ ВИГАДУЙ страв, яких немає в меню.

{menu_json}

Це історія нашої розмови (від найстарішого до найновішого):
Користувач: {user_prompt}

# Інструкції
1. Завжди відповідай українською мовою.
2. Відповідай дружньо, доброзичливо та інформативно.
3. Усі відповіді мають ґрунтуватися виключно на наданому меню.
4. Якщо клієнт запитує про страву, якої немає в меню, чесно повідомляй про це, використовуючи фразу: 'Вибачте, цієї страви немає в нашому меню. Можливо, я можу запропонувати щось інше?'.
5. Якщо питання не стосується меню, відповідай: 'Вибачте, я можу допомогти лише з питаннями щодо нашого меню. Чим можу вас почастувати?'.
6. Використовуй історію розмови для персоналізації.
7. Якщо клієнт щось обрав, можеш порадити додаткову страву чи напій.
8. Виділяй **назви страв** і **ціни** для кращої читабельності.
"""

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return jsonify({"error": "Invalid token"}), 403

    update = request.json
    logger.info(f"Received update: {update}")

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        user_id = message["from"]["id"]
        user_name = message["from"].get("first_name", "Друже")
        
        # Обробка команд
        if text == "/start":
            greeting = generate_personalized_greeting(user_name)
            tg_send_message(chat_id, greeting)
            set_state(user_id, 'main')
        elif text == "/menu":
            menu_data = get_menu_from_sheet(gspread_client, GOOGLE_SHEET_ID)
            menu_text = "<b>Наше меню:</b>\n\n"
            categories = {}
            for item in menu_data:
                category = item.get("Категорія", "Інше")
                if category not in categories:
                    categories[category] = []
                categories[category].append(f'<b>{item["Страви"]}</b> - {item["Опис"]} - <b>{item["Ціна"]}</b> грн.')
            
            for category, items in categories.items():
                menu_text += f"<b>{category}</b>\n"
                menu_text += "\n".join(items)
                menu_text += "\n\n"
            
            tg_send_message(chat_id, menu_text)
            
        elif text == "/cart":
            show_cart(chat_id, user_id)
        elif text.startswith("/add_item"):
            try:
                item_id = text.split("_")[2]
                add_item_to_cart(chat_id, user_id, item_id, gspread_client, GOOGLE_SHEET_ID)
            except IndexError:
                tg_send_message(chat_id, "Некоректний формат команди. Використовуйте /add_item_<ID>")
        elif text == "/checkout":
            start_checkout_process(chat_id, user_id)
        elif text == "/history":
             # Це лише заглушка для прикладу
            tg_send_message(chat_id, "Історія ваших замовлень буде тут!")
        elif text == "/help":
            help_message = (
                "<b>Список команд:</b>\n"
                "/start - Почати спілкування\n"
                "/menu - Показати наше меню\n"
                "/cart - Показати ваш кошик\n"
                "/checkout - Оформити замовлення\n"
                "/history - Показати історію ваших замовлень\n"
                "/help - Показати цю довідку"
            )
            tg_send_message(chat_id, help_message)
        else:
            # === ПОКРАЩЕННЯ 2: ВИКОРИСТОВУЄМО ШАБЛОН ПРОМПТА ===
            # Тепер ми просто заповнюємо шаблон даними, що робить код лаконічнішим
            menu_data = get_menu_from_sheet(gspread_client, GOOGLE_SHEET_ID)
            menu_json = json.dumps(menu_data, ensure_ascii=False, indent=2)

            prompt = GEMINI_PROMPT_TEMPLATE.format(
                menu_json=menu_json,
                user_prompt=text
            )
            
            # Викликаємо функцію, передаючи оновлений промпт
            response_text = get_gemini_recommendation(prompt, GEMINI_API_KEY)
            
            # Відправка відповіді користувачу
            tg_send_message(chat_id, response_text)

    elif "callback_query" in update:
        callback_query = update["callback_query"]
        chat_id = callback_query["message"]["chat"]["id"]
        query_data = callback_query["data"]
        callback_id = callback_query["id"]
        user_id = callback_query["from"]["id"]
        
        # Обробка callback запитів
        if query_data.startswith("add_to_cart_"):
            item_id = query_data.replace("add_to_cart_", "")
            add_item_to_cart(chat_id, user_id, item_id, gspread_client, GOOGLE_SHEET_ID)
            tg_answer_callback(callback_id, "Товар додано до кошика!")
        elif query_data.startswith("remove_from_cart_"):
            item_id = query_data.replace("remove_from_cart_", "")
            cart = get_cart(user_id)
            if item_id in cart:
                del cart[item_id]
                set_cart(user_id, cart)
            show_cart(chat_id, user_id)
            tg_answer_callback(callback_id, "Товар видалено з кошика!")

    return jsonify({"status": "ok"})

def generate_personalized_greeting(user_name="Друже"):
    user_name = (user_name or '').strip() or 'Друже'
    current = datetime.now() if not ZoneInfo else datetime.now(ZoneInfo('Europe/Kiev'))
    hour = current.hour

    greeting = f"Доброго {'ранку' if 6 <= hour < 12 else 'дня' if 12 <= hour < 18 else 'вечора'}, {user_name}! 😊"
    status = "Ресторан відкритий! 🍽️ Готові прийняти ваше замовлення." if is_restaurant_open() else "Ресторан закритий. 😔 Працюємо з 9:00 до 22:00."
    return f"{greeting}\n\n{status}\n\nЯ ваш помічник для замовлення їжі! 🍔🍕"

def is_restaurant_open():
    current_hour = datetime.now().hour if not ZoneInfo else datetime.now(ZoneInfo('Europe/Kiev')).hour
    return 9 <= current_hour < 22

# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

# Ініціалізація
with app.app_context():
    logger.info("Bot initialization started.")
    try:
        init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
