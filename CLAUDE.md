# MergeMind — Development Instructions

## Stage ownership

- **Stage 6 — Review History & Feedback is assigned to a groupmate.** Do not
  implement, modify, or plan Stage 6 features unless explicitly authorized
  here or by the user in-session. *(Update this line when ownership changes.)*

## Where things live

- **Overall progress & roadmap**: [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)
  — stage status, standing requirements. Check this first for "what stage are
  we on."
- **Approved plans in flight**: `docs/plans/stage-N-plan.md` — read the one
  matching the current stage before planning further; see
  [docs/plans/README.md](docs/plans/README.md).
- **Completed-task summaries**: `docs/reviews/<task-slug>-review.md` — read
  the one for the current or a related past task before starting review;
  see [docs/reviews/README.md](docs/reviews/README.md).
- **Lessons learned / recurring problems**: `docs/growth-log/YYYY-MM-DD.md`
  — skim filenames/titles for relevance to the current task's area (don't
  read the whole log); see [docs/growth-log/README.md](docs/growth-log/README.md).

## Workflow

- Use ECC's existing `/orch-add-feature` / `/orch-change-feature` /
  `/orch-fix-defect` / `/orch-refine-code` pipeline for standard-or-larger
  tasks. Do not build custom agents, hooks, or a separate pipeline.
- Trivial/small changes don't need the full pipeline — plain conversational
  edits are fine, consistent with the pipeline's own size classifier.
- Write the three document types above only for substantial tasks — skip
  them for trivial fixes to avoid log bloat.
