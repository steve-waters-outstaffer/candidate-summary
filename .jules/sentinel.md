# 🛡️ Sentinel's Journal - Security Learnings

## 2025-04-12 - Wide-Open Firestore Rules
**Vulnerability:** Firestore security rules were set to allow anyone to read and write all documents as long as the request was made before September 19, 2025.
**Learning:** This is a common default configuration when setting up a new Firebase project, meant for initial development but often forgotten when moving towards production or more formal testing environments.
**Prevention:** Always implement authentication checks (`if request.auth != null;`) as the minimum security baseline for Firestore rules, even in early development stages.

## 2025-04-12 - Information Leakage via Error Responses
**Vulnerability:** Backend API routes were returning raw exception strings and stack traces (`traceback.format_exc()`) to the client in JSON error responses.
**Learning:** Developers often include stack traces in responses during debugging to quickly identify issues without checking server logs. However, this leaks internal code structure, library versions, and potential environment details to attackers.
**Prevention:** Catch exceptions on the server, log the full details (including stack trace) using a structured logger, and return a generic, non-descriptive error message to the client.
