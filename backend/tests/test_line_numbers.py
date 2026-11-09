"""Stage 11 line-number accuracy: pull request files are sent with explicit line
numbers, and impossible line references are dropped. Manual reviews are unchanged."""
import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest

from app.services.ai_review_service import (
    PULL_REQUEST_PROMPT_ADDENDUM, _instructions, build_review_payload, number_lines,
)
from app.services.diff_service import focus_findings, line_count

CODE = "import sqlite3\n\nfrom app.models import User\n"


def test_lines_are_numbered_like_github_counts_them():
    assert number_lines(CODE) == "1 | import sqlite3\n2 | \n3 | from app.models import User"
    assert number_lines("a\r\nb") == "1 | a\n2 | b"
    assert number_lines("") == "1 | "


def test_line_numbers_are_right_aligned_for_long_files():
    numbered = number_lines("x\n" * 12).split("\n")
    assert numbered[0] == " 1 | x" and numbered[11] == "12 | x" and len(numbered) == 12


@pytest.mark.parametrize("code, count", [(CODE, 3), ("a", 1), ("a\n", 1), ("a\r\nb\r\n", 2), ("", 1), ("a\n\n", 2)])
def test_line_count_matches_the_numbering(code, count):
    assert line_count(code) == count == len(number_lines(code).split("\n"))


def test_pull_request_payload_sends_numbered_code():
    payload = json.loads(build_review_payload(CODE, "python", file_path="app/users.py", changed_lines=[3]))
    assert payload["submitted_code"] == number_lines(CODE)
    assert payload["changed_lines"] == [3]
    assert "starts with its line number" in PULL_REQUEST_PROMPT_ADDENDUM
    assert "Do not copy the line-number prefixes" in PULL_REQUEST_PROMPT_ADDENDUM


def test_manual_payload_and_prompt_are_unchanged():
    payload = json.loads(build_review_payload(CODE, "python"))
    assert payload == {"language": "python", "file_path": None, "submitted_code": CODE, "related_files": []}
    assert PULL_REQUEST_PROMPT_ADDENDUM not in _instructions(None)


def test_numbered_code_still_respects_the_prompt_limit():
    with pytest.raises(ValueError, match="prompt limit"):
        build_review_payload("x\n" * 120_000, "python", changed_lines=[1])


def issue(line, severity="high"):
    return {"title": "t", "severity": severity, "line_number": line, "category": "logic", "explanation": "e"}


def test_line_references_past_the_end_of_the_file_are_dropped():
    kept = focus_findings([issue(99), issue(0), issue(3)], {3}, line_count=5)
    assert [(item["line_number"], item["outside_diff"]) for item in kept] == [(3, False), (None, True), (None, True)]


def test_an_impossible_line_cannot_land_inside_the_diff():
    # Line 6 would be "next to" changed line 5, but the file only has 5 lines.
    kept = focus_findings([issue(6, "low")], {5}, line_count=5)
    assert kept == []


def test_without_a_line_count_lines_are_not_range_checked():
    assert focus_findings([issue(99)], {99})[0]["line_number"] == 99
