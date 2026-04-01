## 2025-04-01 - [Prevent Information Leakage via Stack Traces]
**Vulnerability:** Internal stack traces were being exposed to the client in the `/api/test-quil` endpoint during error conditions.
**Learning:** Using `traceback.format_exc()` in API responses is a security risk as it exposes internal code structure, library versions, and potentially sensitive environment details to any user of the endpoint.
**Prevention:** Always log the full stack trace on the server for debugging purposes but return a generic, non-descriptive error message to the client.
