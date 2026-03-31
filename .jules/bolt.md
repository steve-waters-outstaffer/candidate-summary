## 2025-03-24 - [Parallelize bulk candidate processing]
**Learning:** Sequential I/O-bound operations (RecruitCRM API, Gemini API) in bulk processing loops are a major performance bottleneck that scales linearly with the number of candidates. Parallelizing these operations using `ThreadPoolExecutor` significantly improves processing speed.
**Action:** Always look for sequential loops containing I/O-bound tasks (API calls, DB queries) and consider parallelization with appropriate concurrency limits to respect API quotas.
