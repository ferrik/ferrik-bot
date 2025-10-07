# 🤖 Hubsy Bot - AI-Powered Food Ordering Assistant

Розумний Telegram-бот для замовлення їжі з інтеграцією штучного інтелекту (Gemini AI) та Google Sheets.

## ✨ Функції (Phase 2)

### 🎯 Основні можливості:
- **📋 Інтерактивне меню** з категоріями та навігацією
- **🔍 Розумний пошук** - "хочу щось солодке" → AI знайде десерти
- **✨ AI-рекомендації** на основі історії замовлень
- **🛒 Кошик** з підрахунком суми
- **📜 Історія замовлень** - швидке повторне замовлення
- **🔥 Популярні страви** - трекінг найчастіших замовлень
- **💬 Персоналізація** - бот запам'ятовує уподобання

### 🤖 AI-Features:
1. **Розумний пошук у вільній формі**
   - "Хочу м'ясне" → показує бургери/піцу з м'ясом
   - "Щось швидке" → страви з коротким часом приготування
   
2. **Персональні рекомендації**
   - Аналізує історію замовлень
   - Пропонує схожі страви
   
3. **Діалог з користувачем**
   - Відповідає на питання про меню
   - Допомагає з вибором

## 🏗️ Архітектура

```
ferrik-bot/
├── main.py                 # Flask app + bot logic
├── config.py              # Configuration
├── services/
│   ├── telegram.py        # Telegram API wrapper
│   ├── sheets.py          # Google Sheets integration
│   └── gemini.py          # AI (Gemini) integration
├── requirements.txt       # Dependencies
├── .gitignore            # Security
└── .env.example          # Environment template
```

## 📊 Google Sheets Structure

### Аркуш "Меню":
| ID | Категорія | Страви | Опис | Ціна | Ресторан | Рейтинг | Активний |
|----|-----------|--------|------|------|----------|---------|----------|
| PZ001 | Піца | Маргарита | Сир, томати | 150 | Челентано | 4.5 | Так |

### Аркуш "Замовлення":
| ID Замовлення | Telegram User ID | Час | Товари (JSON) | Сума | Статус |
|---------------|------------------|-----|---------------|------|--------|
| ORD-xxx | 123456 | 2025-01-01 | [...] | 300 | Нове |

## 🚀 Deployment (Render)

### 1. Environment Variables:

```bash
# Telegram
BOT_TOKEN=your_bot_token
WEBHOOK_SECRET=your_secure_secret_32chars

# Google Sheets
GOOGLE_SHEET_ID=your_spreadsheet_id
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}

# AI
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL_NAME=gemini-2.0-flash-exp

# Optional
OPERATOR_CHAT_ID=your_telegram_id
DEBUG=False
PORT=10000
```

### 2. Згенеруйте WEBHOOK_SECRET:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### 3. Встановіть webhook:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.onrender.com/webhook",
    "secret_token": "YOUR_WEBHOOK_SECRET"
  }'
```

## 🔒 Безпека

- ✅ Секрети НЕ в коді (тільки ENV)
- ✅ Webhook authentication через X-Telegram-Bot-Api-Secret-Token
- ✅ HTML escaping для захисту від injection
- ✅ Thread-safe операції з корзинами
- ✅ Rate limiting готовий

## 📈 Аналітика

Бот автоматично трекає:
- 📊 Популярність страв (Counter)
- 📜 Історію замовлень користувачів
- 🎯 Уподобання (які категорії обирають)

## 🛠️ Local Development

```bash
# 1. Clone
git clone https://github.com/ferrik/ferrik-bot.git
cd ferrik-bot

# 2. Install
pip install -r requirements.txt

# 3. Create .env
cp .env.example .env
# Заповніть змінні

# 4. Run
python main.py
```

## 📝 User Flow

```
/start
  ↓
Головне меню
  ↓
├─→ 🍽️ Меню → Категорії → Карусель страв → Додати
├─→ 🔥 Популярне → Топ-3 страви
├─→ 🔍 Пошук (AI) → Результати
├─→ ✨ AI-Порада → Персональні рекомендації
├─→ 🛒 Кошик → Оформити → ✅ Готово
└─→ 📜 Історія → Повторити замовлення
```

## 🎨 UX Improvements (Phase 2)

1. **FSM (Finite State Machine)** - контекст користувача
2. **Карусель з навігацією** - ⬅️ 1/5 ➡️
3. **Кнопка "Назад"** на кожному кроці
4. **Персоналізація** - "Привіт, Ім'я! Бачу ти любиш Піцу 😉"
5. **Історія** - швидке повторне замовлення

## 🤖 AI Integration

### Gemini API використовується для:

1. **Пошук** - розуміє запити у вільній формі
2. **Рекомендації** - аналіз історії + персоналізація
3. **Діалог** - відповідає на питання користувачів

### Промпти оптимізовані для:
- Короткі відповіді (2-3 речення)
- Українська мова
- Дружній тон
- Конкретність

## 📊 Performance

- **Menu cache**: 5 хвилин TTL
- **Thread-safe**: RLock для корзин/станів
- **Retry logic**: 2 спроби для AI requests
- **Logging**: Structured logging з timestamp

## 🔮 Roadmap (Phase 3)

- [ ] 📸 Фото страв з Google Sheets
- [ ] 💳 Онлайн оплата (LiqPay/Stripe)
- [ ] 📍 Відстеження доставки
- [ ] 👤 Профіль користувача
- [ ] 🎁 Промокоди та знижки
- [ ] 📊 Admin Dashboard (analytics)
- [ ] 🌐 Multi-restaurant support
- [ ] 📱 Push-повідомлення про статус

## 🆘 Troubleshooting

### Бот не відповідає:
```bash
# 1. Перевірте webhook
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# 2. Перевірте health
curl https://your-app.onrender.com/health

# 3. Перевірте логи на Render
# Dashboard → Logs
```

### Меню порожнє:
1. Перевірте GOOGLE_SHEET_ID
2. Додайте Service Account email до таблиці (Share → Editor)
3. Перевірте аркуш "Меню" існує
4. Перевірте колонка "Активний" = "Так"

### AI не працює:
1. Перевірте GEMINI_API_KEY
2. Змініть GEMINI_MODEL_NAME на `gemini-2.0-flash-exp`
3. Перевірте квоти на https://aistudio.google.com

## 📞 Support

- Issues: https://github.com/ferrik/ferrik-bot/issues
- Telegram: @ferrikfoot_bot

## 📄 License

MIT License - використовуйте як хочете!

---

**Made with 💙 in Ukraine**# 🔧 Інструкція по заміні файлів

## 📋 CHECKLIST - Які файли замінити

### ✅ ПОВНІСТЮ ЗАМІНИТИ (скопіювати весь код):

1. **`main.py`** ← Артефакт `full_main_py`
2. **`config.py`** ← Артефакт `full_config_py`
3. **`services/sheets.py`** ← Артефакт `full_sheets_py`
4. **`services/telegram.py`** ← Артефакт `full_telegram_py`
5. **`services/gemini.py`** ← Артефакт `full_gemini_py`
6. **`services/database.py`** ← Артефакт `full_database_py`

### ✅ НОВІ ФАЙЛИ (створити і додати код):

7. **`utils/html_formatter.py`** ← Артефакт `full_html_formatter`
8. **`utils/price_handler.py`** ← Артефакт `full_price_handler`
9. **`config/field_mapping.py`** ← Артефакт `full_field_mapping`
10. **`tests/test_quick.py`** ← Артефакт `full_quick_test`
11. **`run_after_install.py`** ← Артефакт `final_integration_test`

### ✅ КОНФІГУРАЦІЯ:

12. **`.env.example`** ← Створити з прикладу вище
13. **`.gitignore`** ← Оновити (додати рядки)
14. **`requirements.txt`** ← Оновити (додати redis)

---

## 🚀 ШВИДКИЙ СТАРТ (3 простих кроки)

### Крок 1: Backup
```bash
cd ~/ferrik-bot
git add .
git commit -m "backup: before critical fixes"
git checkout -b fix/security-and-precision
```

### Крок 2: Створити структуру
```bash
mkdir -p utils config state tests data
touch utils/__init__.py
touch config/__init__.py
touch state/__init__.py
touch tests/__init__.py
```

### Крок 3: Скопіювати файли
Відкрийте кожен артефакт і скопіюйте **ВЕСЬ КОД**:

#### 3.1 Нові модулі (utils/config):
- `utils/html_formatter.py` ← full_html_formatter
- `utils/price_handler.py` ← full_price_handler
- `config/field_mapping.py` ← full_field_mapping

#### 3.2 Основні файли (ЗАМІНА):
- `main.py` ← full_main_py ⚠️ **BACKUP перед заміною!**
- `config.py` ← full_config_py
- `services/sheets.py` ← full_sheets_py
- `services/telegram.py` ← full_telegram_py
- `services/gemini.py` ← full_gemini_py
- `services/database.py` ← full_database_py

#### 3.3 Тести:
- `tests/test_quick.py` ← full_quick_test
- `run_after_install.py` ← final_integration_test

---

## ⚙️ НАЛАШТУВАННЯ

### 1. Оновити requirements.txt
```bash
# Додайте ці рядки:
redis==5.0.0
```

```bash
pip install -r requirements.txt
```

### 2. Налаштувати .env
```bash
cp .env.example .env
nano .env
```

**Обов'язково:**
- `BOT_TOKEN=` ← від @BotFather
- `WEBHOOK_SECRET=` ← згенерувати: `python run_after_install.py --secret`
- `GOOGLE_SHEET_ID=`
- `GOOGLE_CREDENTIALS_JSON=`
- `OPERATOR_CHAT_ID=`

### 3. Перевірити
```bash
# Швидкі тести
python tests/test_quick.py

# Фінальна перевірка
python run_after_install.py

# Має вивести:
# ✅ Passed: 10
# ❌ Failed: 0
```

---

## 🧪 ТЕСТУВАННЯ

### Базові тести
```bash
# 1. Імпорти
python -c "from utils.html_formatter import escape_field; print('✅ OK')"
python -c "from utils.price_handler import parse_price; print('✅ OK')"
python -c "import main; print('✅ OK')"

# 2. Config
python -c "import config; print('✅ OK')"

# 3. XSS тест
python -c "from utils.html_formatter import escape_field; assert '<script>' not in escape_field('<script>'); print('✅ XSS blocked')"

# 4. Decimal тест
python -c "from utils.price_handler import parse_price; from decimal import Decimal; assert parse_price('0.1') + parse_price('0.2') == Decimal('0.3'); print('✅ Decimal works')"
```

### Запустити бота
```bash
python main.py
```

**Очікується вивід:**
```
====================================
INITIALIZING BOT
====================================
Loading menu...
✅ Menu loaded: XX items
Setting up webhook...
✅ Webhook configured
====================================
✅ BOT INITIALIZED SUCCESSFULLY
====================================
```

---

## 📊 ЩО ВИПРАВЛЕНО

### 🔐 Security (CRITICAL):
- ✅ **XSS захист** - всі user дані escaped
- ✅ **Webhook secret** - перевірка при кожному запиті
- ✅ **Input санітизація** - очищення HTML з запитів

### 💰 Precision (CRITICAL):
- ✅ **Decimal замість float** - точність 0.1 + 0.2 = 0.3
- ✅ **Правильний формат для Sheets** - без 0.30000004
- ✅ **Фінансова точність** - всі розрахунки точні

### 🔄 Architecture:
- ✅ **Field mapping** - уніфіковані ключі
- ✅ **Backward compatibility** - старий код працює
- ✅ **Кращa обробка помилок** - graceful degradation

### 📝 Code Quality:
- ✅ **Type hints** - де можливо
- ✅ **Docstrings** - всі функції документовані
- ✅ **Logging** - детальне логування
- ✅ **Error handling** - proper try/except

---

## 🔍 ПЕРЕВІРКА ПІСЛЯ ЗАПУСКУ

### 1. Security тест в Telegram:
```
Відправте боту: <script>alert(1)</script>
Очікується: текст буде escaped (&lt;script&gt;...)
```

### 2. Precision тест:
```
1. Додайте товар ціною 120.50 грн (2 шт)
2. Додайте товар ціною 99.99 грн (1 шт)
3. Перевірте корзину
Очікується: Разом: 340.99 грн (ТОЧНО, не 340.9900000004)
```

### 3. Webhook тест:
```bash
# Без secret - має бути 401
curl -X POST http://localhost:5000/webhook

# З secret - має працювати
curl -X POST http://localhost:5000/webhook \
  -H "X-Telegram-Bot-Api-Secret-Token: $WEBHOOK_SECRET"
```

### 4. Sheets тест:
```
1. Створіть тестове замовлення
2. Відкрийте Google Sheets
3. Перевірте Orders лист
Очікується: ціни збережені як 120.50 (string, не float)
```

---

## 🐛 TROUBLESHOOTING

### Проблема: ImportError
```bash
# Перевірити структуру
ls -la utils/
ls -la config/

# Має бути __init__.py
touch utils/__init__.py
touch config/__init__.py
```

### Проблема: Config validation failed
```bash
# Перевірити .env
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('BOT_TOKEN'))"
```

### Проблема: Webhook не працює
```bash
# Діагностика
python -c "from services.telegram import tg_get_webhook_info; tg_get_webhook_info()"

# Перевстановити
python -c "from services.telegram import setup_webhook_safe; setup_webhook_safe()"
```

### Проблема: Sheets не працює
```bash
# Тест з'єднання
python -c "from services.sheets import test_sheets_connection; test_sheets_connection()"
```

### Проблема: Тести не проходять
```bash
# Детальна інформація
python run_after_install.py --info

# Показати наступні кроки
python run_after_install.py --next
```

---

## 📦 COMMIT & DEPLOY

```bash
# Перевірити зміни
git status
git diff main.py  # Подивитись що змінилось

# Додати все
git add .

# Commit
git commit -m "fix(critical): Security and precision improvements

- Fixed XSS vulnerability in HTML formatting
- Decimal instead of float for prices (financial precision)
- Unified field mapping system
- Improved webhook security
- Better error handling and logging

Tested: all unit tests pass
Fixes: #ISSUE_NUMBER"

# Push
git push origin fix/security-and-precision

# Створити Pull Request на GitHub
```

---

## 🎯 PRODUCTION DEPLOY

### Якщо використовуєте Heroku:
```bash
# Встановити buildpack
heroku buildpacks:set heroku/python

# Встановити env vars
heroku config:set BOT_TOKEN="your_token"
heroku config:set WEBHOOK_SECRET="your_secret"
# ... інші змінні

# Deploy
git push heroku main

# Перевірити логи
heroku logs --tail
```

### Якщо використовуєте VPS:
```bash
# Gunicorn для production
gunicorn -w 4 -b 0.0.0.0:$PORT main:app

# Або з Systemd service
sudo systemctl restart telegram-bot
sudo systemctl status telegram-bot
```

---

## 📚 ДОДАТКОВІ РЕСУРСИ

### Створені артефакти:
1. `full_main_py` - Повний main.py
2. `full_config_py` - Повний config.py
3. `full_sheets_py` - Повний services/sheets.py
4. `full_telegram_py` - Повний services/telegram.py
5. `full_gemini_py` - Повний services/gemini.py
6. `full_database_py` - Повний services/database.py
7. `full_html_formatter` - utils/html_formatter.py
8. `full_price_handler` - utils/price_handler.py
9. `full_field_mapping` - config/field_mapping.py
10. `full_quick_test` - tests/test_quick.py
11. `final_integration_test` - run_after_install.py
12. `installation_checklist` - Детальний checklist

### Раніше створені (для reference):
- Migration Guide - для безпечного deploy
- Fix Checklist - повний список виправлень
- Test Examples - приклади тестів

---

## ✅ SUCCESS CRITERIA

Все готово якщо:
- [ ] Всі файли скопійовані
- [ ] `python run_after_install.py` показує 0 failed
- [ ] Бот запускається без помилок
- [ ] XSS тест пройдено (escaped)
- [ ] Decimal тест пройдено (0.1+0.2=0.3)
- [ ] Webhook працює (401 без secret)
- [ ] Замовлення зберігаються правильно
- [ ] Ціни в Sheets без 0.300000004

---

## 🆘 ПОТРІБНА ДОПОМОГА?

Якщо щось не працює:
1. Запустіть `python run_after_install.py --info`
2. Перевірте логи: `tail -f bot.log`
3. Перегляньте помилки вище в checklist
4. Напишіть мені з деталями помилки

**Все готово для копіювання!** Успіхів! 🚀