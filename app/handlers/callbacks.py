"""
🍕 FERRIKBOT - Callback Query Handlers
Обробка всіх callback від кнопок
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTION - Безпечна відповідь на callback query
# ============================================================================

async def safe_answer_query(query, text: str, show_alert: bool = False):
    """
    Безпечна відповідь на callback query з обробкою timeout та інших помилок
    
    Args:
        query: CallbackQuery object
        text: Текст відповіді
        show_alert: Показувати як alert (True) або toast (False)
    """
    try:
        await query.answer(text, show_alert=show_alert)
    except Exception as e:
        # Логуємо попередження, але не кидаємо exception
        logger.warning(f"⚠️ Failed to answer callback query: {e}")
        # Не критична помилка - користувач може просто не побачити toast


# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

async def surprise_me_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка кнопки "Здивуй мене!"
    Показує рекомендації на основі AI або випадковий вибір
    """
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"🎲 Surprise Me від {user.id}")
    
    await safe_answer_query(query, "🎲 Готую сюрприз!")
    
    try:
        # Імпортуємо функцію surprise me
        from app.utils.surprise_me import generate_surprise_combo
        
        # Генеруємо комбо
        combo = generate_surprise_combo()
        
        if combo:
            message = (
                f"🎁 *Сюрприз для тебе!*\n\n"
                f"{combo['description']}\n\n"
                f"💰 Ціна: ~~{combo['original_price']}~~ → *{combo['discounted_price']} грн*\n"
                f"🎉 Знижка: {combo['discount']}%\n\n"
                f"_Пропозиція діє {combo['valid_until']}_"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Додати в кошик", callback_data=f"add_combo_{combo['id']}"),
                    InlineKeyboardButton("🔄 Інший варіант", callback_data="surprise_me")
                ],
                [
                    InlineKeyboardButton("📋 Дивитись меню", callback_data="v2_show_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "😔 Нажаль, зараз немає спеціальних пропозицій.\n\n"
                "Спробуйте переглянути меню через /menu_v2"
            )
            
    except ImportError:
        # Якщо модуль surprise_me не знайдено, показуємо заглушку
        await query.edit_message_text(
            "🎲 *Сюрприз!*\n\n"
            "🍕 Піца Маргарита\n"
            "🥤 Coca-Cola\n"
            "🍰 Тірамісу\n\n"
            "💰 Всього: 350 грн\n"
            "🎉 Знижка 15%: *297 грн*\n\n"
            "_(Функція в розробці)_",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Surprise Me error: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Помилка при генерації сюрпризу. Спробуйте пізніше."
        )


async def add_to_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Додати товар до кошика
    Callback data format: "add_to_cart_{item_id}"
    """
    query = update.callback_query
    user = query.from_user
    data = query.data
    
    # Витягуємо item_id
    item_id = data.replace("add_to_cart_", "")
    
    logger.info(f"🛒 Add to cart: {item_id} від {user.id}")
    
    try:
        # Імпортуємо cart manager
        from app.utils.cart_manager import add_to_cart, get_cart_item_count
        
        # Отримуємо інформацію про товар (якщо є Google Sheets)
        sheets_service = context.bot_data.get('sheets_service')
        
        item_data = None
        if sheets_service:
            try:
                item_data = sheets_service.get_item_by_id(item_id)
            except Exception as e:
                logger.warning(f"⚠️ Failed to get item from Sheets: {e}")
        
        # Якщо товар знайдено, додаємо в кошик
        if item_data:
            add_to_cart(user.id, {
                'id': item_id,
                'name': item_data.get('name', 'Товар'),
                'price': item_data.get('price', 0),
                'quantity': 1
            })
            
            cart_count = get_cart_item_count(user.id)
            
            await safe_answer_query(
                query,
                f"✅ {item_data.get('name')} додано! Кошик: {cart_count}"
            )
        else:
            # Якщо товар не знайдено, додаємо з мінімальними даними
            add_to_cart(user.id, {
                'id': item_id,
                'name': f'Товар #{item_id}',
                'price': 100,  # Placeholder
                'quantity': 1
            })
            
            await safe_answer_query(query, "✅ Додано в кошик!")
        
        # Оновлюємо повідомлення з кнопкою "Перейти до кошика"
        try:
            keyboard = [
                [
                    InlineKeyboardButton("🛒 Кошик", callback_data="view_cart"),
                    InlineKeyboardButton("📋 Меню", callback_data="v2_show_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_reply_markup(reply_markup=reply_markup)
        except:
            pass  # Якщо не вдалось оновити markup, не критично
            
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        await safe_answer_query(query, "❌ Функція недоступна", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Add to cart error: {e}", exc_info=True)
        await safe_answer_query(query, "❌ Помилка додавання", show_alert=True)


async def view_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показати кошик користувача
    """
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"🛒 View cart від {user.id}")
    
    await safe_answer_query(query, "🛒 Завантажую кошик...")
    
    try:
        from app.utils.cart_manager import get_user_cart, get_cart_total, clear_user_cart
        
        cart = get_user_cart(user.id)
        
        if not cart:
            await query.edit_message_text(
                "🛒 *Ваш кошик порожній*\n\n"
                "Додайте щось смачненьке через /menu_v2",
                parse_mode='Markdown'
            )
            return
        
        # Формуємо текст кошика
        items_text = "\n".join([
            f"{i+1}. {item.get('name', 'Товар')} x{item.get('quantity', 1)} = {item.get('price', 0) * item.get('quantity', 1)} грн"
            for i, item in enumerate(cart)
        ])
        
        total = get_cart_total(user.id)
        delivery_cost = 50
        final_total = total + delivery_cost
        
        message = (
            f"🛒 *Ваш кошик:*\n\n"
            f"{items_text}\n\n"
            f"💰 Сума: {total} грн\n"
            f"🚚 Доставка: {delivery_cost} грн\n"
            f"*Разом: {final_total} грн*"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Оформити", callback_data="checkout_start"),
                InlineKeyboardButton("🗑️ Очистити", callback_data="cart_clear")
            ],
            [
                InlineKeyboardButton("📋 Додати ще", callback_data="v2_show_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except ImportError:
        await query.edit_message_text(
            "❌ Кошик недоступний. Використовуйте /cart"
        )
    except Exception as e:
        logger.error(f"❌ View cart error: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Помилка при завантаженні кошика"
        )


async def cart_clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Очистити кошик
    """
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"🗑️ Clear cart від {user.id}")
    
    try:
        from app.utils.cart_manager import clear_user_cart
        
        clear_user_cart(user.id)
        
        await safe_answer_query(query, "🗑️ Кошик очищено!")
        
        await query.edit_message_text(
            "🗑️ Кошик очищено!\n\n"
            "Бажаєте замовити щось інше?"
        )
        
    except Exception as e:
        logger.error(f"❌ Clear cart error: {e}")
        await safe_answer_query(query, "❌ Помилка", show_alert=True)


async def checkout_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Початок оформлення замовлення
    """
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"✅ Checkout start від {user.id}")
    
    await safe_answer_query(query, "✅ Починаємо оформлення!")
    
    try:
        from app.utils.session import update_user_session
        from app.utils.cart_manager import get_user_cart
        
        cart = get_user_cart(user.id)
        
        if not cart:
            await query.edit_message_text(
                "❌ Кошик порожній! Додайте товари через /menu_v2"
            )
            return
        
        # Встановлюємо стан "очікуємо телефон"
        update_user_session(user.id, {'state': 'awaiting_phone'})
        
        await query.edit_message_text(
            "📱 *Оформлення замовлення*\n\n"
            "Крок 1/3: Введіть ваш номер телефону\n\n"
            "Формат:\n"
            "• +380501234567\n"
            "• 0501234567\n"
            "• 050 123 45 67",
            parse_mode='Markdown'
        )
        
    except ImportError:
        await query.edit_message_text(
            "❌ Функція недоступна. Спробуйте /order"
        )
    except Exception as e:
        logger.error(f"❌ Checkout start error: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Помилка при оформленні"
        )


async def confirm_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Підтвердження та збереження замовлення
    """
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"✅ Confirm order від {user.id}")
    
    await safe_answer_query(query, "✅ Зберігаю замовлення...")
    
    try:
        from app.utils.session import get_user_session, update_user_session
        from app.utils.cart_manager import get_user_cart, get_cart_total, clear_user_cart
        
        session = get_user_session(user.id)
        cart = get_user_cart(user.id)
        
        if not cart:
            await query.edit_message_text("❌ Кошик порожній!")
            return
        
        # Підготувати дані замовлення
        order_data = {
            'user_id': user.id,
            'items': cart,
            'phone': session.get('phone'),
            'address': session.get('address'),
            'total': get_cart_total(user.id),
            'delivery_cost': 50,
            'promocode': session.get('promocode', ''),
            'discount': session.get('discount', 0)
        }
        
        # Зберегти в Google Sheets (якщо доступно)
        sheets_service = context.bot_data.get('sheets_service')
        if sheets_service:
            try:
                success = sheets_service.save_order(order_data)
                if success:
                    logger.info(f"✅ Order saved for user {user.id}")
            except Exception as e:
                logger.error(f"⚠️ Failed to save order: {e}")
        
        # Очистити кошик та сесію
        clear_user_cart(user.id)
        update_user_session(user.id, {'state': 'idle'})
        
        # Відправити підтвердження
        await query.edit_message_text(
            "✅ *Замовлення прийнято!*\n\n"
            f"📞 Ми зателефонуємо на {order_data['phone']}\n"
            f"📍 Доставка: {order_data['address']}\n"
            f"⏰ Очікуваний час: 30-45 хв\n\n"
            "Дякуємо за замовлення! 🍕",
            parse_mode='Markdown'
        )
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        await query.edit_message_text("❌ Функція недоступна")
    except Exception as e:
        logger.error(f"❌ Confirm order error: {e}", exc_info=True)
        await query.edit_message_text("❌ Помилка збереження замовлення")


async def cancel_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Скасування замовлення
    """
    query = update.callback_query
    user = query.from_user
    
    logger.info(f"❌ Cancel order від {user.id}")
    
    await safe_answer_query(query, "❌ Скасовано")
    
    try:
        from app.utils.session import update_user_session
        
        update_user_session(user.id, {'state': 'idle'})
        
        await query.edit_message_text(
            "❌ Замовлення скасовано\n\n"
            "Кошик збережено. Ви можете повернутись через /cart"
        )
        
    except Exception as e:
        logger.error(f"❌ Cancel order error: {e}")
        await query.edit_message_text("❌ Скасовано")


# ============================================================================
# ГОЛОВНИЙ CALLBACK HANDLER (catch-all)
# ============================================================================

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Головний обробник callback queries
    Викликається для всіх callback_data які не оброблені окремими handlers
    """
    query = update.callback_query
    user = query.from_user
    data = query.data
    
    logger.info(f"🔘 Callback: {data} від {user.id}")
    
    await safe_answer_query(query, f"⚠️ Обробка {data[:20]}...")
    
    # Якщо callback_data невідомий
    await query.edit_message_text(
        f"⚠️ Невідома команда: {data}\n\n"
        "Спробуйте /menu_v2"
    )


# ============================================================================
# РЕЄСТРАЦІЯ CALLBACK HANDLERS
# ============================================================================

def register_callback_handlers(application):
    """
    Реєстрація всіх callback query handlers
    
    Args:
        application: Telegram Application instance
    """
    logger.info("📝 Registering callback handlers...")
    
    try:
        # Окремі handlers для конкретних callback_data
        
        # Surprise Me
        application.add_handler(
            CallbackQueryHandler(surprise_me_callback, pattern="^surprise_me$")
        )
        
        # Add to Cart
        application.add_handler(
            CallbackQueryHandler(add_to_cart_callback, pattern="^add_to_cart_")
        )
        
        # View Cart
        application.add_handler(
            CallbackQueryHandler(view_cart_callback, pattern="^view_cart$")
        )
        
        # Clear Cart
        application.add_handler(
            CallbackQueryHandler(cart_clear_callback, pattern="^cart_clear$")
        )
        
        # Checkout Start
        application.add_handler(
            CallbackQueryHandler(checkout_start_callback, pattern="^checkout_start$")
        )
        
        # Confirm Order
        application.add_handler(
            CallbackQueryHandler(confirm_order_callback, pattern="^confirm_order$")
        )
        
        # Cancel Order
        application.add_handler(
            CallbackQueryHandler(cancel_order_callback, pattern="^cancel_order$")
        )
        
        # Catch-all handler (має бути останнім!)
        application.add_handler(
            CallbackQueryHandler(callback_query_handler)
        )
        
        logger.info("✅ Callback handlers registered successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to register callback handlers: {e}", exc_info=True)
        raise.