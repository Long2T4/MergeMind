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

**Environment:** Linux, Python 3.12, Semgrep 1.184.0 with MergeMind's rules, Bandit 1.9.4. **The AI was not run**; see [the AI evaluation](#ai-evaluation-not-run-yet). Raw output: [`results/2026-11-23-scanners.json`](../backend/evaluation/results/2026-11-23-scanners.json).

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
- **Other problems:** design, logic and data-flow problems (SSRF, path traversal, off-by-one, missing validation) are outside the scanners' rules. Only the AI can catch them. **How often it does hasn't been measured yet.**
- **Limits of this evaluation:**
  - The dataset is small and written by the team, and it's Python only, so the numbers show behavior, not general accuracy.
  - The Semgrep SQL rule can also match English text that reads like SQL, such as `f"delete from your list? {x}"`.

## AI evaluation (not run yet)

Measuring the AI needs real Anthropic calls: one per case file, so 7 calls at Claude Haiku pricing. It needs team approval:

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
