# MergeMind Project Plan

This is the authoritative record of MergeMind's status, roadmap and project requirements. Where another document disagrees with this one, follow the code first, then this plan.

MergeMind is a university senior capstone and resume project, not a commercial product. The goal is a complete, reliable application that shows strong engineering without unnecessary complexity. Keep this in mind when judging scope.

- **Setup and current features:** [README](../README.md)
- **Team workflow:** [CLAUDE.md](../CLAUDE.md)
- **Project-aware review details:** [usage guide](project-aware-review.md) and [collector guide](project-aware-context.md)

## Current status

Last verified at commit `99be62f` on 2026-10-31.

| Item | Status |
|---|---|
| Stages 1–9 | Complete |
| Frontend redesign | Complete |
| Current stage | **Stage 10: Foundation and Stability** |
| Backend tests | 88 passed, including on Windows |
| Frontend tests | 64 passed |
| Production build | Passed |
| CI | Not set up |
| Live Supabase and Anthropic verification | Not recorded |
| Deployment | None; local only |

## Completed work

The stage numbers below describe what was actually built. They replace the [original roadmap](#superseded-plans).

| Stage | Title | What was delivered | Git evidence |
|---|---|---|---|
| 1 | Project Foundation | React and FastAPI scaffolding, health check | `159a5a2` |
| 2 | Database Foundation | Supabase PostgreSQL, SQLAlchemy models, user and project endpoints | `159a5a2` |
| 3 | Manual Code Submission | Submit code, save it, list reviews | `159a5a2` |
| 4 | AI Review Service | Claude findings, normalization, saved failure state | `159a5a2` |
| 5 | Review Results UI | Summary, severity counts, expandable findings | `159a5a2` |
| 6 | Review History | History, search, filters, pagination, stats. Built by bhavesh70655, with later fixes from Long Truong | PR #1, PR #2 |
| 7 | Confidence Scoring | Evidence weights, per-finding score, UI | PR #3 (Yudith Vazquez-Jacinto) |
| 8 | PR Risk Scoring | Findings-based 0–100 score and breakdown | PR #4 (Yudith Vazquez-Jacinto) |
| 9 | Project-Aware Review | Direct-import context from manually supplied snapshots | PR #6, PR #7 (Akhil Sajja) |

**Stages 1–5** arrived in one initial commit, so Git can't show their individual history. Commit authorship also doesn't prove the full division of work.

**Additional completed work:**
- **Frontend redesign (PR #5, Long Truong):** dark design system, routed pages, code editor, Learning and Projects pages, and Vitest tests. It also added medium and low severity counts to History rows.
- **Windows test fix (PR #8, Long Truong):** short test IDs let the full backend suite run on Windows.

### As-built notes

**Stage 6: Review History**
- `GET /review-history/` returns paged summaries, not full code.
- `GET /review-history/stats` uses the same filters as the list.
- `GET /review-history/{id}` returns one full review.
- Search treats `%` and `_` literally.
- History filters and page are kept in the URL.

**Stage 7: Confidence Scoring**
- Weights: AI 20, Semgrep 25, Bandit 20, failed test 20, git history 10, dependency 5.
- Levels: high at 80 or above, medium at 50 or above, otherwise low.
- Only AI evidence exists today, so every new finding scores 20/low.
- The score measures supporting evidence, not the probability a finding is correct.

**Stage 8: PR Risk Scoring**
- Severity points: high 30, medium 15, low 5.
- Groups: security, testing, maintainability, performance, each capped at 100.
- Weights: 0.35, 0.25, 0.25, 0.15.
- Severity floors: high 70, medium 40, low 10.
- The score is a heuristic based on findings. It isn't the probability of a failed merge, and it doesn't use real PR data yet.

**Stage 9: Project-Aware Review**
- Python imports are read with `ast`. JS and TS imports use a lightweight tokenizer.
- Selected context is limited to 8 direct-import files and 24,000 characters.
- A snapshot may hold 50 files and 200,000 characters. The full prompt is limited to 250,000 characters.
- Snapshots and diagnostics aren't stored.
- The collector doesn't depend on GitHub, the database or the AI provider, so a GitHub adapter can reuse it.

## Approved roadmap: Stages 10–14

The team chose the **Portfolio Version**. Each stage must keep existing features working.

```text
10 Foundation and Stability
 ├─ 11 GitHub Pull Request Integration
 ├─ 12 Developer Feedback and Learning
 └─ 13 Static Analysis Integration
        └─ all three feed 14 Evaluation and Final Demo
```

Stages 11, 12 and 13 can run mostly in parallel after Stage 10, if each has a clear owner. Coordinate schema changes, because Stages 11, 12 and 13 all change the database. Stage 12's access rules must also cover anything Stage 11 adds.

| Stage | Difficulty | Owner | Priority |
|---|---|---|---|
| 10 Foundation and Stability | Low to medium | TBD | Essential |
| 11 GitHub Pull Request Integration | High | TBD | Essential |
| 12 Developer Feedback and Learning | Medium | TBD | Essential |
| 13 Static Analysis Integration | Medium | TBD | Essential for the Portfolio Version |
| 14 Evaluation and Final Demo | Medium | TBD | Essential |

### Stage 10: Foundation and Stability

**Goal:** make the current application dependable and safe to change.

**Depends on:** nothing. All later stages depend on this one.

**Scope:**
- Rewrite `README.md` and this plan.
- Add GitHub Actions CI for backend tests, frontend tests and the build.
- Add database migrations. Start from a baseline that matches the real Supabase schema.
- Add indexes on `code_reviews.created_at`, `code_reviews.project_id` and `review_issues.review_id`.
- Return a clear error for a nonexistent `project_id`.
- Make normalization safe for missing or wrong AI field types.
- Protect the final save, so a review can't stay `pending` after an error.
- Handle reviews left `pending` by an interrupted process.
- Reduce the risk of long AI responses being cut off by `max_tokens=2000`.
- Run and record one live review with Anthropic and Supabase, using a safe test project.
- Add TypeScript syntax highlighting.
- Update stale "Stage 9" feedback text in `models.py`, `lib/learning.js` and `LearningPage.jsx`.
- Update the `.env.example` database URL to match the README's pooler guidance.

**Already done:** Windows pytest test IDs (PR #8). This is verified, so don't redo it.

**Known issues to fix (reproduced 2026-10-31 on SQLite with a mocked AI):**

| Input | Result today |
|---|---|
| Nonexistent `project_id` | 500 error |
| `"explanation": null` from the AI | 500 error, review stuck on `pending` |
| Non-string `title` from the AI | 500 error, review stuck on `pending` |
| Truncated AI JSON | Handled: saved as `failed` |

**Acceptance criteria:**
- CI runs on every pull request and passes.
- The cases above are covered by regression tests.
- A fresh database and a copy of the real schema both migrate correctly.
- No handled failure leaves a review stuck on `pending`.
- A live review is completed and recorded in `docs/reviews/`.
- TypeScript code is highlighted in the editor and results.

**Out of scope:** authentication, GitHub work, new product features.

### Stage 11: GitHub Pull Request Integration

**Goal:** review a real public pull request from its URL.

**Depends on:** Stage 10.

**Scope:**
- Accept public `github.com` PR URLs, with strict URL validation.
- Retrieve PR details, changed files and diffs using a read-only server-side token.
- Focus findings on changed lines.
- Retrieve imported files at the PR's exact commit and pass them to the Stage 9 collector.
- Show the repository, PR title, PR author, commit and changed files.
- Show progress for long reviews.
- Set limits on PR size, and skip binary and generated files.
- Keep manual reviews working.

**Expected data changes:** PR details, changed files and a nullable link from `code_reviews`. Use `review_issues.file_name` for multi-file results. Design this before implementing it.

**Acceptance criteria:**
- A demo PR URL produces saved, per-file findings on changed lines.
- PR author, commit and files are visible.
- Invalid, private, missing and oversized PRs show clear errors.
- GitHub is mocked in automated tests.
- Existing manual review tests still pass.

**Risks:** large PRs, long AI runs, API limits and AI costs.

**Out of scope:** OAuth, GitHub Apps, private repositories, webhooks, posting to GitHub, running repository code.

### Stage 12: Developer Feedback and Learning

**Goal:** give data an owner and record what happened to each finding.

**Depends on:** Stage 10. Access rules must also cover Stage 11's data.

**Scope:**
- Add appropriate authentication and per-user data protection.
- Add simple project creation and management.
- Let users mark findings `open`, `fixed`, `dismissed` or `false_positive`.
- Add validated, owner-only backend updates.
- Add status controls to findings.
- Improve the Learning page with real outcomes, overall and by category.

**Expected data changes:** a user's auth identity, assigned owners for existing rows, a constraint on allowed statuses, and who and when fields for status changes.

**Acceptance criteria:**
- Tests prove one user can't read or change another user's data through any route.
- Status changes persist, and invalid values are rejected.
- Older reviews still open correctly.
- Learning outcomes can be traced to saved findings.

**Risks:** this changes API contracts and touches every route. "Fixed" is self-reported and must be labeled that way.

**Out of scope:** teams and roles, developer identity mapping, XP, levels, streaks, invented improvement scores, complex analytics.

### Stage 13: Static Analysis Integration

**Goal:** back findings with evidence from non-AI tools.

**Depends on:** Stage 10. It works on submitted code, and it can use Stage 11's files once they exist.

**Scope:**
- Integrate Semgrep and Bandit.
- Normalize tool results into MergeMind's finding format.
- Combine AI and tool findings, and remove duplicates.
- Update confidence scoring with real evidence.
- Show which tools support each finding.

**Scoring note:** the current formula gives AI plus Semgrep 45 (low), and AI plus Bandit 40 (low). Only all three reach 65 (medium). Revisit the weights and levels so agreement between sources means something, while keeping the score's meaning as supporting evidence.

**Expected data changes:** the source of each finding, and tool evidence. Existing findings keep their stored scores.

**Acceptance criteria:**
- Fixtures with known problems produce the expected tool findings.
- One problem found by several sources appears as one finding.
- Confidence varies with real evidence, and the UI shows that evidence.
- A tool failure doesn't fail the whole review.
- Analyzers never run repository code, and they use only MergeMind's own configuration.

**Risks:** Semgrep's native Windows support needs checking first, and WSL or Docker may be required. Tool output can be noisy.

**Out of scope:** ESLint (optional future work), auto-fixing, running tests.

### Stage 14: Evaluation and Final Demo

**Goal:** measure the product and finish a reliable demonstration.

**Depends on:** Stages 11, 12 and 13, or whatever the team includes.

**Scope:**
- Evaluate MergeMind on a small set of code with known issues.
- Measure what it catches and misses, and document limitations.
- Prepare a repeatable demo repository with example pull requests.
- Complete integration and regression testing.
- Deploy securely if feasible. Otherwise, prepare a polished demo video.
- Finalize all documentation.

**Acceptance criteria:**
- Evaluation results are reproducible and published with their method.
- The scripted demo works from start to finish.
- All tests and CI pass.
- Docs describe only what works.
- Any public deployment requires login or strict limits. It must not expose saved code or unlimited AI usage.

**Risks:** late scope creep. Features freeze when this stage starts.

**Out of scope:** new features and high-scale infrastructure.

### If time runs short

Cut in this order:
1. Public deployment (use a demo video)
2. Login and project management (accept a local demo, and say so clearly)
3. Bandit
4. Other Stage 12 and 13 polish

Don't cut Stage 10, Stage 11, the evaluation, or the demo.

## Remaining features

| Feature | Status | Plan |
|---|---|---|
| CI | Not implemented | Stage 10 |
| Database migrations | Not implemented | Stage 10 |
| Review reliability | Partial | Stage 10 |
| Live verification | Not recorded | Stage 10 |
| Database indexes | Only `users.email` | Stage 10 |
| TypeScript highlighting | Not implemented | Stage 10 |
| Public PR URL review | Not implemented | Stage 11 |
| Automatic GitHub context | Not implemented; manual snapshots work | Stage 11 |
| Repository, PR and author display | Not implemented | Stage 11 |
| Authentication and data isolation | Not implemented | Stage 12 |
| Project creation UI | API exists; UI is read-only | Stage 12 |
| Developer Feedback | `status` column only | Stage 12 |
| Learning outcomes | Interim page, no outcomes | Stage 12 |
| Semgrep and Bandit | Not implemented | Stage 13 |
| Evidence-based confidence | Formula exists, AI evidence only | Stage 13 |
| Quality evaluation | Not implemented | Stage 14 |
| Demo repository | Not implemented | Stage 14 |
| Deployment | Not implemented | Stage 14, if feasible |

**Optional future work (only if time remains):**
- ESLint
- Dependency vulnerability scanning
- Posting review comments to GitHub
- Simple risk scoring use of PR metadata

**Deliberately not planned for the capstone:**
- GitHub OAuth, GitHub Apps and private repositories
- Executing external project tests
- Git history analysis
- Recursive dependency analysis
- Persistent project snapshots
- A full per-developer Learning Profile with identity mapping
- Teams, roles, microservices and job-queue infrastructure

## Requirements

### Security

- Never commit secrets. `backend/.env` and `.claude/settings.json` stay out of Git.
- API keys and tokens stay on the server.
- Never run submitted or repository code.
- Treat all submitted code as untrusted data in prompts.
- Don't log source code or secrets.
- Don't host publicly without login or strict limits.
- Private code isn't supported.
- Remember that selected code is sent to the AI provider.

The app has no authentication today, so `GET /review-history/{id}` makes it easy to walk through every review. `/stats?q=` also reveals whether saved code contains a given string. Search is an unindexed scan, and `GET /code-reviews/` is unbounded. Stage 12 addresses access. Stage 14 must address request limits before any public deployment.

### Testing

- Every stage adds tests for new behavior, and all existing tests must keep passing.
- Bugs get a regression test.
- Automated tests use SQLite and mocked AI and GitHub services.
- Never test against real Supabase data without team approval.
- Report what was actually run. Don't claim live verification unless it happened.
- UI changes get a browser check.

### Honest data

- Never invent metrics, or show XP, levels, streaks or fix rates without real data.
- A repeated category isn't proof of the same mistake.
- A lower count isn't proof of improvement.
- Confidence isn't the probability a finding is correct.
- Risk isn't the probability of a failed merge.
- Unsupported features are omitted or marked "Coming soon".

## Technical decisions

Keep these unless the team agrees to change them:

- All frontend API calls stay in `services/api.js`.
- AI provider code stays in `ai_review_service.py`.
- The context collector stays independent of GitHub, AI and the database. GitHub code is an adapter that supplies its input.
- Language values have one shared source in `constants/languages.js`.
- Code is sent to the AI as JSON data, separate from instructions.
- History filters stay in the URL, and list rows stay lightweight.
- Project snapshots aren't stored. Store only summaries if needed.
- PR reviews extend the `CodeReview` and `ReviewIssue` flow instead of replacing it.
- Manual reviews stay supported.
- GitHub access uses public PR URLs and a read-only server-side token, not OAuth.

## Team development rules

- Check this plan before starting work. Follow [CLAUDE.md](../CLAUDE.md) for workflow.
- Work on a branch and merge to `main` through a pull request.
- Don't commit, push or merge on another person's behalf without their approval.
- Credit work accurately. Stage 6 is credited to bhavesh70655, and PR #2 only fixed it. Don't attribute a teammate's work to someone else.
- Commit authorship doesn't prove the full division of work.
- Plan before large work, and record it in `docs/plans/`.
- Summarize substantial work in `docs/reviews/`.
- Record real lessons in `docs/growth-log/`.
- Update this plan when a stage's status changes.

## Developer Learning: permanent requirement

Developer Learning is a permanent project goal. It was recorded early so it wouldn't be forgotten:

1. Track findings by the developer who wrote the code.
2. Categorize findings: Security, Testing, Error Handling, Input Validation, Database, Performance, Code Quality, Logic.
3. Store outcomes: `open`, `fixed`, `dismissed`, `false_positive`.
4. Detect recurring mistakes across reviews.
5. Show counts and improvement trends over time.
6. Provide a per-developer Learning Profile.

**Status:** item 2 is complete. Item 3 is planned for Stage 12. Item 5 is limited to real counts and outcomes. Items 1, 4 and 6 aren't fully implemented.

**Capstone scope:** Stage 12 improves the existing Learning page with real outcomes instead of building the full profile. The full requirement remains the long-term goal. See Open question 3.

`ReviewIssue` links through `CodeReview` and `Project` to `User`. That identifies the project owner, not necessarily the code's author, so a future profile must separate the two. Stage 11's PR author data is the starting point.

## Long-term goal

The early MVP reviewed one pasted file. The final goal is project-aware review of GitHub pull requests that uses surrounding code to catch issues a single-file review would miss. Stage 11 delivers this for public pull requests. The manual flow stays supported.

## Open questions

1. **Stage owners:** who owns Stages 10–14, and when is the final demo? Owners are TBD.
2. **Developer Feedback ownership:** `CLAUDE.md` assigns "Review History & Feedback" to a groupmate, but Feedback wasn't built and is now planned for Stage 12.
3. **Developer Learning:** the plan has reduced its capstone scope. The whole team should confirm this.
4. **Existing data:** which user should own existing Supabase rows in Stage 12?
5. **Schema state:** how were Stage 7 columns added to Supabase, and does the live schema match the models? PR #4 says Stage 8 columns were added by hand. Inspect this before the migration baseline.
6. **Database security:** is Row Level Security configured in Supabase?
7. **License:** the repository is public but has no license. Does the team want one?
8. **Pull request reviews:** none of PRs #1–#8 has a recorded GitHub review. Does the team want to require one?

## Superseded plans

This section is kept for history. **Don't use it for planning.**

### Original roadmap

1. Project Foundation
2. Database
3. Manual Code Submission
4. AI Review Service
5. Review Results UI
6. Review History
7. GitHub Integration
8. Smarter Review Context
9. Developer Feedback
10. Final Improvements

Stages 1–6 happened as planned. The rest changed:

| Original item | What happened |
|---|---|
| Stage 7 GitHub Integration | Not built. Confidence Scoring became Stage 7. GitHub work is now Stage 11. |
| Stage 8 Smarter Review Context | Partly delivered as Stage 9, using manual snapshots. PR Risk Scoring became Stage 8. |
| Stage 9 Developer Feedback | Not built. Project-Aware Review became Stage 9. Feedback is now Stage 12. |
| Stage 10 Final Improvements | Replaced by Stages 10–14. |

An older section also placed the Developer Learning Profile in Stage 7. That didn't happen. The redesign's Learning page is an interim view.

### Earlier roadmap proposals

A larger proposal with Stages 10–21 included separate deployment, Git history, dependency scanning, GitHub Apps and sandboxed test execution. It was rejected as too large for a capstone in favor of the Portfolio Version above.
