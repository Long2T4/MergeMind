"""Stage 11: patch parsing, file filtering and changed-line focus. Pure functions, no I/O."""
import pytest

from app.services.diff_service import (
    MAX_OUTSIDE_DIFF_PER_FILE, changed_lines, focus_findings, language_for_path, skip_reason,
)


def test_changed_lines_are_new_file_line_numbers_of_added_lines():
    patch = (
        "@@ -1,4 +1,5 @@\n"
        " import os\n"        # new line 1
        "-old = 1\n"          # removed; anchors at new line 2
        "+new = 1\n"          # new line 2
        "+extra = 2\n"        # new line 3
        " keep()\n"           # new line 4
        "@@ -20,2 +21,3 @@ def f():\n"
        " a()\n"              # 21
        "+b()\n"              # 22
        " c()\n"              # 23
        "\\ No newline at end of file\n"
    )
    assert changed_lines(patch) == {2, 3, 22}


def test_deletion_only_hunks_mark_the_line_where_code_was_removed():
    assert changed_lines("@@ -5,3 +5,2 @@\n a\n-b\n c\n") == {6}


@pytest.mark.parametrize("patch", [None, "", "not a patch", "@@ broken @@\n+x"])
def test_unusable_patches_give_no_lines(patch):
    assert changed_lines(patch) == set()


@pytest.mark.parametrize("path, language", [
    ("src/app.py", "python"), ("web/App.JSX", "javascript"), ("lib/x.mjs", "javascript"),
    ("src/a.ts", "typescript"), ("src/b.tsx", "typescript"), ("Main.java", "java"),
    ("c/x.c", "c"), ("c/x.h", "c"), ("cpp/x.cc", "cpp"), ("cpp/x.hpp", "cpp"),
    ("README.md", None), ("Makefile", None), ("data.json", None),
])
def test_language_comes_from_the_file_extension(path, language):
    assert language_for_path(path) == language


def file(path="src/app.py", status="modified", patch="@@ -1 +1 @@\n-a\n+b", additions=1, deletions=1):
    return {"path": path, "status": status, "patch": patch, "additions": additions, "deletions": deletions}


@pytest.mark.parametrize("changed, reason", [
    (file(), None),
    (file(status="added"), None),
    (file(status="renamed"), None),
    (file(status="removed"), "removed"),
    (file(path="package-lock.json"), "generated"),
    (file(path="frontend/yarn.lock"), "generated"),
    (file(path="poetry.lock"), "generated"),
    (file(path="static/app.min.js"), "generated"),
    (file(path="dist/bundle.js"), "generated"),
    (file(path="web/build/main.js"), "generated"),
    (file(path="vendor/lib/x.py"), "generated"),
    (file(path="node_modules/a/index.js"), "generated"),
    (file(path="proto/msg_pb2.py"), "generated"),
    (file(path="logo.png", patch=None, additions=0, deletions=0), "binary"),
    (file(patch=None, additions=4000, deletions=0), "too_large"),
    (file(path="docs/guide.md"), "unsupported"),
    (file(path="config.yaml"), "unsupported"),
])
def test_skip_reasons(changed, reason):
    assert skip_reason(changed) == reason


def issue(line, severity="medium", title="t"):
    return {"title": title, "severity": severity, "line_number": line, "category": "logic", "explanation": "e"}


def test_findings_on_or_next_to_changed_lines_are_kept_inside_the_diff():
    kept = focus_findings([issue(10), issue(11), issue(9)], {10})
    assert [(item["line_number"], item["outside_diff"]) for item in kept] == [(10, False), (11, False), (9, False)]


def test_relevant_findings_outside_the_diff_are_kept_but_labeled_and_capped():
    issues = [issue(50, "low"), issue(60, "high", "a"), issue(None, "medium", "b"),
              issue(70, "medium", "c"), issue(3)]
    kept = focus_findings(issues, {3})
    assert [(item["title"], item["outside_diff"]) for item in kept] == [
        ("t", False), ("a", True), ("b", True)]
    assert sum(item["outside_diff"] for item in kept) == MAX_OUTSIDE_DIFF_PER_FILE


def test_outside_findings_prefer_higher_severity_when_capped():
    kept = focus_findings([issue(40, "medium", "m1"), issue(41, "medium", "m2"), issue(42, "high", "h")], {1})
    assert [item["title"] for item in kept] == ["h", "m1"]


def test_without_changed_lines_everything_is_outside_the_diff():
    kept = focus_findings([issue(1, "high"), issue(2, "low")], set())
    assert [(item["line_number"], item["outside_diff"]) for item in kept] == [(1, True)]


def test_focus_does_not_mutate_the_input():
    original = issue(5)
    focus_findings([original], {5})
    assert "outside_diff" not in original
