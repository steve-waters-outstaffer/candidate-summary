import functools
from flask import request, jsonify
import firebase_admin.auth
import structlog

log = structlog.get_logger()

def require_auth(f):
    """
    Decorator to protect routes with Firebase Authentication.
    Expects a Bearer token in the Authorization header.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            log.warning("auth.missing_header")
            return jsonify({'success': False, 'error': 'Missing or invalid authorization header'}), 401

        id_token = auth_header.split('Bearer ')[1]
        try:
            # Verify the ID token.
            # On Cloud Run, this uses the default app initialized in app.py
            decoded_token = firebase_admin.auth.verify_id_token(id_token)
            # Attach user info to the request for use in the route if needed
            request.user = decoded_token
        except firebase_admin.auth.ExpiredIdTokenError:
            log.warning("auth.token_expired")
            return jsonify({'success': False, 'error': 'Authentication token has expired'}), 401
        except firebase_admin.auth.InvalidIdTokenError:
            log.warning("auth.token_invalid")
            return jsonify({'success': False, 'error': 'Invalid authentication token'}), 401
        except Exception as e:
            # Log the full error but return a generic message
            log.error("auth.verification_failed", error=str(e))
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401

        return f(*args, **kwargs)
    return decorated_function
