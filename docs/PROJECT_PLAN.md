# MergeMind — Project Plan & Master Requirements

This document is the permanent record of what this project is meant to become.
It exists so that future stages don't lose track of requirements that were
agreed on early but are not implemented yet. It is a planning document only —
it does not describe what is built today. For that, see the main
[README.md](../README.md), which reflects only completed, working stages.

## Status

- **Stage 1 — Project Foundation**: Complete
- **Stage 2 — Database**: Complete
- **Stage 3 — Manual Code Submission**: Complete
- **Stage 4 — AI Review Service**: Complete (uses the category set defined
  in the Developer Learning requirement below)
- **Stage 5 — Review Results UI**: Complete
- **Stage 6 — Review History**: Complete (feature `308bbd5`, fixes merged in
  `015d078`). See
  [Stage 6 — Review History (as built)](#stage-6--review-history-as-built) below.
- **Stage 7 — Confidence Scoring**: Complete (merged in `0c4bc34`). See
  [Stage 7 — Confidence Scoring (as built)](#stage-7--confidence-scoring-as-built).
- **Stage 8 — PR Risk Scoring**: Complete (merged in `9f9f162`). See
  [Stage 8 — PR Risk Scoring (as built)](#stage-8--pr-risk-scoring-as-built).
- **Project-Aware Review context collector (Akhil's original Stage 9)**:
  implemented on `feature/project-aware-context`, pending PR review/merge.
  Standalone Python/JavaScript/TypeScript import-context selection with tests;
  see [scope and usage](project-aware-context.md). API/AI/UI integration and
  GitHub retrieval remain unimplemented. This does not resolve the conflicting
  stage numbering below or implement developer feedback.
- **Stage 10**: Not started.
- **Frontend redesign** (dark theme, routed pages): in progress on
  `feature/ui-redesign`; not merged.

> The Stage 7 and Stage 8 that shipped don't match either definition in the
> roadmap below. See [Open questions](#open-questions-for-team-confirmation).

## Development Workflow & Records

See [CLAUDE.md](../CLAUDE.md) for stage ownership and the development
workflow. Supporting records for in-progress and completed work live in:

- [docs/plans/](plans/README.md) — approved plans for work in flight
- [docs/reviews/](reviews/README.md) — concise summaries of completed tasks
- [docs/growth-log/](growth-log/README.md) — lessons learned, recurring problems

## Stage Roadmap (reference)

1. Project Foundation — frontend/backend scaffolding, health check
2. Database — Supabase PostgreSQL, core models (User, Project, CodeReview, ReviewIssue)
3. Manual Code Submission — paste code, save to DB, display back
4. AI Review Service — modular AI provider, structured findings
5. Review Results UI — summary, severity breakdown, expandable issues
6. Review History — dashboard of past reviews
7. GitHub Integration — read PRs, review changed files
8. Smarter Review Context — related files, project structure, imports
9. Developer Feedback — Helpful / Not Helpful / False Positive / Fixed
10. Final Improvements — error handling, tests, docs, polish

## Master Requirement: Developer Learning Feature (Future)

This is a permanent, standing requirement for the project's end state. It is
**not implemented as of Stage 2** and must not be built until the stages below
explicitly call for it. It is recorded here so it isn't forgotten or designed
around accidentally in earlier stages.

MergeMind should eventually:

1. **Track review findings by the developer who authored the code** — every
   finding should be traceable to the specific developer/user responsible for
   the reviewed code, not just the project.
2. **Categorize mistakes** into a fixed set of categories:
   - Security
   - Testing
   - Error Handling
   - Input Validation
   - Database
   - Performance
   - Code Quality
   - Logic
3. **Store finding outcomes**: `open`, `fixed`, `dismissed`, `false_positive`.
4. **Detect recurring mistakes** — identify when a developer repeats the same
   category of mistake across multiple pull requests/reviews.
5. **Show mistake counts and improvement trends over time** — e.g. a category
   like "Testing" trending down (7 → 5 → 2) across recent reviews.
6. **Provide a Developer Learning Profile** — a summary view per developer
   showing PRs reviewed, issues fixed, common mistake types, and improvement
   trends.

### Where this lands in the roadmap

- **Stage 4**: AI assigns a `category` to each finding (the schema field for
  this already exists as of Stage 2).
- **Stage 6**: Review history is persisted and queryable — the prerequisite
  data for trend detection.
- **Stage 7**: Developer Learning Profile itself — recurring-mistake
  detection, trend analysis, and the profile UI shown above are built here,
  not earlier.
- **Stage 9**: Developer feedback (Helpful/Not Helpful/False Positive/Fixed)
  populates the `status` field added in Stage 2, which Stage 7's outcome
  tracking depends on.

### What already exists in the schema to support this (Stage 2)

- `ReviewIssue.category` (free-text field) — ready to hold the categories above.
- `ReviewIssue.status` — added in Stage 2 specifically to support future
  outcome tracking (`open`, `fixed`, `dismissed`, `false_positive`).
- `ReviewIssue → CodeReview → Project → User` — an existing join path that
  already lets a finding be traced back to a developer, without needing a
  direct foreign key yet.

No further schema or code changes are needed until Stage 4/6/7 actually
require them.

## Master Requirement: MVP Scope vs. Final Goal

**Early MVP (Stages 3–6):** review a single pasted code snippet or a single
file submitted manually through the frontend. No GitHub involvement.

**Final goal (Stage 7+):** project-aware review of a GitHub pull request —
not just the diff in isolation, but using relevant surrounding files and
project context (related files, project structure, imports, function calls,
database models, API routes — see Stage 8) to catch issues a simple
"paste one file into an LLM" tool would miss.

The manual single-file flow is a deliberate stepping stone, not the final
product. Later stages should extend this path rather than replace it outright,
since PR review will still need a place to display and store findings — the
same `CodeReview`/`ReviewIssue` models built in Stage 2.

## Stage 6 — Review History (as built)

Read-only dashboard of past reviews over the existing `code_reviews` /
`review_issues` tables (no schema changes).

- **API** (`backend/app/routes/review_history.py`):
  - `GET /review-history/` — paginated (`limit` ≤ 50, `offset`) newest-first
    list of **summaries**: `code_preview` (first 160 chars), `issue_count`,
    `high_severity_count`, `medium_severity_count`, `low_severity_count`
    (the last two were added with the frontend redesign). Filters: `q`
    (search code/language, `%`/`_` matched literally), `language`, `status`,
    `project_id`.
  - `GET /review-history/stats` — totals for the reviews matching the
    **same filters** as the list.
  - `GET /review-history/{id}` — full review (code + issues) for the detail
    view; 404 if missing.
- **UI**: `ReviewHistory.jsx` (filters, debounced search, pagination, stats,
  issues-per-review chart). A saved review opens at `/reviews/:id`, which
  loads it by id. Filters and page live in the URL
  (`/history?q=&language=&status=&page=`), so they survive opening a review
  and coming back. Language options come from
  `frontend/src/constants/languages.js`, shared with the submit form.
- **Tests**: `backend/tests/test_review_history.py` (in-memory SQLite, never
  Supabase). Install `backend/requirements-dev.txt` to run them.
- **Not in Stage 6**: issue feedback status updates (`fixed`, `dismissed`,
  `false_positive`) stay in **Stage 9**. `ReviewIssue.status` is returned
  but cannot be changed yet.

### Known risk: no authentication or per-user isolation

This applies to the whole app, not just Stage 6. Every endpoint is
unauthenticated, and History can list, search and open (by sequential id)
the submitted source code of every project. That's acceptable for local
development only. Before deployment, or before Stage 7 brings in GitHub
(possibly private) code, add authentication and scope history queries to
the current user's projects. Two related notes:

- `GET /review-history/{id}` makes walking review ids (1, 2, 3, …)
  trivial, and `/stats?q=` lets a caller infer whether some code contains a
  given string.
- Search is a substring scan over `submitted_code`, which has no length
  limit, so the cost grows with stored code size. When auth lands, consider
  a submission size limit, a minimum search length, rate limiting, and an
  upper bound on `offset`.

## Stage 7 — Confidence Scoring (as built)

Each finding gets an evidence-based confidence score.

- **Service**: `backend/app/services/confidence_service.py`.
  `calculate_confidence(evidence)` adds a weight for each confirmed evidence
  source: AI 20, Semgrep 25, Bandit 20, failed test 20, git history 10,
  dependency 5. It returns `confidence_score` (0–100) and
  `confidence_level` (high ≥ 80, medium ≥ 50, otherwise low).
- **Data**: three nullable columns on `review_issues`: `confidence_score`,
  `confidence_level`, `confidence_evidence` (JSON). They're returned on every
  issue in `CodeReviewOut`.
- **Current behaviour**: only AI evidence exists today (`{"ai": true}`), so
  every new finding scores **20 / low**. Higher scores need the static
  analysers or test results, which aren't integrated yet.
- **UI**: a confidence pill on each collapsed finding, plus a meter, evidence
  list and interpretation note when expanded. Older findings show "Not scored".
- **Meaning**: the score measures supporting evidence. It is not the
  probability that a finding is correct.

## Stage 8 — PR Risk Scoring (as built)

Each completed review gets a finding-based merge-risk score.

- **Service**: `backend/app/services/risk_score_service.py`.
  `calculate_risk(issues)` adds severity points per finding (high 30,
  medium 15, low 5) into four groups (security, testing, maintainability,
  performance; each capped at 100). It takes a weighted sum (0.35 / 0.25 /
  0.25 / 0.15) and applies a floor from the highest severity (high 70,
  medium 40, low 10). Level: high ≥ 70, medium ≥ 40, otherwise low.
- **Data**: nullable `risk_score`, `risk_level` and `risk_breakdown` (JSON)
  on `code_reviews`, returned in `CodeReviewOut`. Failed reviews and older
  reviews have no score.
- **UI**: a score ring in the review header and an "Overall Merge Risk" card
  with the per-group breakdown.
- **Meaning**: the score is a heuristic from the detected findings. It is not
  the probability of a failed merge, and it doesn't use PR metadata or test
  results yet.
- **Despite the name**: there's no GitHub pull-request input yet. Scores come
  from pasted-code reviews.

## Open questions for team confirmation

These are flagged, not decided. Nothing here has been changed in code, and
the agreed requirements above have been left as written.

1. **The roadmap doesn't match what shipped as Stages 7 and 8.**
   - The Stage Roadmap lists Stage 7 as *GitHub Integration* and Stage 8 as
     *Smarter Review Context*.
   - The Developer Learning section lists Stage 7 as the *Developer Learning
     Profile*.
   - What merged as Stages 7 and 8 is *Confidence Scoring* and *PR Risk
     Scoring*.
   - The team should confirm the new numbering and where GitHub Integration,
     Smarter Review Context and the Developer Learning Profile now sit.
2. **Learning page vs the Developer Learning Profile.**
   - The redesign's Learning page shows category counts, categories
     repeated across reviews, activity and per-review category counts. It
     computes them in the browser from saved reviews.
   - It doesn't attribute findings to individual developers, track outcomes,
     detect identical mistakes or measure improvement.
   - So it is **not** the Developer Learning Profile requirement. Confirm
     that this interim view is acceptable.
3. **Feedback statuses** (`fixed`, `dismissed`, `false_positive`) remain
   Stage 9. Fix rates and false-positive counts in the redesign mock-ups
   depend on it and aren't shown.
4. **History for PR reviews.**
   - The History list is still built for the single-snippet model: search
     over `submitted_code` and a fixed language list.
   - Once GitHub PR reviews exist, History will probably need repo, PR, file
     and author filters.
   - It will also need database indexes on `code_reviews.created_at`,
     `project_id` and `review_issues.review_id`.
