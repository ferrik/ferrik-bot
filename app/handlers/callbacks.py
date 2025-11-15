"""
Callback Query Handlers - Handle button presses
FerrikBot v3.2 - Final Fixed Version
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

# Import utilities
from app.utils.cart_manager import (
    add_to_cart,
    remove_from_cart,
    clear_user_cart,
    get_cart_summary,
    format_cart_message,
    is_cart_empty
)
from app.utils.warm_greetings import (
    get_greeting_for_user,
    format_user_profile,
    update_user_stats
)
from app.services.sheets_service import sheets_service

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle all callback queries from inline buttons
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    data = query.data
    
    logger.info(f"🔘 Callback '{data}' from {user.username or user.first_name}")
    
    # Answer callback to remove loading state (with error handling)
    try:
        await query.answer()
    except BadRequest as e:
        # Ignore "query too old" errors (happens when bot was sleeping on free tier)
        if "query is too old" in str(e).lower():
            logger.debug(f"Query too old (safe to ignore): {e}")
        else:
            logger.warning(f"Query answer error: {e}")
    except Exception as e:
        logger.warning(f"Unexpected query answer error: {e}")
    
    try:
        # Route to appropriate handler
        if data == "start":
            await handle_start_callback(query, context)
        
        elif data == "menu":
            await handle_menu_callback(query, context)
        
        elif data == "cart":
            await handle_cart_callback(query, context)
        
        elif data == "profile":
            await handle_profile_callback(query, context)
        
        elif data == "help":
            await handle_help_callback(query, context)
        
        elif data.startswith("category_"):
            await handle_category_callback(query, context, data)
        
        elif data.startswith("partner_"):
            await handle_partner_callback(query, context, data)
        
        elif data.startswith("add_"):
            await handle_add_item_callback(query, context, data)
        
        elif data.startswith("remove_"):
            await handle_remove_item_callback(query, context, data)
        
        elif data == "cart_clear":
            await handle_cart_clear_callback(query, context)
        
        elif data == "checkout":
            await handle_checkout_callback(query, context)
        
        elif data == "order_phone":
            await handle_order_phone_callback(query, context)
        
        elif data == "confirm_order":
            await handle_confirm_order_callback(query, context)
        
        elif data == "cancel_order":
            await handle_cancel_order_callback(query, context)
        
        else:
            logger.warning(f"Unknown callback data: {data}")
            await query.edit_message_text("⚠️ Невідома команда. Спробуйте /start")
    
    except BadRequest as e:
        # Handle message not modified error
        if "message is not modified" in str(e).lower():
            logger.debug("Message content unchanged, skipping edit")
        else:
            logger.error(f"❌ BadRequest in callback '{data}': {e}")
            try:
                await query.message.reply_text("⚠️ Виникла помилка. Спробуйте ще раз або /start")
            except:
                pass
    
    except Exception as e:
        logger.error(f"❌ Error handling callback '{data}': {e}", exc_info=True)
        try:
            await query.message.reply_text("⚠️ Виникла помилка. Спробуйте /start")
        except:
            pass


async def handle_start_callback(query, context):
    """Handle 'start' button - back to main menu"""
    user = query.from_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    
    greeting = get_greeting_for_user(user_id, username, first_name)
    
    message = greeting + "\n\n"
    message += (
        "🍕 <b>FerrikBot</b> - твій помічник у замовленні їжі\n\n"
        "📋 <b>Доступні команди:</b>\n"
        "▪️ /menu - Переглянути меню\n"
        "▪️ /cart - Кошик\n"
        "▪️ /order - Оформити замовлення\n"
        "▪️ /profile - Мій профіль\n"
        "▪️ /help - Допомога"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🍕 Меню", callback_data="menu"),
            InlineKeyboardButton("🛒 Кошик", callback_data="cart")
        ],
        [
            InlineKeyboardButton("👤 Профіль", callback_data="profile"),
            InlineKeyboardButton("❓ Допомога", callback_data="help")
        ]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_menu_callback(query, context):
    """Handle 'menu' button - show menu"""
    message = (
        "🍕 <b>Меню FerrikBot</b>\n\n"
        "<b>🍕 Піца:</b>\n"
        "▪️ Маргарита - 180 грн\n"
        "▪️ Пепероні - 200 грн\n"
        "▪️ 4 Сири - 220 грн\n"
        "▪️ М'ясна - 240 грн\n\n"
        "<b>🍔 Бургери:</b>\n"
        "▪️ Класичний - 150 грн\n"
        "▪️ Чізбургер - 170 грн\n"
        "▪️ Бекон бургер - 190 грн\n\n"
        "<b>🍟 Закуски:</b>\n"
        "▪️ Картопля фрі - 60 грн\n"
        "▪️ Нагетси - 80 грн\n"
        "▪️ Крильця - 120 грн\n\n"
        "<b>🥤 Напої:</b>\n"
        "▪️ Coca-Cola - 40 грн\n"
        "▪️ Sprite - 40 грн\n"
        "▪️ Сік - 50 грн\n\n"
        "Оберіть категорію:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🍕 Піца", callback_data="category_pizza"),
            InlineKeyboardButton("🍔 Бургери", callback_data="category_burgers")
        ],
        [
            InlineKeyboardButton("🍟 Закуски", callback_data="category_snacks"),
            InlineKeyboardButton("🥤 Напої", callback_data="category_drinks")
        ],
        [
            InlineKeyboardButton("🛒 Кошик", callback_data="cart"),
            InlineKeyboardButton("◀️ Назад", callback_data="start")
        ]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_cart_callback(query, context):
    """Handle 'cart' button - show shopping cart"""
    user_id = query.from_user.id
    summary = get_cart_summary(user_id)
    
    if summary['is_empty']:
        message = (
            "🛒 <b>Ваш кошик порожній</b>\n\n"
            "Використайте меню щоб додати товари 🍕"
        )
        keyboard = [
            [InlineKeyboardButton("🍕 Меню", callback_data="menu")],
            [InlineKeyboardButton("◀️ Назад", callback_data="start")]
        ]
    else:
        message = format_cart_message(user_id)
        keyboard = [
            [InlineKeyboardButton("✅ Оформити замовлення", callback_data="checkout")],
            [
                InlineKeyboardButton("🍕 Додати ще", callback_data="menu"),
                InlineKeyboardButton("🗑️ Очистити", callback_data="cart_clear")
            ],
            [InlineKeyboardButton("◀️ Назад", callback_data="start")]
        ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_profile_callback(query, context):
    """Handle 'profile' button - show user profile"""
    user_id = query.from_user.id
    username = query.from_user.username
    
    message = format_user_profile(user_id, username)
    
    keyboard = [
        [
            InlineKeyboardButton("🛒 Кошик", callback_data="cart"),
            InlineKeyboardButton("🍕 Меню", callback_data="menu")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="start")]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_help_callback(query, context):
    """Handle 'help' button - show help"""
    message = (
        "❓ <b>Допомога FerrikBot</b>\n\n"
        "<b>📋 Команди:</b>\n"
        "▪️ /start - Головне меню\n"
        "▪️ /menu - Переглянути меню\n"
        "▪️ /cart - Відкрити кошик\n"
        "▪️ /order - Оформити замовлення\n"
        "▪️ /profile - Мій профіль\n\n"
        "<b>🎯 Як замовити:</b>\n"
        "1. Відкрий меню\n"
        "2. Вибери страви\n"
        "3. Перевір кошик\n"
        "4. Оформи замовлення\n\n"
        "<b>💎 Система лояльності:</b>\n"
        "🥉 Bronze (0-4) - 5% знижка\n"
        "🥈 Silver (5-9) - 15% знижка\n"
        "🏆 Gold (10-24) - 20% знижка\n"
        "⭐ Platinum (25-49) - 25% знижка\n"
        "💎 Diamond (50+) - 30% знижка\n\n"
        "<b>📞 Підтримка:</b>\n"
        "Питання? Напиши @support"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🍕 Меню", callback_data="menu"),
            InlineKeyboardButton("🛒 Кошик", callback_data="cart")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="start")]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_category_callback(query, context, data):
    """Handle category selection - load from Google Sheets"""
    try:
        category = data.replace("category_", "")
        
        # Try to load menu from Google Sheets
        items = []
        if sheets_service.is_connected():
            items = sheets_service.get_menu_by_category(category)
        
        # Fallback to sample data if no items
        if not items:
            items = get_sample_items_for_category(category)
        
        if not items:
            await query.answer("⚠️ Немає доступних страв", show_alert=True)
            return
        
        # Get category emoji
        category_emoji = {
            "Піца": "🍕",
            "pizza": "🍕",
            "Бургери": "🍔",
            "burgers": "🍔",
            "Закуски": "🍟",
            "snacks": "🍟",
            "Напої": "🥤",
            "drinks": "🥤"
        }.get(category, "🍴")
        
        message = f"<b>{category_emoji} {category}</b>\n\n"
        
        keyboard = []
        for item in items[:10]:  # Limit to 10 items
            item_id = item.get('ID', 0)
            item_name = item.get('Страви', 'Товар')
            item_price = item.get('Ціна', 0)
            item_desc = item.get('Опис', '')
            restaurant = item.get('Ресторан', '')
            
            message += f"<b>{item_name}</b> - {item_price} грн\n"
            if item_desc:
                message += f"<i>{item_desc}</i>\n"
            if restaurant:
                message += f"📍 {restaurant}\n"
            message += "\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"➕ {item_name} ({item_price} грн)",
                    callback_data=f"add_{item_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("◀️ Меню", callback_data="menu"),
            InlineKeyboardButton("🛒 Кошик", callback_data="cart")
        ])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in category callback: {e}", exc_info=True)
        await query.answer("⚠️ Помилка завантаження", show_alert=True)


async def handle_partner_callback(query, context, data):
    """Handle partner/restaurant selection"""
    try:
        partner_id = data.replace("partner_", "")
        
        # Save selected partner to user context
        context.user_data['selected_partner_id'] = partner_id
        
        # Get partner details
        partner = None
        if sheets_service.is_connected():
            partner = sheets_service.get_partner(partner_id)
        
        if not partner:
            await query.answer("⚠️ Заклад не знайдено", show_alert=True)
            return
        
        partner_name = partner.get('Ім\'я_партнера', 'Заклад')
        partner_category = partner.get('Категорія', '')
        partner_rating = partner.get('Рейтинг', '')
        
        # Get unique categories for this partner
        categories = set()
        if sheets_service.is_connected():
            all_menu = sheets_service.get_menu()
            for item in all_menu:
                if item.get('Ресторан') == partner_name:
                    cat = item.get('Категорія', '')
                    if cat:
                        categories.add(cat)
        
        message = f"🏪 <b>{partner_name}</b>\n\n"
        if partner_category:
            message += f"📁 {partner_category}\n"
        if partner_rating:
            message += f"⭐ Рейтинг: {partner_rating}\n"
        message += "\nОберіть категорію страв:"
        
        keyboard = []
        
        # Add category buttons
        category_buttons = []
        for cat in sorted(categories):
            category_buttons.append(
                InlineKeyboardButton(
                    f"🍴 {cat}",
                    callback_data=f"category_{cat}"
                )
            )
        
        # Arrange in rows of 2
        for i in range(0, len(category_buttons), 2):
            keyboard.append(category_buttons[i:i+2])
        
        # Navigation buttons
        keyboard.append([
            InlineKeyboardButton("🛒 Кошик", callback_data="cart"),
            InlineKeyboardButton("◀️ Заклади", callback_data="menu")
        ])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in partner callback: {e}", exc_info=True)
        await query.answer("⚠️ Помилка", show_alert=True)


def get_sample_items_for_category(category: str) -> list:
    """Get sample items if Google Sheets not available"""
    samples = {
        "Піца": [
            {"ID": 1, "Страви": "Маргарита", "Ціна": 180, "Опис": "Томати, моцарела, базилік"},
            {"ID": 2, "Страви": "Пепероні", "Ціна": 200, "Опис": "Гостра ковбаска пепероні"},
        ],
        "pizza": [
            {"ID": 1, "Страви": "Маргарита", "Ціна": 180, "Опис": "Томати, моцарела, базилік"},
            {"ID": 2, "Страви": "Пепероні", "Ціна": 200, "Опис": "Гостра ковбаска пепероні"},
        ],
        "Бургери": [
            {"ID": 5, "Страви": "Класичний", "Ціна": 150, "Опис": "Яловичина, помідор, огірок"},
            {"ID": 6, "Страви": "Чізбургер", "Ціна": 170, "Опис": "З подвійним сиром"},
        ],
        "burgers": [
            {"ID": 5, "Страви": "Класичний", "Ціна": 150, "Опис": "Яловичина, помідор, огірок"},
            {"ID": 6, "Страви": "Чізбургер", "Ціна": 170, "Опис": "З подвійним сиром"},
        ],
        "Закуски": [
            {"ID": 8, "Страви": "Картопля фрі", "Ціна": 60, "Опис": "Золотиста картопля"},
            {"ID": 9, "Страви": "Нагетси", "Ціна": 80, "Опис": "Курячі нагетси (6 шт)"},
        ],
        "snacks": [
            {"ID": 8, "Страви": "Картопля фрі", "Ціна": 60, "Опис": "Золотиста картопля"},
            {"ID": 9, "Страви": "Нагетси", "Ціна": 80, "Опис": "Курячі нагетси (6 шт)"},
        ],
        "Напої": [
            {"ID": 11, "Страви": "Coca-Cola", "Ціна": 40, "Опис": "0.5л"},
            {"ID": 12, "Страви": "Sprite", "Ціна": 40, "Опис": "0.5л"},
        ],
        "drinks": [
            {"ID": 11, "Страви": "Coca-Cola", "Ціна": 40, "Опис": "0.5л"},
            {"ID": 12, "Страви": "Sprite", "Ціна": 40, "Опис": "0.5л"},
        ]
    }
    
    return samples.get(category, [])


async def handle_add_item_callback(query, context, data):
    """Handle adding item to cart - with Google Sheets support"""
    item_id = int(data.replace("add_", ""))
    user_id = query.from_user.id
    
    # Try to get item from Google Sheets
    item = None
    if sheets_service.is_connected():
        item = sheets_service.get_menu_item(item_id)
    
    # Fallback to sample data
    if not item:
        all_items = {
            1: {"id": 1, "name": "Маргарита", "price": 180, "category": "pizza"},
            2: {"id": 2, "name": "Пепероні", "price": 200, "category": "pizza"},
            3: {"id": 3, "name": "4 Сири", "price": 220, "category": "pizza"},
            4: {"id": 4, "name": "М'ясна", "price": 240, "category": "pizza"},
            5: {"id": 5, "name": "Класичний", "price": 150, "category": "burgers"},
            6: {"id": 6, "name": "Чізбургер", "price": 170, "category": "burgers"},
            7: {"id": 7, "name": "Бекон бургер", "price": 190, "category": "burgers"},
            8: {"id": 8, "name": "Картопля фрі", "price": 60, "category": "snacks"},
            9: {"id": 9, "name": "Нагетси", "price": 80, "category": "snacks"},
            10: {"id": 10, "name": "Крильця", "price": 120, "category": "snacks"},
            11: {"id": 11, "name": "Coca-Cola", "price": 40, "category": "drinks"},
            12: {"id": 12, "name": "Sprite", "price": 40, "category": "drinks"},
            13: {"id": 13, "name": "Сік", "price": 50, "category": "drinks"}
        }
        sample_item = all_items.get(item_id)
        if sample_item:
            item = {
                'ID': sample_item['id'],
                'Страви': sample_item['name'],
                'Ціна': sample_item['price'],
                'Категорія': sample_item['category']
            }
    
    if item:
        # Convert to cart format
        cart_item = {
            'id': item.get('ID'),
            'name': item.get('Страви', 'Товар'),
            'price': item.get('Ціна', 0),
            'category': item.get('Категорія', ''),
            'restaurant': item.get('Ресторан', ''),
            'partner_id': context.user_data.get('selected_partner_id', '')
        }
        
        add_to_cart(user_id, cart_item)
        
        try:
            await query.answer(
                f"✅ {cart_item['name']} додано в кошик!",
                show_alert=True
            )
        except:
            pass
    else:
        try:
            await query.answer("❌ Товар не знайдено", show_alert=True)
        except:
            pass


async def handle_remove_item_callback(query, context, data):
    """Handle removing item from cart"""
    item_id = int(data.replace("remove_", ""))
    user_id = query.from_user.id
    
    remove_from_cart(user_id, item_id)
    
    try:
        await query.answer("🗑️ Товар видалено", show_alert=False)
    except:
        pass
    
    # Refresh cart
    await handle_cart_callback(query, context)


async def handle_cart_clear_callback(query, context):
    """Handle clearing cart"""
    user_id = query.from_user.id
    clear_user_cart(user_id)
    
    try:
        await query.answer("🗑️ Кошик очищено", show_alert=False)
    except:
        pass
    
    # Show empty cart
    await handle_cart_callback(query, context)


async def handle_checkout_callback(query, context):
    """Handle checkout button"""
    user_id = query.from_user.id
    
    if is_cart_empty(user_id):
        try:
            await query.answer("⚠️ Кошик порожній!", show_alert=True)
        except:
            pass
        return
    
    message = (
        "📦 <b>Оформлення замовлення</b>\n\n"
        f"{format_cart_message(user_id)}\n\n"
        "Для продовження введіть ваш номер телефону у форматі:\n"
        "<code>+380XXXXXXXXX</code>"
    )
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад до кошика", callback_data="cart")]
    ]
    
    # Set state for phone input
    context.user_data['awaiting_p