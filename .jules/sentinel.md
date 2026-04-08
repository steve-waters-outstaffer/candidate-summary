## 2025-05-15 - Information Leakage via Error Messages
**Vulnerability:** API endpoints in the backend (e.g., `backend/routes/single.py`) were returning internal details such as stack traces (via `traceback.format_exc()`) and raw exception strings (via `str(e)`) in error responses to the client.
**Learning:** Returning detailed error messages can expose sensitive information about the application's architecture, dependencies, and code structure, which can be leveraged by attackers to find further vulnerabilities.
**Prevention:** Always sanitize error messages before returning them to the client. Log the full error details on the server for debugging purposes and return generic, non-descriptive error messages to the client.
