## 2025-03-24 - [Parallelize bulk candidate processing]
**Learning:** Sequential I/O-bound operations (RecruitCRM API, Gemini API) in bulk processing loops are a major performance bottleneck that scales linearly with the number of candidates. Parallelizing these operations using `ThreadPoolExecutor` significantly improves processing speed.
**Action:** Always look for sequential loops containing I/O-bound tasks (API calls, DB queries) and consider parallelization with appropriate concurrency limits to respect API quotas.

## 2026-04-05 - [Implement connection pooling for external APIs]
**Learning:** External API calls (RecruitCRM, AlphaRun) are frequently used, often in parallel loops. Without connection pooling, each call incurs the overhead of a full TCP/TLS handshake, which can add hundreds of milliseconds of latency per request. Using a shared `requests.Session` significantly reduces this overhead.
**Action:** Use a module-level or application-level `requests.Session` for service-to-service communication to leverage connection reuse and Keep-Alive.
