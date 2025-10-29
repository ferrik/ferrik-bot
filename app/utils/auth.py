"""🔐 Authentication"""
import os
from functools import wraps
from flask import request, jsonify

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def require_admin_token(f):
    """Декоратор для перевірки адмін-токена"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-Admin-Token')
        
        if not token or token != ADMIN_TOKEN:
            return {"error": "Unauthorized", "code": 401}, 401
        
        return f(*args, **kwargs)
    
    return decorated_function
