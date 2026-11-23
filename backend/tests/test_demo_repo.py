"""Stage 14: the demo repository can be rebuilt, and its pull requests show what
docs/demo-script.md promises (real scanners, when installed)."""
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from app.services.bandit_service import _default_executable as bandit_executable, run_bandit_scan
from app.services.semgrep_service import run_semgrep_scan

DEMO = Path(__file__).resolve().parents[2] / "demo"
PRS = DEMO / "mergemind-demo" / "pull-requests"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_demo_repo", DEMO / "build_demo_repo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


@pytest.mark.skipif(shutil.which("git") is None, reason="git isn't installed")
def test_the_demo_repository_rebuilds_with_both_pull_requests(tmp_path):
    branches = load_builder().build(tmp_path / "demo")
    repo = tmp_path / "demo"

    assert [pr["branch"] for pr in branches] == ["demo/add-signup", "demo/add-backup-tool"]
    assert git(repo, "branch", "--show-current").strip() == "main"
    signup = set(git(repo, "diff", "--name-status", "main", "demo/add-signup").split("\n")) - {""}
    assert signup == {"M\tapp/legacy.py", "A\tapp/users.py", "M\tdocs/notes.md", "D\told_helpers.py",
                      "M\tpackage-lock.json", "A\tweb/format.js"}
    assert git(repo, "diff", "--name-status", "main", "demo/add-backup-tool").strip() == "A\tapp/backup.py"
    # Fixed author and dates: every rebuild gives the same commits.
    again = load_builder().build(tmp_path / "again")
    assert len(again) == 2
    assert git(repo, "rev-parse", "demo/add-signup") == git(tmp_path / "again", "rev-parse", "demo/add-signup")


def test_it_refuses_to_overwrite_a_folder(tmp_path):
    (tmp_path / "existing.txt").write_text("keep me")
    with pytest.raises(SystemExit, match="not empty"):
        load_builder().build(tmp_path)
    assert (tmp_path / "existing.txt").read_text() == "keep me"


def found(findings):
    return {(finding["line_number"], finding["kind"]) for finding in findings}


@pytest.mark.real_scanners
def test_the_demo_pull_requests_trigger_the_scanners_as_scripted():
    semgrep_installed = shutil.which(os.environ.get("SEMGREP_EXECUTABLE", "semgrep")) is not None
    bandit_installed = shutil.which(bandit_executable()) is not None or Path(bandit_executable()).is_file()
    if not (semgrep_installed or bandit_installed):
        pytest.skip("no scanner installed")
    backup = (PRS / "02-add-backup-tool" / "files" / "app" / "backup.py").read_text(encoding="utf-8")
    users = (PRS / "01-add-signup" / "files" / "app" / "users.py").read_text(encoding="utf-8")
    # PR 2: hard-coded token (4), shell=True (8), os.system (12); the logic bug
    # in latest() (16) is for the AI only.
    expected_backup = {(4, "hardcoded-secret"), (8, "shell-injection"), (12, "shell-injection")}
    for installed, scan in ((semgrep_installed, run_semgrep_scan), (bandit_installed, run_bandit_scan)):
        if installed:
            assert found(scan(backup)) == expected_backup
    # PR 1: the SQL query built with an f-string and stored in a variable (12).
    if semgrep_installed:
        assert found(run_semgrep_scan(users)) == {(12, "sql-injection")}
