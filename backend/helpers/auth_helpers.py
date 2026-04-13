# backend/helpers/auth_helpers.py
from functools import wraps
from flask import request, jsonify
import firebase_admin.auth
import structlog

log = structlog.get_logger()

def require_auth(f):
    """
    Decorator to require Firebase Authentication.
    Expects a Bearer token in the Authorization header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            log.warning("auth.missing_token")
            return jsonify({'success': False, 'error': 'Unauthorized: Missing or invalid token'}), 401

        id_token = auth_header.split('Bearer ')[1]
        try:
            # Verify the ID token using Firebase Admin SDK
            decoded_token = firebase_admin.auth.verify_id_token(id_token)
            # Attach the user info to the request for use in the route if needed
            request.user = decoded_token
            return f(*args, **kwargs)
        except Exception as e:
            log.error("auth.verification_failed", error=str(e))
            return jsonify({'success': False, 'error': 'Unauthorized: Token verification failed'}), 401

    return decorated_function
