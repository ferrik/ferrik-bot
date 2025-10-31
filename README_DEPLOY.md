# 🚀 Ferrik Bot - Інструкція з деплою

## 🔥 Що змінилось у версії 2.0

### ✅ Виправлення критичних помилок
- **ВИПРАВЛЕНО:** Webhook маршрут з `/webhook/webhook` на `/webhook`
- **ВИПРАВЛЕНО:** 404 помилки на запити Telegram

### ✨ Нові фічі
- 🎨 Теплий, дружній інтерфейс з емоджі
- 🤖 AI-рекомендації на основі історії
- 🏆 Система досягнень та бейджів
- 🔍 Розумний пошук по меню
- 🎁 Щоденні челенджі
- ⭐ Система рівнів (Новачок → Легенда)

---

## 📋 Швидкий старт

### 1. Оновити код на Render.com

```bash
# В GitHub репозиторії
git add .
git commit -m "Update to Ferrik Bot 2.0"
git push origin main
```

Render автоматично задеплоїть нову версію.

### 2. Перевстановити Webhook

Після деплою виконай цей запит (заміни `YOUR_BOT_TOKEN` та `YOUR_RENDER_URL`):

```bash
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://YOUR_RENDER_URL/webhook",
    "allowed_updates": ["message", "callback_query"]
  }'
```

**Приклад:**
```bash
curl -X POST "https://api.telegram.org/bot7865904321:AAG1234567890abcdef/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://ferrik-bot.onrender.com/webhook",
    "allowed_updates": ["message", "callback_query"]
  }'
```

### 3. Перевірити Webhook

```bash
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
```

Має показати:
```json
{
  "ok": true,
  "result": {
    "url": "https://your-app.onrender.com/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

---

## 🗂️ Структура проєкту

```
ferrik-bot/
├── main.py                    # ⭐ Головний файл (ОНОВЛЕНО)
├── ai_recommender.py          # 🆕 AI рекомендації
├── gamification.py            # 🆕 Геймифікація
│
├── app/
│   ├── utils/
│   │   └── validators.py      # Валідація
│   └── services/
│       └── session.py         # Сесії
│
├── services/
│   ├── database.py            # БД
│   ├── sheets.py              # Google Sheets
│   └── telegram.py            # Telegram API
│
├── requirements.txt           # Залежності
├── .env                       # Environment variables
└── README.md                  # Документація
```

---

## 🔧 Environment Variables (.env)

```env
BOT_TOKEN=твій_токен_бота
PORT=10000

# Google Sheets
GOOGLE_SHEETS_ID=твій_sheets_id
GOOGLE_CREDENTIALS_JSON={"type":"service_account"...}

# Optional
DEBUG=False
LOG_LEVEL=INFO
```

---

## 📦 requirements.txt

```txt
Flask==3.0.0
requests==2.31.0
gspread==5.12.0
oauth2client==4.1.3
python-dotenv==1.0.0
```

---

## 🎯 Як використовувати нові фічі

### 1. AI Рекомендації

```python
from ai_recommender import AIRecommender

recommender = AIRecommender(db, sheets)

# Рекомендації по часу доби
items = recommender.get_recommendations(user_id, context='morning')

# Рекомендації по настрою
items = recommender.get_mood_recommendations('happy')

# Пошук
results = recommender.search_by_query("піца без м'яса")
```

### 2. Геймифікація

```python
from gamification import GamificationSystem

gamification = GamificationSystem(db)

# Рівень користувача
level = gamification.get_user_level(user_id)
# {'level': 'Гурман', 'emoji': '👨‍🍳', ...}

# Бейджі
badges = gamification.get_earned_badges(user_id)

# Профіль
profile = gamification.get_profile_summary(user_id)
```

---

## 🧪 Тестування

### Локально (перед деплоєм)

```bash
# 1. Встановити залежності
pip install -r requirements.txt

# 2. Налаштувати .env
cp .env.example .env
# Відредагувати .env

# 3. Запустити
python main.py
```

### Тест Webhook (після деплою)

```bash
# Надішли тестове повідомлення боту в Telegram
/start
/menu
/cart
```

---

## 🐛 Troubleshooting

### Помилка 404 на /webhook/webhook
**Вирішення:** Оновлено на `/webhook` у новій версії

### Бот не відповідає
1. Перевірити webhook: `curl https://api.telegram.org/botTOKEN/getWebhookInfo`
2. Перевірити логи на Render: Dashboard → Logs
3. Перевстановити webhook (див. пункт 2)

### Помилки з Google Sheets
- Перевірити `GOOGLE_SHEETS_ID` в .env
- Перевірити права доступу service account
- Перевірити формат `GOOGLE_CREDENTIALS_JSON`

---

## 📈 Roadmap

### ✅ Фаза 1: Стабілізація (Завершено)
- Виправлено webhook
- Додано персоналізацію
- Геймифікація

### 🔄 Фаза 2: Розширення (В розробці)
- [ ] Інтеграція платежів (LiqPay)
- [ ] Реферальна програма
- [ ] Голосові замовлення
- [ ] PWA веб-версія

### 🚀 Фаза 3: AI (Майбутнє)
- [ ] ChatGPT для NLP пошуку
- [ ] Генерація зображень страв
- [ ] Предиктивні рекомендації

---

## 💡 Корисні команди

```bash
# Перевірити статус бота
curl https://api.telegram.org/botTOKEN/getMe

# Очистити webhook
curl https://api.telegram.org/botTOKEN/deleteWebhook

# Отримати оновлення вручну (для дебагу)
curl https://api.telegram.org/botTOKEN/getUpdates

# Перевірити живість сервера
curl https://your-app.onrender.com/
```

---

## 📞 Підтримка

**GitHub:** https://github.com/ferrik/ferrik-bot  
**Issues:** https://github.com/ferrik/ferrik-bot/issues

---

## 🎉 Дякую за використання Ferrik Bot!

Зроблено з ❤️ для твого бізнесу