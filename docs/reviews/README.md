# Task Review Summaries

A concise record of what happened for each substantial task completed via
the ECC orchestration pipeline (Review/Commit phases). Skip this for trivial
fixes — only write one when the task actually went through Plan → Implement
→ Test → Review.

## Convention

- **Filename**: `<task-slug>-review.md` (e.g. `stage-7-github-integration-review.md`).
- **Created**: after Gate 2 (commit approval), summarizing the completed work.
- **Keep it short** — a few lines per section, not a transcript.

## Template

```markdown
# <Task name> — Review Summary

**What was implemented**: one or two sentences.

**Tests run**: which test files/commands, and the result (pass/fail counts).

**Review findings**: anything CRITICAL/HIGH raised during review, and
whether it was fixed before commit.

**Unresolved issues**: anything deliberately deferred, and why.

**Lessons for future work**: only if there's something genuinely transferable.
If none, write "None" — don't pad this section. If there is a real lesson,
also add it to `docs/growth-log/` per that folder's convention (link it here
instead of repeating it in full).
```

## For future ECC pipeline runs / agents

Before starting Review for a task, check this folder for a summary from a
related prior task (same area of the codebase) — it may already answer
"has this kind of thing caused problems before."
