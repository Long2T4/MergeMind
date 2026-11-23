"""Stage 14: measure what MergeMind catches and misses on code with known problems.

Run from backend/:

    python -m evaluation.run_evaluation                      # Semgrep + Bandit only; no AI calls
    python -m evaluation.run_evaluation --ai-findings F.json # also score saved AI findings (no calls)
    python -m evaluation.run_evaluation --ai --allow-ai-spending --record-ai F.json
                                                             # real AI: one Anthropic call per case file

It uses MergeMind's own pipeline (collect_security_findings, merge_findings,
calculate_confidence), so the numbers describe what a user would see. The
dataset is evaluation/cases/ with the known problems in evaluation/expected.json.
See docs/evaluation.md for the method and published results.
"""
import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.services.analysis_service import analysis_status, collect_security_findings, merge_findings
from app.services.bandit_service import _default_executable as bandit_executable
from app.services.confidence_service import calculate_confidence
from app.services.finding_kinds import kind_from_text

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases"
MANIFEST = HERE / "expected.json"
LINE_TOLERANCE = 1
SOURCES = ("ai", "semgrep", "bandit")


# --- Dataset ------------------------------------------------------------------

def load_manifest(manifest_path=MANIFEST, cases_dir=CASES):
    """The expected problems, each with its line found from its snippet."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    expected = []
    for item in manifest["expected"]:
        lines = (Path(cases_dir) / item["file"]).read_text(encoding="utf-8").splitlines()
        matches = [number for number, text in enumerate(lines, start=1) if item["contains"] in text]
        if len(matches) != 1:
            raise ValueError(f"{item['id']}: snippet {item['contains']!r} found {len(matches)} times in {item['file']}")
        expected.append({**item, "line": matches[0]})
    return expected, manifest["clean_files"]


def case_files(cases_dir=CASES):
    return sorted(path.name for path in Path(cases_dir).glob("*.py"))


# --- Scoring ------------------------------------------------------------------

def finding_kind(finding):
    return finding.get("kind") or kind_from_text(finding.get("title"), finding.get("explanation"))


def matches(finding, expected):
    """Same problem: same file, within one line, and not identified as a
    different problem. If both have a vulnerability kind, the kinds must be
    equal; if the finding has a kind and the problem doesn't (or the other way
    round), they don't match; otherwise the finding matches. Scanner findings
    without a kind (e.g. Bandit's try/except/pass) can match logic and
    error-handling problems, because scanners label everything "security"."""
    line = finding.get("line_number")
    if finding.get("file") != expected["file"] or not isinstance(line, int):
        return False
    if abs(line - expected["line"]) > LINE_TOLERANCE:
        return False
    kind = finding_kind(finding)
    if expected["kind"] or kind:
        return kind == expected["kind"]
    return True


def score(expected, findings, clean_files):
    """Score merged findings (each with `file` and `evidence`) against the
    expected problems. Each finding counts for at most one problem."""
    # Each finding goes to the nearest problem it matches (ties: the first).
    assigned = {}
    for index, finding in enumerate(findings):
        candidates = [item for item in expected if matches(finding, item)]
        if candidates:
            nearest = min(candidates, key=lambda item: abs(item["line"] - finding["line_number"]))
            assigned[index] = nearest["id"]
    used = set(assigned)
    rows = []
    for item in expected:
        hits = [index for index, problem in assigned.items() if problem == item["id"]]
        sources = sorted({source for index in hits for source in findings[index]["evidence"]})
        levels = [calculate_confidence(findings[index]["evidence"])["confidence_level"] for index in hits]
        rows.append({**item, "caught": bool(hits), "sources": sources, "cards": len(hits),
                     "confidence": max(levels, key=["low", "medium", "high"].index) if levels else None})

    false_positives = [f for f in findings if f["file"] in clean_files]
    unlabeled = [f for index, f in enumerate(findings) if index not in used and f["file"] not in clean_files]

    def recall(rows_subset, source=None):
        caught = [r for r in rows_subset if r["caught"] and (source is None or source in r["sources"])]
        return {"caught": len(caught), "total": len(rows_subset)}

    rule_covered = [r for r in rows if r["kind"]]
    other = [r for r in rows if not r["kind"]]
    summary = {
        "expected": len(rows),
        "combined": recall(rows),
        "by_source": {source: recall(rows, source) for source in SOURCES},
        "rule_covered": {"combined": recall(rule_covered), **{s: recall(rule_covered, s) for s in SOURCES}},
        "other_problems": {"combined": recall(other), **{s: recall(other, s) for s in SOURCES}},
        "duplicate_cards": sum(max(r["cards"] - 1, 0) for r in rows),
        "false_positives": {source: sum(source in f["evidence"] for f in false_positives) for source in SOURCES},
        "false_positive_findings": len(false_positives),
        "unlabeled_findings": len(unlabeled),
    }
    return {"summary": summary, "expected": rows,
            "false_positives": [_brief(f) for f in false_positives],
            "unlabeled": [_brief(f) for f in unlabeled]}


def _brief(finding):
    return {"file": finding["file"], "line": finding.get("line_number"), "title": finding.get("title"),
            "sources": sorted(finding["evidence"])}


# --- Running MergeMind ----------------------------------------------------------

def run(ai_mode="off", ai_findings_path=None, record_ai_path=None, cases_dir=CASES):
    """Run MergeMind on every case file; return merged findings and statuses."""
    saved_ai = json.loads(Path(ai_findings_path).read_text(encoding="utf-8")) if ai_findings_path else {}
    recorded_ai = {}
    findings, statuses = [], {}
    for name in case_files(cases_dir):
        code = (Path(cases_dir) / name).read_text(encoding="utf-8")
        if ai_mode == "live":
            from app.services.ai_review_service import review_code  # only imported when spending is allowed
            ai = review_code(code, "python")
            recorded_ai[name] = ai
        else:
            ai = saved_ai.get(name, [])
        scanners = collect_security_findings(code, "python")
        statuses[name] = analysis_status(scanners)
        for finding in merge_findings(ai, scanners["semgrep"], scanners["bandit"]):
            findings.append({**finding, "file": name})
    if record_ai_path and recorded_ai:
        Path(record_ai_path).write_text(json.dumps(recorded_ai, indent=2) + "\n", encoding="utf-8")
    return findings, statuses


def _version(command):
    try:
        output = subprocess.run(command, capture_output=True, text=True, timeout=60).stdout.strip()
        return output.splitlines()[0] if output else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "not installed"


def environment(ai_mode):
    import os
    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "python": platform.python_version(),
        "platform": platform.system(),
        "semgrep": _version([os.getenv("SEMGREP_EXECUTABLE", "semgrep"), "--version"]),
        "bandit": _version([bandit_executable(), "--version"]),
        "ai": {"off": "not run", "replay": "saved findings", "live": "live Anthropic calls"}[ai_mode],
    }


# --- Report -------------------------------------------------------------------

def _pct(part):
    return f"{part['caught']}/{part['total']}" + (f" ({100 * part['caught'] // part['total']}%)" if part["total"] else "")


def markdown(result, env, statuses):
    s = result["summary"]
    ai_ran = env["ai"] != "not run"
    lines = [
        f"## Results ({env['date']})", "",
        f"Semgrep: `{env['semgrep']}`, Bandit: `{env['bandit']}`, AI: {env['ai']}, "
        f"Python {env['python']} on {env['platform']}", "",
        "| Measure | Result |", "|---|---|",
        f"| Known problems caught, all sources | {_pct(s['combined'])} |",
        f"| Caught by Semgrep | {_pct(s['by_source']['semgrep'])} |",
        f"| Caught by Bandit | {_pct(s['by_source']['bandit'])} |",
        f"| Caught by the AI | {_pct(s['by_source']['ai']) if ai_ran else 'not run'} |",
        f"| Problems with a scanner rule (kind set) | {_pct(s['rule_covered']['combined'])} |",
        f"| Other problems (SSRF, path traversal, logic, errors) | {_pct(s['other_problems']['combined'])} |",
        f"| Duplicate cards for one problem | {s['duplicate_cards']} |",
        f"| False positives on clean files | {s['false_positive_findings']} |",
        f"| Findings not matching a labeled problem | {s['unlabeled_findings']} |",
        "", "| ID | Problem | Location | Caught by | Confidence |", "|---|---|---|---|---|",
    ]
    for row in result["expected"]:
        caught = ", ".join(row["sources"]) if row["caught"] else "**missed**"
        lines.append(f"| {row['id']} | {row['problem']} | `{row['file']}:{row['line']}` | {caught} | "
                     f"{row['confidence'] or '-'} |")
    for title, items in (("False positives", result["false_positives"]), ("Unlabeled findings", result["unlabeled"])):
        if items:
            lines += ["", f"**{title}:**", ""]
            lines += [f"- `{i['file']}:{i['line']}` {i['title']} ({', '.join(i['sources'])})" for i in items]
    failed = sorted({f"{name}: {tool} {status}" for name, status_by_tool in statuses.items()
                     for tool, status in status_by_tool.items() if status != "completed"})
    if failed:
        lines += ["", "**Scanners that didn't complete:** " + "; ".join(failed)]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ai", action="store_true", help="also run the real AI review (costs money)")
    parser.add_argument("--allow-ai-spending", action="store_true", help="required with --ai")
    parser.add_argument("--ai-findings", help="score AI findings saved earlier with --record-ai (no AI calls)")
    parser.add_argument("--record-ai", help="with --ai: save the AI findings to this JSON file")
    parser.add_argument("--json", help="write the full result as JSON to this file")
    parser.add_argument("--markdown", help="write the report as Markdown to this file")
    args = parser.parse_args(argv)

    if args.ai and not args.allow_ai_spending:
        parser.error(f"--ai makes {len(case_files())} Anthropic calls; add --allow-ai-spending to confirm")
    ai_mode = "live" if args.ai else "replay" if args.ai_findings else "off"

    expected, clean_files = load_manifest()
    findings, statuses = run(ai_mode, args.ai_findings, args.record_ai)
    result = score(expected, findings, clean_files)
    env = environment(ai_mode)
    report = markdown(result, env, statuses)
    if args.json:
        Path(args.json).write_text(json.dumps({"environment": env, "scanner_status": statuses, **result},
                                              indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        Path(args.markdown).write_text(report, encoding="utf-8")
    sys.stdout.write(report)


if __name__ == "__main__":
    main()
