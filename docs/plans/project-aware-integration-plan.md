# Project aware review integration plan

- [x] Extend the existing POST review request with optional reviewed path, Python source root, and a bounded supplied-file snapshot. Validate context before storing a review or calling AI.
- [x] Select direct imports with the merged collector and send only selected files to the provider as JSON code data under separate reviewer instructions. Preserve single-file requests and structured findings.
- [x] Add an optional JSON snapshot upload/paste UI with file path and source-root inputs. Show context selection diagnostics for the just-created review; explain that snapshots are not saved for retry/history.
- [x] Add API/provider integration tests and frontend flow/validation tests. Run full backend and frontend suites, production build, and a local UI smoke check using isolated test data.
- [x] Update usage/status documentation, self-review, and Jira MM-20 to match.
- [ ] Obtain Akhil's approval for the exact first-person PR text, then open the PR. Commit and push are part of the handoff before this approval.

Scope authorized October 29, 2026. GitHub fetching, recursive analysis, feedback actions, and database migrations are outside this task. ECC commands are unavailable; the plan, implementation, test, and self-review sequence is performed directly.
