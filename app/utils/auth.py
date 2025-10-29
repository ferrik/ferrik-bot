"""
🔐 AUTHENTICATION - Безпека адмін-функцій
Перевірка прав доступу до чутливих операцій
"""

import os
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

# Отримати токен з .env
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

if not ADMIN_TOKEN:
    logger.warning("⚠️ ADMIN_TOKEN not set! Admin endpoints will be disabled.")


def require_admin_token(f):
    """
    Декоратор для перевірки адмін-токена
    
    Використання:
    @app.route('/admin/endpoint', methods=['POST'])
    @require_admin_token
    def admin_endpoint():
        return {"ok": True}
    
    Запит:
    curl -H "X-Admin-Token: secret_token" http://localhost:5000/admin/endpoint
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Отримати токен з заголовку
        token = request.headers.get('X-Admin-Token')
        
        # Перевірити токен
        if not token:
            logger.warning(f"❌ Missing admin token from {request.remote_addr}")
            return jsonify({
                "error": "Missing X-Admin-Token header",
                "code": 401
            }), 401
        
        if token != ADMIN_TOKEN:
            logger.warning(f"❌ Invalid admin token from {request.remote_addr}")
            return jsonify({
                "error": "Invalid admin token",
                "code": 401
            }), 401
        
        # Токен валідний
        logger.info(f"✅ Admin access granted to {request.remote_addr}")
        return f(*args, **kwargs)
    
    return decorated_function


def get_admin_token() -> str:
    """Отримати адмін-токен (ТІЛЬКИ для налаштування)"""
    return ADMIN_TOKEN


def set_admin_token(token: str):
    """Встановити адмін-токен (ПОТРІБНО ПЕРЕЗАПУСТИТИ)"""
    global ADMIN_TOKEN
    ADMIN_TOKEN = token
    logger.info("🔐 Admin token updated")
