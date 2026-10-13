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
- **Stages 6–10**: Not started

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
