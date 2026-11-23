# Stage 14: Evaluation and Final Demo — Review Summary

**Status:** done on `stage-14/evaluation-demo`, **not merged**. Nothing deployed; no real Anthropic, GitHub-write or Supabase calls were made.

## What was implemented

- **Evaluation:**
  - a reproducible runner (`backend/evaluation/`) using MergeMind's own scanning, merging and confidence code;
  - a dataset of 19 known problems in fictional Python, plus clean look-alike files;
  - published results with their method in [evaluation.md](../evaluation.md).
- **Fixes from the evaluation:**
  - Semgrep missed SQL built into a variable (also in the demo PR);
  - Bandit reported `TOKEN = ""` as a secret;
  - Bandit "blacklist" findings were titled "Blacklist".
- **Demo:**
  - the published demo repository and PR #1, captured in `demo/`, plus a new PR #2 where scanners and AI agree;
  - `demo/build_demo_repo.py` rebuilds it identically;
  - a manual-review sample;
  - the scripted [demo](../demo-script.md), rehearsed start to finish.
- **Deployment configuration, not deployed:**
  - `CORS_ALLOWED_ORIGINS` (wildcard refused) and `API_DOCS_ENABLED`;
  - `backend/Dockerfile`: one worker, non-root, Semgrep in its own environment, no automatic migrations;
  - `render.yaml` with no secret values, and `frontend/vercel.json`;
  - [deployment.md](../deployment.md) with the security checklist.
- **Docs:**
  - README sections for the evaluation, demo and deployment, and updated status and contributors;
  - this plan's Stage 14 progress;
  - outdated "not merged" notes fixed.

## Tests run

| Suite | Result |
|---|---|
| Backend, Windows + local PostgreSQL 16 | 549 passed, 7 skipped (5 need Semgrep; 2 SQLite copies of PostgreSQL-only tests) |
| Backend, Linux with real Semgrep 1.184.0 and Bandit 1.9.4 required | 481 passed, 75 skipped (PostgreSQL-only) |
| Frontend | 115 passed |
| Production build | Passed |
| Evaluation (Linux, real scanners) | 13/19 known problems; 11/11 rule-covered; 0 false positives; 0 duplicates (`main` before: 12/19, 10/11, 1 false positive) |
| API image | Built and run. Checks: <ul><li>migrations to `0007`;</li><li>`/health` ok;</li><li>docs 404;</li><li>CORS allows only the configured origin;</li><li>401 without sign-in;</li><li>non-root;</li><li>both scanners completed</li></ul> |
| Demo rehearsal (browser) | All 10 steps worked with real scanners and fake sign-in, GitHub and AI; no console errors; phone width OK |

New tests:
- `test_evaluation.py`: dataset, scoring, the AI permission flag, and replay;
- `test_demo_repo.py`: the rebuild, and that the demo PRs trigger the scripted findings;
- `test_deployment_config.py`;
- Semgrep SQL-shape and Bandit regression tests.

## Unresolved issues

- **AI evaluation:** run once on 2026-11-23 (7 calls): 15/19 with the AI, 4/8 AI-only problems. It showed manual-review line numbers were off; fixed. Re-measuring needs 7 more approved calls.
- **Live demo rehearsal:** with the real AI, GitHub and Supabase, about 8 AI calls. Record the fallback video during it.
- **Demo PR #2** isn't published to `Long2T4/mergemind-demo`; that needs a team member's GitHub access.
- **Supabase:** migrations `0005`–`0007`, plus the settings in [deployment.md](../deployment.md), need approval and a backup.
- **Deployment:** not done. Run one API instance only.
- **Semgrep SQL rule:** can match English text that reads like SQL (`f"delete from your list? {x}"`).

## Lessons for future work

Measuring against a labeled dataset found two detection gaps that every unit test missed. One was in the demo PR itself. Run the evaluation again whenever rules or merging change.
