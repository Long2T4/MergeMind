# Beginner explanations for review findings

- Add a shared action to the finding card used by manual and GitHub PR review results.
- Generate a short explanation and a before-and-after example from saved finding details. Use the matching file's language for PR findings when available.
- Save the validated answer on the finding via a nullable column. Return the saved answer before spending another AI request.
- Check finding ownership, prevent overlapping generation for one finding, and cap generation attempts on the local server. Show loading and allow retry after a failure.
- Test both review paths, access control, persistence, retry, request limits, and the migration.

Stage 13 is merged in PR #16. This feature starts from that merge. ECC's feature command is unavailable in this session, so the plan, implementation, tests, and self-review are performed directly.
