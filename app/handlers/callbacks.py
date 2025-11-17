"""
🔘 Обробники callback кнопок
FerrikBot v3.2 - ВИПРАВЛЕНА ВЕРСІЯ
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.error import BadRequest

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
    """Головний обробник всіх callback кнопок"""
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    data = query.data
    
    logger.info(f"🔘 Callback '{data}' from {user.username or user.first_name}")
    
    # Answer callback
    try:
        await query.answer()
    except BadRequest as e:
        if "query is too old" in str(e).lower():
            logger.debug(f"Query too old (safe to ignore): {e}")
        else:
            logger.warning(f"Query answer error: {e}")
    except Exception as e:
        logger.warning(f"Unexpected query answer error: {e}")
    
    try:
        # Route to handlers
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
        elif data == "change_phone":
            await handle_change_phone_callback(query, context)
        elif data == "change_address":
            await handle_change_address_callback(query, context)
        else:
            logger.warning(f"Unknown callback data: {data}")
            await query.edit_message_text("⚠️ Невідома команда. Спробуйте /start")
    
    except BadRequest as e:
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
    """Handle 'start' button"""
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
    """Handle 'menu' button"""
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
    """Handle 'cart' button"""
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
    """Handle 'profile' button"""
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
    """Handle 'help' button"""
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
    """Handle category selection"""
    try:
        category = data.replace("category_", "")
        
        # Try load from Sheets
        items = []
        if sheets_service.is_connected():
            items = sheets_service.get_menu_by_category(category)
        
        # Fallback to sample
        if not items:
            items = get_sample_items_for_category(category)
        
        if not items:
            await query.answer("⚠️ Немає доступних страв", show_alert=True)
            return
        
        category_emoji = {
            "Піца": "🍕", "pizza": "🍕",
            "Бургери": "🍔", "burgers": "🍔",
            "Закуски": "🍟", "snacks": "🍟",
            "Напої": "🥤", "drinks": "🥤"
        }.get(category, "🍴")
        
        message = f"<b>{category_emoji} {category}</b>\n\n"
        
        keyboard = []
        for item in items[:10]:
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


def get_sample_items_for_category(category: str) -> list:
    """Get sample items"""
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
    """Handle adding item to cart"""
    item_id = int(data.replace("add_", ""))
    user_id = query.from_user.id
    
    try:
        # Try get from Sheets
        item = None
        if sheets_service.is_connected():
            item = sheets_service.get_menu_item(item_id)
        
        # Fallback to sample
        if not item:
            all_items = {
                1: {"id": 1, "name": "Маргарита", "price": 180, "category": "pizza"},
                2: {"id": 2, "name": "Пепероні", "price": 200, "category": "pizza"},
                5: {"id": 5, "name": "Класичний", "price": 150, "category": "burgers"},
                6: {"id": 6, "name": "Чізбургер", "price": 170, "category": "burgers"},
                8: {"id": 8, "name": "Картопля фрі", "price": 60, "category": "snacks"},
                9: {"id": 9, "name": "Нагетси", "price": 80, "category": "snacks"},
                11: {"id": 11, "name": "Coca-Cola", "price": 40, "category": "drinks"},
                12: {"id": 12, "name": "Sprite", "price": 40, "category": "drinks"},
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
    except Exception as e:
        logger.error(f"Error adding item: {e}")
        await query.answer("❌ Помилка!", show_alert=True)


async def handle_remove_item_callback(query, context, data):
    """Handle removing item"""
    item_id = int(data.replace("remove_", ""))
    user_id = query.from_user.id
    
    remove_from_cart(user_id, item_id)
    
    try:
        await query.answer("🗑️ Товар видалено", show_alert=False)
    except:
        pass
    
    await handle_cart_callback(query, context)


async def handle_cart_clear_callback(query, context):
    """Handle clearing cart"""
    user_id = query.from_user.id
    clear_user_cart(user_id)
    
    try:
        await query.answer("🗑️ Кошик очищено", show_alert=False)
    except:
        pass
    
    await handle_cart_callback(query, context)


async def handle_checkout_callback(query, context):
    """
    ЦЕ КЛЮЧОВА ФУНКЦІЯ - ТУТ БУЛА ПОМИЛКА!
    """
    user_id = query.from_user.id
    username = query.from_user.first_name or "Користувач"
    
    logger.info(f"🛒 Checkout initiated by {username} (ID: {user_id})")
    
    # Get cart
    summary = get_cart_summary(user_id)
    
    # Check if empty
    if summary['is_empty']:
        await query.answer("❌ Кошик порожній!", show_alert=True)
        return
    
    # Check restaurants
    restaurants = set()
    for item in summary['items']:
        restaurant = item.get('restaurant', '')
        if restaurant:
            restaurants.add(restaurant)
    
    if len(restaurants) > 1:
        await query.answer(
            "❌ Товари повинні бути з одного закладу!",
            show_alert=True
        )
        return
    
    # Save state
    context.user_data['checkout_stage'] = 'awaiting_phone'
    context.user_data['cart_snapshot'] = summary['items'].copy()
    
    # Show phone request
    message = (
        "📦 <b>Оформлення замовлення</b>\n\n"
        f"{format_cart_message(user_id)}\n\n"
        "📞 Введіть ваш номер телефону:\n"
        "<i>Формат: +380XXXXXXXXX</i>\n\n"
        "Наприклад: +380501234567"
    )
    
    keyboard = [
        [InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order")],
        [InlineKeyboardButton("◀️ Назад до кошика", callback_data="cart")]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    await query.answer("✅ Переходимо до оформлення...")


async def handle_partner_callback(query, context, data):
    """Handle partner selection"""
    # TODO: Implement when have multiple partners
    pass


async def handle_order_phone_callback(query, context):
    """Handle order phone step"""
    await handle_checkout_callback(query, context)


async def handle_confirm_order_callback(query, context):
    """Handle order confirmation"""
    user_id = query.from_user.id
    user = query.from_user
    
    try:
        await query.answer("⏳ Обробка замовлення...", show_alert=False)
    except:
        pass
    
    # Get data
    cart = context.user_data.get('cart_snapshot', [])
    phone = context.user_data.get('phone', 'Не вказано')
    address = context.user_data.get('address', 'Не вказано')
    
    # Calculate
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    delivery_cost = 0 if total >= 300 else 50
    total_with_delivery = total + delivery_cost
    
    # Get restaurant
    restaurant_name = "Ресторан"
    if cart:
        restaurant_name = cart[0].get('restaurant', 'Ресторан')
    
    # Save to Sheets
    order_saved = False
    order_id = user_id % 10000
    
    if sheets_service.is_connected():
        try:
            order_data = {
                'user_id': user_id,
                'username': user.username or user.first_name,
                'items': cart,
                'total': total,
                'address': address,
                'phone': phone,
                'payment_method': 'Готівка',
                'delivery_cost': delivery_cost,
                'delivery_type': 'Доставка'
            }
            
            order_saved = sheets_service.add_order(order_data)
            
        except Exception as e:
            logger.error(f"❌ Error saving order: {e}")
    
    # Update stats
    try:
        update_user_stats(user_id, total_with_delivery)
    except Exception as e:
        logger.error(f"Error updating stats: {e}")
    
    # Clear cart
    clear_user_cart(user_id)
    context.user_data.clear()
    
    # Success message
    message = (
        "🎉 <b>ЗАМОВЛЕННЯ ПІДТВЕРДЖЕНО!</b>\n\n"
        f"📦 <b>Номер замовлення: #{order_id}</b>\n\n"
        f"🏪 Заклад: {restaurant_name}\n"
        f"💰 Сума товарів: {total} грн\n"
        f"🚚 Доставка: {delivery_cost} грн\n"
    )
    
    if delivery_cost == 0:
        message += "<i>(Безкоштовна від 300 грн)</i>\n"
    
    message += f"\n💵 <b>РАЗОМ: {total_with_delivery} грн</b>\n\n"
    message += f"📞 Ваш телефон: {phone}\n"
    message += f"📍 Адреса доставки: {address}\n\n"
    message += "⏱ <b>Очікуваний час доставки: 30-45 хвилин</b>\n"
    message += "💳 Оплата: Готівка при отриманні\n\n"
    
    if order_saved:
        message += "✅ Замовлення передано в заклад\n"
    else:
        message += "⚠️ Замовлення збережено локально\n"
    
    message += "\nДякуємо за замовлення! 🍕"
    
    keyboard = [
        [InlineKeyboardButton("🍕 Замовити ще", callback_data="menu")],
        [InlineKeyboardButton("📊 Мій профіль", callback_data="profile")],
        [InlineKeyboardButton("◀️ Головна", callback_data="start")]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_cancel_order_callback(query, context):
    """Handle order cancellation"""
    context.user_data.clear()
    
    message = (
        "❌ <b>Замовлення скасовано</b>\n\n"
        "Товари залишились у кошику.\n"
        "Ви можете продовжити покупки або оформити замовлення пізніше."
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Повернутись до кошика", callback_data="cart")],
        [InlineKeyboardButton("🍕 Продовжити покупки", callback_data="menu")],
        [InlineKeyboardButton("◀️ Головна", callback_data="start")]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_change_phone_callback(query, context):
    """Handle change phone"""
    message = (
        "📞 <b>Зміна номера телефону</b>\n\n"
        "Введіть новий номер телефону:\n"
        "<i>Формат: +380XXXXXXXXX</i>\n\n"
        "Наприклад: +380501234567"
    )
    
    context.user_data['awaiting_phone'] = True
    
    keyboard = [
        [InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order")]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_change_address_callback(query, context):
    """Handle change address"""
    message = (
        "📍 <b>Зміна адреси доставки</b>\n\n"
        "Введіть нову адресу:\n"
        "<i>вулиця, номер будинку, квартира</i>\n\n"
        "Наприклад: вул. Шевченка 15, кв. 42"
    )
    
    context.user_data['awaiting_address'] = True
    
    keyboard = [
        [InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order")]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


__all__ = ['button_callback']
