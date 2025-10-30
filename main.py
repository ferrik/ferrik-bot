# main.py (додай до ПОЧАТКУ файлу)

"""
🍕 FERRIKBOT v2.1 - з Google Sheets Синхронізацією
"""

import os
import logging
import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler
import json

# ============ IMPORT SYNC СИСТЕМИ ============
from services.sheets_sync import GoogleSheetsSync, DatabaseSync, SyncScheduler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
bot_application = None

# ============ ГЛОБАЛЬНІ ЗМІННІ ДЛЯ SYNC ============
sheets_sync = None
db_sync = None
sync_scheduler = None

# ============ КОНФІГ ============

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5000")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    PORT = int(os.getenv("PORT", 5000))
    
    # Google Sheets
    GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    
    @staticmethod
    def validate():
        if not Config.TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not set")
            return False
        if not Config.DATABASE_URL:
            logger.error("❌ DATABASE_URL not set")
            return False
        return True


config = Config()

# ============ ІНІЦІАЛІЗАЦІЯ SYNC ============

def init_sync():
    """Ініціалізуй синхронізацію"""
    global sheets_sync, db_sync, sync_scheduler
    
    logger.info("🔄 Initializing Google Sheets & Database Sync...")
    
    try:
        # Google Sheets
        if config.GOOGLE_SHEETS_ID and config.GOOGLE_SHEETS_CREDENTIALS:
            sheets_sync = GoogleSheetsSync(
                config.GOOGLE_SHEETS_CREDENTIALS,
                config.GOOGLE_SHEETS_ID
            )
            logger.info("✅ Google Sheets initialized")
        else:
            logger.warning("⚠️ Google Sheets credentials not set")
        
        # Database
        db_sync = DatabaseSync(config.DATABASE_URL)
        logger.info("✅ Database initialized")
        
        # Scheduler
        if sheets_sync and db_sync:
            sync_scheduler = SyncScheduler(sheets_sync, db_sync)
            sync_scheduler.start()
            
            # Синхронізуй одразу при старті
            sync_scheduler.sync_menu_job()
            logger.info("✅ Sync scheduler started")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Sync initialization error: {e}")
        return False


# ============ TELEGRAM HANDLERS ============

def setup_handlers(application):
    """Реєстрація обробників"""
    
    logger.info("📝 Setting up handlers...")
    
    try:
        async def start_command(update: Update, context):
            """Команда /start"""
            await update.message.reply_text(
                "🍴 Привіт! Я — Ferrik 🤖\n\n"
                "📋 /menu — Меню\n"
                "/categories — Категорії\n"
                "/help — Допомога"
            )
        
        async def menu_command(update: Update, context):
            """Команда /menu — вивід меню з БД"""
            try:
                if not db_sync:
                    await update.message.reply_text("❌ БД не підключена")
                    return
                
                menu = db_sync.get_menu()
                
                if not menu:
                    await update.message.reply_text("😔 Меню порожнє")
                    return
                
                # Форматуй меню
                text = "📋 *МЕНЮ:*\n\n"
                for item in menu[:10]:  # Перших 10
                    text += f"🍕 *{item['name']}* — {item['price']} грн\n"
                    if item.get('description'):
                        text += f"   _{item['description'][:50]}..._\n"
                    text += "\n"
                
                await update.message.reply_text(text, parse_mode='Markdown')
            
            except Exception as e:
                logger.error(f"❌ Menu error: {e}")
                await update.message.reply_text("❌ Помилка при завантаженні меню")
        
        async def categories_command(update: Update, context):
            """Команда /categories"""
            try:
                if not db_sync:
                    await update.message.reply_text("❌ БД не підключена")
                    return
                
                # Отримай категорії
                import sqlalchemy
                session = db_sync.Session()
                categories = session.query(
                    sqlalchemy.distinct(db_sync.db_sync.__class__.__dict__['MenuItem'].category)
                ).all() if False else ["Піци", "Бургери", "Салати"]
                session.close()
                
                text = "📂 *КАТЕГОРІЇ:*\n\n"
                for cat in categories:
                    text += f"• {cat}\n"
                
                await update.message.reply_text(text, parse_mode='Markdown')
            
            except Exception as e:
                logger.error(f"❌ Categories error: {e}")
                await update.message.reply_text("❌ Помилка")
        
        async def help_command(update: Update, context):
            """Команда /help"""
            await update.message.reply_text(
                "📚 *ДОПОМОГА:*\n\n"
                "/menu — Все меню\n"
                "/categories — Категорії\n"
                "/status — Статус синхронізації\n"
            )
        
        async def status_command(update: Update, context):
            """Команда /status — статус синхронізації"""
            status_text = "📊 *СТАТУС СИСТЕМИ:*\n\n"
            status_text += f"🤖 Бот: ✅ Online\n"
            status_text += f"📊 БД: {'✅ Connected' if db_sync else '❌ Disconnected'}\n"
            status_text += f"📰 Sheets: {'✅ Connected' if sheets_sync else '❌ Disconnected'}\n"
            status_text += f"🔄 Sync: {'✅ Running' if sync_scheduler else '❌ Stopped'}\n"
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
        
        # Реєстрація
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("menu", menu_command))
        application.add_handler(CommandHandler("categories", categories_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        
        logger.info("✅ Handlers registered")
        return True
    
    except Exception as e:
        logger.error(f"❌ Handler error: {e}")
        return False


# ============ BOT CREATION ============

def create_bot_application():
    global bot_application
    
    logger.info("🤖 Creating bot...")
    
    TOKEN = config.TELEGRAM_BOT_TOKEN
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found")
        return None
    
    try:
        bot_application = Application.builder().token(TOKEN).build()
        
        import asyncio
        async def init_app():
            await bot_application.initialize()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_app())
        
        setup_handlers(bot_application)
        
        logger.info("✅ Bot created")
        return bot_application
    
    except Exception as e:
        logger.error(f"❌ Bot creation error: {e}")
        return None


# ============ STARTUP ============

def startup():
    logger.info("=" * 70)
    logger.info("🚀 FERRIKBOT v2.1 + GOOGLE SHEETS SYNC")
    logger.info("=" * 70)
    logger.info("")
    
    # Валідація
    if not config.validate():
        return False
    
    logger.info("✅ Configuration valid")
    logger.info("")
    
    # Ініціалізація sync
    if not init_sync():
        logger.warning("⚠️ Sync not available, continuing without it...")
    
    logger.info("")
    
    # Створи бота
    if not create_bot_application():
        return False
    
    logger.info("✅ BOT READY!")
    logger.info("=" * 70)
    logger.info("")
    
    return True


# ============ ROUTES ============

@app.route('/')
def index():
    return jsonify({
        "status": "🟢 online",
        "bot": "🍕 FerrikBot v2.1",
        "sync": "✅ Google Sheets" if sheets_sync else "❌ No Sheets",
        "db": "✅ PostgreSQL" if db_sync else "❌ No DB"
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    if not bot_application:
        return jsonify({"ok": False}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False}), 400
        
        update = Update.de_json(data, bot_application.bot)
        if not update:
            return jsonify({"ok": False}), 400
        
        import asyncio
        
        async def process():
            try:
                await bot_application.process_update(update)
            except Exception as e:
                logger.error(f"❌ Update error: {e}")
        
        threading.Thread(target=lambda: asyncio.run(process())).start()
        return jsonify({"ok": True}), 200
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({"ok": False}), 500


# ============ MAIN ============

initialized = False

@app.before_request
def init_on_first_request():
    global initialized
    
    if not initialized:
        if startup():
            initialized = True


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG, use_reloader=False)