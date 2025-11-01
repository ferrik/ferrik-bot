# ⚡ Ferrik Bot - Швидкий старт за 10 хвилин

## 🎯 Мета: Запустити бота в production за 10 хвилин

---

## ⏱️ Хвилина 1-2: Підготовка

### 1. Клонувати репозиторій

```bash
git clone https://github.com/ferrik/ferrik-bot.git
cd ferrik-bot
```

### 2. Перевірити файли

```bash
ls -la
# Має бути:
# main.py, ai_recommender.py, gamification.py
# requirements.txt, .env.example
# README.md, PRODUCTION_DEPLOY.md
```

---

## ⏱️ Хвилина 3-4: Render Setup

### 3. Створити Web Service

1. Відкрити [dashboard.render.com](https://dashboard.render.com)
2. **New + → Web Service**
3. Підключити GitHub repo
4. Копіювати ці налаштування:

```
Name: ferrik-bot
Runtime: Python 3
Build: pip install -r requirements.txt
Start: gunicorn main:app --bind 0.0.0.0:$PORT
```

5. **Create Web Service** ✅

### 4. Створити PostgreSQL

1. **New + → PostgreSQL**
2. Name: `ferrik-bot-db`
3. Region: той самий, що Web Service
4. **Create Database** ✅
5. Скопіювати **Internal Database URL**

---

## ⏱️ Хвилина 5-6: Environment Variables

### 5. Додати змінні в Render

Web Service → **Environment** → Add:

```bash
BOT_TOKEN=твій_токен_від_BotFather
DATABASE_URL=Internal_Database_URL_з_кроку_4
GOOGLE_SHEETS_ID=твій_sheets_id
GOOGLE_CREDENTIALS_JSON={"type":"service_account"...}
WEBHOOK_URL=https://твій-app.onrender.com
```

**Швидка довідка:**

- `BOT_TOKEN`: [t.me/BotFather](https://t.me/BotFather) → /newbot
- `GOOGLE_SHEETS_ID`: з URL таблиці
- `GOOGLE_CREDENTIALS_JSON`: з Google Cloud Console
- `WEBHOOK_URL`: з Render (Settings → Copy URL)

**Save Changes** ✅

---

## ⏱️ Хвилина 7: Deploy

### 6. Запустити deploy

1. Render автоматично запустить deploy після збереження змінних
2. Чекати зеленого статусу **"Live"** (2-3 хв)
3. Перевірити логи: має бути `✅ Database tables created`

---

## ⏱️ Хвилина 8-9: Webhook

### 7. Встановити webhook

**Варіант A: Автоматичний скрипт**

```bash
chmod +x setup_webhook.sh
./setup_webhook.sh
```

**Варіант B: Ручна команда**

```bash
curl -X POST "https://api.telegram.org/botТВОЙ_ТОКЕН/setWebhook" \
  -d "url=https://твій-app.onrender.com/webhook" \
  -d "drop_pending_updates=true"
```

### 8. Перевірити webhook

```bash
curl "https://api.telegram.org/botТВОЙ_ТОКЕН/getWebhookInfo"
```

Має бути:
```json
{"ok":true,"result":{"url":"https://твій-app.onrender.com/webhook"}}
```

---

## ⏱️ Хвилина 10: Тестування

### 9. Протестувати бота

1. Відкрити бота в Telegram
2. Натиснути **/start**
3. Має з'явитись:

```
✨ Вітаю в Ferrik! ✨

Привіт, друже! Я — твій персональний 
смаковий супутник 👨‍🍳

[🍴 Меню] [🔍 Пошук]
[🛒 Кошик] [🎁 Акції]
```

### 10. Швидкий smoke test

- [ ] `/start` працює ✅
- [ ] Кнопки натискаються ✅  
- [ ] Меню завантажується ✅
- [ ] Кошик працює ✅
- [ ] Можна оформити замовлення ✅

---

## 🎉 Готово за 10 хвилин!

Якщо все працює - вітаю! Бот запущений в production! 🚀

---

## 🔥 Бонус: Наступні кроки (опціонально)

### За 5 хвилин: Додати дані в Google Sheets

1. Відкрити твою таблицю
2. **Лист "Меню"** - додати страви:

```
ID | Категорія | Страви | Опис | Ціна | Фото URL
1  | Піца     | Маргарита | Класична піца | 180 | https://...
2  | Бургери  | Класик    | Соковитий     | 150 | https://...
```

3. **Share** → Додати email з `GOOGLE_CREDENTIALS_JSON` → Editor

### За 10 хвилин: Налаштувати моніторинг

```python
# Додати в main.py
@app.route('/health')
def health():
    return {'status': 'ok', 'time': datetime.now().isoformat()}
```

Test:
```bash
curl https://твій-app.onrender.com/health
```

### За 15 хвилин: Додати real-time статистику

```sql
-- В PostgreSQL Shell
SELECT 
    COUNT(*) as users,
    SUM(total_orders) as orders,
    SUM(total_spent) as revenue
FROM user_profiles;
```

---

## 🆘 Швидка допомога

### Бот не відповідає?

```bash
# 1. Перевірити сервер
curl https://твій-app.onrender.com/

# 2. Перевірити webhook
curl https://api.telegram.org/botТОКЕН/getWebhookInfo

# 3. Перевірити логи
# Render Dashboard → Logs
```

### 404 Error?

```bash
# Видалити старий webhook
curl https://api.telegram.org/botТОКЕН/deleteWebhook

# Встановити новий (БЕЗ /webhook/webhook!)
curl -X POST https://api.telegram.org/botТОКЕН/setWebhook \
  -d "url=https://твій-app.onrender.com/webhook"
```

### Database Error?

1. Перевірити `DATABASE_URL` в Environment
2. Має бути `postgresql://` (не `postgres://`)
3. Код автоматично виправляє, але перевір!

---

## 📞 Контакти

**Проблеми з деплоєм?**
- Логи Render: Screenshot + опис
- GitHub Issues: [github.com/ferrik/ferrik-bot/issues](https://github.com/ferrik/ferrik-bot/issues)

**Все працює?**
- ⭐ Star на GitHub
- 💬 Відгук у Issues
- 🚀 Діліться з друзями!

---

## 🎯 Checklist успішного деплою

- [x] ⏱️ За 10 хвилин
- [x] ✅ Бот відповідає
- [x] 🗄️ Database працює
- [x] 📊 Замовлення зберігаються
- [x] 🎨 Красивий інтерфейс з емоджі
- [x] 🏆 Геймифікація увімкнена
- [x] 🚀 Production ready

---

**Час на завершення:** 10 хвилин ⏱️  
**Складність:** Легко 😊  
**Результат:** Професійний бот в production 🎉

✨ Let's go! Починай з хвилини 1!
