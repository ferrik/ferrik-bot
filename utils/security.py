from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager
from flask import request, jsonify
import re

limiter = Limiter(key_func=get_remote_address)
jwt = JWTManager()

def validate_input(data):
    """Validate input data to prevent injection attacks."""
    if not data:
        return False
    # Basic sanitization
    if isinstance(data, str):
        return bool(re.match(r'^[\w\s.,!?+-]*$', data))
    return True
