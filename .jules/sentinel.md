# Sentinel Security Journal

## 2025-04-14 - Information Leakage in Admin API Responses
**Vulnerability:** API error responses in `backend/routes/admin.py` were returning raw exception strings (`str(e)`) to the client.
**Learning:** Returning raw exception messages to the frontend can expose internal system details, such as database field names, file paths, or stack traces, which could be leveraged by an attacker to gain deeper insight into the application's architecture.
**Prevention:** Catch exceptions and log them with full detail (including stack traces using `exc_info=True`) on the server for debugging, while returning a generic, safe error message to the client.
