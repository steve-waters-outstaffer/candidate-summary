from functools import wraps
from flask import request, jsonify
import firebase_admin.auth as auth
import structlog

log = structlog.get_logger()

def require_auth(f):
    """
    Decorator to protect routes that require Firebase Authentication.
    Expects a Bearer token in the Authorization header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            log.warning("auth.missing_header")
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        id_token = auth_header.split('Bearer ')[1]
        try:
            # Verify the ID token while checking if the token is revoked.
            decoded_token = auth.verify_id_token(id_token, check_revoked=True)
            # Store the decoded token in the request object for use in the route if needed.
            request.user = decoded_token
        except auth.RevokedIdTokenError:
            log.error("auth.token_revoked")
            return jsonify({'success': False, 'error': 'Token has been revoked'}), 401
        except auth.ExpiredIdTokenError:
            log.error("auth.token_expired")
            return jsonify({'success': False, 'error': 'Token has expired'}), 401
        except Exception as e:
            # Log the full error but return a generic message to the client
            log.error("auth.verification_failed", error=str(e))
            return jsonify({'success': False, 'error': 'Invalid authentication token'}), 401

        return f(*args, **kwargs)
    return decorated_function
