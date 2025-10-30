# handlers/cart.py
"""
🛒 ОБРОБНИКИ КОШИКА
Додавання, видалення, перегляд товарів у кошику
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from services.models import get_session, UserCart, MenuItem
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ============================================================================
# ДОБАВЛЕННЯ В КОШИК
# ============================================================================

async def add_to_cart(user_id: str, item_id: str, quantity: int, db_engine) -> bool:
    """
    Додай товар у кошик користувача
    
    Args:
        user_id: Telegram user ID
        item_id: ID товару
        quantity: Кількість
        db_engine: SQLAlchemy engine
    
    Returns:
        True якщо успішно, False якщо помилка
    """
    try:
        session = get_session(db_engine)
        
        # Отримай товар
        menu_item = session.query(MenuItem).filter(MenuItem.id == item_id).first()
        
        if not menu_item:
            logger.warning(f"❌ Item not found: {item_id}")
            return False
        
        # Перевіри, чи вже в кошику
        existing = session.query(UserCart).filter(
            UserCart.user_id == user_id,
            UserCart.item_id == item_id
        ).first()
        
        if existing:
            # Збільш кількість
            existing.quantity += quantity
            logger.info(f"✅ Updated cart: {user_id} - {item_id} qty={existing.quantity}")
        else:
            # Додай новий товар
            cart_item = UserCart(
                user_id=user_id,
                item_id=item_id,
                item_name=menu_item.name,
                quantity=quantity,
                price=menu_item.price
            )
            session.add(cart_item)
            logger.info(f"✅ Added to cart: {user_id} - {item_id} qty={quantity}")
        
        session.commit()
        return True
    
    except Exception as e:
        logger.error(f"❌ Add to cart error: {e}")
        return False
    
    finally:
        session.close()


# ============================================================================
# ВИДАЛЕННЯ З КОШИКА
# ============================================================================

async def remove_from_cart(user_id: str, cart_id: int, db_engine) -> bool:
    """Видали товар з кошика"""
    try:
        session = get_session(db_engine)
        
        item = session.query(UserCart).filter(
            UserCart.id == cart_id,
            UserCart.user_id == user_id
        ).first()
        
        if item:
            session.delete(item)
            session.commit()
            logger.info(f"✅ Removed from cart: {user_id} - cart_id={cart_id}")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"❌ Remove from cart error: {e}")
        return False
    
    finally:
        session.close()


# ============================================================================
# ПЕРЕГЛЯД КОШИКА
# ============================================================================

async def get_user_cart(user_id: str, db_engine) -> list:
    """Отримай весь кошик користувача"""
    try:
        session = get_session(db_engine)
        
        items = session.query(UserCart).filter(
            UserCart.user_id == user_id
        ).all()
        
        return [item.to_dict() for item in items]
    
    except Exception as e:
        logger.error(f"❌ Get cart error: {e}")
        return []
    
    finally:
        session.close()


async def get_cart_total(user_id: str, db_engine) -> float:
    """Розраховуй суму кошика"""
    try:
        session = get_session(db_engine)
        
        items = session.query(UserCart).filter(
            UserCart.user_id == user_id
        ).all()
        
        total = sum(item.quantity * item.price for item in items)
        return total
    
    except Exception as e:
        logger.error(f"❌ Get cart total error: {e}")
        return 0
    
    finally:
        session.close()


# ============================================================================
# ПОКАЗ КОШИКА В TELEGRAM
# ============================================================================

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, db_engine):
    """Команда /cart - показ кошика користувача"""
    try:
        user_id = str(update.effective_user.id)
        
        # Отримай товари
        cart_items = await get_user_cart(user_id, db_engine)
        
        if not cart_items:
            await update.message.reply_text(
                "🛒 Твій кошик порожній.\n\n"
                "Обери товар: /menu"
            )
            return
        
        # Форматуй кошик
        text = "🛒 *ТВІЙ КОШИК:*\n\n"
        total = 0
        
        for item in cart_items:
            item_total = item['quantity'] * item['price']
            total += item_total
            
            text += f"• *{item['item_name']}*\n"
            text += f"  Кількість: {item['quantity']} ✕ {item['price']} грн = {item_total} грн\n"
            text += f"  [🆔 {item['id']}]\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"*РАЗОМ: {total} грн*\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        
        # Кнопки
        keyboard = [
            [
                InlineKeyboardButton("🛍️ Продовжити покупки", callback_data="menu"),
                InlineKeyboardButton("❌ Очистити", callback_data="cart_clear"),
            ],
            [
                InlineKeyboardButton("✅ Оформити замовлення", callback_data="order_start"),
            ]
        ]
        
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        logger.error(f"❌ Show cart error: {e}")
        await update.message.reply_text("❌ Помилка при завантаженні кошика")


# ============================================================================
# ОЧИСТКА КОШИКА
# ============================================================================

async def clear_cart(user_id: str, db_engine) -> bool:
    """Видали ВСІ товари з кошика"""
    try:
        session = get_session(db_engine)
        
        session.query(UserCart).filter(
            UserCart.user_id == user_id
        ).delete()
        
        session.commit()
        logger.info(f"✅ Cleared cart: {user_id}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Clear cart error: {e}")
        return False
    
    finally:
        session.close()


# ============================================================================
# INLINE КНОПКИ ДЛЯ ТОВАРІВ
# ============================================================================

def get_item_buttons(item_id: str) -> InlineKeyboardMarkup:
    """Кнопки для товару (додати в кошик, деталі)"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Додати", callback_data=f"add_item_{item_id}"),
            InlineKeyboardButton("❤️", callback_data=f"favorite_{item_id}"),
        ],
        [
            InlineKeyboardButton("📋 Деталі", callback_data=f"item_details_{item_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)