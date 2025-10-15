from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity
from functools import wraps
from flask import jsonify
import re

def hash_password(password):
    return generate_password_hash(password)

def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)

def generate_tokens(identity, additional_claims=None):
    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity)
    return access_token, refresh_token

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    # Kenyan phone number validation (accepts 254, 0, +254 formats)
    pattern = r'^(\+254|0|254)[17]\d{8}$'
    return re.match(pattern, phone) is not None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            from app.models import User
            user = User.query.get(user_id)
            
            if not user or not user.is_admin:
                return jsonify({'error': 'Admin access required'}), 403
                
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Authorization failed'}), 401
    return decorated_function