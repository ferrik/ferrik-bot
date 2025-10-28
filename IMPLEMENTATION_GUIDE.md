# 🚀 Ferrik Bot v2.1 - Інструкція по установці

## 📋 Що змінилось?

### ✨ НОВІ ФІЧІ:
- 🎭 **Теплі привітання** - персоналізовані вітання для кожного користувача
- 🏆 **Бейджи & Рівні** - Новачок → Гурман → Фанат → Легенда
- 🎯 **Щотижневі Челленджи** - мотивація замовляти!
- 🎁 **Surprise Me** - AI вибирає комбо зі знижкою 15-20%
- 👑 **Профіль** - статистика, досягнення, реферали
- 👥 **Реферальна система** - +100 бонусів за друга
- 💬 **Розумна AI** - розуміє намір та настрій користувача
- 📊 **Адміністративна статистика** - `/stats` endpoint

---

## 🔧 Крок 1: Замініть файли

### Видаліть старі файли:
```bash
rm -rf app/utils/session.py
rm -rf app/handlers/commands.py
rm -rf app/handlers/messages.py
rm -rf app/handlers/callbacks.py
rm -rf app/services/gemini_service.py
rm -rf prompts.py
rm -rf main.py
```

### Копіюйте НОВІ файли:
1. **app/utils/session.py** - новий (зі сесіями + бейджами)
2. **app/handlers/commands.py** - оновлений (теплі привітання)
3. **app/handlers/messages.py** - новий (AI обробка)
4. **app/handlers/callbacks.py** - оновлений (нові фічи)
5. **app/services/gemini_service.py** - старий OK (сумісний)
6. **main.py** - оновлений (нові endpoints)
7. **prompts.py** - новий (текстуры та промпти)

---

## 📦 Крок 2: Оновіть requirements.txt

```bash
# Вже мають бути:
Flask==3.0.0
python-telegram-bot==20.0
google-generativeai==0.3.0
gspread==5.12.0
python-dotenv==1.0.0
requests==2.31.0
gunicorn==21.0.0
```

Запустіть:
```bash
pip install -r requirements.txt
```

---

## 🎯 Крок 3: Тестування локально

```bash
# 1. Завантажте нові файли
# 2. Запустіть
python main.py

# 3. Перевірте endpoints
curl http://localhost:5000/health
# Має бути: {"status": "healthy", "services": {...}}

curl http://localhost:5000/stats
# Показує статистику платформи
```

---

## 🌐 Крок 4: Deploy на Render

### 1. Push до GitHub:
```bash
git add .
git commit -m "feat: v2.1 - warm greetings, badges, challenges, AI improvements"
git push origin main
```

### 2. Render автоматично передеплоїть

### 3. Перевірте:
```bash
https://your-app.onrender.com/health
https://your-app.onrender.com/stats
https://your-app.onrender.com/set_webhook
```

---

## 🧪 Тестування фічей

### Тест 1: Теплі привітання
```
Користувач пише: /start
БОТ: Показує РІЗНІ привітання для:
  - Новачків (перший раз)
  - Постійних користувачів
  - VIP (50+ замовлень)
```

### Тест 2: Сюрприз
```
Користувач: /start → [🎁 Сюрприз!]
БОТ: Показує 3 випадкові страви + 15-20% знижка
```

### Тест 3: Челлендж
```
Користувач: /start → [🎯 Челлендж]
БОТ: "Замовте 3 сніданки - отримайте 150 бонусів!"
```

### Тест 4: Профіль
```
Користувач: /start → [⭐ Мій профіль]
БОТ: Показує статус, досягнення, реферальне посилання
```

### Тест 5: AI розуміння
```
Користувач: "Мені грусто, щось комфортне"
БОТ: Рекомендує "comfort food" + десерти
     
Користувач: "Спішу, щось швидке"
БОТ: Рекомендує "fast food" + напитки
```

---

## 🎨 Кастомізація

### Змінити привітання:
**app/handlers/commands.py**, лінія ~45:
```python
WARM_GREETINGS = {
    'first_time': "Ваш текст тут",
    ...
}
```

### Змінити бейджи:
**app/utils/session.py**, лінія ~25:
```python
BADGES = {
    1: {"emoji": "🆕", "name": "Новачок"},
    5: {"emoji": "👨‍🍳", "name": "Гурман"},
    ...
}
```

### Змінити челленджі:
**prompts.py**, лінія ~120:
```python
WEEKLY_CHALLENGES = [
    {'title': 'ВАША НАЗВА', ...},
    ...
]
```

### Змінити Surprise Me знижку:
**app/handlers/callbacks.py**, лінія ~40:
```python
discount = random.randint(15, 20)  # Змініть 15, 20
```

---

## 📊 Моніторинг

### Переглянути статистику:
```
GET /stats
```

Відповідь:
```json
{
  "status": "ok",
  "platform": {
    "active_users": 42,
    "total_orders": 156,
    "total_revenue": 45230.50,
    "avg_orders_per_user": 3.71,
    "avg_revenue_per_user": 1076.93
  }
}
```

### Логи на Render:
```
Dashboard → Your Service → Logs
```

---

## 🐛 Troubleshooting

### ❌ "AttributeError: 'NoneType' object"
**Рішення:** Перевірте, що всі НОВI файли завантажені правильно
```bash
ls -la app/utils/session.py
ls -la app/handlers/messages.py
```

### ❌ "ModuleNotFoundError: No module named 'prompts'"
**Рішення:** Переконайтесь, що `prompts.py` в корені проекту

### ❌ Бот не відповідає на /start
**Рішення:** Перевірте що새로운 `main.py` завантажений
```bash
grep "warm_greetings" main.py
```

### ❌ Статистика не показується
**Рішення:** Переконайтесь що `session.py` завантажений
```bash
grep "get_platform_stats" app/utils/session.py
```

---

## 📈 Результати

### Очікуємі метрики через 2 тижні:
| Метрика | Бюджет | Результат |
|---------|--------|-----------|
| D1 Retention | 20% | **55%+** |
| Avg Orders/User | 1.0 | **3-5** |
| Share Rate | 0% | **30%+** |
| Rating | 3.5⭐ | **4.8⭐** |

---

## 🎯 Наступні кроки

### Тиждень 2-3:
- [ ] Додати платежі (Stripe/LiqPay)
- [ ] Трекінг доставки в реальному часі
- [ ] Email розсилки за промо

### Тиждень 4-6:
- [ ] Веб-версія бота
- [ ] Мобільний додаток (базовий)
- [ ] Dashboard для партнерів

---

## 📞 Підтримка

Якщо щось не працює:
1. Перевірте `/health` endpoint
2. Перевірте логи на Render
3. Переконайтесь що всі файли завантажені
4. Restart сервіс на Render

---

**Удачи! Твій бот буде найлюдянішим! 🚀**
