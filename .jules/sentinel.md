## 2025-04-17 - Missing Authentication on Core API Endpoints
**Vulnerability:** Most backend API endpoints (single, multi, bulk, floating) were completely unprotected, allowing anyone to trigger AI generations and push data to RecruitCRM if they knew the candidate/job slugs.
**Learning:** The application relied on "security by obscurity" for its core candidate summary generation logic, only protecting the admin-specific prompt management routes.
**Prevention:** Always use a standard authentication decorator like `@require_auth` for any endpoint that interacts with external APIs or sensitive candidate data. Ensure the frontend uses an `authFetch` wrapper to consistently provide authentication tokens.
