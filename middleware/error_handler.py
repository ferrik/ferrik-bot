import functools
import os
from services.logger import setup_logger

logger = setup_logger()

def handler_guard(func):
    """Decorator to wrap Telegram handlers to catch exceptions and log them.
    
    Usage:
        @handler_guard
        def my_handler(chat_id, text):
            # handler code
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("Unhandled exception in handler %s: %s", func.__name__, e)
            
            # Try to notify admin via Telegram
            try:
                from services import telegram as tg_service
                admin_id = int(os.getenv('ADMIN_TELEGRAM_ID', 0))
                if admin_id:
                    error_msg = f"🚨 Error in handler {func.__name__}:\n\n{str(e)[:200]}"
                    tg_service.tg_send_message(admin_id, error_msg)
            except Exception as notify_err:
                logger.debug("Failed to notify admin via bot: %s", notify_err)
            
            # Re-raise or swallow based on your needs
            # raise  # Uncomment if you want to re-raise
    
    return wrapper