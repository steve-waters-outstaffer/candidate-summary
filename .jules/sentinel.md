## 2025-04-07 - [Information Leakage via Error Messages]
**Vulnerability:** API endpoints were returning raw exception strings (`str(e)`) and stack traces (`traceback.format_exc()`) to the client in JSON responses.
**Learning:** Returning internal error details can expose sensitive information about the application's code, structure, and environment to potential attackers.
**Prevention:** Always log the full error on the server and return a generic, safe error message to the client. Ensure that `exc_info=True` is used in logs to maintain debuggability without compromising security.
