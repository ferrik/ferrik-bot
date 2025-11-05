# Персоналізація v2.0 - Інструкція Інтеграції

## 📋 Огляд

9 файлів для реалізації персоналізації в Ferrik Bot:

1. `models/user_profile.py` - Профіль користувача
2. `models/user_preferences.py` - Уподобання
3. `services/personalization_service.py` - Сервіс рекомендацій
4. `storage/user_repository.py` - DAO для користувачів
5. `handlers/user_profile_handler.py` - Обробник профілю
6. `utils/personalization_helpers.py` - Допоміжні функції
7. `scripts/migrate_v2.py` - Міграція БД
8. `tests/test_personalization.py` - Тести

---

## 🚀 Крок 1: Скопіювати файли

```bash
# 1. Models
cp models/user_profile.py ferrik-bot/models/
cp models/user_preferences.py ferrik-bot/models/

# 2. Services
cp services/personalization_service.py ferrik-bot/services/

# 3. Storage
cp storage/user_repository.py ferrik-bot/storage/

# 4. Handlers
cp handlers/user_profile_handler.py ferrik-bot/handlers/

# 5. Utils
cp utils/personalization_helpers.py ferrik-bot/utils/

# 6. Scripts
mkdir -p ferrik-bot/scripts
cp scripts/migrate_v2.py ferrik-bot/scripts/

# 7. Tests
cp tests/test_personalization.py ferrik-bot/tests/
```

---

## 💾 Крок 2: Міграція БД

```bash
cd ferrik-bot

# Запустити міграцію
python scripts/migrate_v2.py

# Вихід повинен бути:
# 🔄 Starting migration to v2.0...
# 📊 Creating user_profiles table...
# ⚙️ Creating user_preferences table...
# 📜 Creating order_history table...
# ✅ Migration v2.0 completed successfully!
```

---

## 🔧 Крок 3: Оновити main.py

```python
# main.py - додати в импорты

from storage.user_repository import UserRepository
from models.user_profile import UserProfile
from services.personalization_service import PersonalizationService
from handlers.user_profile_handler import router as profile_router

# При ініціалізації бота
async def on_startup():
    # Ініціалізувати БД
    UserRepository.init_db()
    logger.info("✅ Database initialized")

# Зареєструвати роутер для профілю
dp.include_router(profile_router)
```

---

## 🎯 Крок 4: Оновити handlers/start_handler.py

```python
from storage.user_repository import UserRepository
from models.user_profile import UserProfile
from services.personalization_service import PersonalizationService
from utils.personalization_helpers import format_user_greeting_message

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    # Отримати або створити профіль
    profile = UserRepository.get_profile(user_id)
    if not profile:
        profile = UserProfile(
            user_id=user_id,
            name=message.from_user.first_name or "User"
        )
        UserRepository.save_profile(profile)
    
    # ✨ НОВЕ: Персоналізоване привітання
    greeting = format_user_greeting_message(profile)
    
    await message.answer(greeting, parse_mode="HTML")
```

---

## 🛒 Крок 5: Оновити handlers/order_handler.py

```python
from storage.user_repository import UserRepository
from services.personalization_service import PersonalizationService

async def confirm_order(message: types.Message):
    user_id = message.from_user.id
    
    # ... існуюча логіка ...
    
    # ✨ НОВЕ: Обновити профіль після замовлення
    profile = UserRepository.get_profile(user_id)
    
    if profile:
        # Додати в історію
        UserRepository.update_order_history(user_id, {
            'order_id': order_id,
            'restaurant_id': restaurant_id,
            'items': [item.get('name') for item in order_items],
            'total_amount': total_amount
        })
        
        # Обновити профіль
        profile.add_order(
            amount=total_amount,
            dish_names=[item.get('name') for item in order_items],
            restaurant_id=restaurant_id
        )
        UserRepository.save_profile(profile)
        
        # Перевірити рівень вверх
        old_level = profile.level
        new_level = UserRepository.increment_level(user_id)
        
        if new_level:
            level_up_msg = PersonalizationService.get_level_up_message(profile, old_level)
            await message.answer(level_up_msg, parse_mode="HTML")
```

---

## 📝 Крок 6: Додати команду профілю

```python
# handlers/start_handler.py - додати кнопку в меню

keyboard = {
    'inline_keyboard': [
        [
            {'text': '📖 Меню', 'callback_data': 'show_menu'},
            {'text': '👤 Профіль', 'callback_data': 'show_profile'}
        ],
        # ... інші кнопки ...
    ]
}
```

---

## 🧪 Крок 7: Тестування

```bash
# 1. Перевірити імпорти
python -c "from models.user_profile import UserProfile; print('✅ OK')"
python -c "from services.personalization_service import PersonalizationService; print('✅ OK')"
python -c "from storage.user_repository import UserRepository; print('✅ OK')"

# 2. Запустити тести
pytest tests/test_personalization.py -v

# Очікуваний вихід:
# test_user_profile_creation PASSED
# test_user_profile_add_order PASSED
# test_user_level_update PASSED
# ... і т.д.

# 3. Локально запустити бота
python main.py

# 4. В Telegram:
# /start → побачити персоналізоване привітання
# /profile → переглянути профіль
```

---

## 🔄 Крок 8: Додати нагадування (опціонально)

```python
# services/scheduler_service.py - НОВИЙ ФАЙЛ

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from storage.user_repository import UserRepository
from services.personalization_service import PersonalizationService
from utils.personalization_helpers import format_reminder_message

scheduler = AsyncIOScheduler()

async def remind_inactive_users():
    """Send reminders to inactive users"""
    all_profiles = UserRepository.get_all_profiles()
    
    for profile in all_profiles:
        if PersonalizationService.should_remind_user(profile, days_threshold=2):
            reminder_msg = format_reminder_message(profile)
            
            try:
                await bot.send_message(profile.user_id, reminder_msg, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send reminder to {profile.user_id}: {e}")

# У main.py
scheduler.add_job(
    remind_inactive_users,
    trigger='interval',
    hours=24,
    start_date=datetime.now()
)
scheduler.start()
```

---

## 🚀 Крок 9: Deploy на Render

```bash
# 1. Git commit
git add .
git commit -m "feat: Add personalization v2.0 with user profiles"

# 2. Push
git push origin main

# 3. Render автоматично запустить GitHub Actions
# Перевірити у Render Dashboard → Events

# 4. Перевірити логи
# Render Dashboard → Logs → див. "✅ Migration v2.0 completed"
```

---

## 📊 БД Структура

```sql
-- user_profiles
user_id          (Primary Key)
name             (Telegram ім'я)
total_orders     (кількість замовлень)
total_spent      (витрачено грн)
points           (бонус-бали)
level            (novice/gourmet/foodie/vip)
favorite_dishes  (JSON массив)
last_order_date  (дата останнього замовлення)

-- user_preferences
user_id          (Primary Key)
favorite_categories
dietary_restrictions
push_notifications
preferred_delivery_method

-- order_history
order_id         (Primary Key)
user_id          (Foreign Key)
items_ordered    (JSON)
total_amount
timestamp
```

---

## 🎯 Користувач Буде Бачити

### /start
```
👋 Привіт, Володимир!

🍽️ Ти вже Гурман! (+20 бонус-балів)

Твої замовлення:
📊 Всього: 5
💰 Витрачено: 1 350 грн
🎁 Бонус-балів: 234
```

### /profile
```
👤 МІЙ ПРОФІЛЬ

Ім'я: Володимир
Рівень: 🍽️ Гурман
Бонус-бали: 🎁 234

📊 Статистика:
• Замовлень: 5
• Витрачено: 1 350 грн
• Середній чек: 270 грн

⭐ Твої улюблені:
1. Піца Маргарита
2. Салат Цезар
```

---

## 🐛 Troubleshooting

### Помилка: "No module named 'models'"
```bash
# Переконайтеся що __init__.py існує
touch ferrik-bot/models/__init__.py
touch ferrik-bot/services/__init__.py
touch ferrik-bot/storage/__init__.py
touch ferrik-bot/utils/__init__.py
```

### Помилка: "Database is locked"
```bash
# Закрити всі з'єднання
pkill -f "python main.py"

# Або видалити локальний db
rm ferrik_bot.db

# Запустити міграцію знову
python scripts/migrate_v2.py
```

### Профіль не зберігається
```python
# Переконайтеся що UserRepository.init_db() викликається
# У main.py при старті

async def on_startup():
    from storage.user_repository import UserRepository
    UserRepository.init_db()
```

---

## 📞 Support

Якщо щось не працює:

1. Перевірити логи: `tail -f bot.log`
2. Запустити тести: `pytest tests/test_personalization.py -v`
3. Перевірити БД: `sqlite3 ferrik_bot.db ".tables"`

---

## ✅ Checklist

- [ ] Скопіювати всі 9 файлів
- [ ] Запустити міграцію БД
- [ ] Оновити main.py з імпортами
- [ ] Оновити handlers/start_handler.py
- [ ] Оновити handlers/order_handler.py
- [ ] Запустити тести
- [ ] Локально протестувати
- [ ] Git commit та push
- [ ] Deploy на Render

---

**Ready to launch personalization! 🚀**