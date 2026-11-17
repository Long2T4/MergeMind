# Stage 13: Static Analysis Integration — Review Summary

**Status:** implemented and tested in PR [#16](https://github.com/Long2T4/MergeMind/pull/16), **not merged**. Migration `0006` isn't applied to Supabase.

## What was implemented

Semgrep and Bandit check Python code alongside the AI, in manual and pull request reviews:
- findings that describe the same problem are merged;
- agreement between sources raises confidence;
- the results page shows whether each scanner ran.

**Original implementation:** Yudith Vazquez-Jacinto (`edfdcbe`):
- the Semgrep and Bandit services, and the coordinating analysis service;
- integration into manual and pull request reviews;
- evidence tracking;
- failure handling, so a scanner can't fail a review;
- the first tests.

**Integration fixes:** Long Truong, in the commits after it. A review and a real-scanner check (2026-11-17) found:
- the scanners were never installed;
- duplicates never merged: 8 real problems became 24 findings;
- Semgrep downloaded its rules on every scan, found 4 of 8 problems, and hung for 119 s without network;
- Bandit added noise, and titles were raw rule IDs;
- scanner failures were invisible.

## Changes

| Commit | Change |
|---|---|
| `4e5c763` | Confidence weights: AI 20, each scanner 30, capped at 100. AI + one scanner is medium (50), all three high (80) |
| `0cba9e9` | Bandit pinned in `requirements.txt`, and Semgrep in `requirements-semgrep.txt` (separate environment; CI installs it with pipx). Plus: <ul><li>local Semgrep rules, offline;</li><li>Bandit skip list;</li><li>readable titles and fixes per vulnerability kind;</li><li>merging by kind and line;</li><li>"unavailable" vs "failed";</li><li>real-scanner tests and fixtures</li></ul> |
| `3cbc5a1` | Migration `0006`: `code_reviews.analysis_status` (JSON, nullable), saved by manual and pull request reviews |
| `44b17d2` | Results page "Static analysis" card; New Review shows Semgrep and Bandit as on for Python |
| (docs) | README, PROJECT_PLAN, this summary, growth log |

## Key decisions

- **Semgrep is installed separately.** `semgrep==1.184.0` needs `click~=8.4.2`, which conflicts with the backend's pinned `uvicorn[standard]`, so it can't go in `requirements.txt`. It runs as an executable (pipx, or `SEMGREP_EXECUTABLE`). It doesn't run natively on Windows; there, use WSL, or reviews use Bandit and the AI.
- **MergeMind's own Semgrep rules.** `backend/app/analysis_rules/semgrep-python.yml` has 7 rules, each tagged with a vulnerability kind and a CWE. Compared with `p/security-audit`: it works offline, results are stable, it found 8 of 8 test problems instead of 4, and it gave 0 false positives on the clean and edge-case fixtures.
- **Merging by kind, not title.** The three sources word, rate and number (CWE) the same problem differently, so none of those can be matched.
  - Each finding gets a kind: from Semgrep rule metadata, a Bandit test table, or the AI's wording.
  - Findings merge only when the kinds match and are known, the lines are at most 1 apart, and the sources differ. The nearest line wins.
  - Vague or ambiguous AI wording never merges.
- **Status per scanner:** `completed`, `failed`, `unavailable` or `not_run`. A pull request review reports a failure in any file first.

## Tests run

| Suite | Result |
|---|---|
| Backend, Windows + local PostgreSQL 16 | 506 passed, 6 skipped (4 need Semgrep; 2 SQLite copies of PostgreSQL-only tests) |
| Backend, Linux container like CI's Ubuntu job: real Semgrep 1.184.0 and Bandit 1.9.4, **network disconnected** | 447 passed, 65 skipped (PostgreSQL-only) |
| Real-scanner tests (`test_stage13_real_scanners.py`) on Linux, offline | 8 of 8 passed. Semgrep scan of `vulnerable.py`: 8 findings in 2.3 s |
| Frontend | 111 passed |
| Production build | Passed |

New tests:
- `test_stage13_real_scanners.py`: real tools on `tests/fixtures/stage13/` (vulnerable, clean, edge cases, syntax error);
- `test_stage13_merge.py`: recorded real output, plus must-not-merge traps;
- `test_stage13_scanners.py`: commands, local rules, timeouts, statuses, kinds;
- `test_stage13_status.py`: end to end for manual and pull request reviews, including the regression of 8 problems saved as 8 findings;
- the `0006` cases in `test_migrations.py`;
- frontend `stage13.test.jsx`.

`tests/conftest.py` treats the scanners as not installed in other tests, so results don't depend on the machine.

## Security

- Code is written to a temporary file and only parsed by the scanners, never executed.
- `subprocess.run` gets an argument list, never a shell. The scanners have 30 s timeouts.
- Semgrep has metrics and version checks turned off, and makes no network calls. Verified with the network disconnected.
- Stage 12 ownership checks, sign-in and the manual review limit are unchanged.
- `0006` adds no tables, so Row Level Security is unaffected.

## Unresolved issues

- **Python only.** Semgrep could cover JavaScript and TypeScript later with more rules.
- **AI matching is keyword-based.** It's conservative (unclear findings stay separate), but it can miss a match.
- **Bandit flags `eval`/`os.system` on fixed strings**, which the local Semgrep rules ignore. Such findings show as Bandit-only, low confidence.
- **Scans add a few seconds per Python file:** about 2–3 s for Semgrep and 0.2 s for Bandit. They run one after the other.
- **CI hasn't run these fixes yet.** That includes the Ubuntu job's pipx install of Semgrep.
- **Migration `0006`** needs team approval and a backup before it's applied to Supabase.

## Lessons for future work

See [growth log 2026-11-17](../growth-log/2026-11-17.md).
