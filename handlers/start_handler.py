"""
Updated start handler with personalization
Integrate this with your existing start_handler.py
"""
import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from storage.user_repository import UserRepository
from models.user_profile import UserProfile
from services.personalization_service import PersonalizationService
from utils.personalization_helpers import format_user_greeting_message

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Start command with personalized greeting"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    
    try:
        # Initialize database (first run)
        UserRepository.init_db()
        
        # Get existing profile or create new
        profile = UserRepository.get_profile(user_id)
        
        if not profile:
            # New user
            logger.info(f"👤 New user registered: {first_name} (ID: {user_id})")
            profile = UserProfile(
                user_id=user_id,
                name=first_name
            )
            UserRepository.save_profile(profile)
        else:
            # Returning user - update last seen
            logger.info(f"📍 User {first_name} returned (ID: {user_id})")
            UserRepository.update_last_seen(user_id)
        
        # ✨ PERSONALIZED GREETING
        greeting = format_user_greeting_message(profile)
        
        # Main menu keyboard
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📋 Меню', 'callback_data': 'show_menu'},
                    {'text': '👤 Профіль', 'callback_data': 'show_profile'}
                ],
                [
                    {'text': '⭐ Рекомендації', 'callback_data': 'show_recommendations'},
                    {'text': '🛒 Кошик', 'callback_data': 'show_cart'}
                ],
                [
                    {'text': 'ℹ️ Допомога', 'callback_data': 'show_help'}
                ]
            ]
        }
        
        await message.answer(greeting, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer(
            "❌ Помилка при запуску бота\n\n"
            "Спробуйте пізніше або напишіть /help для допомоги",
            parse_mode="HTML"
        )


@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Show user profile"""
    user_id = message.from_user.id
    
    try:
        profile = UserRepository.get_profile(user_id)
        
        if not profile:
            await message.answer("❌ Профіль не знайдено. Напишіть /start")
            return
        
        # Get order history
        order_history = UserRepository.get_user_order_history(user_id, limit=5)
        
        # Format profile
        from utils.personalization_helpers import (
            format_profile_message,
            create_profile_keyboard
        )
        
        profile_text = format_profile_message(profile, order_history)
        keyboard = create_profile_keyboard()
        
        await message.answer(profile_text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing profile: {e}")
        await message.answer("❌ Помилка при завантаженні профілю")


@router.message(Command("recommendations"))
async def cmd_recommendations(message: types.Message):
    """Show personalized recommendations"""
    user_id = message.from_user.id
    
    try:
        profile = UserRepository.get_profile(user_id)
        
        if not profile:
            await message.answer("❌ Профіль не знайдено. Напишіть /start")
            return
        
        # Get menu (integrate with your menu_service)
        # This is a placeholder - adjust based on your menu_service.py
        from services.menu_service import MenuService
        all_items = MenuService.get_all_menu_items()
        
        # Get recommendations
        from services.personalization_service import PersonalizationService
        from utils.personalization_helpers import format_recommendations_message, create_recommendations_keyboard
        
        recommendations = PersonalizationService.get_recommendations(
            profile=profile,
            all_menu_items=all_items,
            limit=3
        )
        
        text = format_recommendations_message(recommendations)
        keyboard = create_recommendations_keyboard(recommendations)
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing recommendations: {e}")
        await message.answer("❌ Помилка при загруженні рекомендацій")


@router.callback_query(lambda c: c.data == "show_profile")
async def callback_show_profile(query: types.CallbackQuery):
    """Callback for show profile button"""
    await cmd_profile(query.message)
    await query.answer()


@router.callback_query(lambda c: c.data == "show_recommendations")
async def callback_show_recommendations(query: types.CallbackQuery):
    """Callback for recommendations button"""
    await cmd_recommendations(query.message)
    await query.answer()


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Help command"""
    help_text = """
<b>ℹ️ ДОПОМОГА</b>

<b>Доступні команди:</b>
/start - Головне меню
/profile - Переглянути профіль
/recommendations - Персональні рекомендації
/help - Ця допомога

<b>Як це працює:</b>
1️⃣ Натисни <b>📋 Меню</b> для перегляду страв
2️⃣ Натисни <b>⭐ Рекомендації</b> для персональних порад
3️⃣ Додавай страви в <b>🛒 Кошик</b>
4️⃣ Перегляди свій <b>👤 Профіль</b> та <b>📊 Статистику</b>

<b>Рівні користувачів:</b>
🆕 <b>Новачок</b> - 0-2 замовлення
🍽️ <b>Гурман</b> - 3-10 замовлень
👨‍🍳 <b>Фуді</b> - 11+ замовлень

<b>Бонус-бали:</b>
💰 За кожне замовлення: +1 бал за 100 грн
📈 За рівень вверх: +50 балів
🎁 100 балів = 50 грн знижки

<b>Потрібна допомога?</b>
Напишіть @ferrik_support або натисніть 📞 Контакти
"""
    
    await message.answer(help_text, parse_mode="HTML")