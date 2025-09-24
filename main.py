import os
import logging
import json
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Імпорти обробників
from handlers.cart import show_cart, add_item_to_cart, handle_cart_quantity_change, remove_item_from_cart, clear_cart
from handlers.order import start_checkout_process, handle_delivery_type, handle_payment_method, handle_delivery_time, confirm_order, cancel_order
from handlers.budget import handle_budget_input, show_price_ranges, handle_budget_range
from handlers.message_processor import process_text_message

# Імпорти сервісів
from services.sheets import init_gspread_client, get_menu_from_sheet, get_categories, get_items_by_category
from services.telegram import tg_send_message, tg_answer_callback, tg_edit_message
from services.gemini import analyze_user_request_with_gemini

# Імпорти моделей
from models.user import init_db, get_state, set_state, get_or_create_user, add_chat_history

try:
    from zoneinfo import ZoneInfo
except ImportError:
    logging.warning("zoneinfo not found. Using naive datetime.")
    ZoneInfo = None

app = Flask(__name__)

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ferrik_bot.log')
    ]
)
logger = logging.getLogger("ferrik")

# Thread pool для асинхронної обробки
EXECUTOR = ThreadPoolExecutor(max_workers=5)

# Змінні середовища
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "Ferrik123").strip()
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "").strip()
OPERATOR_CHAT_ID = os.environ.get("OPERATOR_CHAT_ID", "").strip()
TIMEZONE_NAME = os.environ.get("TIMEZONE", "Europe/Kyiv").strip()

# Логування конфігурації
logger.info(f"TELEGRAM_TOKEN: {'✓' if TELEGRAM_TOKEN else '✗'}")
logger.info(f"GOOGLE_SHEET_ID: {'✓' if GOOGLE_SHEET_ID else '✗'}")
logger.info(f"OPERATOR_CHAT_ID: {'✓' if OPERATOR_CHAT_ID else '✗'}")

def main_keyboard():
    """Головне меню бота з покращеними кнопками"""
    return {
        "keyboard": [
            [{"text": "🍕 Піца"}, {"text": "🍣 Суші"}],
            [{"text": "🥗 Салати"}, {"text": "🥤 Напої"}],
            [{"text": "🍰 Десерти"}, {"text": "💰 Бюджет"}],
            [{"text": "🛒 Мій кошик"}, {"text": "📞 Оператор"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def show_menu(chat_id):
    """Показує меню з категоріями"""
    try:
        categories = get_categories()
        if not categories:
            tg_send_message(chat_id, "Меню тимчасово недоступне 😔")
            return
            
        keyboard = {
            "inline_keyboard": [
                [{"text": f"🍽️ {cat}", "callback_data": f"category_{cat}"}] 
                for cat in categories
            ]
        }
        keyboard["inline_keyboard"].append([
            {"text": "💰 Пошук за бюджетом", "callback_data": "budget_search"}
        ])
        
        tg_send_message(chat_id, "Оберіть категорію:", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing menu: {e}")
        tg_send_message(chat_id, "Помилка при завантаженні меню")

def show_category_items(chat_id, category):
    """Показує страви конкретної категорії"""
    try:
        items = get_items_by_category(category)
        
        if not items:
            tg_send_message(chat_id, f"У категорії '{category}' немає страв")
            return
            
        # Заголовок з кількістю страв
        header = f"🍽️ <b>{category}</b> ({len(items)} позицій):"
        tg_send_message(chat_id, header)
            
        # Показуємо кожну страву
        for item in items:
            text = f"<b>{item['name']}</b>\n"
            text += f"💰 <b>Ціна:</b> {item['price']:.2f} грн"
            
            if item.get("description"):
                desc = item['description'][:100] + "..." if len(item['description']) > 100 else item['description']
                text += f"\n📝 {desc}"
            
            if item.get("rating"):
                stars = '⭐' * int(float(item['rating']))
                text += f"\n{stars} {item['rating']}/5"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"➕ Додати ({item['price']:.0f} грн)", 
                      "callback_data": f"add_item_{item['ID']}"}]
                ]
            }
            
            # Відправляємо з фото якщо є
            photo_url = item.get("photo", "").strip()
            if photo_url:
                from services.telegram import tg_send_photo
                tg_send_photo(chat_id, photo_url, text, reply_markup=keyboard)
            else:
                tg_send_message(chat_id, text, reply_markup=keyboard)
                
        # Навігація назад
        back_keyboard = {
            "inline_keyboard": [
                [{"text": "⬅️ Назад до категорій", "callback_data": "show_menu"}]
            ]
        }
        tg_send_message(chat_id, "───────────", reply_markup=back_keyboard)
        
    except Exception as e:
        logger.error(f"Error showing category {category}: {e}")
        tg_send_message(chat_id, "Помилка при завантаженні категорії")

def generate_personalized_greeting(user_name="Друже"):
    """Генерує персоналізоване вітання"""
    user_name = (user_name or '').strip() or 'Друже'
    current = datetime.now()
    if ZoneInfo:
        current = datetime.now(ZoneInfo(TIMEZONE_NAME))
    
    hour = current.hour
    time_greeting = (
        'ранку' if 6 <= hour < 12 else
        'дня' if 12 <= hour < 18 else 'вечора'
    )
    
    greeting = f"Доброго {time_greeting}, {user_name}! 😊"
    
    # Перевіряємо чи відкритий ресторан
    is_open = 9 <= hour < 22
    status = (
        "Ресторан відкритий! 🍽️ Готові прийняти замовлення." if is_open else
        "Ресторан закритий 😔 Працюємо з 9:00 до 22:00."
    )
    
    return f"{greeting}\n\n{status}\n\nЯ ваш помічник FerrikFootBot! Допоможу з вибором і замовленням їжі 🍔🍕"

# Webhook обробник
@app.route('/webhook', methods=['POST'])
def webhook():
    """Головний webhook для обробки оновлень Telegram"""
    try:
        # Перевірка секретного токену
        header_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if WEBHOOK_SECRET and header_secret != WEBHOOK_SECRET:
            logger.warning(f"Invalid webhook secret: {header_secret}")
            return jsonify({"ok": False, "error": "invalid secret"}), 403

        # Отримуємо дані
        data = request.get_json(silent=True)
        if not data:
            logger.warning("Empty webhook data received")
            return jsonify({"status": "empty"}), 200

        logger.info(f"Webhook update: {json.dumps(data, ensure_ascii=False)[:200]}...")

        # Обробляємо асинхронно
        EXECUTOR.submit(process_update, data)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

def process_update(data):
    """Асинхронна обробка оновлення"""
    try:
        # Обробка текстових повідомлень
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user_info = msg.get("from", {})
            text = msg.get("text", "").strip()
            
            # Створюємо/оновлюємо користувача
            get_or_create_user(
                chat_id,
                user_info.get("username"),
                user_info.get("first_name"),
                user_info.get("last_name")
            )
            
            # Обробляємо текст
            if text:
                process_text_message(chat_id, text, user_info)
        
        # Обробка callback queries
        elif "callback_query" in data:
            cq = data["callback_query"]
            process_callback_query(cq)
            
    except Exception as e:
        logger.exception(f"Error processing update: {e}")

def process_callback_query(cq):
    """Обробляє callback queries"""
    try:
        callback_id = cq.get("id")
        data = cq.get("data", "")
        message = cq.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_info = cq.get("from", {})
        
        # Створюємо/оновлюємо користувача
        get_or_create_user(
            chat_id,
            user_info.get("username"),
            user_info.get("first_name"),
            user_info.get("last_name")
        )
        
        logger.info(f"Callback query: {data} from {chat_id}")
        
        # Обробляємо різні типи callback-ів
        if data == "show_menu":
            show_menu(chat_id)
            tg_answer_callback(callback_id)
            
        elif data == "show_cart":
            show_cart(chat_id)
            tg_answer_callback(callback_id)
            
        elif data.startswith("category_"):
            category = data.replace("category_", "")
            show_category_items(chat_id, category)
            tg_answer_callback(callback_id)
            
        elif data.startswith("add_item_"):
            item_id = data.replace("add_item_", "")
            add_item_to_cart(chat_id, item_id)
            tg_answer_callback(callback_id, "Додано до кошика! 🛒")
            
        elif data == "budget_search":
            show_price_ranges(chat_id)
            tg_answer_callback(callback_id)
            
        elif data.startswith("budget_range_"):
            handle_budget_range(chat_id, data, callback_id)
            
        elif data == "custom_budget":
            tg_answer_callback(callback_id)
            tg_send_message(chat_id, "Введіть ваш бюджет (в гривнях):")
            set_state(chat_id, "awaiting_budget")
            
        elif data == "checkout":
            start_checkout_process(chat_id)
            tg_answer_callback(callback_id)
            
        elif data == "contact_operator":
            tg_send_message(chat_id, "Напишіть повідомлення для оператора:")
            set_state(chat_id, "awaiting_operator_message")
            tg_answer_callback(callback_id)
            
        elif data == "leave_feedback":
            tg_send_message(chat_id, "Напишіть ваш відгук:")
            set_state(chat_id, "awaiting_feedback")
            tg_answer_callback(callback_id)
            
        # Обробка кошика
        elif data.startswith("qty_"):
            handle_cart_callbacks(chat_id, data, callback_id)
            
        elif data.startswith("remove_item_"):
            idx = int(data.replace("remove_item_", ""))
            remove_item_from_cart(chat_id, idx, callback_id)
            
        elif data == "clear_cart":
            clear_cart(chat_id, callback_id)
            
        # Обробка замовлення
        elif data.startswith("delivery_type_"):
            delivery_type = data.replace("delivery_type_", "")
            handle_delivery_type(chat_id, delivery_type, callback_id)
            
        elif data.startswith("payment_"):
            payment_method = data.replace("payment_", "")
            handle_payment_method(chat_id, payment_method, callback_id)
            
        elif data.startswith("delivery_time_"):
            delivery_time = data.replace("delivery_time_", "")
            handle_delivery_time(chat_id, delivery_time, callback_id)
            
        elif data == "confirm_order":
            confirm_order(chat_id, callback_id)
            
        elif data == "cancel_order":
            cancel_order(chat_id, callback_id)
            
        else:
            logger.warning(f"Unhandled callback: {data}")
            tg_answer_callback(callback_id, "Невідома команда")
            
    except Exception as e:
        logger.exception(f"Error processing callback query: {e}")
        tg_answer_callback(cq.get("id", ""), "Помилка обробки команди")

def handle_cart_callbacks(chat_id, data, callback_id):
    """Обробляє callback-и для кошика"""
    try:
        if data.startswith("qty_plus_"):
            idx = int(data.replace("qty_plus_", ""))
            handle_cart_quantity_change(chat_id, "plus", idx, callback_id)
        elif data.startswith("qty_minus_"):
            idx = int(data.replace("qty_minus_", ""))
            handle_cart_quantity_change(chat_id, "minus", idx, callback_id)
        elif data.startswith("qty_info_"):
            # Просто відповідаємо на callback
            tg_answer_callback(callback_id)
            
    except Exception as e:
        logger.error(f"Error handling cart callback: {e}")
        tg_answer_callback(callback_id, "Помилка")

# Health check
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "components": {
            "database": "ok",
            "google_sheets": "ok" if init_gspread_client() else "error",
            "telegram": "ok" if TELEGRAM_TOKEN else "error"
        }
    })

# Root endpoint
@app.route("/", methods=["GET"])
def root():
    """Root endpoint з інформацією про API"""
    return jsonify({
        "name": "FerrikFootBot API",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "AI-powered recommendations",
            "Budget-based search", 
            "Multi-category menu",
            "Smart cart management",
            "Complete order flow"
        ],
        "endpoints": ["/webhook", "/health", "/set_webhook"]
    })

# Встановлення webhook
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    """Встановлення webhook URL"""
    if not TELEGRAM_TOKEN:
        return jsonify({"ok": False, "error": "TELEGRAM_TOKEN not set"}), 400
    
    webhook_url = request.args.get('url')
    if not webhook_url:
        # Автоматично визначаємо URL
        base_url = os.environ.get("RENDER_EXTERNAL_URL") or f"https://{request.host}"
        webhook_url = f"{base_url}/webhook"
    
    try:
        import requests
        response = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            params={
                "url": webhook_url,
                "secret_token": WEBHOOK_SECRET
            },
            timeout=10
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Ініціалізація додатку
with app.app_context():
    logger.info("🚀 FerrikFootBot starting...")
    
    try:
        # Ініціалізація бази даних
        if init_db():
            logger.info("✅ Database initialized")
        else:
            logger.error("❌ Database initialization failed")
        
        # Підключення до Google Sheets
        if init_gspread_client():
            logger.info("✅ Google Sheets connected")
            
            # Завантажуємо меню для кешування
            menu_items = get_menu_from_sheet(force=True)
            logger.info(f"✅ Menu cached: {len(menu_items)} items")
        else:
            logger.error("❌ Google Sheets connection failed")
        
        logger.info("🎉 FerrikFootBot ready!")
        
    except Exception as e:
        logger.exception(f"❌ Startup error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting server on port {port}, debug={debug_mode}")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)