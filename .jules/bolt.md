## 2025-03-24 - [Parallelize bulk candidate processing]
**Learning:** Sequential I/O-bound operations (RecruitCRM API, Gemini API) in bulk processing loops are a major performance bottleneck that scales linearly with the number of candidates. Parallelizing these operations using `ThreadPoolExecutor` significantly improves processing speed.
**Action:** Always look for sequential loops containing I/O-bound tasks (API calls, DB queries) and consider parallelization with appropriate concurrency limits to respect API quotas.

## 2025-05-15 - [API connection pooling and redundancy elimination]
**Learning:** Reusing HTTP connections via `requests.Session` (HTTP Keep-Alive) and passing pre-fetched data to downstream helpers significantly reduces API latency and total request count. In `multi.py` and `bulk.py` routes, this prevents N+1 or redundant fetching patterns that otherwise slow down candidate processing.
**Action:** Use a shared `requests.Session` for internal API helpers and design helper functions to accept optional pre-fetched objects to avoid redundant network I/O.
