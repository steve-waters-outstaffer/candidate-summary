# Sentinel's Journal - Critical Security Learnings

## 2025-05-14 - [Critical] Missing Authentication Helpers for Admin Routes
**Vulnerability:** The `backend/routes/admin.py` file imports `require_auth` from `helpers.auth_helpers`, but the file `backend/helpers/auth_helpers.py` is missing from the repository. This results in a `ModuleNotFoundError` when the application attempts to load admin routes, effectively breaking the admin interface and potentially leaving it vulnerable if the decorator is bypassed or improperly implemented during a quick fix. Additionally, some endpoints were found to be leaking stack traces via `traceback.format_exc()`.
**Learning:** A broken authentication flow due to missing dependencies can lead to both denial of service for administrative functions and a risk of developers disabling security checks to "just make it work" during emergencies.
**Prevention:** Always verify that all imported security decorators and helpers are present in the codebase. Implement automated tests to ensure that protected routes actually reject unauthenticated requests.
