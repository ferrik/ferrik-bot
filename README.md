# 🤖 Ferrik Bot 2.0 — Персональний Смаковий Супутник

> Telegram-бот нового покоління для замовлення їжі з AI-рекомендаціями, гейміфікацією та персоналізацією

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Зміст

- [Про проєкт](#про-проєкт)
- [Ключові фічі](#ключові-фічі)
- [Архітектура](#архітектура)
- [Встановлення](#встановлення)
- [Конфігурація](#конфігурація)
- [Використання](#використання)
- [API та інтеграції](#api-та-інтеграції)
- [База даних](#база-даних)
- [Розробка](#розробка)
- [Deployment](#deployment)
- [Тестування](#тестування)
- [Roadmap](#roadmap)
- [Ліцензія](#ліцензія)

---

## 🎯 Про проєкт

**Ferrik Bot** — це не просто бот для замовлення їжі. Це персональний смаковий супутник, який:

- 🧠 **Думає:** AI аналізує твої вподобання та пропонує найкраще
- 🎭 **Розуміє:** Рекомендації на основі настрою та часу доби
- 🎮 **Захоплює:** Геймфікація з бейджами, рівнями та челенджами
- 🤝 **Винагороджує:** Реферальна програма та бонусна система
- 💬 **Спілкується:** Дружні повідомлення, емодзі та персоналізація

---

## ✨ Ключові фічі

### 🍽️ Основний функціонал

- **Інтелектуальне меню** з категоріями, фільтрами та красивим форматуванням
- **Пошук по меню** з NLP — знаходить навіть при помилках у запиті
- **Кошик покупок** з персистентним зберіганням
- **Оформлення замовлення** з валідацією даних
- **Трекінг замовлень** в реальному часі з push-сповіщеннями

### 🤖 AI та персоналізація

- **Рекомендації на основі настрою** — обирай емоцію, отримуй ідеальну страву
- **Часові рекомендації** — різні пропозиції для сніданку, обіду, вечері
- **Історія замовлень** — бот пам'ятає твої улюблені страви
- **Адаптивні промо** — персональні знижки на основі поведінки

### 🎮 Гейміфікація

- **Система рівнів** (1-10) з титулами та прогресом
- **16 унікальних бейджів** за різні досягнення
- **Тижневі челенджі** з винагородами
- **Бонусна система** — 1 бал за 10 грн витрат
- **Онбординг-квест** для нових користувачів

### 🤝 Соціальні фічі

- **Реферальна програма** — запрошуй друзів, отримуй бонуси
- **Система відгуків** з рейтингами (1-5 зірок)
- **Групові замовлення** (планується)
- **Шерінг у соцмережах**

### 🛡️ Безпека та якість

- **Валідація всіх вводів** (телефон, адреса, ціни)
- **Rate limiting** для захисту від спаму
- **Обробка помилок** з дружніми повідомленнями
- **Логування** всіх важливих подій
- **Кешування** для швидкодії

---

## 🏗️ Архітектура

```
ferrik-bot/
│
├── 📁 app/                     # Головний пакет
│   ├── config/
│   │   └── settings.py         # Налаштування
│   ├── services/
│   │   └── session.py          # Менеджер сесій
│   ├── utils/
│   │   └── validators.py       # Валідатори
│   ├── handlers/               # Обробники команд
│   └── models/                 # ORM моделі
│
├── 📁 services/                # Зовнішні сервіси
│   ├── telegram.py             # Telegram API
│   ├── sheets.py               # Google Sheets API
│   └── database.py             # База даних
│
├── 📁 modules/                 # Модулі 2.0
│   ├── welcome_messages.py     # Привітання
│   ├── onboarding_quest.py     # Онбординг
│   ├── menu_formatter.py       # Форматування меню
│   ├── mood_recommender.py     # AI-рекомендації
│   ├── gamification.py         # Геймфікація
│   ├── referral.py             # Реферали
│   ├── friendly_errors.py      # Дружні помилки
│   ├── menu_search.py          # Пошук
│   └── order_tracking.py       # Трекінг
│
├── 📁 migrations/              # SQL міграції
│   └── schema_v2.sql           # Повна схема БД
│
├── 📁 tests/                   # Тести
│
├── 📄 main.py                  # Точка входу
├── 📄 requirements.txt         # Залежності
├── 📄 .env.example             # Приклад конфігурації
├── 📄 README.md                # Документація
└── 📄 bot.db                   # SQLite БД

```

### Потік даних

```
User (Telegram) 
    ↓
Webhook (Flask)
    ↓
Message Handler
    ↓
┌─────────────────────────────┐
│   Business Logic Layer      │
│  - Session Manager          │
│  - Validators               │
│  - Formatters               │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│   Data Layer                │
│  - SQLite Database          │
│  - Google Sheets API        │
│  - Cache (Redis)            │
└─────────────────────────────┘
    ↓
Response (Telegram)
```

---

## 🚀 Встановлення

### Передумови

- Python 3.11+
- Git
- Telegram Bot Token ([@BotFather](https://t.me/botfather))
- Google Sheets API credentials

### Крок 1: Клонування репозиторію

```bash
git clone https://github.com/ferrik/ferrik-bot.git
cd ferrik-bot
```

### Крок 2: Створення віртуального середовища

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows
```

### Крок 3: Встановлення залежностей

```bash
pip install -r requirements.txt
```

### Крок 4: Конфігурація

```bash
cp .env.example .env
# Відредагуй .env файл своїми даними
```

### Крок 5: Ініціалізація бази даних

```bash
python -c "from services.database import Database; Database('bot.db').init_schema()"
```

### Крок 6: Запуск

```bash
python main.py
```

---

## ⚙️ Конфігурація

### Файл `.env`

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# Database
DATABASE_PATH=bot.db

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id

# Server
PORT=5000
DEBUG=False

# Features
ENABLE_CACHE=True
CACHE_TTL=300
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_PERIOD=60

# Admin
ADMIN_USER_IDS=123456789,987654321
```

### Google Sheets налаштування

1. Створи Google Sheets з листами:
   - `Меню` (ID, Категорія, Страви, Опис, Ціна, ...)
   - `Замовлення` (ID, User ID, Товари, Сума, ...)
   - `Промокоди` (Код, Знижка, ...)
   
2. Отримай credentials.json:
   ```bash
   # Перейди: https://console.cloud.google.com
   # Створи проєкт → Enable Google Sheets API
   # Credentials → Service Account → Create Key (JSON)
   ```

3. Додай Service Account email у Google Sheets (Sharing)

---

## 💻 Використання

### Основні команди бота

- `/start` — Почати роботу з ботом
- `/menu` — Переглянути меню
- `/cart` — Відкрити кошик
- `/profile` — Мій профіль та досягнення
- `/referral` — Реферальна програма
- `/support` — Підтримка та FAQ
- `/help` — Довідка

### Приклади використання

#### 1. Пошук страви

```
Користувач: щось вегетаріанське і недороге
Бот: 🔍 Знайдено 5 результатів...
     1. 🥗 Овочевий салат — 85 грн
     2. 🍜 Крем-суп з броколі — 95 грн
     ...
```

#### 2. Рекомендації за настроєм

```
Користувач: /recommend
Бот: 🎭 Як ти себе почуваєш сьогодні?
     [😊 Щасливий] [💪 Енергійний] [😌 Спокійно]
     
Користувач: [натискає 💪 Енергійний]
Бот: 💪 Для енергії рекомендую:
     1. 🥩 Стейк Рібай — 450 грн
     2. 🍔 Бургер XL — 185 грн
     ...
```

#### 3. Реферальна програма

```
Користувач: /referral
Бот: 🎁 Твій реферальний код: FERRIK_A1B2C3
     
     Запросив друзів: 3
     Заробив балів: 250
     Активна знижка: 15%
     
     [📤 Поділитись] [📊 Статистика]
```

---

## 🔌 API та інтеграції

### Telegram Bot API

```python
from services.telegram import TelegramAPI

telegram = TelegramAPI(bot_token)

# Відправити повідомлення
telegram.send_message(user_id, "Привіт!", reply_markup={...})

# Відповісти на callback
telegram.answer_callback_query(callback_id, text="Готово!")

# Відправити фото
telegram.send_photo(user_id, photo_url, caption="...")
```

### Google Sheets API

```python
from services.sheets import SheetsAPI

sheets = SheetsAPI()

# Отримати меню
menu = sheets.get_menu()

# Зберегти замовлення
sheets.save_order(order_data)

# Отримати промокоди
promos = sheets.get_promo_codes()
```

### Database API

```python
from services.database import Database

db = Database('bot.db')

# Користувач
user = db.get_user(user_id)
db.update_user_phone(user_id, phone)

# Замовлення
order_id = db.save_order(user_id, order_data)
orders = db.get_user_orders(user_id)

# Бейджі
db.award_badge(user_id, 'first_order')
badges = db.get_user_badges(user_id)
```

---

## 🗄️ База даних

### Основні таблиці

#### `users`
Користувачі з профілями, XP, балами

#### `orders`
Замовлення з повною історією

#### `user_badges`
Досягнення користувачів

#### `referrals`
Реферальна мережа

#### `reviews`
Відгуки та рейтинги

#### `promo_codes`
Промокоди та знижки

### Міграції

```bash
# Застосувати нову міграцію
python manage.py migrate migrations/002_add_reviews.sql

# Відкотити міграцію
python manage.py rollback
```

---

## 🛠️ Розробка

### Структура модулів

Кожен модуль відповідає за певну фічу:

```python
# welcome_messages.py — Привітання
WelcomeMessages.get_greeting_text(user_name, is_new=True)

# mood_recommender.py — Рекомендації
recommendations = MoodRecommender.recommend(items, mood='happy')

# gamification.py — Геймфікація
GamificationManager.award_badge(user_id, BadgeType.FIRST_ORDER)

# menu_search.py — Пошук
results = MenuSearch.search(query, items, limit=10)
```

### Додавання нової фічі

1. Створи модуль у `modules/`
2. Додай обробник у `main.py`
3. Оновити схему БД якщо потрібно
4. Додай тести в `tests/`
5. Оновити документацію

### Code Style

```bash
# Format code
black *.py modules/*.py

# Lint
flake8 *.py modules/*.py

# Type check
mypy main.py
```

---

## 🚢 Deployment

### Render.com (Рекомендовано)

1. Push код на GitHub
2. Створ новий Web Service на Render
3. Підключи GitHub repo
4. Налаштуй Environment Variables
5. Deploy!

```yaml
# render.yaml
services:
  - type: web
    name: ferrik-bot
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python main.py"
    envVars:
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: ferrik-db
          property: connectionString
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

```bash
# Build
docker build -t ferrik-bot .

# Run
docker run -d -p 5000:5000 --env-file .env ferrik-bot
```

### Heroku

```bash
heroku create ferrik-bot
heroku config:set TELEGRAM_BOT_TOKEN=your_token
git push heroku main
```

---

## 🧪 Тестування

### Unit тести

```bash
pytest tests/
```

### Integration тести

```bash
pytest tests/integration/
```

### Покриття коду

```bash
pytest --cov=app --cov=services --cov=modules tests/
```

---

## 📈 Roadmap

### ✅ Фаза 1: Foundation (Завершено)
- Базовий функціонал замовлень
- Інтеграція з Google Sheets
- Валідація даних
- Обробка помилок

### 🔄 Фаза 2: Enhancement (В процесі)
- AI-рекомендації ✅
- Гейміфікація ✅
- Реферальна програма ✅
- Інтелектуальний пошук ✅
- Трекінг замовлень ✅
- Система відгуків 🔄
- Кешування меню 🔄

### 🎯 Фаза 3: Advanced (Q1 2025)
- [ ] Платежі (Stripe/LiqPay)
- [ ] Live доставка трекінг (карта)
- [ ] Голосове замовлення (voice recognition)
- [ ] Розпізнавання фото страв
- [ ] Генерація AI-зображень
- [ ] Web PWA додаток

### 🚀 Фаза 4: Scale (Q2 2025)
- [ ] Multi-tenant (кілька ресторанів)
- [ ] Admin dashboard (web)
- [ ] Analytics та метрики
- [ ] A/B тестування
- [ ] ML для персоналізації
- [ ] API для інтеграції

---

## 📊 Метрики

### Поточні показники
- **Uptime:** 99.2%
- **Response time:** ~350ms
- **Error rate:** 0.8%
- **Active users:** —
- **Daily orders:** —

### Цільові показники (2025)
- **Uptime:** 99.9%
- **Response time:** <200ms
- **Error rate:** <0.1%
- **Active users:** 1000+
- **Daily orders:** 50+

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 Ліцензія

MIT License - see [LICENSE](LICENSE) file for details

---

## 👥 Автори

- **Ferrik Team** — Initial work
- See also: [CONTRIBUTORS](CONTRIBUTORS.md)

---

## 📞 Контакти

- **Telegram:** [@FerrikBot](https://t.me/FerrikBot)
- **Email:** support@ferrik.com
- **GitHub:** [github.com/ferrik/ferrik-bot](https://github.com/ferrik/ferrik-bot)

---

## 🙏 Подяки

- Telegram Bot API
- Google Sheets API
- Flask Framework
- SQLite
- Render.com hosting

---

<div align="center">

**Зроблено з ❤️ та 🍕 командою Ferrik**

[⬆ На початок](#-ferrik-bot-20--персональний-смаковий-супутник)

</div>
