"""
🤖 Ferrik Bot 2.0 - Головний файл
Персональний смаковий супутник з AI
"""
import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Імпорти наших модулів
from app.config.settings import *
from app.services.session import SessionManager
from app.utils.validators import *
from services.telegram import TelegramAPI
from services.sheets import SheetsAPI
from services.database import Database

# Нові модулі
from welcome_messages import WelcomeMessages
from onboarding_quest import OnboardingQuest, QuestStage
from menu_formatter import MenuFormatter
from mood_recommender import MoodRecommender
from gamification import GamificationManager, Badge, BadgeType, UserLevel
from referral import ReferralSystem
from friendly_errors import FriendlyMessages, SupportSystem, ErrorType

# ============================================================================
# Конфігурація
# ============================================================================
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Ініціалізація сервісів
telegram = TelegramAPI(TELEGRAM_BOT_TOKEN)
sheets = SheetsAPI()
db = Database(DATABASE_PATH)
session_manager = SessionManager(db)

# ============================================================================
# Стани бота
# ============================================================================
class BotState:
    """Розширені стани бота"""
    IDLE = "idle"
    BROWSING_MENU = "browsing_menu"
    VIEWING_ITEM = "viewing_item"
    AWAITING_PHONE = "awaiting_phone"
    AWAITING_ADDRESS = "awaiting_address"
    AWAITING_PAYMENT = "awaiting_payment"
    
    # Нові стани
    ONBOARDING_QUEST = "onboarding_quest"
    MOOD_SELECTION = "mood_selection"
    SEARCHING_MENU = "searching_menu"
    LEAVING_REVIEW = "leaving_review"
    SUPPORT_CHAT = "support_chat"


# ============================================================================
# Обробники команд
# ============================================================================

def handle_start_command(user_id: int, user_name: str = None, referral_code: str = None):
    """
    Обробка команди /start з онбордингом та рефералами
    """
    # Перевірка, чи це новий користувач
    user_data = db.get_user(user_id)
    is_new_user = user_data is None
    
    if is_new_user:
        # Створюємо користувача
        db.create_user(user_id, user_name or "Користувач")
        
        # Обробка реферального коду
        if referral_code and ReferralSystem.validate_referral_code(referral_code):
            referrer_id = db.get_user_by_referral_code(referral_code)
            if referrer_id:
                # Застосовуємо бонуси
                bonus_data = ReferralSystem.apply_referral_bonus(referrer_id, user_id)
                
                # Зберігаємо реферала
                db.save_referral(referrer_id, user_id, referral_code)
                
                # Нараховуємо бонуси обом
                db.add_bonus_points(referrer_id, bonus_data['referrer']['bonus_points'])
                db.add_bonus_points(user_id, bonus_data['referee']['bonus_points'])
                
                # Відправляємо повідомлення
                telegram.send_message(
                    referrer_id,
                    ReferralSystem.format_bonus_notification(bonus_data['referrer'], 'referrer')
                )
                telegram.send_message(
                    user_id,
                    ReferralSystem.format_bonus_notification(bonus_data['referee'], 'referee')
                )
        
        # Видаємо бейдж "Дослідник"
        GamificationManager.award_badge(user_id, BadgeType.EXPLORER)
        
    # Привітання
    greeting = WelcomeMessages.get_greeting_text(user_name, is_new_user)
    keyboard = WelcomeMessages.get_onboarding_keyboard()
    
    telegram.send_message(user_id, greeting, reply_markup=keyboard)
    
    # Пропонуємо квест новим користувачам
    if is_new_user:
        session_manager.set_state(user_id, BotState.ONBOARDING_QUEST)
        quest_intro = OnboardingQuest.get_quest_intro()
        quest_keyboard = OnboardingQuest.get_quest_keyboard(QuestStage.NOT_STARTED)
        telegram.send_message(user_id, quest_intro, reply_markup=quest_keyboard)


def handle_menu_command(user_id: int, category: str = None):
    """
    Показує меню з красивим форматуванням
    """
    try:
        # Отримуємо меню з кешу або Google Sheets
        menu_items = sheets.get_menu()
        
        if not menu_items:
            error_msg = FriendlyMessages.get_error_message(ErrorType.NOT_FOUND)
            telegram.send_message(user_id, error_msg)
            return
        
        # Фільтруємо за категорією, якщо задано
        if category:
            menu_items = [item for item in menu_items if item.get('Категорія', '').lower() == category.lower()]
        
        # Групуємо за категоріями
        categories = {}
        for item in menu_items:
            cat = item.get('Категорія', 'Інше')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        # Відправляємо меню по категоріях
        session_manager.set_state(user_id, BotState.BROWSING_MENU)
        
        intro_msg = "📋 **Наше меню**\n\nОбери категорію або скористайся пошуком! 🔍"
        
        # Клавіатура з категоріями
        keyboard = {
            'inline_keyboard': []
        }
        
        # Додаємо кнопки категорій (по 2 в ряд)
        cat_list = list(categories.keys())
        for i in range(0, len(cat_list), 2):
            row = []
            for j in range(i, min(i + 2, len(cat_list))):
                cat = cat_list[j]
                emoji = MenuFormatter.get_category_emoji(cat)
                row.append({
                    'text': f'{emoji} {cat}',
                    'callback_data': f'cat_{cat}'
                })
            keyboard['inline_keyboard'].append(row)
        
        # Додаткові опції
        keyboard['inline_keyboard'].append([
            {'text': '🔍 Пошук', 'callback_data': 'search_menu'},
            {'text': '🎯 Підібрати страву', 'callback_data': 'recommend'}
        ])
        keyboard['inline_keyboard'].append([
            {'text': '🛒 Кошик', 'callback_data': 'view_cart'},
            {'text': '🎁 Акції', 'callback_data': 'promo'}
        ])
        
        telegram.send_message(user_id, intro_msg, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in handle_menu: {e}")
        error_msg = FriendlyMessages.get_error_message(ErrorType.SERVER)
        telegram.send_message(user_id, error_msg)


def handle_recommend_command(user_id: int):
    """
    AI-рекомендації на основі настрою
    """
    # Пропонуємо вибрати настрій
    mood_text = WelcomeMessages.get_mood_selection_text()
    mood_keyboard = WelcomeMessages.get_mood_keyboard()
    
    session_manager.set_state(user_id, BotState.MOOD_SELECTION)
    telegram.send_message(user_id, mood_text, reply_markup=mood_keyboard)


def handle_mood_selection(user_id: int, mood: str):
    """
    Обробка вибраного настрою та генерація рекомендацій
    """
    # Показуємо повідомлення очікування
    waiting_msg = FriendlyMessages.get_waiting_message()
    telegram.send_message(user_id, waiting_msg)
    
    try:
        # Отримуємо меню
        menu_items = sheets.get_menu()
        
        # Отримуємо історію замовлень користувача
        user_history = db.get_user_order_history(user_id)
        ordered_items = [str(item['item_id']) for item in user_history]
        
        # Генеруємо рекомендації
        recommendations = MoodRecommender.recommend(
            menu_items, 
            mood, 
            limit=3,
            user_history=ordered_items
        )
        
        if recommendations:
            # Форматуємо та відправляємо
            rec_text = MoodRecommender.format_recommendations(recommendations, mood)
            rec_keyboard = MoodRecommender.create_recommendation_keyboard(recommendations)
            
            telegram.send_message(user_id, rec_text, reply_markup=rec_keyboard)
        else:
            error_msg = FriendlyMessages.get_error_message(ErrorType.NOT_FOUND)
            telegram.send_message(user_id, error_msg)
    
    except Exception as e:
        logger.error(f"Error in mood recommendation: {e}")
        error_msg = FriendlyMessages.get_error_message(ErrorType.SERVER)
        telegram.send_message(user_id, error_msg)


def handle_cart_command(user_id: int):
    """
    Показує кошик з покращеним форматуванням
    """
    cart_items = session_manager.get_cart(user_id)
    
    if not cart_items:
        empty_msg = FriendlyMessages.get_error_message(ErrorType.CART_EMPTY)
        telegram.send_message(user_id, empty_msg)
        return
    
    # Розраховуємо загальну суму
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Форматуємо кошик
    cart_text = MenuFormatter.format_cart(cart_items, total)
    
    # Клавіатура
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '✅ Оформити замовлення', 'callback_data': 'checkout'},
                {'text': '🗑️ Очистити кошик', 'callback_data': 'clear_cart'}
            ],
            [
                {'text': '➕ Додати ще', 'callback_data': 'menu'},
                {'text': '🏠 Головна', 'callback_data': 'main_menu'}
            ]
        ]
    }
    
    telegram.send_message(user_id, cart_text, reply_markup=keyboard)


def handle_checkout(user_id: int):
    """
    Оформлення замовлення
    """
    cart_items = session_manager.get_cart(user_id)
    
    if not cart_items:
        empty_msg = FriendlyMessages.get_error_message(ErrorType.CART_EMPTY)
        telegram.send_message(user_id, empty_msg)
        return
    
    # Перевіряємо, чи є збережені дані
    user_data = db.get_user(user_id)
    phone = user_data.get('phone')
    address = user_data.get('address')
    
    if not phone:
        # Запитуємо телефон
        session_manager.set_state(user_id, BotState.AWAITING_PHONE)
        msg = (
            "📱 **Оформлення замовлення**\n\n"
            "Будь ласка, введи свій номер телефону:\n"
            "Формат: +380501234567"
        )
        telegram.send_message(user_id, msg)
    elif not address:
        # Запитуємо адресу
        session_manager.set_state(user_id, BotState.AWAITING_ADDRESS)
        msg = (
            "📍 **Адреса доставки**\n\n"
            "Введи адресу у форматі:\n"
            "_вул. Шевченка, 15, кв. 10_"
        )
        telegram.send_message(user_id, msg)
    else:
        # Підтверджуємо замовлення
        confirm_order(user_id, phone, address)


def confirm_order(user_id: int, phone: str, address: str):
    """
    Фінальне підтвердження та збереження замовлення
    """
    cart_items = session_manager.get_cart(user_id)
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Генеруємо номер замовлення
    order_number = db.generate_order_number()
    
    # Зберігаємо в БД
    order_id = db.save_order(
        user_id=user_id,
        order_number=order_number,
        phone=phone,
        address=address,
        items=cart_items,
        total=total
    )
    
    # Зберігаємо в Google Sheets
    sheets.save_order({
        'order_id': order_id,
        'order_number': order_number,
        'user_id': user_id,
        'phone': phone,
        'address': address,
        'items': cart_items,
        'total': total,
        'status': 'new'
    })
    
    # Очищаємо кошик
    session_manager.clear_cart(user_id)
    
    # Нараховуємо бали (1 бал за 10 грн)
    points_earned = int(total / 10)
    db.add_bonus_points(user_id, points_earned)
    
    # Перевіряємо досягнення
    user_stats = db.get_user_stats(user_id)
    new_badges = GamificationManager.check_badge_eligibility(user_stats)
    
    for badge in new_badges:
        # Перевіряємо, чи користувач вже має цей бейдж
        if not db.user_has_badge(user_id, badge):
            badge_data = GamificationManager.award_badge(user_id, badge)
            db.save_badge(user_id, badge.value, badge_data['xp_bonus'])
    
    # Відправляємо підтвердження
    order_data = {
        'order_number': order_number,
        'items': cart_items,
        'total': total,
        'phone': phone,
        'address': address,
        'delivery_time': '45-60 хв'
    }
    
    confirmation_text = MenuFormatter.format_order_confirmation(order_data)
    success_text = FriendlyMessages.get_success_message('order_placed')
    
    telegram.send_message(user_id, success_text)
    telegram.send_message(user_id, confirmation_text)
    
    # Повідомлення про бали
    if points_earned > 0:
        points_msg = f"⭐ Ти заробив {points_earned} бонусних балів!"
        telegram.send_message(user_id, points_msg)
    
    # Повідомлення про нові бейджі
    if new_badges:
        for badge in new_badges:
            badge_info = Badge.get_badge_info(badge)
            badge_msg = (
                f"🏆 **Нове досягнення!**\n\n"
                f"{badge_info['emoji']} {badge_info['name']}\n"
                f"_{badge_info['description']}_\n\n"
                f"+{badge_info['points']} XP"
            )
            telegram.send_message(user_id, badge_msg)
    
    # Пропонуємо залишити відгук через 30 хв (планувальник)
    # schedule_review_request(user_id, order_id, delay_minutes=30)
    
    session_manager.set_state(user_id, BotState.IDLE)


def handle_profile_command(user_id: int):
    """
    Показує профіль користувача з досягненнями
    """
    user_data = db.get_user_with_stats(user_id)
    
    if not user_data:
        telegram.send_message(user_id, "Користувача не знайдено")
        return
    
    profile_text = GamificationManager.format_profile(user_data)
    
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '🏆 Всі досягнення', 'callback_data': 'view_badges'},
                {'text': '📊 Статистика', 'callback_data': 'view_stats'}
            ],
            [
                {'text': '🎯 Челенджі', 'callback_data': 'view_challenges'},
                {'text': '🎁 Реферали', 'callback_data': 'referral'}
            ],
            [
                {'text': '⚙️ Налаштування', 'callback_data': 'settings'}
            ]
        ]
    }
    
    telegram.send_message(user_id, profile_text, reply_markup=keyboard)


def handle_referral_command(user_id: int):
    """
    Показує реферальну програму
    """
    user_data = db.get_user(user_id)
    referrals_count = db.get_referrals_count(user_id)
    
    ref_info = ReferralSystem.get_referral_info(user_id, referrals_count)
    ref_message = ReferralSystem.format_referral_message(
        ref_info, 
        user_data.get('name')
    )
    ref_keyboard = ReferralSystem.create_referral_keyboard(ref_info['code'])
    
    telegram.send_message(user_id, ref_message, reply_markup=ref_keyboard)


def handle_support_command(user_id: int):
    """
    Показує FAQ та підтримку
    """
    faq_message = SupportSystem.get_faq_message()
    faq_keyboard = SupportSystem.get_faq_keyboard()
    
    telegram.send_message(user_id, faq_message, reply_markup=faq_keyboard)


# ============================================================================
# Webhook обробник
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Головний webhook для обробки повідомлень"""
    try:
        update = request.get_json()
        logger.info(f"Received update: {update}")
        
        # Обробка callback queries (кнопки)
        if 'callback_query' in update:
            handle_callback_query(update['callback_query'])
        
        # Обробка текстових повідомлень
        elif 'message' in update:
            handle_message(update['message'])
        
        return jsonify({'ok': True})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


def handle_message(message: dict):
    """Обробка текстових повідомлень"""
    user_id = message['from']['id']
    user_name = message['from'].get('first_name', 'Користувач')
    text = message.get('text', '')
    
    # Команди
    if text.startswith('/'):
        command = text.split()[0].lower()
        
        if command == '/start':
            # Перевірка на реферальний код
            ref_code = text.split()[1] if len(text.split()) > 1 else None
            handle_start_command(user_id, user_name, ref_code)
        
        elif command == '/menu':
            handle_menu_command(user_id)
        
        elif command == '/cart':
            handle_cart_command(user_id)
        
        elif command == '/profile':
            handle_profile_command(user_id)
        
        elif command == '/referral':
            handle_referral_command(user_id)
        
        elif command == '/support':
            handle_support_command(user_id)
        
        elif command == '/help':
            help_text = (
                "🤖 **Доступні команди:**\n\n"
                "/menu - Переглянути меню\n"
                "/cart - Мій кошик\n"
                "/profile - Мій профіль\n"
                "/referral - Реферальна програма\n"
                "/support - Підтримка\n"
                "/help - Ця довідка"
            )
            telegram.send_message(user_id, help_text)
        
        return
    
    # Обробка в залежності від стану
    state = session_manager.get_state(user_id)
    
    if state == BotState.AWAITING_PHONE:
        # Валідація телефону
        if validate_phone(text):
            phone = normalize_phone(text)
            db.update_user_phone(user_id, phone)
            
            # Переходимо до адреси
            session_manager.set_state(user_id, BotState.AWAITING_ADDRESS)
            msg = (
                "✅ Телефон збережено!\n\n"
                "📍 Тепер введи адресу доставки:\n"
                "_вул. Шевченка, 15, кв. 10_"
            )
            telegram.send_message(user_id, msg)
        else:
            error_msg = (
                "❌ Невірний формат телефону\n\n"
                "Спробуй ще раз у форматі:\n"
                "+380501234567"
            )
            telegram.send_message(user_id, error_msg)
    
    elif state == BotState.AWAITING_ADDRESS:
        # Валідація адреси
        if validate_address(text):
            address = sanitize_input(text)
            db.update_user_address(user_id, address)
            
            # Підтверджуємо замовлення
            user_data = db.get_user(user_id)
            confirm_order(user_id, user_data['phone'], address)
        else:
            error_msg = (
                "❌ Адреса здається неповною\n\n"
                "Введи, будь ласка, повну адресу:\n"
                "_вул. Назва, номер будинку, квартира_"
            )
            telegram.send_message(user_id, error_msg)
    
    elif state == BotState.SEARCHING_MENU:
        # Пошук по меню
        handle_search(user_id, text)
    
    else:
        # Загальний пошук або підказка
        if len(text) > 3:
            handle_search(user_id, text)
        else:
            telegram.send_message(
                user_id, 
                "💡 Використовуй команди для навігації:\n/menu /cart /profile"
            )


def handle_callback_query(callback: dict):
    """Обробка натискань на кнопки"""
    user_id = callback['from']['id']
    data = callback['data']
    
    # Відповідаємо на callback (прибираємо годинник)
    telegram.answer_callback_query(callback['id'])
    
    # Обробка різних callback'ів
    if data == 'menu':
        handle_menu_command(user_id)
    
    elif data == 'view_cart':
        handle_cart_command(user_id)
    
    elif data == 'recommend':
        handle_recommend_command(user_id)
    
    elif data.startswith('mood_'):
        mood = data.split('_')[1]
        handle_mood_selection(user_id, mood)
    
    elif data.startswith('cat_'):
        category = data.split('_', 1)[1]
        show_category_items(user_id, category)
    
    elif data.startswith('item_'):
        item_id = data.split('_')[1]
        show_item_details(user_id, item_id)
    
    elif data.startswith('add_'):
        item_id = data.split('_')[1]
        add_to_cart(user_id, item_id)
    
    elif data == 'checkout':
        handle_checkout(user_id)
    
    elif data == 'referral':
        handle_referral_command(user_id)
    
    elif data.startswith('faq_'):
        faq_key = data.split('_')[1]
        show_faq_answer(user_id, faq_key)
    
    # ... інші обробники


# ============================================================================
# Запуск
# ============================================================================

if __name__ == '__main__':
    logger.info("🚀 Ferrik Bot 2.0 starting...")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
