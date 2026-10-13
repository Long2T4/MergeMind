# Approved Plans

This folder holds the approved `task_list` for whichever stage/feature is
currently being implemented via the ECC orchestration pipeline
(`/orch-add-feature`, `/orch-change-feature`, etc.).

## Convention

- **Filename**: `stage-N-plan.md` (e.g. `stage-7-plan.md`). For non-stage
  work, use a short task slug instead: `<task-slug>-plan.md`.
- **Created**: when a plan is approved at Gate 1 (before any implementation
  starts).
- **Contents**: the plan's `task_list` as produced by the `planner` agent —
  nothing more. Don't duplicate `docs/PROJECT_PLAN.md`'s roadmap content here.
- **Lifecycle**: the file stays until the stage/task merges to `main`. After
  merge, delete it (the fact that it shipped is already reflected in
  `docs/PROJECT_PLAN.md`'s status table). If a decision from the plan is
  worth keeping permanently, that belongs in an ADR or in
  `docs/PROJECT_PLAN.md`, not here.

## Why this exists

So a plan survives a single session — if work on a stage is interrupted or
picked up by someone else, the approved plan is a real file in Git, not
something that has to be re-explained from a chat transcript.

## For future ECC pipeline runs / agents

Before starting Plan (Gate 1) for a stage, check this folder for an existing
`stage-N-plan.md` matching the stage in question — don't re-plan from
scratch if an approved plan already exists.
