# Sentinel's Journal - Security Learnings

## 2025-05-14 - Information Leakage and Missing Authentication in Admin Routes
**Vulnerability:** Admin routes in `backend/routes/admin.py` were using a non-existent `require_auth` decorator, leaving sensitive prompt management endpoints effectively unprotected if the server-side import failure was bypassed. Additionally, all error handlers returned raw exception strings (`str(e)`), potentially leaking internal configuration, database structure, or file paths.
**Learning:** The codebase had structural placeholders for security (the decorator import) that were never actually implemented. Developers often use `str(e)` for quick debugging, which frequently survives into production.
**Prevention:** Always verify that security decorators are backed by actual implementations. Use a standardized error handling utility or decorator to ensure all API responses return generic messages while logging detailed information server-side.
