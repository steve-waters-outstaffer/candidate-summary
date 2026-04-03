## 2025-03-24 - [Parallelize bulk candidate processing]
**Learning:** Sequential I/O-bound operations (RecruitCRM API, Gemini API) in bulk processing loops are a major performance bottleneck that scales linearly with the number of candidates. Parallelizing these operations using `ThreadPoolExecutor` significantly improves processing speed.
**Action:** Always look for sequential loops containing I/O-bound tasks (API calls, DB queries) and consider parallelization with appropriate concurrency limits to respect API quotas.

## 2026-04-03 - [Optimize Backend API interactions with connection pooling and redundancy elimination]
**Learning:** Reusing TCP connections via `requests.Session` and `HTTPAdapter` significantly reduces latency for high-frequency API calls to RecruitCRM and AlphaRun. Additionally, passing pre-fetched data objects to helper functions eliminates redundant network requests in summary generation flows.
**Action:** Implement connection pooling for all external API integrations and prioritize data reuse to avoid N+1-style redundant API calls in backend routes.
