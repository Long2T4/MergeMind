"""Stage 13: how MergeMind runs Semgrep and Bandit, and reports what happened.

The scanners are faked here (subprocess.run is patched); the real tools are
tested in test_stage13_real_scanners.py.
"""
import json
import subprocess
from unittest.mock import patch

import pytest
import yaml

from app.services import analysis_service, bandit_service, semgrep_service
from app.services.bandit_service import BanditScanError, BanditUnavailable, normalize_bandit_finding, run_bandit_scan
from app.services.finding_kinds import KINDS, kind_from_text
from app.services.semgrep_service import (
    RULES_FILE, SemgrepScanError, SemgrepUnavailable, normalize_semgrep_finding, run_semgrep_scan,
)


def completed(stdout, returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


# --- Semgrep -------------------------------------------------------------------

def test_semgrep_uses_mergemind_local_rules_offline():
    with patch.object(semgrep_service.subprocess, "run", return_value=completed('{"results": [], "errors": []}')) as run:
        assert run_semgrep_scan("x = 1", "semgrep") == []

    command = run.call_args.args[0]
    assert command[command.index("--config") + 1] == str(RULES_FILE)
    assert not any(part.startswith(("p/", "r/", "http")) for part in command)  # no registry download
    assert {"--metrics=off", "--disable-version-check", "--json"} <= set(command)
    assert run.call_args.kwargs["timeout"] == 30
    assert "shell" not in run.call_args.kwargs  # never through a shell


def test_semgrep_rules_file_is_valid_and_every_rule_has_a_known_kind():
    rules = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))["rules"]
    assert len(rules) == 7
    for rule in rules:
        assert rule["languages"] == ["python"]
        assert rule["metadata"]["mergemind_kind"] in KINDS, rule["id"]
        assert rule["metadata"]["cwe"].startswith("CWE-")


def test_a_missing_semgrep_is_unavailable_not_failed():
    with patch.object(semgrep_service.subprocess, "run", side_effect=FileNotFoundError):
        with pytest.raises(SemgrepUnavailable):
            run_semgrep_scan("x = 1", "semgrep")


def test_semgrep_keeps_partial_results_but_fails_with_only_errors():
    result = {"check_id": "rules.mergemind.code-eval", "start": {"line": 2},
              "extra": {"severity": "ERROR", "message": "eval() runs text.",
                        "metadata": {"mergemind_kind": "code-eval", "cwe": "CWE-95"}}}
    partial = json.dumps({"results": [result], "errors": [{"message": "Syntax error at line 9"}]})
    with patch.object(semgrep_service.subprocess, "run", return_value=completed(partial)):
        assert len(run_semgrep_scan("x = 1", "semgrep")) == 1

    only_errors = json.dumps({"results": [], "errors": [{"message": "Syntax error"}]})
    with patch.object(semgrep_service.subprocess, "run", return_value=completed(only_errors)):
        with pytest.raises(SemgrepScanError, match="errors"):
            run_semgrep_scan("x = (", "semgrep")


def test_semgrep_finding_gets_a_readable_title_fix_and_rule_reference():
    finding = normalize_semgrep_finding({
        "check_id": "app.analysis_rules.mergemind.shell-injection", "start": {"line": 18},
        "extra": {"severity": "ERROR", "message": "The command runs through a shell.",
                  "metadata": {"mergemind_kind": "shell-injection", "cwe": "CWE-78"}}})

    assert finding["title"] == "Command run through a shell"
    assert finding["suggested_fix"] == KINDS["shell-injection"].fix
    assert finding["why_it_matters"] == "Semgrep's shell-injection rule matched this line (CWE-78)."
    assert finding["severity"] == "high"
    assert finding["kind"] == "shell-injection"


# --- Bandit --------------------------------------------------------------------

def test_bandit_skips_noisy_checks_and_never_uses_a_shell():
    with patch.object(bandit_service.subprocess, "run", return_value=completed('{"results": [], "errors": []}')) as run:
        assert run_bandit_scan("x = 1", "bandit") == []

    command = run.call_args.args[0]
    assert command[command.index("--skip") + 1] == "B101,B403,B404,B603,B607"
    assert run.call_args.kwargs["timeout"] == 30
    assert "shell" not in run.call_args.kwargs


def test_a_missing_bandit_is_unavailable_not_failed():
    with patch.object(bandit_service.subprocess, "run", side_effect=FileNotFoundError):
        with pytest.raises(BanditUnavailable):
            run_bandit_scan("x = 1", "bandit")


def test_bandit_failure_without_results_is_an_error():
    only_errors = json.dumps({"results": [], "errors": [{"filename": "x.py", "reason": "syntax error"}]})
    with patch.object(bandit_service.subprocess, "run", return_value=completed(only_errors)):
        with pytest.raises(BanditScanError, match="errors"):
            run_bandit_scan("x = (", "bandit")


def test_bandit_drops_low_confidence_findings():
    finding = {"test_id": "B105", "issue_text": "Possible hardcoded password", "issue_severity": "LOW",
               "line_number": 3, "issue_confidence": "LOW"}
    assert normalize_bandit_finding(finding) is None
    assert normalize_bandit_finding({**finding, "issue_confidence": "MEDIUM"})["title"] == KINDS["hardcoded-secret"].title


def test_bandit_is_found_next_to_python_when_not_on_path(monkeypatch):
    monkeypatch.delenv("BANDIT_EXECUTABLE", raising=False)
    executable = bandit_service._default_executable()
    assert executable == "bandit" or executable.lower().endswith(("bandit", "bandit.exe"))
    monkeypatch.setenv("BANDIT_EXECUTABLE", "/opt/tools/bandit")
    assert bandit_service._default_executable() == "/opt/tools/bandit"


# --- What the review records about each scanner --------------------------------

@pytest.mark.parametrize("semgrep_error, expected", [
    (None, "completed"),
    (SemgrepUnavailable("missing"), "unavailable"),
    (SemgrepScanError("timed out"), "failed"),
])
def test_each_scanner_status_is_reported_separately(monkeypatch, semgrep_error, expected):
    def semgrep(code):
        if semgrep_error:
            raise semgrep_error
        return []

    monkeypatch.setattr(analysis_service, "run_semgrep_scan", semgrep)
    monkeypatch.setattr(analysis_service, "run_bandit_scan", lambda code: [])
    result = analysis_service.collect_security_findings("x = 1", "python")

    assert analysis_service.analysis_status(result) == {"semgrep": expected, "bandit": "completed"}


def test_only_python_is_scanned():
    result = analysis_service.collect_security_findings("eval(x)", "javascript")
    assert analysis_service.analysis_status(result) == {"semgrep": "not_run", "bandit": "not_run"}


# --- Reading the kind of an AI finding -----------------------------------------

@pytest.mark.parametrize("title, explanation, kind", [
    ("Hard-coded database password", "", "hardcoded-secret"),
    ("Arbitrary code execution via eval()", "", "code-eval"),
    ("Command injection via os.system", "", "shell-injection"),
    ("Unsafe deserialization with pickle", "", "deserialization"),
    ("Weak MD5 hash", "", "weak-hash"),
    ("SQL injection through string formatting", "", "sql-injection"),
    ("Possible security issue", "The query uses an f-string with user input in SQL.", "sql-injection"),
    ("Possible security issue", "", None),
    ("eval() runs an SQL string", "", None),  # two kinds named: don't guess
    ("Database cursor.execute is slow", "", None),  # 'execute' is not 'exec'
])
def test_ai_findings_get_a_kind_only_when_clear(title, explanation, kind):
    assert kind_from_text(title, explanation) == kind


def test_bandit_ignores_an_empty_string_assigned_to_a_secret_name():
    """Stage 14 evaluation: TOKEN = "" isn't a hard-coded secret."""
    empty = {"test_id": "B105", "issue_text": "Possible hardcoded password: ''", "issue_severity": "LOW",
             "issue_confidence": "MEDIUM", "line_number": 7}
    assert normalize_bandit_finding(empty) is None
    real = {**empty, "issue_text": "Possible hardcoded password: 'Winter2024!'"}
    assert normalize_bandit_finding(real)["kind"] == "hardcoded-secret"


def test_bandit_blacklist_checks_get_a_readable_title():
    finding = normalize_bandit_finding({
        "test_id": "B311", "test_name": "blacklist", "issue_severity": "LOW", "issue_confidence": "HIGH",
        "line_number": 3,
        "issue_text": "Standard pseudo-random generators are not suitable for security/cryptographic purposes."})
    assert finding["title"] == "Standard pseudo-random generators are not suitable for security/cryptographic purposes"

