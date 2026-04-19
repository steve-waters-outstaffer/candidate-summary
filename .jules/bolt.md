## 2025-03-24 - [Parallelize bulk candidate processing]
**Learning:** Sequential I/O-bound operations (RecruitCRM API, Gemini API) in bulk processing loops are a major performance bottleneck that scales linearly with the number of candidates. Parallelizing these operations using `ThreadPoolExecutor` significantly improves processing speed.
**Action:** Always look for sequential loops containing I/O-bound tasks (API calls, DB queries) and consider parallelization with appropriate concurrency limits to respect API quotas.

## 2025-05-22 - [Two-Wave Parallel Data Fetching]
**Learning:** For complex objects with dependencies (e.g., summary generation needing candidate ID for interview fetch), a two-wave parallel approach maximizes throughput while respecting data dependencies. Connection pooling via `requests.Session()` further reduces latency by ~20% by avoiding redundant TLS handshakes.
**Action:** Use `ThreadPoolExecutor` to fetch independent base data in Wave 1, then use results to concurrently fetch dependent data in Wave 2. Always implement connection pooling for high-frequency API helpers.
