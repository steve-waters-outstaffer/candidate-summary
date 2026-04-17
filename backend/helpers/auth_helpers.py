from functools import wraps
from flask import request, jsonify
import firebase_admin.auth
import structlog

log = structlog.get_logger()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid Authorization header'}), 401

        id_token = auth_header.split('Bearer ')[1]
        try:
            decoded_token = firebase_admin.auth.verify_id_token(id_token)
            request.user = decoded_token
        except Exception as e:
            log.error("auth.verify_token.failed", error=str(e))
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        return f(*args, **kwargs)
    return decorated
