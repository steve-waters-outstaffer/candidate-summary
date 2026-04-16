from functools import wraps
from flask import request, jsonify
import firebase_admin.auth as auth
import structlog

log = structlog.get_logger()

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized: Missing or invalid token'}), 401

        id_token = auth_header.split('Bearer ')[1]
        try:
            # Verify the ID token using the Firebase Admin SDK
            decoded_token = auth.verify_id_token(id_token)
            # Store the decoded token (which includes the user's UID) in request.user
            request.user = decoded_token
        except Exception as e:
            log.error("auth.verification_failed", error="Invalid token")
            return jsonify({'error': 'Unauthorized: Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated_function
