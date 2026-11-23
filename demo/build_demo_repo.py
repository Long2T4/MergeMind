"""Rebuild MergeMind's demo repository locally: main plus one branch per example PR.

    python demo/build_demo_repo.py <empty-or-new-folder>

Uses demo/mergemind-demo/main (the base) and demo/mergemind-demo/pull-requests/*
(each: pr.json and the files that pull request adds or changes). Only local git
commands run; nothing is pushed. The output ends with the commands to publish
the repository and open the pull requests, for a team member to run.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent / "mergemind-demo"
# Fixed author and dates, so every rebuild gives the same commits.
GIT_ENV = {
    "GIT_AUTHOR_NAME": "MergeMind Demo", "GIT_AUTHOR_EMAIL": "demo@example.com",
    "GIT_COMMITTER_NAME": "MergeMind Demo", "GIT_COMMITTER_EMAIL": "demo@example.com",
    "GIT_AUTHOR_DATE": "2026-11-01T12:00:00+00:00", "GIT_COMMITTER_DATE": "2026-11-01T12:00:00+00:00",
}


def git(target, *args):
    return subprocess.run(["git", *args], cwd=target, check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


def pull_requests():
    return [(folder, json.loads((folder / "pr.json").read_text(encoding="utf-8")))
            for folder in sorted((HERE / "pull-requests").iterdir()) if (folder / "pr.json").is_file()]


def build(target):
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"{target} is not empty; choose a new folder")
    target.mkdir(parents=True, exist_ok=True)

    git(target, "init", "--initial-branch=main")
    shutil.copytree(HERE / "main", target, dirs_exist_ok=True)
    git(target, "add", "--all")
    git(target, "commit", "--message", "Fictional demo project for MergeMind")

    branches = []
    for folder, pr in pull_requests():
        git(target, "switch", "--create", pr["branch"], "main")
        shutil.copytree(folder / "files", target, dirs_exist_ok=True)
        for removed in pr.get("removed", []):
            git(target, "rm", "--quiet", removed)
        git(target, "add", "--all")
        git(target, "commit", "--message", pr["title"])
        branches.append(pr)
    git(target, "switch", "main")
    return branches


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit(__doc__)
    branches = build(args[0])
    print(f"Built {args[0]}: main and {len(branches)} pull request branch(es).\n")
    print("To publish (a team member, with their own GitHub access):")
    print("  git remote add origin https://github.com/<owner>/mergemind-demo.git")
    print("  git push -u origin main " + " ".join(pr["branch"] for pr in branches))
    for pr in branches:
        print(f'  gh pr create --base main --head {pr["branch"]} --title "{pr["title"]}" --body "{pr["body"]}"')


if __name__ == "__main__":
    main()
