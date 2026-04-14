## 2025-03-24 - [Parallelize bulk candidate processing]
**Learning:** Sequential I/O-bound operations (RecruitCRM API, Gemini API) in bulk processing loops are a major performance bottleneck that scales linearly with the number of candidates. Parallelizing these operations using `ThreadPoolExecutor` significantly improves processing speed.
**Action:** Always look for sequential loops containing I/O-bound tasks (API calls, DB queries) and consider parallelization with appropriate concurrency limits to respect API quotas.

## 2025-03-25 - [Enable connection pooling for external APIs]
**Learning:** Each `requests.get()` or `requests.post()` call without a session creates a new TCP/TLS connection. For apps making frequent calls to the same hosts (RecruitCRM, AlphaRun), the overhead of repeated handshakes adds significant latency (50-200ms per request).
**Action:** Use a global `requests.Session()` to enable connection pooling for frequently accessed API hosts.
