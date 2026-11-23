# MergeMind demo script

**Length:** about 8 minutes, with a presenter driving the app.

**What it shows:**
- sign-in and projects;
- a manual review where the AI and two scanners agree;
- a beginner explanation, and recording an outcome;
- two GitHub pull request reviews;
- History and Learning;
- an honest close on limitations.

All demo code is fictional and contains deliberate mistakes. It lives in [`demo/`](../demo/README.md).

## Before the demo

1. **Services are running:**
   - the backend, with migrations applied and `SEMGREP_EXECUTABLE` working (`semgrep --version`);
   - the frontend;
   - Supabase Auth, set up as in [supabase-auth.md](supabase-auth.md).

   For a hosted demo, see [deployment.md](deployment.md).
2. **A presenter account** exists and has signed in once. With invite-only sign-up, invite it in Supabase.
3. **The demo pull requests are public on GitHub.** PR #1 is already published: <https://github.com/Long2T4/mergemind-demo/pull/1>. PR #2 isn't published yet:
   - build it with `python demo/build_demo_repo.py <folder>`;
   - push the `demo/add-backup-tool` branch to `Long2T4/mergemind-demo`;
   - open a pull request from it.

   That needs a team member's GitHub access.
4. **AI spending:** an Anthropic spending limit is set. The whole demo makes about 8 AI calls:
   - 1 for the manual review;
   - 1 per reviewed file in the pull requests (3 + 1);
   - 1 for the beginner explanation;
   - 1–2 spare.
5. **Browser:** zoom at 110–125%, with `demo/manual-review-sample.py` open, ready to copy.
6. **Fallback:** the [demo video](#fallback) is ready.

## Script

| # | Do | Point out |
|---|---|---|
| 1 | Sign in. | The email and **Log out** in the sidebar. Every review belongs to the signed-in user; nobody else can see it. |
| 2 | **Projects** → create "Demo project". | New Review uses the selected project. |
| 3 | **New Review** → paste `demo/manual-review-sample.py` → **Run review**. | Findings on lines 4 (hard-coded key), 8 (`shell=True`), 12 (MD5) and 16 (division by zero). The **Static analysis** card shows Semgrep and Bandit checked the code. |
| 4 | Open the `shell=True` finding. | **Confidence high (80)**: the AI, Semgrep and Bandit agree, so it's one finding, not three. The division by zero is AI-only (low, 20): confidence measures supporting evidence, not probability. |
| 5 | **Explain like I'm new** on that finding. | A plain-language explanation and a before-and-after example, saved for next time. |
| 6 | Set **Your outcome** to **Fixed (self-reported)**. | Outcomes feed Learning. "Fixed" is the student's own report. |
| 7 | **New Review** → **GitHub pull request** → `https://github.com/Long2T4/mergemind-demo/pull/1`. | Progress while files are reviewed. Then: <ul><li>the SQL injection in `app/users.py` line 12, backed by the AI and Semgrep;</li><li>the JavaScript off-by-one in `web/format.js`;</li><li>the old `eval()` labeled **Outside the diff**;</li><li>docs, the lockfile and the removed file listed as skipped.</li></ul> |
| 8 | Review PR #2 (`demo/add-backup-tool`). | The token and both shell commands are high confidence (all three sources). The `latest()` index bug is found by the AI alone. |
| 9 | **History** → search `subprocess`; open a review and go back. | Filters stay in the URL. |
| 10 | **Learning**. | Outcomes by category, including the self-reported fix. Counts come from saved findings only. |
| 11 | Close on [evaluation.md](evaluation.md). | The scanners catch every known problem they have rules for, with no false positives. Logic and design problems need the AI, and AI findings can be wrong. |

With the real AI, wording and exact findings vary between runs. The scanner findings and their lines don't.

## Rehearsal record

**2026-11-23, rehearsed start to finish in a browser on the Stage 14 branch.** Setup:
- the real backend and frontend, with real Semgrep 1.184.0 and Bandit 1.9.4 in a Linux container;
- a fake Supabase Auth server issuing real RS256 tokens;
- a fake GitHub serving the two demo PRs built from `demo/`;
- a scripted stand-in for the AI. No Anthropic, GitHub or Supabase calls.

Every step worked:

| Step | Result |
|---|---|
| 3–4 | Confidence 80 for `shell=True` and MD5; 50 for the key (Bandit only checks names like "password", "secret" and "token"); 20 for the AI-only division by zero |
| 5 | Explanation shown |
| 6 | Outcome saved |
| 7 | SQL injection backed by the AI and Semgrep; `eval()` outside the diff; three files skipped |
| 8 | 80/80/80 and an AI-only 20 |
| 9 | History: 3 reviews |
| 10 | Learning: 12 findings, 1 fixed |

Also checked: no console errors, no sideways scrolling at 390 px, and **Log out** works from the mobile menu.

**Not yet rehearsed:** a live run with the real AI, real GitHub and Supabase. Do it once with the presenter account before the final demo; it costs about 8 AI calls.

## Fallback

If Anthropic, GitHub or the hosting is unavailable during the presentation, play a recorded run of this script. Record it during the live rehearsal above, and keep it under 8 minutes.
