import jwt
from datetime import datetime, timedelta
from flask import current_app

def generate_token(user, expires_in=3600):
    payload = {
        "user_id": user.id,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    return token

def decode_token(token):
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload  # Returns dict with user_id, role, etc.
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None