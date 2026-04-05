## 2025-04-05 - [Information Disclosure via Error Messages]
**Vulnerability:** Backend routes in `backend/routes/*.py` were leaking internal implementation details (including full stack traces and raw exception strings) to the client via JSON error responses.
**Learning:** Using `str(e)` or `traceback.format_exc()` in a `jsonify` call is a common pattern for fast debugging but creates a significant security risk by exposing the server's internal state to potential attackers.
**Prevention:** Always return generic, non-descriptive error messages to the client. Use `log.error(..., exc_info=True)` to ensure that the full error context is preserved in server-side logs for debugging purposes without compromising security.
