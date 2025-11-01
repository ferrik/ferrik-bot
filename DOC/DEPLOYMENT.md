# 🚀 Ferrik Bot — Production Deployment Checklist

> Повний чеклист для безпечного та надійного деплою

---

## ✅ Pre-Deployment Checklist

### 🔐 Security

- [ ] **Всі секрети в environment variables** (не в коді!)
- [ ] **`.env` додано в `.gitignore`**
- [ ] **credentials.json** не закоміче но
- [ ] **DEBUG=False** в production
- [ ] **SECRET_KEY** змінено з прикладу
- [ ] **ADMIN_USER_IDS** налаштовано
- [ ] **Rate limiting** увімкнено
- [ ] **SSL/TLS** для webhook (HTTPS)

### 🗄️ Database

- [ ] **Схема БД** застосована (`schema_v2.sql`)
- [ ] **Backup стратегія** налаштована
- [ ] **Індекси** створені
- [ ] **Тестові дані** очищені
- [ ] **Migration плани** готові

### 🔌 External Services

- [ ] **Telegram Bot Token** валідний
- [ ] **Webhook URL** доступний (HTTPS)
- [ ] **Google Sheets** credentials налаштовані
- [ ] **Google Sheets** доступ надано Service Account
- [ ] **Spreadsheet ID** правильний
- [ ] **Листи** створені з правильними назвами

### 📊 Monitoring & Logging

- [ ] **Sentry/ErrorTracking** налаштовано (опціонально)
- [ ] **Logs** зберігаються
- [ ] **Metrics** збираються (опціонально)
- [ ] **Health check endpoint** працює
- [ ] **Алерти** налаштовані

### ⚡ Performance

- [ ] **Caching** увімкнено
- [ ] **Rate limiting** протестовано
- [ ] **Database indexes** оптимізовані
- [ ] **Connection pooling** налаштовано

---

## 🏗️ Deployment Steps

### Step 1: Підготовка коду

```bash
# 1. Оновити залежності
pip freeze > requirements.txt

# 2. Перевірити код
python -m pytest tests/
python -m flake8 *.py modules/
python -m black --check *.py modules/

# 3. Commit & Push
git add .
git commit -m "Production ready"
git push origin main
```

### Step 2: Environment Setup

```bash
# На сервері створи .env
nano .env

# Мінімальний production .env:
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook
GOOGLE_SHEETS_CREDENTIALS=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_id
DATABASE_PATH=/var/lib/ferrik/bot.db
PORT=5000
DEBUG=False
LOG_LEVEL=INFO
ENABLE_CACHE=True
RATE_LIMIT_REQUESTS=30
```

### Step 3: Database Migration

```bash
# Створити БД
python -c "from services.database import Database; Database('/var/lib/ferrik/bot.db').init_schema()"

# Backup старої БД (якщо є)
cp bot.db bot.db.backup.$(date +%Y%m%d)

# Застосувати міграції
python manage.py migrate
```

### Step 4: Webhook Setup

```bash
# Встановити webhook
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/webhook"}'

# Перевірити webhook
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

### Step 5: Start Application

#### Option A: Gunicorn (Recommended)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 main:app --timeout 120 --log-level info
```

#### Option B: Systemd Service

```bash
# /etc/systemd/system/ferrik-bot.service
[Unit]
Description=Ferrik Bot
After=network.target

[Service]
Type=simple
User=ferrik
WorkingDirectory=/opt/ferrik-bot
Environment="PATH=/opt/ferrik-bot/venv/bin"
ExecStart=/opt/ferrik-bot/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ferrik-bot
sudo systemctl start ferrik-bot
sudo systemctl status ferrik-bot
```

#### Option C: Docker

```bash
docker build -t ferrik-bot .
docker run -d -p 5000:5000 --env-file .env --name ferrik-bot ferrik-bot
```

---

## 🔍 Post-Deployment Verification

### ✅ Health Checks

```bash
# 1. Server відповідає
curl https://your-domain.com/health
# Очікується: {"status": "healthy"}

# 2. Webhook активний
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
# Очікується: "url": "https://your-domain.com/webhook"

# 3. База даних доступна
python -c "from services.database import Database; print(Database('bot.db').test_connection())"
# Очікується: True

# 4. Google Sheets працює
python -c "from services.sheets import SheetsAPI; print(len(SheetsAPI().get_menu()))"
# Очікується: > 0
```

### 📊 Functional Tests

```bash
# Відправ тестове повідомлення боту
telegram-cli -e "msg @YourBot /start"

# Перевір основні команди:
/start → Має показати вітання
/menu → Має показати меню
/help → Має показати команди
```

### 🔍 Log Review

```bash
# Перегляньперші логи
tail -f logs/bot.log

# Шукай помилки
grep ERROR logs/bot.log
grep WARNING logs/bot.log
```

---

## 🚨 Rollback Plan

### Якщо щось пішло не так:

```bash
# 1. STOP сервіс
sudo systemctl stop ferrik-bot
# або
docker stop ferrik-bot

# 2. Restore backup БД
cp bot.db.backup.YYYYMMDD bot.db

# 3. Rollback code
git checkout previous-stable-tag

# 4. Restart
sudo systemctl start ferrik-bot
```

---

## 📈 Monitoring Setup

### Application Metrics

```python
# В main.py додай endpoint
@app.route('/metrics')
def metrics():
    return {
        'uptime': get_uptime(),
        'users_total': db.count_users(),
        'orders_today': db.count_orders_today(),
        'errors_24h': db.count_errors_24h()
    }
```

### Alerting Rules

```yaml
# alerts.yml
alerts:
  - name: high_error_rate
    condition: error_rate > 5%
    action: send_telegram_notification
    
  - name: webhook_down
    condition: webhook_status != 200
    action: send_telegram_notification
    
  - name: database_slow
    condition: query_time > 1s
    action: log_warning
```

---

## 🔒 Security Hardening

### Server Security

```bash
# 1. Firewall
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# 2. SSH keys only
sudo nano /etc/ssh/sshd_config
# PasswordAuthentication no

# 3. Fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# 4. Updates
sudo apt update && sudo apt upgrade -y
```

### Application Security

```python
# В config.py
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
}
```

---

## 📝 Maintenance Schedule

### Daily
- [ ] Перевірка логів на помилки
- [ ] Моніторинг uptime
- [ ] Backup бази даних

### Weekly
- [ ] Аналіз метрик користувачів
- [ ] Перевірка використання дискового простору
- [ ] Оновлення залежностей (security patches)

### Monthly
- [ ] Повний аудит безпеки
- [ ] Огляд performance метрик
- [ ] Очищення старих логів
- [ ] Database optimization (VACUUM, REINDEX)

---

## 🔄 CI/CD Pipeline (Optional)

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Render
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}
```

---

## 📊 Success Metrics

### Track These KPIs:

- **Uptime:** Target 99.9%
- **Response Time:** < 500ms average
- **Error Rate:** < 0.1%
- **Active Users:** Growing weekly
- **Orders/Day:** Increasing trend
- **Customer Satisfaction:** > 4.5/5.0

---

## 🆘 Emergency Contacts

### Критичні проблеми:

```
1. Server Down → Hosting Support
2. Database Issues → DBA Contact
3. Security Breach → Security Team
4. Payment Failures → Payment Provider
```

### Contact List

```
- DevOps Lead: @username
- Backend Dev: @username
- Database Admin: @username
- Security: security@ferrik.com
```

---

## ✅ Final Checklist

Before going live:

- [ ] All tests passing
- [ ] Security audit completed
- [ ] Backup systems tested
- [ ] Monitoring configured
- [ ] Webhook confirmed working
- [ ] Error tracking active
- [ ] Documentation updated
- [ ] Team notified
- [ ] Rollback plan ready
- [ ] Success metrics baseline captured

---

## 🎉 Go Live!

```bash
# Final command:
sudo systemctl restart ferrik-bot
echo "🚀 Ferrik Bot is now LIVE!"
```

---

<div align="center">

**Production Ready! 🎊**

Monitor, iterate, and scale! 📈

[⬆ Back to Top](#-ferrik-bot--production-deployment-checklist)

</div>
