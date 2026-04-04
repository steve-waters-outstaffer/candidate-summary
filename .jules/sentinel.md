## 2025-04-04 - [Information Leakage in Error Responses]
**Vulnerability:** Backend API endpoints were returning internal exception details (`str(e)`) and stack traces (`traceback.format_exc()`) directly to the client in JSON error responses.
**Learning:** Returning raw error information can leak sensitive data about the application's internal structure, library versions, and database schemas, which can be used by attackers to plan further exploits.
**Prevention:** Always catch exceptions, log the full details on the server for debugging, and return a generic, non-descriptive error message to the client.
