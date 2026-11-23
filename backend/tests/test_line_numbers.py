"""Line-number accuracy: code is sent with explicit line numbers (pull request
files since Stage 11, manual reviews since Stage 14), and impossible line
references are dropped."""
import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest

from app.services import ai_review_service
from app.services.ai_review_service import (
    NUMBERED_CODE_PROMPT_ADDENDUM, PULL_REQUEST_PROMPT_ADDENDUM, _instructions, _review_prompt,
    build_review_payload, number_lines,
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


def test_manual_reviews_are_sent_numbered_too():
    """Stage 14 evaluation: unnumbered manual code made the model's lines 1-4 off."""
    payload = json.loads(build_review_payload(CODE, "python"))
    assert payload == {"language": "python", "file_path": None, "submitted_code": number_lines(CODE),
                       "related_files": []}
    manual = _instructions(None)
    assert NUMBERED_CODE_PROMPT_ADDENDUM in manual and "count lines yourself" in manual
    assert PULL_REQUEST_PROMPT_ADDENDUM not in manual  # no changed_lines guidance


def test_a_manual_submission_too_big_to_number_is_sent_plain_with_matching_instructions():
    # Many short lines: numbering would push it past the prompt limit, but
    # the plain code still fits, so it's sent as before instead of refused.
    code = "total = 1\n" * 20_000  # 200,000 characters, 20,000 lines
    system, payload = _review_prompt(code, "python")
    assert json.loads(payload)["submitted_code"] == code
    assert NUMBERED_CODE_PROMPT_ADDENDUM not in system
    assert build_review_payload(code, "python") == payload


def test_the_claude_call_gets_matching_instructions_and_payload(monkeypatch):
    sent = {}
    monkeypatch.setattr(ai_review_service, "request_claude_text",
                        lambda **kwargs: sent.update(kwargs) or '{"issues": []}')
    ai_review_service._review_with_claude(CODE, "python")
    assert NUMBERED_CODE_PROMPT_ADDENDUM in sent["system"]
    assert json.loads(sent["payload"])["submitted_code"] == number_lines(CODE)


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
