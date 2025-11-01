# 🚀 Ferrik Bot — Швидкий старт

> Запусти бота за 15 хвилин!

---

## 📋 Що потрібно

- [ ] Python 3.11+
- [ ] Telegram Bot Token
- [ ] Google Sheets API credentials
- [ ] 15 хвилин часу ☕

---

## ⚡ Крок 1: Створення Telegram бота

### 1.1 Відкрий @BotFather у Telegram

```
/newbot
```

### 1.2 Введи назву та username

```
Назва: Ferrik Bot
Username: YourFerrikBot
```

### 1.3 Отримай токен

```
✅ Done! Your bot token is:
123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

**💾 Збережи токен — він знадобиться!**

---

## 📊 Крок 2: Google Sheets налаштування

### 2.1 Створи Google Sheets

1. Відкрий [Google Sheets](https://sheets.google.com)
2. Створи нову таблицю "Ferrik Bot Data"
3. Додай листи:
   - **Меню**
   - **Замовлення**
   - **Промокоди**
   - **Відгуки**
   - **Партнери**

### 2.2 Заповни лист "Меню"

| ID | Категорія | Страви | Опис | Ціна | Активний | Рейтинг |
|----|-----------|--------|------|------|----------|---------|
| 1  | Піца      | Маргарита | Класична піца | 180 | TRUE | 4.8 |
| 2  | Бургери   | Чізбургер | З сиром | 150 | TRUE | 4.5 |

### 2.3 Отримай Google API credentials

1. Перейди: https://console.cloud.google.com
2. Створи новий проєкт "Ferrik Bot"
3. Enable APIs:
   - Google Sheets API
   - Google Drive API
4. Credentials → Create Service Account
5. Create Key → JSON → Download

**💾 Збережи як `credentials.json`**

### 2.4 Дай доступ Service Account

```
1. Відкрий credentials.json
2. Знайди "client_email": "ferrik-bot@....iam.gserviceaccount.com"
3. Додай цей email в Google Sheets (Share → Editor)
```

---

## 💻 Крок 3: Встановлення бота

### 3.1 Клонуй репозиторій

```bash
git clone https://github.com/ferrik/ferrik-bot.git
cd ferrik-bot
```

### 3.2 Створи віртуальне середовище

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3.3 Встанов залежності

```bash
pip install -r requirements.txt
```

### 3.4 Налаштуй `.env`

```bash
# Скопіюй приклад
cp .env.example .env

# Відредагуй .env
nano .env  # або будь-який редактор
```

**Мінімальна конфігурація:**

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
GOOGLE_SHEETS_CREDENTIALS=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=твій_id_таблиці
PORT=5000
DEBUG=False
```

**Як знайти SPREADSHEET_ID?**

```
URL: https://docs.google.com/spreadsheets/d/1ABC...XYZ/edit
                                            ^^^^^^^^
                                            Це ID!
```

### 3.5 Ініціалізуй базу даних

```bash
python -c "from services.database import Database; db = Database('bot.db'); db.init_schema()"
```

---

## 🎯 Крок 4: Запуск бота

### 4.1 Локальний запуск (development)

```bash
python main.py
```

Побачиш:

```
🚀 Ferrik Bot 2.0 starting...
 * Running on http://0.0.0.0:5000
```

### 4.2 Налаштуй Webhook (для production)

```bash
# Отримай публічний URL (ngrok для тестування)
ngrok http 5000

# Встанови webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://your-ngrok-url.ngrok.io/webhook"
```

---

## ✅ Крок 5: Тестування

### 5.1 Відкрий бота в Telegram

```
/start
```

Повинен побачити:

```
🍴 Привіт! Я — Ferrik, твій персональний помічник зі смаку.
Хочеш я покажу найпопулярніше сьогодні чи підберу щось під твій настрій?

[🔍 Підказати] [📋 Меню] [🎁 Акції]
```

### 5.2 Перевір основні команди

```
/menu — Має показати меню з Google Sheets
/cart — Пустий кошик
/profile — Твій профіль (новий користувач)
/help — Список команд
```

### 5.3 Спробуй замовлення

```
1. /menu → Обери категорію
2. Вибери страву → Додай у кошик
3. /cart → Перевір кошик
4. Оформити замовлення
5. Введи телефон: +380501234567
6. Введи адресу: вул. Шевченка, 15
7. ✅ Замовлення прийнято!
```

---

## 🚀 Крок 6: Deployment на Render.com

### 6.1 Push на GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/твій-username/ferrik-bot.git
git push -u origin main
```

### 6.2 Створи Web Service

1. Відкрий [Render.com](https://render.com)
2. New → Web Service
3. Connect GitHub repo
4. Settings:
   ```
   Name: ferrik-bot
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python main.py
   ```

### 6.3 Додай Environment Variables

```
TELEGRAM_BOT_TOKEN=...
GOOGLE_SHEETS_SPREADSHEET_ID=...
PORT=10000
DEBUG=False
```

**⚠️ credentials.json:**
```
1. Скопіюй вміст credentials.json
2. Створи змінну GOOGLE_CREDENTIALS
3. Вставfull JSON як значення
4. В коді читай з env замість файлу
```

### 6.4 Deploy!

```
Click "Create Web Service"
⏳ Чекай 3-5 хвилин...
✅ Deployed!
```

### 6.5 Встанови Webhook

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://твій-render-url.onrender.com/webhook"
```

---

## 🎉 Готово!

Твій бот працює! 🚀

### Що далі?

- [ ] Додай більше страв у Google Sheets
- [ ] Налаштуй промокоди
- [ ] Запроси друзів (реферальна програма)
- [ ] Переглянь статистику

### Корисні команди

```bash
# Логи (Render)
render logs --tail

# Перезапуск
render restart

# База даних backup
python -c "from services.database import Database; Database('bot.db').backup()"
```

---

## 🆘 Troubleshooting

### Проблема: Бот не відповідає

**Рішення:**
```bash
# Перевір webhook
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Видали webhook (для локального тестування)
curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

### Проблема: Google Sheets не працює

**Рішення:**
1. Перевір, чи Service Account має доступ
2. Перевір SPREADSHEET_ID
3. Перевір назви листів (case-sensitive!)

```python
# Тест підключення
python
>>> from services.sheets import SheetsAPI
>>> sheets = SheetsAPI()
>>> menu = sheets.get_menu()
>>> print(len(menu))  # Має бути > 0
```

### Проблема: База даних помилки

**Рішення:**
```bash
# Видали стару БД
rm bot.db

# Створи нову
python -c "from services.database import Database; Database('bot.db').init_schema()"
```

### Проблема: ImportError

**Рішення:**
```bash
# Переконайся, що venv активовано
which python  # має бути у venv/

# Переустанови залежності
pip install -r requirements.txt --force-reinstall
```

---

## 📚 Наступні кроки

1. [Повна документація](README.md)
2. [Приклади використання](EXAMPLES.md)
3. [Deployment guide](DEPLOYMENT.md)
4. [Contribution guide](CONTRIBUTING.md)

---

## 💬 Потрібна допомога?

- **Документація:** [README.md](README.md)
- **Issues:** [GitHub Issues](https://github.com/ferrik/ferrik-bot/issues)
- **Telegram:** @FerrikSupport

---

<div align="center">

**Готовий! Тепер створюй найкращий бот для замовлення їжі! 🍕**

[⬆ На початок](#-ferrik-bot--швидкий-старт)

</div>
