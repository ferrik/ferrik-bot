# 📖 Детальна інструкція по налаштуванню FerrikFoot Bot

## 📋 Зміст

1. [Створення Telegram бота](#1-створення-telegram-бота)
2. [Налаштування Google Gemini AI](#2-налаштування-google-gemini-ai)
3. [Налаштування Google Sheets](#3-налаштування-google-sheets)
4. [Деплой на Render](#4-деплой-на-render)
5. [Тестування](#5-тестування)

---

## 1. Створення Telegram бота

### Крок 1: Відкрийте @BotFather в Telegram

1. Знайдіть [@BotFather](https://t.me/BotFather) в Telegram
2. Натисніть **Start**

### Крок 2: Створіть нового бота

```
/newbot
```

### Крок 3: Введіть назву

```
FerrikFoot Bot
```

### Крок 4: Введіть username (має закінчуватись на bot)

```
ferrikfoot_bot
```

### Крок 5: Збережіть токен

BotFather надасть вам токен типу:
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

**⚠️ ВАЖЛИВО: Не діліться цим токеном ні з ким!**

### Крок 6: Налаштуйте команди

Надішліть BotFather:
```
/setcommands
```

Виберіть вашого бота і вставте:
```
start - Почати роботу
menu - Переглянути меню
cart - Переглянути кошик
order - Оформити замовлення
help - Допомога
cancel - Скасувати
```

---

## 2. Налаштування Google Gemini AI

### Крок 1: Перейдіть на AI Studio

Відкрийте: https://makersuite.google.com/app/apikey

### Крок 2: Увійдіть через Google акаунт

### Крок 3: Створіть API ключ

1. Натисніть **Create API Key**
2. Виберіть існуючий проєкт або створіть новий
3. Скопіюйте ключ

Ключ виглядає так:
```
AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**💡 Порада:** Використовуйте модель `gemini-1.5-flash` для швидкості та економії.

---

## 3. Налаштування Google Sheets

### Крок 1: Створіть Google Cloud проєкт

1. Перейдіть на https://console.cloud.google.com
2. Створіть новий проєкт або виберіть існуючий
3. Запам'ятайте назву проєкту

### Крок 2: Увімкніть необхідні API

1. В меню зліва виберіть **APIs & Services** → **Library**
2. Знайдіть та увімкніть:
   - **Google Sheets API**
   - **Google Drive API**

### Крок 3: Створіть Service Account

1. **APIs & Services** → **Credentials**
2. **Create Credentials** → **Service Account**
3. Введіть назву: `ferrik-bot-service`
4. Натисніть **Create and Continue**
5. Виберіть роль: **Editor**
6. Натисніть **Done**

### Крок 4: Створіть JSON ключ

1. Знайдіть створений Service Account в списку
2. Натисніть на нього
3. Перейдіть на вкладку **Keys**
4. **Add Key** → **Create new key**
5. Виберіть формат **JSON**
6. Завантажте файл

### Крок 5: Підготуйте credentials

Відкрийте завантажений JSON файл. Він виглядає так:

```json
{
  "type": "service_account",
  "project_id": "your-project-123",
  "private_key_id": "xxx...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "ferrik-bot@your-project.iam.gserviceaccount.com",
  ...
}
```

**Для Render:** Вставте весь JSON в ОДНУ ЛІНІЮ (видаліть всі переноси рядків):
```
{"type":"service_account","project_id":"your-project-123",...}
```

### Крок 6: Створіть Google Sheets таблицю

1. Перейдіть на https://docs.google.com/spreadsheets
2. Створіть нову таблицю: **Blank** або **+**
3. Назвіть таблицю: `FerrikFoot Menu & Orders`

### Крок 7: Надайте доступ Service Account

1. Натисніть **Share** (Поділитися)
2. Вставте email вашого Service Account:
   ```
   ferrik-bot@your-project.iam.gserviceaccount.com
   ```
3. Виберіть роль: **Editor**
4. Зніміть галочку "Notify people"
5. Натисніть **Share**

### Крок 8: Створіть аркуш "Menu"

Створіть таблицю з такими колонками:

| id | name | category | price | description | image_url | available | active |
|----|------|----------|-------|-------------|-----------|-----------|--------|
| 1 | Піца Маргарита | Піца | 120 | Класична піца з томатами | | TRUE | TRUE |
| 2 | Піца Пепероні | Піца | 150 | Гостра піца | | TRUE | TRUE |
| 3 | Coca-Cola 0.5л | Напої | 30 | Газована вода | | TRUE | TRUE |

**Опис колонок:**
- `id` - Унікальний номер товару
- `name` - Назва товару
- `category` - Категорія (Піца, Напої, Десерти, тощо)
- `price` - Ціна в гривнях
- `description` - Опис товару (опціонально)
- `image_url` - Посилання на фото (опціонально)
- `available` - Чи є в наявності (TRUE/FALSE)
- `active` - Чи показувати в меню (TRUE/FALSE)

### Крок 9: Створіть аркуш "Orders"

Створіть другий аркуш з назвою **Orders** та колонками:

| order_id | timestamp | user_id | username | phone | address | items | total | comment | status |
|----------|-----------|---------|----------|-------|---------|-------|-------|---------|--------|

Цей аркуш заповнюватиметься автоматично при замовленнях.

### Крок 10: Збережіть Spreadsheet ID

З URL таблиці:
```
https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit
                                       ^^^^^^^^^^^^^^^^^^^^^^^^
                                       Це ваш SPREADSHEET_ID
```

---

## 4. Деплой на Render

### Крок 1: Підготуйте код

1. Клонуйте або завантажте репозиторій
2. Переконайтесь, що всі файли на місці

### Крок 2: Створіть GitHub репозиторій

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ferrik-bot.git
git push -u origin main
```

### Крок 3: Зареєструйтесь на Render

1. Перейдіть на https://render.com
2. Зареєструйтесь через GitHub

### Крок 4: Створіть Web Service

1. Натисніть **New** → **Web Service**
2. Підключіть ваш GitHub репозиторій
3. Render автоматично визначить налаштування з `render.yaml`

### Крок 5: Додайте Environment Variables

В розділі **Environment** додайте:

```
TELEGRAM_BOT_TOKEN = ваш_токен_від_BotFather
GEMINI_API_KEY = ваш_ключ_від_Gemini
GOOGLE_SHEETS_CREDENTIALS = {"type":"service_account",...}
GOOGLE_SHEETS_ID = ваш_spreadsheet_id
WEBHOOK_URL = https://ваше-ім'я.onrender.com
```

**⚠️ Для WEBHOOK_URL:** Спочатку залиште порожнім, після першого деплою вставте URL вашого додатку.

### Крок 6: Deploy

1. Натисніть **Create Web Service**
2. Дочекайтесь завершення деплою (5-10 хвилин)
3. Скопіюйте URL вашого додатку

### Крок 7: Встановіть WEBHOOK_URL

1. Поверніться до **Environment Variables**
2. Додайте/оновіть:
   ```
   WEBHOOK_URL = https://your-app-name.onrender.com
   ```
3. Збережіть зміни (Render автоматично передеплоїть)

### Крок 8: Встановіть Webhook

Відкрийте в браузері:
```
https://your-app-name.onrender.com/set_webhook
```

Ви побачите:
```json
{
  "ok": true,
  "webhook_url": "https://your-app-name.onrender.com/webhook"
}
```

---

## 5. Тестування

### Крок 1: Перевірте здоров'я додатку

Відкрийте:
```
https://your-app-name.onrender.com/health
```

Має бути:
```json
{
  "status": "healthy",
  "services": {
    "telegram": true,
    "sheets": true,
    "gemini": true
  }
}
```

### Крок 2: Тест бота

1. Знайдіть вашого бота в Telegram: `@your_bot_username`
2. Натисніть **Start**
3. Напишіть `/menu` - має показати меню з Google Sheets

### Крок 3: Тест замовлення

```
Ви: Хочу піцу Маргарита
Бот: ✅ Додано до кошика!

Ви: /cart
Бот: [показує кошик]

Ви: /order
Бот: [просить телефон]

Ви: 0501234567
Бот: [просить адресу]

Ви: вул. Хрещатик, 1
Бот: [показує підсумок]

[Натискаєте "Підтвердити"]
Бот: ✅ Замовлення прийнято!
```

### Крок 4: Перевірте Google Sheets

Відкрийте аркуш **Orders** - має з'явитись нове замовлення!

---

## 🎉 Вітаємо! Бот працює!

### Що далі?

- 📝 Додайте більше товарів в меню
- 🎨 Додайте фото товарів (колонка `image_url`)
- 👥 Додайте адміністраторів в `ADMIN_IDS`
- 📊 Аналізуйте замовлення в Google Sheets

---

## 🐛 Проблеми?

### Бот не відповідає:
1. Перевірте `/health`
2. Перевірте логи на Render
3. Перевірте `/set_webhook`

### "Services: false":
- `telegram: false` → Перевірте TELEGRAM_BOT_TOKEN
- `sheets: false` → Перевірте GOOGLE_SHEETS_CREDENTIALS
- `gemini: false` → Перевірте GEMINI_API_KEY

### Помилки в Google Sheets:
1. Перевірте, чи надано доступ Service Account
2. Перевірте назви аркушів (Menu, Orders)
3. Перевірте структуру таблиць

---

## 📞 Підтримка

Якщо щось не працює - перевірте:
1. Всі environment variables встановлені правильно
2. Google Sheets має правильну структуру
3. Service Account має доступ до таблиці
4. Webhook встановлений правильно

**Успішного запуску! 🚀**
