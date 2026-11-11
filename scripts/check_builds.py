#!/usr/bin/env python3
"""Check every Claude Code build the chapters quote, in builds/<slug>/.

    python3 scripts/check_builds.py

A build is what a chapter's "Build it with Claude Code" section quotes, so, like a recording, it has to say
where it came from and carry nothing it shouldn't. For each folder it checks that:

  - build.json, prompt.md and given/ are there, and build.json is a format-1 build
  - transcript.json is a format-1 record of a run in record mode, for this slug, naming the Claude Code
    version, the model build.json asked for, the date and the cost
  - the run ended without an error, the tests passed, and Claude Code left the given tests unchanged
  - generated/ holds exactly the files the transcript lists, with the same contents
  - each step keeps only the fields scripts/claude_build.py writes, so no ID or account field slips in
  - no file names a machine path, holds a key, or carries a request, message, session or tool-use ID

It needs only the standard library. Exits 1 if anything is wrong, and passes when there are no builds yet.
"""
import datetime
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILDS = ROOT / "builds"
CONFIG_FIELDS = {"format", "model", "allowed_commands", "test_command", "max_budget_usd", "timeout_s"}
RECORD_FIELDS = {"format", "slug", "mode", "date", "claude_code_version", "model", "permission_mode", "tools",
                 "command", "exit_code", "result", "generated", "tests", "steps"}
STEP_FIELDS = {"role", "text", "thinking", "tool", "id", "input", "is_error", "result", "denied"}
FORBIDDEN = {
    "machine path": re.compile(r"/(?:home|Users|root|tmp)/"),
    "Anthropic key": re.compile(r"sk-ant-"),
    "request ID": re.compile(r"\breq_[A-Za-z0-9]{8,}"),
    "message ID": re.compile(r"\bmsg_[A-Za-z0-9]{8,}"),
    "tool-use ID": re.compile(r"\btoolu_[A-Za-z0-9]{8,}"),
    "session or event ID": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
}


def _cache(path):
    """Python's bytecode caches, which importing a generated module leaves behind. Git ignores them."""
    return "__pycache__" in path.parts or path.suffix == ".pyc" or ".pytest_cache" in path.parts


def check(folder):
    problems = []
    try:
        config = json.loads((folder / "build.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"build.json: {e}"]
    if config.get("format") != 1 or set(config) - CONFIG_FIELDS:
        problems.append(f"build.json: format must be 1, unknown fields {sorted(set(config) - CONFIG_FIELDS)}")
    if not (folder / "prompt.md").is_file() or not (folder / "prompt.md").read_text(encoding="utf-8").strip():
        problems.append("no prompt.md")
    if not (folder / "given").is_dir():
        problems.append("no given/ folder")
    try:
        record = json.loads((folder / "transcript.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return problems + [f"transcript.json: {e} (has the build been run?)"]
    if set(record) != RECORD_FIELDS:
        problems.append(f"transcript.json: fields {sorted(set(record) ^ RECORD_FIELDS)} differ from the format")
    if record.get("format") != 1 or record.get("slug") != folder.name or record.get("mode") != "record":
        problems.append("transcript.json: not a format-1 record-mode run of this slug")
    try:
        datetime.date.fromisoformat(record.get("date", ""))
    except (TypeError, ValueError):
        problems.append(f"transcript.json: date {record.get('date')!r} is not YYYY-MM-DD")
    if not record.get("claude_code_version"):
        problems.append("transcript.json: no Claude Code version")
    if record.get("model") != config.get("model"):
        problems.append(f"transcript.json: model {record.get('model')!r}, build.json asked for {config.get('model')!r}")
    result = record.get("result") or {}
    if not isinstance(result.get("cost_usd"), (int, float)):
        problems.append("transcript.json: no cost")
    if record.get("exit_code") != 0 or result.get("is_error"):
        problems.append("transcript.json: the run ended with an error")
    tests = record.get("tests") or {}
    if tests.get("passed") is not True:
        problems.append("transcript.json: the tests did not pass")
    if tests.get("changed_by_claude"):
        problems.append(f"transcript.json: Claude Code changed the given tests {tests['changed_by_claude']}")
    for i, step in enumerate(record.get("steps") or [], 1):
        if not isinstance(step, dict) or set(step) - STEP_FIELDS:
            problems.append(f"transcript.json: step {i} has fields {sorted(set(step) - STEP_FIELDS)}")
    if not (folder / "test-run.txt").is_file():
        problems.append("no test-run.txt")
    generated = folder / "generated"
    listed = record.get("generated") or {}
    present = {str(p.relative_to(generated)) for p in generated.rglob("*")
               if p.is_file() and not _cache(p)} if generated.is_dir() else set()
    for name in sorted(present ^ set(listed)):
        problems.append(f"generated/{name}: {'not listed in the transcript' if name in present else 'missing'}")
    for name in sorted(present & set(listed)):
        if hashlib.sha256((generated / name).read_bytes()).hexdigest() != listed[name]:
            problems.append(f"generated/{name}: differs from the file Claude Code wrote")
    for p in sorted(folder.rglob("*")):
        if p.is_file() and not _cache(p):
            text = p.read_text(encoding="utf-8", errors="replace")
            for what, pattern in FORBIDDEN.items():
                if pattern.search(text):
                    problems.append(f"{p.relative_to(folder)}: holds a {what}")
    return problems


def main():
    folders = sorted(p for p in BUILDS.iterdir() if p.is_dir()) if BUILDS.is_dir() else []
    bad = 0
    for folder in folders:
        for problem in check(folder):
            bad += 1
            print(f"  builds/{folder.name}: {problem}")
    print(f"builds: {len(folders)} build(s), {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
