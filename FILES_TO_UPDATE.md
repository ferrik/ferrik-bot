# 📋 Список файлів для оновлення репозиторію

## 🔄 Файли для заміни/оновлення

### 📌 Кореневі файли

```
✅ main.py                      # Головний файл Flask + Telegram Bot
✅ requirements.txt             # Python залежності
✅ Procfile                     # Gunicorn конфігурація
✅ runtime.txt                  # Версія Python
✅ render.yaml                  # Конфігурація Render
✅ .gitignore                   # Git ignore
✅ README.md                    # Основна документація
✅ SETUP_GUIDE.md              # Детальна інструкція налаштування
✅ QUICK_DEPLOY.md             # Швидкий деплой гід
✅ CHANGELOG.md                # Історія змін
✅ .env.example                # Приклад environment variables
```

### 📁 app/ - Головний пакет

```
✅ app/__init__.py             # Ініціалізація пакету
✅ app/config.py               # Конфігурація додатку
```

### 📁 app/handlers/ - Обробники Telegram

```
✅ app/handlers/__init__.py    # Експорт обробників
✅ app/handlers/commands.py    # Команди (/start, /menu, /cart, тощо)
✅ app/handlers/messages.py    # Текстові повідомлення + AI
✅ app/handlers/callbacks.py   # Inline кнопки (callback queries)
```

### 📁 app/services/ - Сервіси

```
✅ app/services/__init__.py       # Експорт сервісів
✅ app/services/sheets_service.py # Google Sheets API
✅ app/services/gemini_service.py # Gemini AI API
```

### 📁 app/utils/ - Утиліти

```
✅ app/utils/__init__.py       # Експорт утиліт
✅ app/utils/validators.py     # Валідація та парсинг (ОНОВЛЕНИЙ)
✅ app/utils/session.py        # Управління сесіями та кошиками
```

---

## 📊 Структура директорій

```
ferrik-bot/
├── 📄 main.py
├── 📄 requirements.txt
├── 📄 Procfile
├── 📄 runtime.txt
├── 📄 render.yaml
├── 📄 .gitignore
├── 📄 .env.example
├── 📄 README.md
├── 📄 SETUP_GUIDE.md
├── 📄 QUICK_DEPLOY.md
├── 📄 CHANGELOG.md
│
└── 📁 app/
    ├── 📄 __init__.py
    ├── 📄 config.py
    │
    ├── 📁 handlers/
    │   ├── 📄 __init__.py
    │   ├── 📄 commands.py
    │   ├── 📄 messages.py
    │   └── 📄 callbacks.py
    │
    ├── 📁 services/
    │   ├── 📄 __init__.py
    │   ├── 📄 sheets_service.py
    │   └── 📄 gemini_service.py
    │
    └── 📁 utils/
        ├── 📄 __init__.py
        ├── 📄 validators.py
        └── 📄 session.py
```

---

## 🔄 Інструкції по оновленню

### Варіант 1: Повне оновлення

```bash
# 1. Створіть backup існуючого коду
git checkout -b backup-old-version

# 2. Поверніться на main
git checkout main

# 3. Видаліть старі файли (якщо потрібно)
rm -rf app/ main.py

# 4. Додайте всі нові файли з цього списку

# 5. Commit та push
git add .
git commit -m "Update to v2.0.0 - Improved architecture"
git push origin main
```

### Варіант 2: Поступове оновлення

```bash
# 1. Оновіть по одному файлу
# 2. Тестуйте після кожного оновлення
# 3. Commit після кожної зміни

git add app/utils/validators.py
git commit -m "Update validators with new functions"

git add app/config.py
git commit -m "Add centralized configuration"

# ... і так далі
```

---

## ⚠️ Важливі зауваження

### 🔴 Обов'язково оновити:

1. **app/utils/validators.py** - Розширений функціонал валідації
2. **main.py** - Нова структура з Flask + асинхронністю
3. **requirements.txt** - Оновлені версії бібліотек
4. **app/config.py** - Централізована конфігурація

### 🟡 Створити нові файли:

1. **app/utils/session.py** - Управління сесіями
2. **app/handlers/** - Всі файли (нова структура)
3. **app/services/** - Всі файли (рефакторинг)
4. **render.yaml** - Конфігурація для Render
5. **SETUP_GUIDE.md** - Документація

### 🟢 Опціонально оновити:

1. **README.md** - Покращена документація
2. **.gitignore** - Додані нові шаблони
3. **.env.example** - Додані нові змінні

---

## 🧪 Тестування після оновлення

### Локально:

```bash
# 1. Встановіть залежності
pip install -r requirements.txt

# 2. Створіть .env з прикладу
cp .env.example .env
# Заповніть своїми даними

# 3. Запустіть
python main.py

# 4. Перевірте
curl http://localhost:5000/health
```

### На Render:

```
1. Push код на GitHub
2. Render автоматично задеплоїть
3. Перевірте: https://your-app.onrender.com/health
4. Встановіть webhook: /set_webhook
5. Тест бота в Telegram
```

---

## 📝 Чеклист після оновлення

- [ ] Всі файли додані в репозиторій
- [ ] .env файл НЕ в репозиторії (перевірте .gitignore)
- [ ] requirements.txt оновлений
- [ ] Render environment variables налаштовані
- [ ] Webhook встановлений
- [ ] /health повертає "healthy"
- [ ] Бот відповідає на /start
- [ ] Меню завантажується з Google Sheets
- [ ] Можна додати товар в кошик
- [ ] Можна оформити замовлення
- [ ] Замовлення зберігається в Google Sheets

---

## 🆘 Якщо щось не працює

### Крок 1: Перевірте логи
```
Render Dashboard → Your Service → Logs
```

### Крок 2: Перевірте health
```
GET https://your-app.onrender.com/health
```

### Крок 3: Перевірте webhook
```
GET https://your-app.onrender.com/set_webhook
```

### Крок 4: Перевірте environment variables
```
Render Dashboard → Environment
Переконайтесь що всі змінні встановлені
```

---

## 📞 Підтримка

Детальні інструкції:
- **README.md** - Загальний огляд
- **SETUP_GUIDE.md** - Покрокова настройка
- **QUICK_DEPLOY.md** - Швидкий старт

**Успішного оновлення! 🚀**
