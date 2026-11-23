"""Stage 13: the REAL Semgrep and Bandit on known vulnerable and clean code.

These run the installed tools (no mocks). A missing tool skips its tests,
except where MERGEMIND_REQUIRE_SCANNERS names it (CI: "semgrep,bandit" on
Ubuntu, "bandit" on Windows), so CI can't pass without really scanning.
Semgrep must be installed separately; see requirements-semgrep.txt.
"""
import os
import shutil
from pathlib import Path

import pytest

from app.services import analysis_service
from app.services.analysis_service import collect_security_findings, merge_findings
from app.services.bandit_service import _default_executable as bandit_executable, run_bandit_scan
from app.services.confidence_service import calculate_confidence
from app.services.semgrep_service import run_semgrep_scan

pytestmark = pytest.mark.real_scanners

FIXTURES = Path(__file__).parent / "fixtures" / "stage13"
REQUIRED = {name.strip() for name in os.environ.get("MERGEMIND_REQUIRE_SCANNERS", "").split(",") if name.strip()}

# vulnerable.py: line -> kind. Both tools must find exactly these.
VULNERABLE = {
    6: "hardcoded-secret", 9: "hardcoded-secret", 14: "code-eval", 18: "shell-injection",
    22: "shell-injection", 26: "deserialization", 27: "weak-hash", 32: "sql-injection",
}


def installed(name):
    executable = os.environ.get("SEMGREP_EXECUTABLE", "semgrep") if name == "semgrep" else bandit_executable()
    return shutil.which(executable) is not None or Path(executable).is_file()


def need(*names):
    for name in names:
        if not installed(name):
            if name in REQUIRED:
                pytest.fail(f"{name} is required here (MERGEMIND_REQUIRE_SCANNERS) but isn't installed")
            pytest.skip(f"{name} isn't installed")


def code(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def found(findings):
    return {finding["line_number"]: finding["kind"] for finding in findings}


def test_bandit_finds_every_planted_problem():
    need("bandit")
    findings = run_bandit_scan(code("vulnerable.py"))
    assert found(findings) == VULNERABLE
    assert len(findings) == len(VULNERABLE)  # nothing extra: noisy checks are skipped


def test_bandit_reports_nothing_on_clean_code():
    need("bandit")
    assert run_bandit_scan(code("clean.py")) == []


def test_bandit_edge_cases():
    need("bandit")
    # Bandit also flags eval/os.system with fixed strings (lines 9-10); its
    # low-confidence "no timeout" warning on line 14 is dropped.
    assert found(run_bandit_scan(code("edge_cases.py"))) == {
        9: "code-eval", 10: "shell-injection", 12: "deserialization", 14: "tls-disabled"}


def test_semgrep_local_rules_find_every_planted_problem():
    need("semgrep")
    findings = run_semgrep_scan(code("vulnerable.py"))
    assert found(findings) == VULNERABLE
    assert len(findings) == len(VULNERABLE)


def test_semgrep_reports_nothing_on_clean_code():
    need("semgrep")
    assert run_semgrep_scan(code("clean.py")) == []


def test_semgrep_edge_cases():
    need("semgrep")
    # Flags unsafe yaml.load and verify=False. Ignores an empty API_KEY, a
    # token from the environment, eval/os.system on fixed strings, SafeLoader,
    # MD5 with usedforsecurity=False and a parameterized query.
    assert found(run_semgrep_scan(code("edge_cases.py"))) == {12: "deserialization", 14: "tls-disabled"}


def test_both_real_scanners_and_the_ai_give_one_finding_per_problem():
    need("semgrep", "bandit")
    result = collect_security_findings(code("vulnerable.py"), "python")
    assert analysis_service.analysis_status(result) == {"semgrep": "completed", "bandit": "completed"}

    ai = [{"title": title, "category": "security", "severity": "high", "line_number": line,
           "explanation": title, "why_it_matters": "", "suggested_fix": ""}
          for line, title in [(6, "Hard-coded password"), (14, "Use of eval()"), (18, "Command injection via shell=True")]]
    merged = merge_findings(ai, result["semgrep"], result["bandit"])

    assert len(merged) == len(VULNERABLE)
    levels = {f["line_number"]: calculate_confidence(f["evidence"])["confidence_level"] for f in merged}
    assert {line: levels[line] for line in (6, 14, 18)} == {6: "high", 14: "high", 18: "high"}  # AI + both tools
    assert levels[22] == "medium"  # both tools, no AI finding


def test_code_with_a_syntax_error_is_reported_as_failed_not_clean():
    need("bandit")
    result = collect_security_findings("def broken(:\n    pass\n", "python")
    assert result["bandit_status"] == "failed"
    assert result["bandit"] == []


def test_semgrep_finds_sql_built_from_strings_anywhere():
    """Stage 14 evaluation: SQL built with %, +, .format() or an f-string is
    found even when stored in a variable first. Parameterized queries and
    ordinary text starting with "select"/"update" are not."""
    need("semgrep")
    assert found(run_semgrep_scan(code("sql_shapes.py"))) == {line: "sql-injection" for line in range(2, 7)}

