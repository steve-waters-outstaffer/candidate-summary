## 2025-03-24 - [Parallelize bulk candidate processing]
**Learning:** Sequential I/O-bound operations (RecruitCRM API, Gemini API) in bulk processing loops are a major performance bottleneck that scales linearly with the number of candidates. Parallelizing these operations using `ThreadPoolExecutor` significantly improves processing speed.
**Action:** Always look for sequential loops containing I/O-bound tasks (API calls, DB queries) and consider parallelization with appropriate concurrency limits to respect API quotas.

## 2025-03-26 - [Connection Pooling and Parallel Data Fetching]
**Learning:** For applications heavily reliant on external APIs (like RecruitCRM and AlphaRun), the overhead of repeated TCP/TLS handshakes is significant. Using a global `requests.Session()` enables connection pooling, reducing latency for every request. Additionally, parallelizing initial data fetching in "Single Summary" routes (not just bulk) provides a substantial performance boost (~1.2s - 1.5s per generation) by overlapping independent I/O waits.
**Action:** Default to using `requests.Session` for repetitive external API calls and look for opportunities to parallelize independent data-fetching tasks within single-request flows.
