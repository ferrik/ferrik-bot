import logging
from flask import Flask, request, abort
from services import telegram, sheets, database
import bot_config as config
from utils.field_mapping import get_field_value, MenuField

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(config.LOGGER_NAME)

app = Flask(__name__)
db = database.Database()

@app.route('/')
def index():
    """Стартова сторінка для перевірки роботи сервісу."""
    return "Ferrik Bot is running!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Основна функція для обробки вебхуків від Telegram."""
    # 1. Перевірка секретного токена для безпеки
    secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if secret_token != config.WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret token received.")
        abort(403)  # Forbidden

    # 2. Обробка оновлення
    try:
        update = request.get_json()
        if not update or 'message' not in update:
            logger.warning("Received an empty or invalid update.")
            return 'ok', 200

        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        user_id = message['from']['id']

        logger.info(f"Received update: {update.get('update_id')}")
        logger.info(f"Message from {user_id}: {text}")

        # Зберігаємо дані користувача
        db.add_user(user_id, message['from'].get('username'), message['from'].get('first_name'))

        # Маршрутизація команд
        if text == '/start':
            handle_start(chat_id, message)
        elif text == '🍕 Меню':
            handle_menu(chat_id)
        elif text == '📞 Контакти':
            handle_contacts(chat_id)
        elif text == '💡 Допомога':
            handle_help(chat_id)
        else:
            handle_unknown(chat_id)

    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        if config.OPERATOR_CHAT_ID:
            telegram.send_message(config.OPERATOR_CHAT_ID, f"🔴 **Bot Error**\n\n```{e}```", parse_mode='Markdown')

    return 'ok', 200

def handle_start(chat_id, message):
    """Обробник команди /start."""
    user_id = message['from']['id']
    user_name = message['from'].get('first_name', '')
    logger.info(f"User {user_name} ({user_id}) started the bot.")

    # ВИПРАВЛЕНО: Використовуємо коректний HTML
    welcome_message = (
        f"👋 <b>Привіт, {user_name}!</b>\n\n"
        "Я — бот для ресторану <b>Ferrik</b>.\n\n"
        "Використовуйте кнопки нижче, щоб:\n"
        "🍕 Переглянути меню\n"
        "📞 Дізнатись контакти\n"
        "💡 Отримати допомогу\n\n"
        f"Ваш ID для звернень: <code>{user_id}</code>"
    )

    telegram.send_message(
        chat_id,
        welcome_message,
        reply_markup=telegram.create_main_keyboard(),
        parse_mode='HTML'
    )
    if config.OPERATOR_CHAT_ID:
        notification = f"✅ Новий користувач почав діалог:\nІм'я: {user_name}\nID: {user_id}"
        telegram.send_message(config.OPERATOR_CHAT_ID, notification)

def handle_menu(chat_id):
    """Обробник команди 'Меню'."""
    try:
        menu_items = sheets.get_menu()
        if not menu_items:
            telegram.send_message(chat_id, "На жаль, не вдалося завантажити меню. Спробуйте пізніше.")
            return

        logger.info(f"Loaded {len(menu_items)} menu items from Google Sheets")

        # Групуємо страви за категоріями
        menu_by_category = {}
        for item in menu_items:
            category = get_field_value(item, MenuField.CATEGORY, default="Інше")
            if category not in menu_by_category:
                menu_by_category[category] = []
            menu_by_category[category].append(item)

        # Формуємо повідомлення
        full_menu_message = "<b>🍕 НАШЕ МЕНЮ 🍕</b>\n\n"
        for category, items in menu_by_category.items():
            full_menu_message += f"<b>--- {category.upper()} ---</b>\n"
            for item in items:
                name = get_field_value(item, MenuField.NAME, "Назва не вказана")
                price = get_field_value(item, MenuField.PRICE, "Ціна не вказана")
                description = get_field_value(item, MenuField.DESCRIPTION)
                
                full_menu_message += f"<b>{name}</b> - {price} грн\n"
                if description:
                    full_menu_message += f"<i>{description}</i>\n"
            full_menu_message += "\n"

        telegram.send_message(chat_id, full_menu_message, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Failed to get or format menu: {e}", exc_info=True)
        telegram.send_message(chat_id, "Виникла помилка при завантаженні меню. Ми вже працюємо над цим.")
        if config.OPERATOR_CHAT_ID:
            telegram.send_message(config.OPERATOR_CHAT_ID, f"🔴 **Menu Error**\n\nНе вдалося завантажити меню.\nПричина: ```{e}```", parse_mode='Markdown')

def handle_contacts(chat_id):
    """Обробник команди 'Контакти'."""
    contacts_message = (
        "📞 <b>Наші контакти</b> 📞\n\n"
        "<b>Адреса:</b> м. Тернопіль, вул. Замкова, 5\n"
        "<b>Телефон:</b> <a href=\"tel:+380991234567\">+38 (099) 123-45-67</a>\n"
        "<b>Години роботи:</b> 10:00 - 22:00 (Щодня)"
    )
    telegram.send_message(chat_id, contacts_message, parse_mode='HTML')

def handle_help(chat_id):
    """Обробник команди 'Допомога'."""
    help_message = (
        "💡 <b>Допомога</b> 💡\n\n"
        "Я можу показати вам меню та надати контактну інформацію.\n"
        "Просто використовуйте кнопки внизу екрану.\n\n"
        "Якщо у вас виникли проблеми, зверніться до оператора за телефоном, вказаним у контактах."
    )
    telegram.send_message(chat_id, help_message, parse_mode='HTML')

def handle_unknown(chat_id):
    """Обробник для невідомих команд."""
    unknown_message = "Не розумію вас. Будь ласка, скористайтесь кнопками меню."
    telegram.send_message(chat_id, unknown_message)

if __name__ == '__main__':
    # Встановлюємо вебхук при запуску (якщо потрібно)
    # Зазвичай це робиться один раз окремим скриптом або через API
    # telegram.set_webhook()
    app.run(host='0.0.0.0', port=config.PORT)

