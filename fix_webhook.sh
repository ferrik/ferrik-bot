#!/bin/bash
# ============================================================================
# Швидке виправлення webhook для FerrikBot
# ============================================================================

echo "🤖 FerrikBot Webhook Fix Script"
echo "================================"

# Перевірка BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Помилка: BOT_TOKEN не встановлена"
    echo "Встановіть: export BOT_TOKEN=your_token"
    exit 1
fi

WEBHOOK_URL="${WEBHOOK_URL:-https://ferrik-bot-zvev.onrender.com}"

echo ""
echo "📋 Конфігурація:"
echo "   Bot Token: ${BOT_TOKEN:0:10}..."
echo "   Webhook URL: $WEBHOOK_URL"
echo ""

# 1. Отримати поточну інформацію
echo "1️⃣ Отримую поточну інформацію про webhook..."
CURRENT=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo")
echo "$CURRENT" | python3 -m json.tool

# 2. Видалити webhook
echo ""
echo "2️⃣ Видаляю старий webhook..."
DELETE_RESULT=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/deleteWebhook?drop_pending_updates=true")
echo "$DELETE_RESULT" | python3 -m json.tool

# 3. Встановити новий webhook
echo ""
echo "3️⃣ Встановлюю новий webhook..."
NEW_WEBHOOK="$WEBHOOK_URL/webhook"
SET_RESULT=$(curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$NEW_WEBHOOK\", \"allowed_updates\": [\"message\", \"callback_query\"], \"drop_pending_updates\": true}")
echo "$SET_RESULT" | python3 -m json.tool

# 4. Перевірка
echo ""
echo "4️⃣ Перевірка нового webhook..."
VERIFY=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo")
echo "$VERIFY" | python3 -m json.tool

echo ""
echo "================================"
echo "✅ Готово!"
echo ""
echo "Перевірте що webhook встановлений на:"
echo "   $NEW_WEBHOOK"
echo ""
