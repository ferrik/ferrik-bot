# 📝 Ferrik Bot - Cheatsheet всіх команд

## 🤖 Telegram Bot API

### Встановити webhook
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.onrender.com/webhook",
    "allowed_updates": ["message", "callback_query"],
    "drop_pending_updates": true
  }'
```

### Перевірити webhook
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

### Видалити webhook
```bash
curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

### Отримати інфо про бота
```bash
curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

### Очистити pending updates
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://your-app.onrender.com/webhook" \
  -d "drop_pending_updates=true"
```

---

## 🗄️ PostgreSQL Commands

### Підключення
```bash
# На Render
psql $DATABASE_URL

# Локально
psql -h localhost -U ferrik_user -d ferrik_db
```

### Перевірка таблиць
```sql
-- Список таблиць
\dt

-- Структура таблиці
\d user_profiles

-- Вихід
\q
```

### Базові запити
```sql
-- Кількість користувачів
SELECT COUNT(*) FROM user_profiles;

-- Кількість замовлень
SELECT COUNT(*) FROM orders;

-- Замовлення сьогодні
SELECT COUNT(*) FROM orders WHERE DATE(created_at) = CURRENT_DATE;

-- Топ користувачів
SELECT user_id, total_orders, total_spent 
FROM user_profiles 
ORDER BY total_spent DESC 
LIMIT 10;

-- Популярні товари
SELECT 
    item->>'name' as name,
    COUNT(*) as times_ordered
FROM orders, jsonb_array_elements(items_json) as item
GROUP BY item->>'name'
ORDER BY times_ordered DESC
LIMIT 10;

-- Денна статистика
SELECT 
    DATE(created_at) as date,
    COUNT(*) as orders,
    SUM(total_amount) as revenue
FROM orders
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 7;
```

### Очистка даних
```sql
-- Видалити старі кошики (>7 днів)
DELETE FROM user_carts 
WHERE updated_at < NOW() - INTERVAL '7 days';

-- Видалити тестові дані
DELETE FROM user_profiles WHERE user_id = 123456789;
DELETE FROM orders WHERE user_id = 123456789;
```

### Backup і Restore
```bash
# Backup
pg_dump $DATABASE_URL > backup.sql

# Restore
psql $DATABASE_URL < backup.sql
```

---

## 🐳 Git Commands

### Оновити код
```bash
git add .
git commit -m "✨ Update to Ferrik Bot 2.0"
git push origin main
```

### Скинути до попередньої версії
```bash
git log --oneline  # Знайти commit hash
git reset --hard <commit-hash>
git push -f origin main
```

### Створити новий branch
```bash
git checkout -b feature/new-feature
git push -u origin feature/new-feature
```

---

## 🌐 Render.com

### Manual Deploy
```
Dashboard → Web Service → Manual Deploy → Deploy latest commit
```

### Перезапустити сервіс
```
Dashboard → Web Service → Settings → Suspend → Resume
```

### Переглянути логи
```
Dashboard → Web Service → Logs
```

### Отримати URL
```
Dashboard → Web Service → Settings → Copy URL
```

---

## 🧪 Testing Commands

### Перевірка сервера
```bash
curl https://your-app.onrender.com/
```

### Health check
```bash
curl https://your-app.onrender.com/health
```

### Load testing
```bash
# Apache Bench
ab -n 100 -c 10 https://your-app.onrender.com/

# wrk (якщо встановлено)
wrk -t4 -c100 -d30s https://your-app.onrender.com/
```

---

## 🐍 Python Local Development

### Віртуальне середовище
```bash
# Створити
python3 -m venv venv

# Активувати (Linux/Mac)
source venv/bin/activate

# Активувати (Windows)
venv\Scripts\activate

# Деактивувати
deactivate
```

### Встановити залежності
```bash
pip install -r requirements.txt
```

### Запустити локально
```bash
# Development mode
python main.py

# Production mode
gunicorn main:app --bind 0.0.0.0:5000
```

### Оновити requirements
```bash
pip freeze > requirements.txt
```

---

## 📊 Google Sheets API

### Перевірка доступу (в Python)
```python
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

sheet = client.open_by_key('YOUR_SHEET_ID')
print(sheet.worksheets())
```

### Дати доступ Service Account
```
Google Sheets → Share → Add email з credentials.json (client_email) → Editor
```

---

## 🔍 Debugging Commands

### Перевірити environment variables
```bash
# На Render (в Shell)
echo $BOT_TOKEN
echo $DATABASE_URL
echo $GOOGLE_SHEETS_ID

# Локально
cat .env
```

### Python debug mode
```bash
# В main.py змінити:
app.run(debug=True, host='0.0.0.0', port=5000)
```

### Детальні логи
```python
# В main.py додати:
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🛠️ Maintenance Commands

### Очистка кешу (якщо використовується Redis)
```bash
redis-cli FLUSHALL
```

### Перевірка розміру БД
```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
```

### Vacuum БД (оптимізація)
```sql
VACUUM ANALYZE;
```

### Переіндексація
```sql
REINDEX DATABASE ferrik_db;
```

---

## 📱 Telegram Bot Commands (для користувачів)

```
/start - Початок роботи з ботом
/menu - Показати меню
/cart - Переглянути кошик
/help - Допомога
/cancel - Скасувати поточну дію
```

---

## 🚨 Emergency Commands

### Якщо бот впав
```bash
# 1. Перевірити статус
curl https://your-app.onrender.com/health

# 2. Переглянути логи на Render
Dashboard → Logs → Фільтр по ERROR

# 3. Перезапустити
Render → Settings → Suspend → Resume

# 4. Перевстановити webhook
curl -X POST https://api.telegram.org/botTOKEN/setWebhook \
  -d "url=https://your-app.onrender.com/webhook" \
  -d "drop_pending_updates=true"
```

### Якщо БД недоступна
```bash
# Перевірити з'єднання
psql $DATABASE_URL -c "SELECT 1"

# Перезапустити БД на Render
Dashboard → PostgreSQL → Restart
```

### Rollback до попередньої версії
```bash
git log --oneline
git revert <last-commit-hash>
git push origin main
```

---

## 🔐 Security

### Rotuvate bot token
```
1. @BotFather → /revoke
2. Отримати новий токен
3. Оновити BOT_TOKEN на Render
4. Перевстановити webhook
```

### Regenerate database credentials
```
1. Render → PostgreSQL → Settings → Reset credentials
2. Оновити DATABASE_URL на Web Service
3. Restart сервісу
```

---

## 📈 Analytics Queries

### Conversion funnel
```sql
SELECT 
    COUNT(DISTINCT user_id) as total_users,
    COUNT(DISTINCT CASE WHEN total_orders > 0 THEN user_id END) as converted_users,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN total_orders > 0 THEN user_id END) / COUNT(DISTINCT user_id), 2) as conversion_rate
FROM user_profiles;
```

### Revenue by day
```sql
SELECT 
    DATE(created_at) as date,
    COUNT(*) as orders,
    SUM(total_amount) as revenue,
    AVG(total_amount) as avg_order_value
FROM orders
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### User retention
```sql
SELECT 
    user_id,
    MIN(created_at) as first_order,
    MAX(created_at) as last_order,
    COUNT(*) as total_orders,
    DATE_PART('day', MAX(created_at) - MIN(created_at)) as days_active
FROM orders
GROUP BY user_id
HAVING COUNT(*) > 1
ORDER BY total_orders DESC;
```

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Deploy | `git push origin main` |
| Check logs | Render Dashboard → Logs |
| Restart bot | Render → Suspend → Resume |
| Test webhook | `curl BOT_API/getWebhookInfo` |
| Connect DB | `psql $DATABASE_URL` |
| Backup DB | `pg_dump $DATABASE_URL > backup.sql` |
| Run locally | `python main.py` |

---

## 🔗 Important Links

- **Render Dashboard:** https://dashboard.render.com
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **Google Cloud Console:** https://console.cloud.google.com
- **GitHub Repo:** https://github.com/ferrik/ferrik-bot

---

**💡 Tip:** Додай цей файл в закладки для швидкого доступу!

✨ Усе найнеобхідніше в одному місці!
