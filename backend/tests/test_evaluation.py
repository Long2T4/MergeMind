"""Stage 14: the evaluation dataset and scoring (no scanners, no AI calls)."""
import json

import pytest

from evaluation import run_evaluation as evaluation


def finding(file, line, title, sources=("bandit",), category="security", kind=None):
    return {"file": file, "line_number": line, "title": title, "explanation": title, "category": category,
            "evidence": {source: True for source in sources}, **({"kind": kind} if kind else {})}


def problem(pid, file, line, kind, category="security"):
    return {"id": pid, "file": file, "line": line, "kind": kind, "category": category, "problem": pid}


def test_the_dataset_is_consistent():
    expected, clean_files = evaluation.load_manifest()
    assert len(expected) == 19
    assert len({item["id"] for item in expected}) == 19
    files = set(evaluation.case_files())
    assert {item["file"] for item in expected} <= files
    assert set(clean_files) <= files and all(name.startswith("clean_") for name in clean_files)
    assert not {item["file"] for item in expected} & set(clean_files)
    # Every snippet points at exactly one real line (load_manifest checks this).
    assert all(item["line"] >= 1 for item in expected)


def test_a_snippet_must_match_exactly_one_line(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\nx = 1\n")
    (tmp_path / "expected.json").write_text(json.dumps({
        "expected": [{"id": "E1", "file": "a.py", "contains": "x = 1", "kind": None, "category": "logic"}],
        "clean_files": []}))
    with pytest.raises(ValueError, match="found 2 times"):
        evaluation.load_manifest(tmp_path / "expected.json", tmp_path)


def test_each_finding_counts_for_its_nearest_problem_only():
    # Two hard-coded secrets on lines 5 and 6; two findings on 5 and 6.
    expected = [problem("E1", "a.py", 5, "hardcoded-secret"), problem("E2", "a.py", 6, "hardcoded-secret")]
    findings = [finding("a.py", 5, "Hard-coded password or secret"), finding("a.py", 6, "Hard-coded password or secret")]

    result = evaluation.score(expected, findings, [])

    assert [row["caught"] for row in result["expected"]] == [True, True]
    assert result["summary"]["duplicate_cards"] == 0


def test_a_finding_of_a_different_kind_does_not_count():
    expected = [problem("E1", "a.py", 5, "sql-injection")]
    result = evaluation.score(expected, [finding("a.py", 5, "Weak hash (MD5 or SHA-1)")], [])
    assert result["expected"][0]["caught"] is False
    assert result["summary"]["unlabeled_findings"] == 1


def test_scanner_findings_without_a_kind_can_match_non_security_problems():
    # Bandit's try/except/pass is filed as "security" but is the swallowed-error problem.
    expected = [problem("E1", "a.py", 20, None, "error_handling")]
    result = evaluation.score(expected, [finding("a.py", 20, "Try except pass")], [])
    assert result["expected"][0]["caught"] is True


def test_recall_by_source_duplicates_and_false_positives():
    expected = [problem("E1", "a.py", 3, "code-eval"), problem("E2", "a.py", 9, None, "logic")]
    findings = [
        finding("a.py", 3, "Code execution with eval() or exec()", sources=("ai", "semgrep", "bandit")),
        finding("a.py", 4, "eval() runs input", sources=("ai",), kind="code-eval"),  # a second card
        finding("clean_a.py", 2, "Hard-coded password or secret", sources=("semgrep",)),
    ]

    summary = evaluation.score(expected, findings, ["clean_a.py"])["summary"]

    assert summary["combined"] == {"caught": 1, "total": 2}
    assert summary["by_source"]["semgrep"] == {"caught": 1, "total": 2}
    assert summary["rule_covered"]["combined"] == {"caught": 1, "total": 1}
    assert summary["other_problems"]["combined"] == {"caught": 0, "total": 1}
    assert summary["duplicate_cards"] == 1
    assert summary["false_positive_findings"] == 1
    assert summary["false_positives"]["semgrep"] == 1


def test_real_ai_runs_only_with_explicit_permission(capsys):
    with pytest.raises(SystemExit):
        evaluation.main(["--ai"])
    assert "--allow-ai-spending" in capsys.readouterr().err


def test_saved_ai_findings_are_scored_without_calling_the_ai(tmp_path, monkeypatch):
    saved = {"orders.py": [{"title": "Off-by-one skips the last item", "category": "logic", "severity": "medium",
                            "line_number": 3, "explanation": "range(len(items) - 1) skips the last item.",
                            "why_it_matters": "", "suggested_fix": ""}]}
    (tmp_path / "ai.json").write_text(json.dumps(saved))
    called = []
    monkeypatch.setattr("app.services.ai_review_service.review_code", lambda *a, **k: called.append(a))

    findings, _ = evaluation.run("replay", tmp_path / "ai.json")
    expected, clean_files = evaluation.load_manifest()
    rows = {row["id"]: row for row in evaluation.score(expected, findings, clean_files)["expected"]}

    assert called == []
    assert rows["E15"]["caught"] and rows["E15"]["sources"] == ["ai"]
