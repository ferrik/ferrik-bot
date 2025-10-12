"""
Handler for user profile operations
Shows profile, history, preferences, favorites
"""
import logging
from typing import Optional
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from storage.user_repository import UserRepository
from models.user_profile import UserProfile
from services.personalization_service import PersonalizationService
from utils.personalization_helpers import (
    format_profile_message,
    format_order_history_message,
    format_recommendations_message,
    create_profile_keyboard,
    format_discount_offer
)

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("profile"))
async def show_profile(message: types.Message, state: FSMContext):
    """Show user profile command"""
    user_id = message.from_user.id
    
    # Get or create profile
    profile = UserRepository.get_profile(user_id)
    if not profile:
        profile = UserProfile(
            user_id=user_id,
            name=message.from_user.first_name or "User"
        )
        UserRepository.save_profile(profile)
    
    # Update last seen
    UserRepository.update_last_seen(user_id)
    
    # Get order history
    order_history = UserRepository.get_user_order_history(user_id, limit=5)
    
    # Format message
    profile_text = format_profile_message(profile, order_history)
    
    # Create keyboard
    keyboard = create_profile_keyboard()
    
    await message.answer(profile_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "view_history")
async def view_order_history(query: types.CallbackQuery, state: FSMContext):
    """View order history callback"""
    user_id = query.from_user.id
    
    order_history = UserRepository.get_user_order_history(user_id, limit=10)
    history_text = format_order_history_message(order_history)
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '🔙 Назад в профіль', 'callback_data': 'back_to_profile'}]
        ]
    }
    
    await query.message.edit_text(history_text, reply_markup=keyboard, parse_mode="HTML")
    await query.answer()


@router.callback_query(F.data == "view_favorites")
async def view_favorites(query: types.CallbackQuery, state: FSMContext):
    """View favorite dishes callback"""
    user_id = query.from_user.id
    
    profile = UserRepository.get_profile(user_id)
    if not profile or not profile.favorite_dishes:
        await query.answer("Поки немає улюблених страв")
        return
    
    text = "⭐ <b>Твої улюблені страви:</b>\n\n"
    
    keyboard = {'inline_keyboard': []}
    
    for i, dish in enumerate(profile.favorite_dishes[:10], 1):
        text += f"{i}. {dish}\n"
        keyboard['inline_keyboard'].append([
            {'text': f"🍕 {dish}", 'callback_data': f"order_{i}"}
        ])
    
    keyboard['inline_keyboard'].append([
        {'text': '🔙 Назад в профіль', 'callback_data': 'back_to_profile'}
    ])
    
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await query.answer()


@router.callback_query(F.data == "view_bonuses")
async def view_bonuses(query: types.CallbackQuery):
    """View bonus points callback"""
    user_id = query.from_user.id
    
    profile = UserRepository.get_profile(user_id)
    if not profile:
        await query.answer("Профіль не знайдено")
        return
    
    text = f"🎁 <b>ТВОЇ БОНУС-БАЛИ</b>\n\n"
    text += f"<b>Всього балів:</b> <code>{profile.points}</code>\n\n"
    text += f"<b>Як заробити бали:</b>\n"
    text += f"• Кожне замовлення: +1 бал за 100 грн\n"
    text += f"• Рівень вверх: +50 балів\n"
    text += f"• Першого замовлення: +10 балів\n\n"
    text += f"<b>Як використати:</b>\n"
    text += f"• 100 балів = 50 грн знижки\n"
    text += f"• 50 балів = 25 грн знижки\n"
    text += f"• 10 балів = 5 грн знижки\n"
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '🔙 Назад в профіль', 'callback_data': 'back_to_profile'}]
        ]
    }
    
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await query.answer()


@router.callback_query(F.data == "settings")
async def settings_menu(query: types.CallbackQuery):
    """Settings menu callback"""
    user_id = query.from_user.id
    
    preferences = UserRepository.get_preferences(user_id)
    
    text = "⚙️ <b>НАЛАШТУВАННЯ</b>\n\n"
    text += f"<b>Доставка:</b> {preferences.preferred_delivery_method}\n"
    text += f"<b>Сповіщення:</b> {'Увімкнено ✅' if preferences.push_notifications else 'Вимкнено ❌'}\n"
    text += f"<b>Бюджет:</b> до {preferences.max_budget} грн\n\n"
    
    if preferences.dietary_restrictions:
        text += f"<b>Дієтичні обмеження:</b>\n"
        for restriction in preferences.dietary_restrictions:
            text += f"• {restriction}\n"
        text += "\n"
    
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '📢 Сповіщення', 'callback_data': 'toggle_notifications'},
                {'text': '🚚 Доставка', 'callback_data': 'edit_delivery'}
            ],
            [
                {'text': '🌱 Дієта', 'callback_data': 'edit_diet'},
                {'text': '💰 Бюджет', 'callback_data': 'edit_budget'}
            ],
            [{'text': '🔙 Назад в профіль', 'callback_data': 'back_to_profile'}]
        ]
    }
    
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await query.answer()


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(query: types.CallbackQuery):
    """Toggle push notifications"""
    user_id = query.from_user.id
    
    preferences = UserRepository.get_preferences(user_id)
    preferences.push_notifications = not preferences.push_notifications
    UserRepository.save_preferences(preferences)
    
    status = "Увімкнено ✅" if preferences.push_notifications else "Вимкнено ❌"
    await query.answer(f"Сповіщення: {status}")
    
    # Refresh settings
    await settings_menu(query)


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(query: types.CallbackQuery):
    """Go back to profile view"""
    user_id = query.from_user.id
    
    profile = UserRepository.get_profile(user_id)
    order_history = UserRepository.get_user_order_history(user_id, limit=5)
    
    profile_text = format_profile_message(profile, order_history)
    keyboard = create_profile_keyboard()
    
    await query.message.edit_text(profile_text, reply_markup=keyboard, parse_mode="HTML")
    await query.answer()


@router.callback_query(F.data == "quick_reorder")
async def quick_reorder_action(query: types.CallbackQuery):
    """Quick reorder favorite dish"""