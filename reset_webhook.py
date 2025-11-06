#!/usr/bin/env python3
"""
Скрипт для скидання webhook Telegram бота
"""
import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://ferrik-bot-zvev.onrender.com')

async def reset_webhook():
    """Скинути та встановити webhook"""
    bot = Bot(token=BOT_TOKEN)
    
    print("🔄 Отримую поточну інформацію про webhook...")
    webhook_info = await bot.get_webhook_info()
    print(f"📍 Поточний webhook: {webhook_info.url}")
    print(f"📊 Pending updates: {webhook_info.pending_update_count}")
    
    print("\n❌ Видаляю старий webhook...")
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook видалено!")
    
    print("\n⏳ Встановлюю новий webhook...")
    new_webhook = f"{WEBHOOK_URL}/webhook"
    success = await bot.set_webhook(
        url=new_webhook,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )
    
    if success:
        print(f"✅ Webhook встановлено: {new_webhook}")
    else:
        print("❌ Помилка встановлення webhook")
    
    print("\n📋 Перевірка нового webhook...")
    webhook_info = await bot.get_webhook_info()
    print(f"📍 URL: {webhook_info.url}")
    print(f"📊 Pending updates: {webhook_info.pending_update_count}")
    print(f"🔐 Max connections: {webhook_info.max_connections}")
    print(f"🔄 Allowed updates: {webhook_info.allowed_updates}")
    
    if webhook_info.last_error_date:
        print(f"\n⚠️ Остання помилка: {webhook_info.last_error_message}")

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 TELEGRAM BOT WEBHOOK RESET")
    print("=" * 60)
    asyncio.run(reset_webhook())
    print("\n" + "=" * 60)
    print("✅ ГОТОВО!")
    print("=" * 60)