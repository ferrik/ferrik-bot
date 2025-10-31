#!/bin/bash

# 🚀 Ferrik Bot - Швидке налаштування Webhook
# Автоматично встановлює webhook для Telegram бота

echo "🤖 Ferrik Bot - Setup Webhook"
echo "==============================="
echo ""

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Запитуємо дані
echo -e "${YELLOW}Введи BOT_TOKEN:${NC}"
read -r BOT_TOKEN

if [ -z "$BOT_TOKEN" ]; then
    echo -e "${RED}❌ Помилка: BOT_TOKEN не може бути порожнім!${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Введи WEBHOOK_URL (наприклад: https://ferrik-bot.onrender.com):${NC}"
read -r WEBHOOK_URL

if [ -z "$WEBHOOK_URL" ]; then
    echo -e "${RED}❌ Помилка: WEBHOOK_URL не може бути порожнім!${NC}"
    exit 1
fi

# Формуємо повний URL
FULL_WEBHOOK_URL="${WEBHOOK_URL}/webhook"

echo ""
echo "📋 Налаштування:"
echo "   Bot Token: ${BOT_TOKEN:0:10}..."
echo "   Webhook URL: $FULL_WEBHOOK_URL"
echo ""

# Запитуємо підтвердження
echo -e "${YELLOW}Продовжити? (y/n)${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "❌ Скасовано"
    exit 0
fi

echo ""
echo "⏳ Встановлюю webhook..."

# Встановлюємо webhook
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{
        \"url\": \"${FULL_WEBHOOK_URL}\",
        \"allowed_updates\": [\"message\", \"callback_query\"]
    }")

# Перевіряємо результат
if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo -e "${GREEN}✅ Webhook успішно встановлено!${NC}"
    echo ""
    echo "📊 Інформація про webhook:"
    
    # Отримуємо інфо про webhook
    WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo")
    
    echo "$WEBHOOK_INFO" | python3 -m json.tool
    
    echo ""
    echo -e "${GREEN}🎉 Готово! Бот налаштовано!${NC}"
    echo ""
    echo "Наступні кроки:"
    echo "1. Відкрий бота в Telegram"
    echo "2. Надішли /start"
    echo "3. Перевір, що бот відповідає"
    
else
    echo -e "${RED}❌ Помилка встановлення webhook!${NC}"
    echo ""
    echo "Відповідь сервера:"
    echo "$RESPONSE" | python3 -m json.tool
    echo ""
    echo "Можливі причини:"
    echo "- Невірний BOT_TOKEN"
    echo "- Недоступний WEBHOOK_URL"
    echo "- Проблеми з SSL сертифікатом"
    exit 1
fi

echo ""
echo "🔍 Для перевірки виконай:"
echo "curl \"https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo\""