"""Stage 13: the kinds of vulnerability MergeMind can match across sources.

Semgrep, Bandit and the AI describe the same problem differently (different
titles, severities and even CWE numbers), so findings are matched by *kind*
instead. Each kind has a readable title and a suggested fix used for scanner
findings, the Bandit tests that report it, and words that identify it in an
AI finding. Semgrep rules carry their kind in `metadata.mergemind_kind`
(see app/analysis_rules/semgrep-python.yml).
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Kind:
    title: str
    fix: str
    bandit_tests: frozenset[str]
    ai_patterns: tuple[str, ...]


KINDS: dict[str, Kind] = {
    "hardcoded-secret": Kind(
        title="Hard-coded password or secret",
        fix="Read the value from an environment variable or a secrets manager instead of writing it in the code.",
        bandit_tests=frozenset({"B105", "B106", "B107"}),
        ai_patterns=(r"hard[- ]?coded", r"password", r"secret", r"credential", r"api[ _-]?key"),
    ),
    "code-eval": Kind(
        title="Code execution with eval() or exec()",
        fix="Don't run text as code. Use ast.literal_eval() for literal values, or parse the input explicitly.",
        bandit_tests=frozenset({"B102", "B307"}),
        ai_patterns=(r"\beval\b", r"\bexec\b"),
    ),
    "shell-injection": Kind(
        title="Command run through a shell",
        fix="Pass the command as a list to subprocess.run() without shell=True, and never build it from user input.",
        bandit_tests=frozenset({"B602", "B604", "B605", "B609"}),
        ai_patterns=(r"shell", r"command injection", r"os\.system", r"os\.popen"),
    ),
    "deserialization": Kind(
        title="Unsafe deserialization",
        fix="Only load data you created yourself, or use a safe format such as JSON or yaml.safe_load().",
        bandit_tests=frozenset({"B301", "B302", "B506"}),
        ai_patterns=(r"pickle", r"deserializ", r"marshal", r"yaml\.load", r"unsafe yaml"),
    ),
    "weak-hash": Kind(
        title="Weak hash (MD5 or SHA-1)",
        fix="Use hashlib.sha256() or stronger. For passwords, use a password hash such as bcrypt or argon2.",
        bandit_tests=frozenset({"B303", "B324"}),
        ai_patterns=(r"\bmd5\b", r"\bsha-?1\b", r"weak hash"),
    ),
    "sql-injection": Kind(
        title="SQL query built from strings",
        fix="Pass values as query parameters, e.g. cursor.execute(\"... WHERE id = %s\", (value,)).",
        bandit_tests=frozenset({"B608"}),
        ai_patterns=(r"\bsql\b",),
    ),
    "tls-disabled": Kind(
        title="Certificate checks turned off",
        fix="Remove verify=False so HTTPS certificates are checked.",
        bandit_tests=frozenset({"B501"}),
        ai_patterns=(r"verify\s*=\s*false", r"certificate", r"\btls\b", r"\bssl\b"),
    ),
}

_BANDIT_KIND = {test: name for name, kind in KINDS.items() for test in kind.bandit_tests}


def kind_for_bandit_test(test_id: str | None) -> str | None:
    return _BANDIT_KIND.get(test_id or "")


def _kinds_in(text: str) -> set[str]:
    text = text.lower()
    return {name for name, kind in KINDS.items() if any(re.search(p, text) for p in kind.ai_patterns)}


def kind_from_text(title: str | None, explanation: str | None = None) -> str | None:
    """The kind an AI-written finding describes, or None if unclear.

    The title decides when it names exactly one kind. Otherwise the
    explanation is used, again only if it names exactly one kind. Vague or
    ambiguous wording returns None, and such findings are never merged.
    """
    for text in (title, explanation):
        kinds = _kinds_in(text or "")
        if len(kinds) == 1:
            return kinds.pop()
        if kinds:  # several kinds named: don't guess
            return None
    return None
