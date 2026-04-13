# Sentinel Security Journal 🛡️

## 2025-05-15 - Wide-Open Firestore Rules
**Vulnerability:** Firestore rules allowed unauthenticated read/write access to all documents until a future date (Sept 2025).
**Learning:** Default "start in test mode" rules in Firebase are a major risk if not replaced early. They provide a false sense of security with an expiration date.
**Prevention:** Always require `request.auth != null` for all Firestore operations as a baseline, even in development.

## 2025-05-15 - Information Leakage via API Errors
**Vulnerability:** Backend API routes were returning raw exception strings (`str(e)`) and stack traces (`traceback.format_exc()`) to the client.
**Learning:** Returning raw error details to the frontend can expose internal system architecture, library versions, and sensitive data from upstream APIs.
**Prevention:** Catch exceptions at the route level, log the full detail on the server with `exc_info=True`, and return generic, user-friendly error messages to the client.

## 2025-05-15 - Broken Admin Authentication
**Vulnerability:** Admin routes imported a `require_auth` decorator from a non-existent file (`helpers.auth_helpers`), potentially rendering them unprotected or broken.
**Learning:** Dead code or missing dependencies in authentication logic can lead to a complete bypass of security controls.
**Prevention:** Implement and verify authentication decorators. Use automated tests to ensure protected routes actually return 401/403 when unauthenticated.
