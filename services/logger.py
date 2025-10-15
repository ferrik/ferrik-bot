import logging
import os

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
except Exception:
    sentry_sdk = None

def setup_logger():
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger("ferrik_bot")
    
    if logger.handlers:
        return logger
    
    logger.setLevel(LOG_LEVEL)
    ch = logging.StreamHandler()
    ch.setLevel(LOG_LEVEL)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Init Sentry if DSN provided
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_sdk and sentry_dsn:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        sentry_sdk.init(dsn=sentry_dsn, integrations=[sentry_logging])
        logger.info("Sentry initialized")
    
    return logger