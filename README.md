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

**Made with 💙 in Ukraine**