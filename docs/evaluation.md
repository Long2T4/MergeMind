# MergeMind evaluation

What MergeMind catches and misses on code with known problems, how this was measured, and how to repeat it.

## Method

- **Dataset:** [`backend/evaluation/cases/`](../backend/evaluation/cases). It's fictional Python with **19 known problems** in 4 files, plus 3 clean look-alike files. The problems are listed in [`expected.json`](../backend/evaluation/expected.json), each located by a code snippet, never by comments in the code, so the AI gets no hints.
  - **11 problems a scanner rule targets:** hard-coded secrets, MD5, SQL built from strings, shell commands, `eval`, `pickle` and YAML loading, and disabled certificate checks.
  - **8 other problems that need the AI:**
    - security: insecure randomness, a request to a user-supplied URL (SSRF), and path traversal;
    - an off-by-one, a mutable default, a swallowed exception, division by zero, and missing input validation.
  - **The clean files** use the safe version of the same code: parameterized SQL, `subprocess` with a list, `yaml.safe_load`, `secrets`, and environment variables. Any finding there is a **false positive**.
- **Pipeline:** the same code a review uses: the scanners, the merge of matching findings, and the confidence score. So the numbers describe what a user would see.
- **A finding counts for a problem** when it's:
  - in the same file;
  - at most 1 line away;
  - not identified as a different kind of problem.

  Each finding counts for its nearest problem only. Two findings for one problem count as a duplicate.
- **Measures:**
  - problems caught, overall and by source (AI, Semgrep, Bandit);
  - rule-covered problems vs other problems;
  - duplicate cards;
  - false positives;
  - findings that match no labeled problem.

## Results (2026-11-23, scanners only)

**Environment:** Linux, Python 3.12, Semgrep 1.184.0 with MergeMind's rules, Bandit 1.9.4. Scanners only; the AI is reported [below](#ai-evaluation-2026-11-23-one-run-before-the-line-number-fix). Raw output: [`results/2026-11-23-scanners.json`](../backend/evaluation/results/2026-11-23-scanners.json).

| Measure | `main` before Stage 14 | Stage 14 |
|---|---|---|
| Known problems caught, all sources | 12/19 | **13/19** |
| Problems a scanner rule targets | 10/11 | **11/11** |
| Other problems (need the AI) | 2/8 | 2/8 |
| Caught by Semgrep | 10/19 | 11/19 |
| Caught by Bandit | 12/19 | 12/19 |
| False positives on the clean files | 1 | **0** |
| Duplicate cards for one problem | 0 | 0 |

**What changed:** the evaluation found two scanner problems, both fixed in Stage 14.
- **SQL stored in a variable was missed.** Semgrep's SQL rule only matched queries formatted inside `.execute(...)`, so a query built into a variable and run later was missed (E05). The demo pull request has the same pattern. The rule now matches SQL built with `%`, `+`, `.format()` or an f-string anywhere.
- **An empty secret was reported.** Bandit flagged `TOKEN = ""` as a hard-coded secret. An empty value is now ignored.

| ID | Problem | Caught by | Confidence |
|---|---|---|---|
| E01 | Hard-coded admin password | Semgrep, Bandit | medium |
| E02 | Hard-coded signing secret | Semgrep, Bandit | medium |
| E03 | MD5 used to hash passwords | Semgrep, Bandit | medium |
| E04 | Reset token from `random` | Bandit | low |
| E05 | SQL built with `%` in a variable, run later | Semgrep | low |
| E06 | SQL built with an f-string | Semgrep, Bandit | medium |
| E07 | `shell=True` with input | Semgrep, Bandit | medium |
| E08 | `os.popen` with input | Semgrep, Bandit | medium |
| E09 | `eval()` on input | Semgrep, Bandit | medium |
| E10 | `pickle.loads` on untrusted data | Semgrep, Bandit | medium |
| E11 | `yaml.load` without a safe loader | Semgrep, Bandit | medium |
| E12 | Certificate checks turned off | Semgrep, Bandit | medium |
| E13 | Request to a user-supplied URL (SSRF) | missed | – |
| E14 | Path traversal through a file name | missed | – |
| E15 | Off-by-one skips the last item | missed | – |
| E16 | Division by zero on an empty list | missed | – |
| E17 | Mutable default argument | missed | – |
| E18 | Swallowed exception | Bandit | low |
| E19 | Quantity not validated | missed | – |

## What this shows

- **Rule-covered problems:** the scanners caught all 11 targeted problems, with no false positives on the look-alike safe code. When both scanners agree, a finding reaches medium confidence. With the AI also agreeing it reaches high, as the demo shows.
- **Other problems:** design, logic and data-flow problems (SSRF, path traversal, off-by-one, missing validation) are outside the scanners' rules. Only the AI can catch them. In one run it caught 4 of 8 (see below).
- **Limits of this evaluation:**
  - The dataset is small and written by the team, and it's Python only, so the numbers show behavior, not general accuracy.
  - The Semgrep SQL rule can also match English text that reads like SQL, such as `f"delete from your list? {x}"`.

## AI evaluation (2026-11-23, one run, before the line-number fix)

The real AI ran once on the same dataset: 7 Anthropic calls, Claude Haiku 4.5, one per case file. Raw files:
- [`results/2026-11-23-ai-unnumbered.json`](../backend/evaluation/results/2026-11-23-ai-unnumbered.json);
- the AI's own findings, [`results/2026-11-23-ai-findings-unnumbered.json`](../backend/evaluation/results/2026-11-23-ai-findings-unnumbered.json), which can be re-scored without new calls.

| Measure | Scanners only | Scanners + AI |
|---|---|---|
| Known problems caught | 13/19 | **15/19** |
| Caught by the AI | – | 7/19 |
| Other problems (need the AI) | 2/8 | **4/8**: SSRF, off-by-one, swallowed exception, insecure token |
| Findings on a labeled problem's line, all sources agreeing (high confidence) | 0 | 2 |
| Duplicate cards for one problem | 0 | 3 |
| False positives on the clean files | 0 | 10 (all from the AI) |
| AI findings not matching a labeled problem | – | 12 |

**What it found: the AI's line numbers were often wrong.**
- **Wrong lines:** most of the 12 unmatched AI findings describe a real labeled problem, but point 1–4 lines away, often at a blank line. For example, the SQL injection was reported on line 15 instead of 19.
- **Why it matters:**
  - such a finding can't merge with the scanners' finding for the same problem, so the user sees it twice (the 3 duplicates);
  - it loses the confidence that agreement would give;
  - it isn't counted as a catch.
- **The cause:** manual reviews sent the code without line numbers, so the model counted lines itself. Pull request reviews already sent numbered lines, which in Stage 11 took exact lines from 1 of 5 to 5 of 6.
- **Fixed in Stage 14:** manual reviews are now sent numbered too. A submission too long to number within the prompt limit is still sent as before.
- **Not yet re-measured:** the fix's effect on these numbers needs another 7 approved calls (see below).

**False positives:** the 10 AI findings on the clean files are partly reasonable style remarks, such as a connection that isn't closed or a missing file encoding. Some are wrong: it called `ast.literal_eval` "unsafe evaluation", and `subprocess.run` with an argument list "unsafe". This is why AI-only findings show low confidence.

**Not caught by anything:** path traversal, division by zero on an empty list, the mutable default argument, and the missing quantity check. Some of these the AI described at a nearby wrong line, so a re-run may change this.

### Running the AI evaluation

It needs approved Anthropic calls: one per case file, so 7 calls at Claude Haiku pricing.

```bash
cd backend
python -m evaluation.run_evaluation --ai --allow-ai-spending --record-ai evaluation/results/<date>-ai-findings.json
```

`--record-ai` saves the AI's findings, so the published result can be scored again later without new calls:

```bash
python -m evaluation.run_evaluation --ai-findings evaluation/results/<date>-ai-findings.json
```

AI output varies between runs, so publish the recorded findings next to the result. Report a range if you run it more than once.

## Reproduce

Semgrep needs Linux, macOS or WSL (see the README's [Static analysis](../README.md#static-analysis) setup). From `backend/`:

```bash
python -m evaluation.run_evaluation --json evaluation/results/<date>-scanners.json --markdown report.md
```

Without Semgrep, the report says "not installed" and shows only Bandit's results. The scoring is tested in `backend/tests/test_evaluation.py`.
