# ⚡ Швидкий деплой - 5 хвилин

Мінімальні кроки для запуску бота.

---

## ✅ Чеклист перед деплоєм

- [ ] Telegram Bot Token від @BotFather
- [ ] Gemini API Key від AI Studio
- [ ] Google Sheets Service Account JSON
- [ ] Google Sheets Spreadsheet ID
- [ ] GitHub репозиторій
- [ ] Render акаунт

---

## 🚀 Крок 1: Telegram Bot (2 хв)

```
1. Відкрийте @BotFather
2. /newbot
3. Введіть назву та username
4. Скопіюйте токен
```

---

## 🤖 Крок 2: Gemini API (1 хв)

```
1. Перейдіть: https://makersuite.google.com/app/apikey
2. Create API Key
3. Скопіюйте ключ
```

---

## 📊 Крок 3: Google Sheets (5 хв)

### A. Service Account

```
1. console.cloud.google.com
2. Увімкніть: Google Sheets API, Google Drive API
3. Створіть Service Account
4. Завантажте JSON ключ
5. Скопіюйте JSON в одну лінію
```

### B. Створіть таблицю

**Аркуш "Menu":**
```
id | name | category | price | description | image_url | available | active
1  | Піца | Основні  | 120   | Смачна піца |           | TRUE      | TRUE
```

**Аркуш "Orders":**
```
order_id | timestamp | user_id | username | phone | address | items | total | comment | status
```

### C. Поділіться доступом

```
1. Share → вставте email з JSON (client_email)
2. Роль: Editor
3. Скопіюйте Spreadsheet ID з URL
```

---

## 🌐 Крок 4: Render Deploy (3 хв)

### A. GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git push origin main
```

### B. Render

```
1. render.com → New Web Service
2. Підключіть GitHub repo
3. Додайте Environment Variables:
   - TELEGRAM_BOT_TOKEN
   - GEMINI_API_KEY
   - GOOGLE_SHEETS_CREDENTIALS
   - GOOGLE_SHEETS_ID
4. Deploy
```

### C. Webhook

```
1. Скопіюйте URL: https://your-app.onrender.com
2. Додайте env: WEBHOOK_URL = ваш_URL
3. Відкрийте: https://your-app.onrender.com/set_webhook
```

---

## ✅ Крок 5: Тест (1 хв)

```
1. Знайдіть бота в Telegram
2. /start
3. /menu
4. Напишіть: "Хочу піцу"
```

---

## 🎉 Готово!

Якщо все працює - ви можете:
- Додати товари в Google Sheets
- Налаштувати команди в @BotFather
- Додати фото товарів
- Запросити користувачів

---

## 🐛 Швидке вирішення проблем

### Бот не відповідає:
```
https://your-app.onrender.com/health
```

Має показати:
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

### Якщо `false`:
- **telegram: false** → Перевірте TELEGRAM_BOT_TOKEN
- **sheets: false** → Перевірте JSON credentials та доступ
- **gemini: false** → Перевірте GEMINI_API_KEY

---

## 📋 Environment Variables Checklist

```bash
# ✅ Обов'язкові
TELEGRAM_BOT_TOKEN=1234567890:ABC...
GEMINI_API_KEY=AIzaSy...
GOOGLE_SHEETS_CREDENTIALS={"type":"service_account",...}
GOOGLE_SHEETS_ID=1AbCd...
WEBHOOK_URL=https://your-app.onrender.com

# ⚙️ Опціональні
ADMIN_IDS=123456789
DEBUG=False
LOG_LEVEL=INFO
```

---

## 📱 Команди для @BotFather

```
start - Почати роботу
