# 🚀 Ferrik Bot - Production Deployment Guide

## 📋 Зміст
1. [Pre-deployment Checklist](#pre-deployment-checklist)
2. [Render.com Setup](#rendercom-setup)
3. [PostgreSQL Configuration](#postgresql-configuration)
4. [Environment Variables](#environment-variables)
5. [Webhook Setup](#webhook-setup)
6. [Testing](#testing)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Pre-deployment Checklist

### Код готовий?
- [ ] Всі файли оновлені до версії 2.0
- [ ] `main.py` використовує `/webhook` (не `/webhook/webhook`)
- [ ] `requirements.txt` містить всі залежності
- [ ] `.env.example` скопійовано як `.env` локально
- [ ] Код протестовано локально

### Сервіси налаштовані?
- [ ] Google Sheets таблиця створена
- [ ] Service Account має доступ до таблиці
- [ ] Telegram Bot Token отриманий від @BotFather
- [ ] GitHub репозиторій готовий

---

## 🌐 Render.com Setup

### Крок 1: Створити Web Service

1. Відкрити [dashboard.render.com](https://dashboard.render.com)
2. Натиснути **"New +"** → **"Web Service"**
3. Підключити GitHub репозиторій
4. Налаштування:

```yaml
Name: ferrik-bot
Region: Frankfurt (EU Central)
Branch: main
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn main:app --bind 0.0.0.0:$PORT
Instance Type: Free (або Starter для production)
```

### Крок 2: Додати PostgreSQL Database

1. В Dashboard → **"New +"** → **"PostgreSQL"**
2. Налаштування:

```yaml
Name: ferrik-bot-db
Database: ferrik_db
User: ferrik_user
Region: Frankfurt (EU Central) # Той самий, що і Web Service
PostgreSQL Version: 15
```

3. Після створення, скопіювати **Internal Database URL**

### Крок 3: Підключити Database до Web Service

1. Відкрити Web Service → **"Environment"**
2. Додати змінну:

```
DATABASE_URL = [Internal Database URL з кроку 2]
```

Render автоматично додасть `DATABASE_URL`, але перевір!

---

## 🗄️ PostgreSQL Configuration

### Автоматична ініціалізація (рекомендовано)

Бот автоматично створить таблиці при першому запуску завдяки SQLAlchemy.

### Ручна ініціалізація (опціонально)

Якщо хочеш створити таблиці вручну:

1. **Підключитись до БД через Render Shell:**

```bash
# В Dashboard → PostgreSQL → Shell
psql $DATABASE_URL
```

2. **Виконати міграцію:**

```sql
\i migrations/001_init_schema.sql
```

3. **Перевірити таблиці:**

```sql
\dt
-- Має показати: user_states, user_carts, orders, user_profiles
```

### Перевірка структури

```sql
-- Кількість таблиць
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- Структура таблиці
\d user_profiles

-- Тестовий запит
SELECT COUNT(*) FROM user_profiles;
```

---

## ⚙️ Environment Variables

### Обов'язкові змінні на Render

В **Web Service → Environment** додай:

```bash
# Telegram
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
WEBHOOK_URL=https://ferrik-bot.onrender.com

# Google Sheets
GOOGLE_SHEETS_ID=1ABC123xyz456
GOOGLE_CREDENTIALS_JSON={"type":"service_account"...}

# Database (автоматично встановлюється Render)
DATABASE_URL=postgresql://user:pass@host:5432/db

# Server
PORT=10000
FLASK_ENV=production
DEBUG=False
```

### Як отримати GOOGLE_CREDENTIALS_JSON

1. Перейти на [console.cloud.google.com](https://console.cloud.google.com)
2. **IAM & Admin** → **Service Accounts** → **Create Service Account**
3. Скачати JSON ключ
4. Відкрити файл та скопіювати **весь JSON в один рядок**
5. Вставити як значення `GOOGLE_CREDENTIALS_JSON`

**Важливо:** JSON має бути в одному рядку без переносів!

### Опціональні змінні

```bash
# Features
ENABLE_AI_RECOMMENDATIONS=True
ENABLE_GAMIFICATION=True
ENABLE_MENU_CACHE=True

# Business
MIN_ORDER_AMOUNT=100
DELIVERY_COST=50
FREE_DELIVERY_FROM=500

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/123
LOG_LEVEL=INFO
```

---

## 🔗 Webhook Setup

### Автоматичне встановлення (рекомендовано)

Використай скрипт:

```bash
chmod +x setup_webhook.sh
./setup_webhook.sh
```

Введи:
- **BOT_TOKEN:** Твій токен від BotFather
- **WEBHOOK_URL:** https://ferrik-bot.onrender.com

### Ручне встановлення

```bash
curl -X POST "https://api.telegram.org/botYOUR_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.onrender.com/webhook",
    "allowed_updates": ["message", "callback_query"],
    "drop_pending_updates": true
  }'
```

### Перевірка Webhook

```bash
curl "https://api.telegram.org/botYOUR_TOKEN/getWebhookInfo"
```

Має показати:

```json
{
  "ok": true,
  "result": {
    "url": "https://your-app.onrender.com/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "last_error_date": null
  }
}
```

**Якщо pending_update_count > 0:**

```bash
# Очистити старі оновлення
curl -X POST "https://api.telegram.org/botYOUR_TOKEN/setWebhook" \
  -d "url=https://your-app.onrender.com/webhook" \
  -d "drop_pending_updates=true"
```

---

## 🧪 Testing

### 1. Перевірка сервера

```bash
curl https://your-app.onrender.com/
```

Має повернути HTML з "Ferrik Bot is running!"

### 2. Перевірка Database

В Render Shell:

```sql
psql $DATABASE_URL

-- Перевірити таблиці
\dt

-- Перевірити дані
SELECT * FROM user_profiles;
SELECT * FROM orders LIMIT 5;
```

### 3. Тестування в Telegram

1. Відкрити бота в Telegram
2. Натиснути `/start`
3. Має з'явитись привітання з емоджі
4. Перевірити:
   - [ ] `/menu` - показує меню
   - [ ] Додавання в кошик
   - [ ] `/cart` - показує кошик
   - [ ] Оформлення замовлення
   - [ ] Збереження в Google Sheets

### 4. Тестування геймифікації

```
/start - має показати рівень
Зробити замовлення - має оновити статистику
Кнопка "Досягнення" - має показати бейджі
```

### 5. Load Testing (опціонально)

```bash
# Apache Bench
ab -n 100 -c 10 https://your-app.onrender.com/

# wrk
wrk -t4 -c100 -d30s https://your-app.onrender.com/
```

---

## 📊 Monitoring

### Логи на Render

```
Dashboard → Web Service → Logs
```

Фільтри:
- Всі логи: показати все
- Тільки помилки: `❌` або `ERROR`
- Webhook запити: `POST /webhook`

### Метрики для відслідковування

**День 1:**
- [ ] 0 critical errors
- [ ] >10 успішних /start
- [ ] >5 успішних замовлень
- [ ] Webhook response time <500ms

**Тиждень 1:**
- [ ] Uptime >99%
- [ ] >100 користувачів
- [ ] >50 замовлень
- [ ] Database size <100MB

**Місяць 1:**
- [ ] Uptime >99.5%
- [ ] >1000 користувачів
- [ ] >500 замовлень
- [ ] Позитивні відгуки

### Database Monitoring

```sql
-- Розмір БД
SELECT pg_size_pretty(pg_database_size(current_database()));

-- Кількість користувачів
SELECT COUNT(*) FROM user_profiles;

-- Кількість замовлень сьогодні
SELECT COUNT(*) FROM orders 
WHERE DATE(created_at) = CURRENT_DATE;

-- Топ користувачів
SELECT user_id, total_orders, total_spent 
FROM user_profiles 
ORDER BY total_spent DESC 
LIMIT 10;
```

### Health Check Endpoint

Додати в `main.py`:

```python
@app.route('/health', methods=['GET'])
def health_check():
    """Health check для моніторингу"""
    try:
        # Перевірка БД
        with db.get_session() as session:
            session.execute('SELECT 1')
        
        return {
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }, 503
```

Перевірка:

```bash
curl https://your-app.onrender.com/health
```

---

## 🐛 Troubleshooting

### Проблема: 404 Not Found

**Рішення:**

```bash
# 1. Видалити webhook
curl https://api.telegram.org/botTOKEN/deleteWebhook

# 2. Встановити правильний
curl -X POST https://api.telegram.org/botTOKEN/setWebhook \
  -d "url=https://your-app.onrender.com/webhook"

# 3. Перевірити
curl https://api.telegram.org/botTOKEN/getWebhookInfo
```

### Проблема: Database Connection Error

**Діагностика:**

```bash
# В Render Shell
echo $DATABASE_URL
```

**Рішення:**

1. Перевірити формат URL: `postgresql://` (не `postgres://`)
2. В `database.py` є автоматична заміна
3. Перезапустити сервіс

### Проблема: Google Sheets Error

**Діагностика:**

Логи показують: `gspread.exceptions.APIError`

**Рішення:**

1. Перевірити GOOGLE_SHEETS_ID
2. Дати доступ Service Account до таблиці:
   - Відкрити Google Sheets
   - Share → Додати email з JSON (`client_email`)
   - Права: Editor
3. Перевірити JSON credentials валідний

### Проблема: Bot не відповідає

**Checklist:**

- [ ] Webhook встановлений правильно?
- [ ] Сервер працює? (відкрити URL в браузері)
- [ ] DATABASE_URL правильний?
- [ ] Немає помилок в логах?
- [ ] BOT_TOKEN правильний?

**Швидкий фікс:**

```bash
# Перезапустити все
1. Render Dashboard → Manual Deploy
2. Видалити і встановити webhook заново
3. Тестувати з /start
```

### Проблема: Out of Memory

Free tier на Render має ліміт 512MB RAM.

**Рішення:**

1. **Короткострокове:** Upgrade до Starter ($7/month)
2. **Довгострокове:**
   - Додати Redis для кешування
   - Оптимізувати запити до БД
   - Використовувати connection pooling

---

## 🎯 Performance Tips

### 1. Кешування меню

```python
# В main.py
MENU_CACHE = {}
MENU_CACHE_TTL = 300  # 5 хвилин

def get_cached_menu():
    now = time.time()
    if 'menu' not in MENU_CACHE or now - MENU_CACHE['time'] > MENU_CACHE_TTL:
        MENU_CACHE['menu'] = sheets.get_menu_items()
        MENU_CACHE['time'] = now
    return MENU_CACHE['menu']
```

### 2. Database Connection Pooling

Вже реалізовано в `database.py`:

```python
engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

### 3. Async Operations (для майбутнього)

```python
# Використати aiohttp та asyncio
import asyncio
import aiohttp

async def async_send_message(chat_id, text):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{TELEGRAM_API}/sendMessage", json={...}) as resp:
            return await resp.json()
```

---

## 🎉 Deployment Complete!

Якщо все працює:

✅ Webhook налаштовано  
✅ Database працює  
✅ Бот відповідає в Telegram  
✅ Замовлення зберігаються  
✅ Геймифікація працює  

**Наступні кроки:**

1. Додати реальні фото страв в Google Sheets
2. Налаштувати платежі (LiqPay/Stripe)
3. Запустити бета-тестування
4. Зібрати фідбек
5. Масштабувати! 🚀

---

**Потрібна допомога?**

- GitHub Issues: [github.com/ferrik/ferrik-bot/issues](https://github.com/ferrik/ferrik-bot/issues)
- Telegram Support: @your_support
- Documentation: [docs.ferrik.com](https://docs.ferrik.com)

✨ Успіхів з запуском!
