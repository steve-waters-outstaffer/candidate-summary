# backend/helpers/auth_helpers.py

from functools import wraps
from flask import request, jsonify
import firebase_admin.auth
import structlog

log = structlog.get_logger()

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            log.warning("auth.missing_header")
            return jsonify({'success': False, 'error': 'Missing or invalid Authorization header'}), 401

        id_token = auth_header.split('Bearer ')[1]
        try:
            # Verify the ID token using the firebase-admin library
            decoded_token = firebase_admin.auth.verify_id_token(id_token)
            request.user = decoded_token
            log.info("auth.token_verified", uid=decoded_token.get('uid'))
        except Exception as e:
            log.error("auth.verification_failed", error=str(e))
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        return f(*args, **kwargs)
    return decorated_function
