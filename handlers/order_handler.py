"""
Updated order handler with personalization
Integrate this with your existing order_handler.py
"""
import logging
import uuid
from datetime import datetime
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from storage.user_repository import UserRepository
from services.personalization_service import PersonalizationService
from utils.personalization_helpers import (
    format_level_up_message,
    format_discount_offer
)

logger = logging.getLogger(__name__)

router = Router()


async def process_order_completion(
    user_id: int,
    order_id: str,
    restaurant_id: str,
    items: list,
    total_amount: float,
    bot
):
    """
    Process order completion and update user profile
    Call this after successful order creation
    
    Args:
        user_id: Telegram user ID
        order_id: Order ID
        restaurant_id: Restaurant ID
        items: List of ordered items (dictionaries with 'name', 'quantity', 'price')
        total_amount: Total order amount
        bot: aiogram Bot instance
    """
    try:
        # Get current profile
        profile = UserRepository.get_profile(user_id)
        if not profile:
            logger.warning(f"Profile not found for user {user_id}")
            return
        
        # Extract dish names
        dish_names = [item.get('name', 'Item') for item in items]
        
        # Store old level for comparison
        old_level = profile.level
        
        # Update profile with order
        profile.add_order(
            amount=total_amount,
            dish_names=dish_names,
            restaurant_id=restaurant_id
        )
        
        # Save updated profile
        UserRepository.save_profile(profile)
        
        # Update order history
        UserRepository.update_order_history(user_id, {
            'order_id': order_id,
            'restaurant_id': restaurant_id,
            'items': dish_names,
            'total_amount': total_amount
        })
        
        logger.info(f"✅ Order {order_id} recorded for user {user_id}")
        
        # Check if level changed
        if profile.level != old_level:
            logger.info(f"🎉 User {user_id} leveled up to {profile.level.value}")
            
            # Send level-up message
            level_up_msg = format_level_up_message(profile)
            try:
                await bot.send_message(user_id, level_up_msg, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send level-up message: {e}")
        
        # Check if eligible for discount offer
        discount_offer = format_discount_offer(profile)
        if discount_offer:
            try:
                await bot.send_message(user_id, discount_offer, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send discount offer: {e}")
        
    except Exception as e:
        logger.error(f"Error processing order completion: {e}")


@router.message(Command("history"))
async def cmd_order_history(message: types.Message):
    """Show user order history"""
    user_id = message.from_user.id
    
    try:
        order_history = UserRepository.get_user_order_history(user_id, limit=10)
        
        if not order_history:
            await message.answer("📭 Історія замовлень порожня")
            return
        
        from utils.personalization_helpers import format_order_history_message
        history_text = format_order_history_message(order_history)
        
        await message.answer(history_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing order history: {e}")
        await message.answer("❌ Помилка при завантаженні історії")


@router.message(Command("stats"))
async def cmd_user_stats(message: types.Message):
    """Show user statistics"""
    user_id = message.from_user.id
    
    try:
        profile = UserRepository.get_profile(user_id)
        
        if not profile:
            await message.answer("❌ Профіль не знайдено")
            return
        
        from services.personalization_service import UserAnalyticsService
        insights = UserAnalyticsService.get_user_insights(profile)
        
        stats_text = "<b>📊 ТВОЯ СТАТИСТИКА</b>\n\n"
        stats_text += f"📦 <b>Замовлень:</b> {insights['total_orders']}\n"
        stats_text += f"💰 <b>Витрачено:</b> {insights['total_spent']:.2f} грн\n"
        stats_text += f"💵 <b>Середній чек:</b> {insights['avg_order_value']:.2f} грн\n"
        stats_text += f"🎁 <b>Рівень:</b> {profile.get_level_name()} {profile.get_level_emoji()}\n"
        stats_text += f"🏆 <b>Бонус-балів:</b> {insights['points']}\n\n"
        
        if insights['days_since_last_order']:
            stats_text += f"📅 <b>Останнє замовлення:</b> {insights['days_since_last_order']} днів тому\n"
        
        if insights['favorite_category']:
            stats_text += f"❤️ <b>Улюблена категорія:</b> {insights['favorite_category']}\n"
        
        await message.answer(stats_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await message.answer("❌ Помилка при завантаженні статистики")


@router.message(Command("favorites"))
async def cmd_favorites(message: types.Message):
    """Show favorite dishes"""
    user_id = message.from_user.id
    
    try:
        profile = UserRepository.get_profile(user_id)
        
        if not profile or not profile.favorite_dishes:
            await message.answer("❌ У тебе поки немає улюблених страв\n\nЗроби кілька замовлень!")
            return
        
        text = "⭐ <b>ТВОЇ УЛЮБЛЕНІ СТРАВИ:</b>\n\n"
        
        keyboard = {'inline_keyboard': []}
        
        for i, dish in enumerate(profile.favorite_dishes[:10], 1):
            text += f"{i}. {dish}\n"
            # Note: Adjust callback based on your menu structure
            keyboard['inline_keyboard'].append([
                {'text': f"🍕 {dish}", 'callback_data': f"search_dish_{i}"}
            ])
        
        keyboard['inline_keyboard'].append([
            {'text': '🔙 Назад в меню', 'callback_data': 'back_to_menu'}
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing favorites: {e}")
        await message.answer("❌ Помилка при завантаженні улюблених")


@router.message(Command("quick_reorder"))
async def cmd_quick_reorder(message: types.Message):
    """Quick reorder favorite dish"""
    user_id = message.from_user.id
    
    try:
        profile = UserRepository.get_profile(user_id)
        
        if not profile or not profile.favorite_dishes:
            await message.answer(
                "❌ У тебе поки немає улюблених страв\n\n"
                "Зробиш кілька замовлень і буду знати твої уподобання! 😊"
            )
            return
        
        favorite = profile.favorite_dishes[0]
        
        text = f"🍕 <b>ШВИДКЕ ЗАМОВЛЕННЯ</b>\n\n"
        text += f"Замовити твою улюблену страву?\n"
        text += f"<b>{favorite}</b>\n\n"
        text += f"💡 Раніше ти замовляв цю страву {len([d for d in profile.favorite_dishes if d == favorite])} раз(и)"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Так, замовляю!', 'callback_data': f'quick_add_{favorite}'},
                    {'text': '❌ Ні', 'callback_data': 'back_to_menu'}
                ]
            ]
        }
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in quick reorder: {e}")
        await message.answer("❌ Помилка при швидкому замовленні")


# Example of how to call process_order_completion
# Use this in your existing order confirmation handler

async def example_order_confirmation():
    """
    Example: How to integrate process_order_completion into your flow
    
    Call this in your order confirmation handler:
    """
    
    # After successful order creation:
    user_id = 123456789
    order_id = str(uuid.uuid4())
    restaurant_id = "rest_001"
    items = [
        {'name': 'Pizza Margherita', 'quantity': 1, 'price': 150},
        {'name': 'Salad Caesar', 'quantity': 1, 'price': 100}
    ]
    total_amount = 250.0
    
    # Call the function
    # await process_order_completion(user_id, order_id, restaurant_id, items, total_amount, bot)
    
    # Then send confirmation to user
    confirmation_text = f"""
✅ <b>Замовлення прийнято!</b>

🆔 Номер замовлення: {order_id}
💰 Сума: {total_amount} грн

Дякуємо за замовлення! 🙏
    """
    # await bot.send_message(user_id, confirmation_text, parse_mode="HTML")