## 2025-04-16 - [Information Leakage & Broken Authentication]
**Vulnerability:** API endpoints were returning raw exception strings (`str(e)`) and stack traces (`traceback.format_exc()`) to the client, and the `auth_helpers.py` file was missing, causing security decorators to fail.
**Learning:** Incomplete refactors or missing files can lead to both operational failures and security bypasses. Sanitizing error messages at the edge while keeping them in logs is critical for both security and maintainability.
**Prevention:** Use a consistent error handling pattern across all blueprints and ensure all referenced helper modules are present in the repository.
