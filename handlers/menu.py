"""
Вдосконалена система меню з прямим додаванням у кошик
"""

import logging
from services.sheets import get_menu_from_sheet, get_menu_by_category, get_item_by_id
from services.telegram import tg_send_message, tg_answer_callback, tg_send_photo
from models.user import get_cart, set_cart, get_state
from handlers.cart import add_item_to_cart

logger = logging.getLogger('ferrik')


def show_menu_with_cart_buttons(chat_id, category=None, page=1):
    """
    Показує меню з кнопками для швидкого додавання в кошик
    
    Args:
        chat_id: ID чату
        category: Фільтр за категорією (опціонально)
        page: Номер сторінки (для пагінації)
    """
    try:
        # Отримуємо меню
        if category:
            menu = get_menu_from_sheet()
            menu = [item for item in menu if item.get('Категорія') == category]
        else:
            menu = get_menu_from_sheet()
        
        if not menu:
            tg_send_message(chat_id, "❌ Меню порожнє або недоступне")
            return
        
        # Пагінація (6 страв на сторінку для зручності)
        ITEMS_PER_PAGE = 6
        total_pages = (len(menu) - 1) // ITEMS_PER_PAGE + 1
        start_idx = (page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_items = menu[start_idx:end_idx]
        
        # Заголовок
        if category:
            header = f"🍽 <b>Категорія: {category}</b>\n"
        else:
            header = "🍽 <b>Наше меню</b>\n"
        
        header += f"Сторінка {page}/{total_pages}\n\n"
        
        # Показуємо кожну страву окремим повідомленням з кнопкою
        tg_send_message(chat_id, header)
        
        for item in page_items:
            send_menu_item_with_button(chat_id, item)
        
        # Навігаційні кнопки внизу
        navigation = build_navigation_keyboard(category, page, total_pages)
        tg_send_message(chat_id, "👆 Натисніть ➕ щоб додати страву в кошик", reply_markup=navigation)
        
    except Exception as e:
        logger.error(f"Error showing menu: {e}", exc_info=True)
        tg_send_message(chat_id, "Помилка завантаження меню")


def send_menu_item_with_button(chat_id, item):
    """
    Відправляє одну страву з кнопкою додавання
    
    Args:
        chat_id: ID чату
        item: Дані страви з Google Sheets
    """
    try:
        item_id = item.get('ID')
        name = item.get('Страви', 'N/A')
        desc = item.get('Опис', '')
        price = item.get('Ціна', 0)
        rating = item.get('Рейтинг', '')
        cook_time = item.get('Час_приготування', '')
        allergens = item.get('Аллергени', '')
        photo_url = item.get('Фото URL', '').strip()
        
        # Формуємо текст
        text = f"<b>{name}</b>\n"
        
        if desc:
            text += f"📝 {desc}\n"
        
        text += f"💰 <b>{price} грн</b>\n"
        
        if rating:
            stars = '⭐' * int(float(rating)) if rating else ''
            text += f"{stars} {rating}/5\n"
        
        if cook_time:
            text += f"⏱ Час приготування: {cook_time} хв\n"
        
        if allergens:
            text += f"⚠️ Алергени: {allergens}\n"
        
        # Inline кнопки
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "➕ Додати в кошик", "callback_data": f"add_to_cart_{item_id}"},
                ],
                [
                    {"text": "➖ 1 ➕", "callback_data": f"quick_qty_{item_id}"},
                    {"text": "🔍 Детальніше", "callback_data": f"item_details_{item_id}"}
                ]
            ]
        }
        
        # Відправляємо з фото або без
        if photo_url and photo_url.startswith('http'):
            tg_send_photo(chat_id, photo_url, text, reply_markup=keyboard)
        else:
            tg_send_message(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error sending menu item: {e}", exc_info=True)


def build_navigation_keyboard(category, current_page, total_pages):
    """Будує клавіатуру навігації по меню"""
    buttons = []
    
    # Кнопки пагінації
    nav_row = []
    if current_page > 1:
        callback = f"menu_page_{category or 'all'}_{current_page - 1}"
        nav_row.append({"text": "⬅️ Назад", "callback_data": callback})
    
    nav_row.append({"text": f"{current_page}/{total_pages}", "callback_data": "noop"})
    
    if current_page < total_pages:
        callback = f"menu_page_{category or 'all'}_{current_page + 1}"
        nav_row.append({"text": "Вперед ➡️", "callback_data": callback})
    
    buttons.append(nav_row)
    
    # Кнопка категорій
    buttons.append([
        {"text": "📂 Категорії", "callback_data": "show_categories"},
        {"text": "🛒 Кошик", "callback_data": "show_cart"}
    ])
    
    return {"inline_keyboard": buttons}


def show_categories(chat_id):
    """Показує список категорій для вибору"""
    try:
        menu = get_menu_from_sheet()
        
        # Отримуємо унікальні категорії
        categories = {}
        for item in menu:
            cat = item.get('Категорія', 'Інше')
            categories[cat] = categories.get(cat, 0) + 1
        
        # Формуємо повідомлення
        text = "📂 <b>Категорії страв:</b>\n\n"
        
        # Кнопки категорій
        keyboard = {"inline_keyboard": []}
        
        for category, count in sorted(categories.items()):
            text += f"• {category}: {count} позицій\n"
            keyboard["inline_keyboard"].append([
                {"text": f"{category} ({count})", "callback_data": f"category_{category}"}
            ])
        
        # Додаємо кнопку "Все меню"
        keyboard["inline_keyboard"].append([
            {"text": "🍽 Все меню", "callback_data": "menu_page_all_1"}
        ])
        
        tg_send_message(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing categories: {e}", exc_info=True)


def handle_add_to_cart_callback(chat_id, callback_data, callback_id):
    """
    Обробляє додавання товару в кошик через callback
    
    Args:
        chat_id: ID чату
        callback_data: Дані callback (формат: add_to_cart_{item_id})
        callback_id: ID callback для відповіді
    """
    try:
        # Витягуємо ID товару
        item_id = callback_data.replace('add_to_cart_', '')
        
        # Отримуємо інформацію про товар
        item = get_item_by_id(item_id)
        
        if not item:
            tg_answer_callback(callback_id, "❌ Товар не знайдено", show_alert=True)
            return
        
        # Додаємо в кошик (quantity=1 за замовчуванням)
        success = add_item_to_cart(chat_id, item_id, quantity=1)
        
        if success:
            item_name = item.get('Страви', 'Товар')
            tg_answer_callback(callback_id, f"✅ {item_name} додано!")
            
            # Показуємо швидкі дії
            show_quick_actions(chat_id, item_id)
        else:
            tg_answer_callback(callback_id, "❌ Помилка додавання", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error handling add to cart: {e}", exc_info=True)
        tg_answer_callback(callback_id, "❌ Помилка", show_alert=True)


def show_quick_actions(chat_id, last_item_id):
    """
    Показує швидкі дії після додавання товару
    
    Args:
        chat_id: ID чату
        last_item_id: ID останнього доданого товару
    """
    try:
        cart = get_cart(chat_id)
        items_count = sum(item.get('qty', 0) for item in cart.get('items', []))
        total = sum(
            float(item.get('price', 0)) * int(item.get('qty', 0)) 
            for item in cart.get('items', [])
        )
        
        text = f"🛒 У кошику: {items_count} поз., сума: {total:.0f} грн\n\n"
        text += "Що далі?"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "➕ Додати ще одну", "callback_data": f"add_to_cart_{last_item_id}"},
                ],
                [
                    {"text": "🍽 Продовжити покупки", "callback_data": "continue_shopping"},
                    {"text": "🛒 Кошик", "callback_data": "show_cart"}
                ],
                [
                    {"text": "✅ Оформити замовлення", "callback_data": "checkout"}
                ]
            ]
        }
        
        tg_send_message(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing quick actions: {e}", exc_info=True)


def handle_quick_quantity_selector(chat_id, callback_data, callback_id):
    """
    Показує селектор кількості для швидкого додавання
    
    Args:
        chat_id: ID чату
        callback_data: Дані callback (формат: quick_qty_{item_id})
        callback_id: ID callback
    """
    try:
        item_id = callback_data.replace('quick_qty_', '')
        item = get_item_by_id(item_id)
        
        if not item:
            tg_answer_callback(callback_id, "❌ Товар не знайдено", show_alert=True)
            return
        
        item_name = item.get('Страви', 'Товар')
        price = item.get('Ціна', 0)
        
        text = f"<b>{item_name}</b>\n💰 {price} грн/шт\n\nОберіть кількість:"
        
        # Кнопки з різною кількістю
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "1 шт", "callback_data": f"add_qty_{item_id}_1"},
                    {"text": "2 шт", "callback_data": f"add_qty_{item_id}_2"},
                    {"text": "3 шт", "callback_data": f"add_qty_{item_id}_3"}
                ],
                [
                    {"text": "4 шт", "callback_data": f"add_qty_{item_id}_4"},
                    {"text": "5 шт", "callback_data": f"add_qty_{item_id}_5"},
                    {"text": "10 шт", "callback_data": f"add_qty_{item_id}_10"}
                ],
                [
                    {"text": "❌ Скасувати", "callback_data": "cancel_qty"}
                ]
            ]
        }
        
        tg_answer_callback(callback_id, "Оберіть кількість")
        tg_send_message(chat_id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing quantity selector: {e}", exc_info=True)


def handle_add_quantity_callback(chat_id, callback_data, callback_id):
    """
    Додає товар з вказаною кількістю
    
    Args:
        callback_data: Формат add_qty_{item_id}_{quantity}
    """
    try:
        parts = callback_data.split('_')
        item_id = parts[2]
        quantity = int(parts[3])
        
        item = get_item_by_id(item_id)
        if not item:
            tg_answer_callback(callback_id, "❌ Товар не знайдено", show_alert=True)
            return
        
        # Додаємо в кошик
        success = add_item_to_cart(chat_id, item_id, quantity=quantity)
        
        if success:
            item_name = item.get('Страви')
            price = item.get('Ціна', 0)
            total = price * quantity
            
            tg_answer_callback(
                callback_id, 
                f"✅ {item_name} x{quantity} = {total:.0f} грн"
            )
            show_quick_actions(chat_id, item_id)
        else:
            tg_answer_callback(callback_id, "❌ Помилка", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error adding quantity: {e}", exc_info=True)
        tg_answer_callback(callback_id, "❌ Помилка", show_alert=True)


def show_item_details(chat_id, item_id, callback_id=None):
    """
    Показує детальну інформацію про страву
    
    Args:
        chat_id: ID чату
        item_id: ID страви
        callback_id: ID callback (опціонально)
    """
    try:
        item = get_item_by_id(item_id)
        
        if not item:
            if callback_id:
                tg_answer_callback(callback_id, "❌ Товар не знайдено", show_alert=True)
            return
        
        # Детальна інформація
        text = f"<b>{item.get('Страви', 'N/A')}</b>\n\n"
        
        desc = item.get('Опис', '')
        if desc:
            text += f"📝 <b>Опис:</b>\n{desc}\n\n"
        
        text += f"💰 <b>Ціна:</b> {item.get('Ціна', 0)} грн\n"
        
        category = item.get('Категорія', '')
        if category:
            text += f"🍽 <b>Категорія:</b> {category}\n"
        
        restaurant = item.get('Ресторан', '')
        if restaurant:
            text += f"🏪 <b>Ресторан:</b> {restaurant}\n"
        
        cook_time = item.get('Час_приготування', '')
        if cook_time:
            text += f"⏱ <b>Приготування:</b> {cook_time} хв\n"
        
        delivery_time = item.get('Час Доставки (хв)', '')
        if delivery_time:
            text += f"🚚 <b>Доставка:</b> {delivery_time} хв\n"
        
        allergens = item.get('Аллергени', '')
        if allergens:
            text += f"⚠️ <b>Алергени:</b> {allergens}\n"
        
        rating = item.get('Рейтинг', '')
        if rating:
            stars = '⭐' * int(float(rating))
            text += f"\n{stars} <b>Рейтинг:</b> {rating}/5\n"
        
        # Кнопки
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "➕ Додати 1 шт", "callback_data": f"add_to_cart_{item_id}"},
                    {"text": "➕ Вибрати кількість", "callback_data": f"quick_qty_{item_id}"}
                ],
                [
                    {"text": "⬅️ Назад до меню", "callback_data": "menu_page_all_1"}
                ]
            ]
        }
        
        # Фото
        photo_url = item.get('Фото URL', '').strip()
        if photo_url and photo_url.startswith('http'):
            tg_send_photo(chat_id, photo_url, text, reply_markup=keyboard)
        else:
            tg_send_message(chat_id, text, reply_markup=keyboard)
        
        if callback_id:
            tg_answer_callback(callback_id)
        
    except Exception as e:
        logger.error(f"Error showing item details: {e}", exc_info=True)


# Експортовані функції для main.py
__all__ = [
    'show_menu_with_cart_buttons',
    'show_categories',
    'handle_add_to_cart_callback',
    'handle_quick_quantity_selector',
    'handle_add_quantity_callback',
    'show_item_details'
]
