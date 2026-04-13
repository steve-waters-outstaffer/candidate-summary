## 2025-03-24 - [Parallelize bulk candidate processing]
**Learning:** Sequential I/O-bound operations (RecruitCRM API, Gemini API) in bulk processing loops are a major performance bottleneck that scales linearly with the number of candidates. Parallelizing these operations using `ThreadPoolExecutor` significantly improves processing speed.
**Action:** Always look for sequential loops containing I/O-bound tasks (API calls, DB queries) and consider parallelization with appropriate concurrency limits to respect API quotas.

## 2025-03-25 - [Connection Pooling for API Latency]
**Learning:** Making repeated API calls (e.g., to RecruitCRM or Alpharun) without connection pooling introduces significant latency due to repeated TCP/TLS handshakes. Using a persistent `requests.Session` at the module level mitigates this.
**Action:** Implement a shared `requests.Session` for backend services that frequently call the same external APIs to improve overall response times.
