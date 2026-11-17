# Beginner explanation implementation review

Manual and pull request findings share the same action. The API checks ownership before reading the explanation or spending an AI request. For pull request findings it looks up the matching file's language when available. The model receives bounded details from the saved finding and returns two plain-language fields and two synthetic code snippets. Results are validated before saving.

Migration `0007_beginner_explanations` adds a nullable JSON column. Older findings remain usable and can request an explanation on demand. Run `alembic upgrade head` against the development database before starting the API with these changes.

Saved answers open directly from the review results. Generation shows a loading state and failures show a retry action. The local server limits generation to 20 attempts per rolling hour and 3 concurrent requests. While a finding's generation is in progress, another request for that finding gets a retryable conflict response. The safeguards are per API process.

Verification on November 17, 2026:

- Backend suite: 449 passed, 75 skipped. New API cases cover both review types, cache reuse and persistence, ownership, invalid output and retry, the rolling limit, and overlapping requests.
- Frontend suite: 115 passed, including four new tests for both review paths, loading, saved answers, and retry. Production build passed.
- SQLite migration coverage passed. The backend suite skipped tests that required an unavailable local PostgreSQL database or scanner. The feature tests used a mocked Claude provider.
- Self-review checked the finding ownership query, migration compatibility with legacy findings, and loading and retry behavior. ECC had no runnable feature command in this session.
