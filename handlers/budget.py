import logging
from services.sheets import get_menu_from_sheet
from services.telegram import tg_send_message, tg_send_photo
from models.user import set_state

logger = logging.getLogger("ferrik.budget")

def start_budget_search(chat_id):
    """Починає пошук страв за бюджетом"""
    try:
        message = "💰 Введіть ваш бюджет (максимальну суму в гривнях):\n\n"
        message += "Наприклад: <code>300</code> або <code>150</code>"
        
        tg_send_message(chat_id, message)
        set_state(chat_id, "awaiting_budget")
        
    except Exception as e:
        logger.error(f"Error starting budget search for {chat_id}: {e}")
        tg_send_message(chat_id, "Помилка при запуску бюджетного пошуку.")

def handle_budget_input(chat_id, budget_text):
    """Обробляє введений бюджет та показує підходящі страви"""
    try:
        # Парсимо бюджет
        budget_str = budget_text.strip().replace(',', '.').replace(' ', '')
        budget = float(budget_str)
        
        if budget <= 0:
            tg_send_message(chat_id, "Будь ласка, введіть позитивне число.")
            return False
            
        if budget > 10000:
            tg_send_message(chat_id, "Це дуже великий бюджет! Введіть реальну суму.")
            return False
        
        # Отримуємо меню
        menu_items = get_menu_from_sheet()
        if not menu_items:
            tg_send_message(chat_id, "Вибачте, меню тимчасово недоступне.")
            return False
        
        # Знаходимо підходящі страви
        suitable_items = [
            item for item in menu_items 
            if item.get('active', True) and item.get('price', 0) <= budget
        ]
        
        if not suitable_items:
            min_price = min(
                item.get('price', 999) for item in menu_items 
                if item.get('active', True)
            )
            message = f"😔 На жаль, немає страв у бюджеті до {budget:.0f} грн.\n"
            message += f"Найдешевша позиція: {min_price:.0f} грн"
            tg_send_message(chat_id, message)
            return False
        
        # Сортуємо за рейтингом, потім за ціною
        suitable_items.sort(key=lambda x: (
            -float(x.get('rating', 0)), 
            x.get('price', 0)
        ))
        
        # Показуємо результати
        show_budget_results(chat_id, budget, suitable_items)
        
        # Скидаємо стан
        set_state(chat_id, "normal")
        return True
        
    except ValueError:
        tg_send_message(chat_id, "Будь ласка, введіть число (наприклад: 250).")
        return False
    except Exception as e:
        logger.error(f"Error handling budget input for {chat_id}: {e}")
        tg_send_message(chat_id, "Помилка при обробці бюджету.")
        return False

def show_budget_results(chat_id, budget, items):
    """Показує результати пошуку за бюджетом"""
    try:
        # Заголовок
        header = f"💰 Знайшов {len(items)} страв у бюджеті до {budget:.0f} грн:\n\n"
        tg_send_message(chat_id, header)
        
        # Показуємо топ-10 результатів
        for item in items[:10]:
            price = item.get('price', 0)
            name = item.get('name', 'N/A')
            description = item.get('description', '')
            rating = item.get('rating')
            category = item.get('category', '')
            
            # Формуємо текст
            text = f"<b>{name}</b>\n"
            text += f"💰 <b>Ціна:</b> {price:.0f} грн"
            
            if rating:
                stars = '⭐' * int(float(rating))
                text += f"\n{stars} <b>Рейтинг:</b> {rating}/5"
            
            if category:
                text += f"\n🍽️ <b>Категорія:</b> {category}"
                
            if description:
                # Обрізаємо опис якщо довгий
                desc = description[:100] + "..." if len(description) > 100 else description
                text += f"\n📝 {desc}"
            
            # Кнопка додавання
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"➕ Додати ({price:.0f} грн)", 
                      "callback_data": f"add_item_{item.get('ID')}"}]
                ]
            }
            
            # Відправляємо з фото якщо є
            photo_url = item.get('photo', '').strip()
            if photo_url:
                tg_send_photo(chat_id, photo_url, text, reply_markup=keyboard)
            else:
                tg_send_message(chat_id, text, reply_markup=keyboard)
        
        # Підсумок
        if len(items) > 10:
            footer = f"\n📊 Показано перші 10 з {len(items)} знайдених страв."
            tg_send_message(chat_id, footer)
        
        # Комбінації страв якщо бюджет дозволяє
        suggest_combinations(chat_id, budget, items)
        
    except Exception as e:
        logger.error(f"Error showing budget results: {e}")
        tg_send_message(chat_id, "Помилка при відображенні результатів.")

def suggest_combinations(chat_id, budget, items):
    """Пропонує комбінації страв в рамках бюджету"""
    try:
        # Шукаємо цікаві комбінації
        combinations = []
        
        # Основна страва + закуска/салат
        main_dishes = [item for item in items if 'піца' in item.get('name', '').lower() or 'суші' in item.get('name', '').lower()]
        salads = [item for item in items if 'салат' in item.get('category', '').lower()]
        
        for main in main_dishes[:3]:
            for salad in salads[:2]:
                combo_price = main.get('price', 0) + salad.get('price', 0)
                if combo_price <= budget:
                    combinations.append({
                        'items': [main, salad],
                        'total': combo_price,
                        'savings': budget - combo_price
                    })
        
        if combinations:
            # Сортуємо за економією (більша економія = краща пропозиція)
            combinations.sort(key=lambda x: -x['savings'])
            
            combo_text = "🍽️ <b>Рекомендовані комбінації:</b>\n\n"
            
            for i, combo in enumerate(combinations[:2], 1):
                items_names = [item.get('name') for item in combo['items']]
                combo_text += f"{i}. {' + '.join(items_names)}\n"
                combo_text += f"   💰 {combo['total']:.0f} грн "
                combo_text += f"(залишиться {combo['savings']:.0f} грн)\n\n"
            
            tg_send_message(chat_id, combo_text)
            
    except Exception as e:
        logger.error(f"Error suggesting combinations: {e}")

def get_price_ranges():
    """Отримує популярні цінові діапазони"""
    return {
        "🍔 Бюджетно": "до 150 грн",
        "🍕 Стандарт": "150-300 грн", 
        "🍣 Преміум": "300-500 грн",
        "🥂 Делюкс": "500+ грн"
    }

def show_price_ranges(chat_id):
    """Показує популярні цінові діапазони"""
    try:
        message = "💰 <b>Популярні бюджети:</b>\n\n"
        
        ranges = get_price_ranges()
        keyboard = {"inline_keyboard": []}
        
        for emoji_name, price_range in ranges.items():
            message += f"{emoji_name}: {price_range}\n"
            # Витягуємо числове значення для callback
            if "до 150" in price_range:
                callback_data = "budget_range_150"
            elif "150-300" in price_range:
                callback_data = "budget_range_300"
            elif "300-500" in price_range:
                callback_data = "budget_range_500"
            else:
                callback_data = "budget_range_1000"
                
            keyboard["inline_keyboard"].append([
                {"text": emoji_name, "callback_data": callback_data}
            ])
        
        message += "\nАбо введіть свою суму:"
        keyboard["inline_keyboard"].append([
            {"text": "✏️ Ввести свій бюджет", "callback_data": "custom_budget"}
        ])
        
        tg_send_message(chat_id, message, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing price ranges: {e}")
        tg_send_message(chat_id, "Помилка при відображенні цінових діапазонів.")

def handle_budget_range(chat_id, range_callback, callback_id):
    """Обробляє вибір готового цінового діапазону"""
    try:
        from services.telegram import tg_answer_callback
        
        range_map = {
            "budget_range_150": 150,
            "budget_range_300": 300,
            "budget_range_500": 500,
            "budget_range_1000": 1000
        }
        
        budget = range_map.get(range_callback)
        if budget:
            tg_answer_callback(callback_id, f"Бюджет {budget} грн обрано!")
            handle_budget_input(chat_id, str(budget))
        else:
            tg_answer_callback(callback_id, "Невідомий діапазон")
            
    except Exception as e:
        logger.error(f"Error handling budget range: {e}")
        tg_answer_callback(callback_id, "Помилка при виборі діапазону")