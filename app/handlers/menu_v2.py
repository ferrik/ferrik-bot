"""
🍔 MENU V2 - Обробка каталогу та категорій
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, Application

from app.services.sheets_service import sheets_service

logger = logging.getLogger(__name__)

# Константи для категорій (щоб було красиво)
CATEGORY_IMAGES = {
    "Піца": "🍕", 
    "Бургери": "🍔", 
    "Супи": "🍜", 
    "Салати": "🥗", 
    "Напої": "🥤", 
    "Десерти": "🍰",
    "Мексиканська": "🌮"
}

async def classic_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує список категорій (Класичне меню)"""
    query = update.callback_query
    await query.answer()
    
    # Отримуємо унікальні категорії з Google Sheets
    categories = set()
    if sheets_service.is_connected():
        items = sheets_service.get_menu_items()
        for item in items:
            cat = item.get('Категорія')
            if cat:
                categories.add(cat)
    else:
        # Fallback якщо база недоступна
        categories = {"Піца", "Бургери", "Напої", "Снеки"}

    message = (
        "📋 **МЕНЮ РЕСТОРАНУ**\n\n"
        "Обери категорію, щоб переглянути страви:"
    )
    
    # Формуємо кнопки категорій (по 2 в ряд)
    keyboard = []
    row = []
    for cat in sorted(list(categories)):
        emoji = CATEGORY_IMAGES.get(cat, "🍽")
        btn = InlineKeyboardButton(f"{emoji} {cat}", callback_data=f"v2_category_{cat}")
        row.append(btn)
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    # Навігація
    keyboard.append([
        InlineKeyboardButton("🛒 Кошик", callback_data="v2_view_cart"),
        InlineKeyboardButton("🔙 Назад", callback_data="v2_back_to_start")
    ])

    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def category_items_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує товари в обраній категорії"""
    query = update.callback_query
    data = query.data
    category_name = data.replace("v2_category_", "")
    
    await query.answer(f"Відкриваю {category_name}...")
    
    # Отримуємо товари
    items = []
    if sheets_service.is_connected():
        items = sheets_service.get_menu_by_category(category_name)
    
    if not items:
        await query.edit_message_text(
            f"😔 У категорії **{category_name}** поки немає страв.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="v2_classic_menu")]])
        )
        return

    # Показуємо товари списком
    # (У V2 краще робити це каруселлю або окремими повідомленнями, 
    # але для старту зробимо компактний список з кнопками)
    
    emoji = CATEGORY_IMAGES.get(category_name, "🍽")
    message = f"{emoji} **{category_name.upper()}**\n\n"
    
    keyboard = []
    
    for item in items:
        # Пропускаємо неактивні
        if str(item.get('Активний')).upper() != 'TRUE':
            continue
            
        name = item.get('Страви', 'Страва')
        price = item.get('Ціна', 0)
        desc = item.get('Опис', '')
        item_id = item.get('ID')
        
        # Додаємо опис товару в текст
        message += f"▪️ **{name}** — {price} грн\n"
        if desc:
            message += f"_{desc}_\n"
        message += "\n"
        
        # Кнопка додавання
        keyboard.append([
            InlineKeyboardButton(f"➕ В кошик: {name}", callback_data=f"v2_add_cart_{item_id}")
        ])
        
    keyboard.append([
        InlineKeyboardButton("🔙 До категорій", callback_data="v2_classic_menu"),
        InlineKeyboardButton("🏠 Головна", callback_data="v2_back_to_start")
    ])

    # Telegram має ліміт на довжину повідомлення. Якщо меню велике, треба розбивати.
    # Тут ми обрізаємо, якщо занадто довге.
    if len(message) > 4000:
        message = message[:4000] + "\n...(список скорочено)..."

    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def register_menu_v2_handlers(application: Application):
    """Реєстрація хендлерів меню"""
    # Класичне меню
    application.add_handler(CallbackQueryHandler(classic_menu_callback, pattern="^v2_classic_menu$"))
    
    # Вибір категорії (динамічний патерн)
    application.add_handler(CallbackQueryHandler(category_items_callback, pattern="^v2_category_"))
    
    logger.info("✅ Menu V2 handlers registered")
