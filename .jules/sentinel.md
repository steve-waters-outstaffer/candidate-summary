## 2025-04-02 - Information Leakage via Error Responses
**Vulnerability:** API endpoints were returning raw exception strings (`str(e)`) and full stack traces (`traceback.format_exc()`) to the client upon failure.
**Learning:** Returning internal error details can expose implementation logic, library versions, and potentially sensitive environment information to an attacker.
**Prevention:** Always log full error details on the server for debugging purposes, but return generic, user-friendly error messages (e.g., "An internal server error occurred.") to the client.
