# MergeMind demo material

Fictional code with deliberate mistakes, for demonstrating MergeMind. None of it is real software.

| Path | What it is |
|---|---|
| `mergemind-demo/main/` | The demo repository's `main` branch. Published as [Long2T4/mergemind-demo](https://github.com/Long2T4/mergemind-demo) |
| `mergemind-demo/pull-requests/01-add-signup/` | PR #1 (`demo/add-signup`), published as [mergemind-demo#1](https://github.com/Long2T4/mergemind-demo/pull/1). Covers changed-line focus, a JavaScript file, skipped files, and SQL injection |
| `mergemind-demo/pull-requests/02-add-backup-tool/` | PR #2 (`demo/add-backup-tool`), **not published yet**. Here Semgrep, Bandit and the AI agree (high confidence), and one logic bug only the AI finds |
| `manual-review-sample.py` | Code to paste for the manual review step |
| `build_demo_repo.py` | Rebuilds the demo repository locally |

Each PR folder has a `pr.json` (branch, title, description, removed files) and the files the PR adds or changes.

## Rebuild the demo repository

```bash
python demo/build_demo_repo.py ../mergemind-demo-rebuild
```

This creates `main` and one branch per pull request, with a fixed author and dates, so every rebuild gives the same commits. It prints the commands to publish them. Nothing is pushed: publishing needs a team member's GitHub access.

`backend/tests/test_demo_repo.py` checks two things:
- the rebuild works;
- the demo files trigger the scanner findings the [demo script](../docs/demo-script.md) relies on, when the scanners are installed.
