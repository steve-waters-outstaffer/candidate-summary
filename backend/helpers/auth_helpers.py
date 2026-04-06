# backend/helpers/auth_helpers.py
import structlog
from flask import request, jsonify
from functools import wraps
from firebase_admin import auth

log = structlog.get_logger()

def require_auth(f):
    """
    Decorator to protect routes with Firebase ID token verification.
    Expects a Bearer token in the Authorization header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            log.warning("auth.missing_token")
            return jsonify({'success': False, 'error': 'Missing or invalid Authorization header'}), 401

        id_token = auth_header.split('Bearer ')[1]
        try:
            # Verify the ID token using the Firebase Admin SDK
            # check_revoked=True adds a bit of latency but is more secure
            decoded_token = auth.verify_id_token(id_token, check_revoked=True)
            # You can attach the decoded token to the request for use in the route
            request.user = decoded_token
            log.info("auth.token_verified", uid=decoded_token.get('uid'))
        except auth.ExpiredIdTokenError:
            log.warning("auth.token_expired")
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        except auth.InvalidIdTokenError:
            log.warning("auth.token_invalid")
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        except Exception as e:
            log.error("auth.verification_error", error=str(e))
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401

        return f(*args, **kwargs)
    return decorated_function
