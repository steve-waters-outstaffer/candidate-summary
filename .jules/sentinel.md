## 2025-05-15 - [API Information Leakage via Verbose Error Responses]
**Vulnerability:** API endpoints were returning raw exception strings (`str(e)`) and full stack traces (`traceback.format_exc()`) directly to the client in JSON error responses.
**Learning:** This pattern was widespread across multiple backend route files (`single.py`, `admin.py`, `bulk.py`, etc.), likely due to prioritizing ease of debugging during development over production security.
**Prevention:** Always use generic error messages for client-facing responses. Use `log.error(..., exc_info=True)` to ensure full diagnostic information is captured in server-side logs without exposing it to the user.
