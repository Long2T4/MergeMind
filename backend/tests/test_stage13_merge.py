"""Stage 13: merging AI, Semgrep and Bandit findings, using REAL scanner output.

tests/fixtures/stage13/{bandit,semgrep}_vulnerable.json were recorded from
Bandit 1.9.4 and Semgrep 1.184.0 (MergeMind's local rules) scanning
fixtures/stage13/vulnerable.py with the app's exact command lines, so these
tests need no scanner installed. The AI findings are written the way Claude
words them (no AI call).
"""
import json
from pathlib import Path

from app.services.analysis_service import combine_statuses, merge_findings
from app.services.bandit_service import normalize_bandit_finding
from app.services.confidence_service import calculate_confidence
from app.services.semgrep_service import normalize_semgrep_finding

FIXTURES = Path(__file__).parent / "fixtures" / "stage13"

# The 8 real problems in vulnerable.py: line -> kind.
EXPECTED = {
    6: "hardcoded-secret", 9: "hardcoded-secret", 14: "code-eval", 18: "shell-injection",
    22: "shell-injection", 26: "deserialization", 27: "weak-hash", 32: "sql-injection",
}


def recorded(tool, normalize):
    results = json.loads((FIXTURES / f"{tool}_vulnerable.json").read_text())["results"]
    return [finding for result in results if (finding := normalize(result))]


def ai(line, title, severity="high", explanation=""):
    return {"title": title, "category": "security", "severity": severity, "line_number": line,
            "explanation": explanation or title, "why_it_matters": "It matters.", "suggested_fix": "Fix it."}


AI_FINDINGS = [
    ai(6, "Hard-coded database password"), ai(9, "Hard-coded default password"),
    ai(14, "Arbitrary code execution via eval()"), ai(18, "Command injection via shell=True"),
    ai(22, "Command injection via os.system"), ai(26, "Unsafe deserialization with pickle"),
    ai(27, "Weak MD5 hash", "medium"), ai(32, "SQL injection through string formatting"),
]


def test_recorded_scanner_output_has_one_finding_per_problem():
    semgrep = recorded("semgrep", normalize_semgrep_finding)
    bandit = recorded("bandit", normalize_bandit_finding)

    assert {f["line_number"]: f["kind"] for f in semgrep} == EXPECTED
    assert {f["line_number"]: f["kind"] for f in bandit} == EXPECTED
    # Readable titles, not rule IDs or "B105: ..."
    assert all("." not in f["title"] and not f["title"].startswith("B") for f in semgrep + bandit)


def test_the_same_problem_from_three_sources_is_one_finding():
    """Regression: PR #16's first version turned these 8 problems into 24 cards."""
    merged = merge_findings(
        AI_FINDINGS, recorded("semgrep", normalize_semgrep_finding), recorded("bandit", normalize_bandit_finding)
    )

    assert len(merged) == 8
    assert sorted(f["line_number"] for f in merged) == sorted(EXPECTED)
    for finding in merged:
        assert finding["evidence"] == {"ai": True, "semgrep": True, "bandit": True}
        assert "kind" not in finding  # internal; never saved
        assert calculate_confidence(finding["evidence"])["confidence_level"] == "high"
    # The AI's wording is kept, and the highest severity wins (Bandit says LOW
    # for line 6; the AI says high).
    line_6 = next(f for f in merged if f["line_number"] == 6)
    assert line_6["title"] == "Hard-coded database password"
    assert line_6["severity"] == "high"


def test_scanner_only_findings_still_merge_with_each_other():
    merged = merge_findings([], recorded("semgrep", normalize_semgrep_finding), recorded("bandit", normalize_bandit_finding))

    assert len(merged) == 8
    assert all(f["evidence"] == {"semgrep": True, "bandit": True} for f in merged)
    # Semgrep came first, so its plain-language explanation is kept.
    eval_finding = next(f for f in merged if f["line_number"] == 14)
    assert eval_finding["title"] == "Code execution with eval() or exec()"
    assert "eval() or exec() runs whatever text" in eval_finding["explanation"]


# --- Traps: different problems must stay separate -----------------------------

def bandit(line, test_id, severity="HIGH"):
    return normalize_bandit_finding({"test_id": test_id, "issue_text": f"{test_id} issue",
                                     "issue_severity": severity, "issue_confidence": "HIGH", "line_number": line})


def test_different_problems_on_neighbouring_lines_stay_separate():
    # pickle.loads on line 26, hashlib.md5 on line 27
    merged = merge_findings([], [], [bandit(26, "B301"), bandit(27, "B324")])
    assert len(merged) == 2


def test_different_problems_on_the_same_line_stay_separate():
    merged = merge_findings([ai(5, "SQL injection in the login query")], [], [bandit(5, "B105", "LOW")])
    assert len(merged) == 2


def test_the_same_kind_far_apart_stays_separate():
    merged = merge_findings([ai(5, "Hard-coded password")], [], [bandit(10, "B105", "LOW")])
    assert len(merged) == 2


def test_vague_or_ambiguous_ai_wording_is_never_merged():
    vague = ai(14, "Possible security issue")
    ambiguous = ai(14, "eval() runs an SQL string")  # names two kinds
    for finding in (vague, ambiguous):
        assert len(merge_findings([finding], [], [bandit(14, "B307")])) == 2


def test_two_findings_from_one_source_are_never_merged_together():
    # Two hard-coded passwords on lines 6 and 7: two problems, even though
    # they're the same kind and next to each other.
    merged = merge_findings([ai(6, "Hard-coded password"), ai(7, "Hard-coded API key")], [], [])
    assert len(merged) == 2


def test_a_scanner_finding_joins_the_nearest_matching_problem():
    merged = merge_findings(
        [ai(6, "Hard-coded password"), ai(7, "Hard-coded API key")], [], [bandit(7, "B105", "LOW")]
    )
    assert [f["evidence"] for f in merged] == [{"ai": True}, {"ai": True, "bandit": True}]


def test_unknown_kinds_are_kept_but_never_merged():
    unknown = normalize_bandit_finding({"test_id": "B113", "test_name": "request_without_timeout",
                                        "issue_text": "Call to requests without timeout", "issue_severity": "MEDIUM",
                                        "issue_confidence": "LOW", "line_number": 3})
    assert unknown is None  # LOW confidence is dropped
    unknown = normalize_bandit_finding({"test_id": "B113", "test_name": "request_without_timeout",
                                        "issue_text": "Call to requests without timeout", "issue_severity": "MEDIUM",
                                        "issue_confidence": "HIGH", "line_number": 3,
                                        "more_info": "https://bandit.readthedocs.io/en/1.9.4/plugins/b113.html"})
    assert unknown["kind"] is None
    assert unknown["title"] == "Request without timeout"
    assert unknown["suggested_fix"].endswith("b113.html")
    assert len(merge_findings([ai(3, "Request without a timeout can hang")], [], [unknown])) == 2


def test_findings_without_a_line_are_never_merged():
    assert len(merge_findings([ai(None, "Hard-coded password")], [], [bandit(1, "B105")])) == 2


# --- Scanner status for pull request reviews ----------------------------------

def test_pull_request_status_reports_any_failure_then_completed():
    done = {"semgrep": "completed", "bandit": "completed"}
    assert combine_statuses([]) is None
    assert combine_statuses([done, {"semgrep": "failed", "bandit": "completed"}]) == {
        "semgrep": "failed", "bandit": "completed"}
    assert combine_statuses([{"semgrep": "not_run", "bandit": "not_run"}, done]) == done
    assert combine_statuses([{"semgrep": "unavailable", "bandit": "not_run"}]) == {
        "semgrep": "unavailable", "bandit": "not_run"}
