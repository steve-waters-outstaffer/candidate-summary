## 2025-03-24 - [Parallelize bulk candidate processing]
**Learning:** Sequential I/O-bound operations (RecruitCRM API, Gemini API) in bulk processing loops are a major performance bottleneck that scales linearly with the number of candidates. Parallelizing these operations using `ThreadPoolExecutor` significantly improves processing speed.
**Action:** Always look for sequential loops containing I/O-bound tasks (API calls, DB queries) and consider parallelization with appropriate concurrency limits to respect API quotas.

## 2025-03-25 - [Optimize RecruitCRM API usage with connection pooling and redundancy elimination]
**Learning:** Redundant I/O is a silent performance killer. Helper functions like `fetch_candidate_interview_id` were performing their own API calls for data already available in the calling scope. Additionally, the lack of connection pooling forced a new TLS handshake for every API call.
**Action:** Use a module-level `requests.Session()` for connection pooling and update helper functions to accept optional pre-fetched data to avoid redundant network requests.
