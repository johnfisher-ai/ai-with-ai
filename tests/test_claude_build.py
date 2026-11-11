"""Tests for scripts/claude_build.py and scripts/check_builds.py, the Claude Code builds the chapters quote.

    python3 -m pytest tests/

No test runs Claude Code or reaches the network. A fake `claude` command stands in for it: it writes one
module, prints events in the shape `claude -p --output-format stream-json --verbose` prints them, with the
session, message, request and tool-use IDs and folder paths the real events carry, and records the
environment and arguments it was given. The keys are strings written for the tests.
"""
import hashlib
import json
import os
import pathlib
import stat
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import check_builds  # noqa: E402
import claude_build  # noqa: E402

BOOK_KEY = "aiwai-test-key-not-real"
READER_KEY = "reader-test-key-not-real"
MODEL = "claude-sonnet-5-5"

FAKE = r'''#!{python}
import json, os, pathlib, sys, uuid
DUMP = {dump!r}
prompt = sys.stdin.read()
pathlib.Path(DUMP).write_text(json.dumps({{"argv": sys.argv[1:], "env": dict(os.environ), "prompt": prompt}}))
cwd = os.getcwd()
pathlib.Path("triage.py").write_text("def normalize_label(s):\n    return s.strip().lower()\n")
if {tamper}:
    pathlib.Path("tests/test_triage.py").write_text("def test_nothing():\n    pass\n")
sid = str(uuid.uuid4())
events = [
    {{"type": "system", "subtype": "init", "session_id": sid, "uuid": str(uuid.uuid4()), "cwd": cwd,
      "claude_code_version": "9.9.9-test", "model": {model!r}, "permissionMode": "acceptEdits",
      "tools": ["Read", "Write", "Bash"], "apiKeySource": "ANTHROPIC_API_KEY"}},
    {{"type": "assistant", "session_id": sid, "uuid": str(uuid.uuid4()), "request_id": "req_fixture_1",
      "message": {{"id": "msg_fixture_1", "content": [
        {{"type": "thinking", "thinking": "Fixture thinking.", "signature": "Zm9v"}},
        {{"type": "tool_use", "id": "toolu_fixture_1", "name": "Write",
          "input": {{"file_path": cwd + "/triage.py", "content": "def normalize_label(s): ..."}}}}]}}}},
    {{"type": "user", "session_id": sid, "uuid": str(uuid.uuid4()), "message": {{"content": [
        {{"type": "tool_result", "tool_use_id": "toolu_fixture_1",
          "content": "File created successfully at: " + cwd + "/triage.py"
                     + (" " + os.environ.get("ANTHROPIC_API_KEY", "") if {leak} else "")}}]}}}},
    {{"type": "assistant", "session_id": sid, "uuid": str(uuid.uuid4()), "request_id": "req_fixture_2",
      "message": {{"id": "msg_fixture_2", "content": [{{"type": "text", "text": "Fixture reply: done."}}]}}}},
    {{"type": "result", "subtype": "success", "is_error": False, "num_turns": 2, "total_cost_usd": 0.0123,
      "duration_ms": 900, "session_id": sid, "uuid": str(uuid.uuid4()), "result": "Fixture reply: done.",
      "usage": {{"input_tokens": 10, "output_tokens": 20, "cache_read_input_tokens": 30,
                "cache_creation_input_tokens": 40}}}},
]
for e in events:
    print(json.dumps(e))
'''


@pytest.fixture
def book(tmp_path, monkeypatch):
    """A builds/ folder with one build, a fake claude on PATH, and both keys in the environment."""
    builds = tmp_path / "builds"
    folder = builds / "a-test-build"
    (folder / "given" / "tests").mkdir(parents=True)
    (folder / "given" / "spec.md").write_text("Write triage.py with normalize_label(s), trimmed and lowercased.\n")
    (folder / "given" / "tests" / "test_triage.py").write_text(
        "from triage import normalize_label\n\ndef test_trims_and_lowers():\n"
        "    assert normalize_label('  Billing ') == 'billing'\n")
    (folder / "prompt.md").write_text("Read spec.md and make the tests in tests/ pass.\n")
    (folder / "build.json").write_text(json.dumps({
        "format": 1, "model": MODEL, "allowed_commands": ["python3 -m pytest *"],
        "test_command": ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        "max_budget_usd": 1.0}))
    monkeypatch.setattr(claude_build, "BUILDS", builds)
    monkeypatch.setattr(check_builds, "BUILDS", builds)
    monkeypatch.setenv("AIWAI_RECORDING_KEY", BOOK_KEY)
    monkeypatch.setenv("ANTHROPIC_API_KEY", READER_KEY)
    monkeypatch.setenv("SOMETHING_PRIVATE", "should-not-reach-the-build")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    dump = tmp_path / "seen.json"

    def install(tamper=False, leak=False):
        fake = bindir / "claude"
        fake.write_text(FAKE.format(python=sys.executable, dump=str(dump), tamper=tamper, leak=leak, model=MODEL))
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)

    install()
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    return {"folder": folder, "seen": lambda: json.loads(dump.read_text()), "install": install, "tmp": tmp_path}


def test_record_mode_hands_the_book_key_to_claude_only(book, monkeypatch):
    monkeypatch.setenv("BOOK_MODE", "record")
    assert claude_build.main(["a-test-build"]) == 0
    seen = book["seen"]()
    env, argv = seen["env"], seen["argv"]
    assert env["ANTHROPIC_API_KEY"] == BOOK_KEY
    assert env["ANTHROPIC_BASE_URL"] == "https://api.anthropic.com"
    assert "AIWAI_RECORDING_KEY" not in env and "SOMETHING_PRIVATE" not in env
    assert env["HOME"] != os.environ["HOME"]
    # LC_CTYPE is set by Python's own locale coercion inside the fake, not passed by the builder.
    assert set(env) - {"LC_CTYPE"} <= set(claude_build.PASS_THROUGH) | {"PATH", "HOME", "DISABLE_AUTOUPDATER",
                                                        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
                                                        "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"}
    assert "--bare" in argv and argv[argv.index("--model") + 1] == MODEL
    assert seen["prompt"] == "Read spec.md and make the tests in tests/ pass.\n"


def test_a_recorded_build_passes_the_check(book, monkeypatch):
    monkeypatch.setenv("BOOK_MODE", "record")
    claude_build.main(["a-test-build"])
    folder = book["folder"]
    assert check_builds.check(folder) == []
    record = json.loads((folder / "transcript.json").read_text())
    assert record["claude_code_version"] == "9.9.9-test" and record["model"] == MODEL
    assert record["result"]["cost_usd"] == 0.0123 and record["tests"]["passed"] is True
    assert list(record["generated"]) == ["triage.py"]
    assert (folder / "generated" / "triage.py").read_text().startswith("def normalize_label")
    tool = [s for s in record["steps"] if s.get("tool")][0]
    assert tool["id"] == "t1" and tool["input"]["file_path"] == "./triage.py"
    assert [s for s in record["steps"] if s["role"] == "tool"][0]["result"].endswith("at: ./triage.py")
    text = "".join(p.read_text() for p in folder.rglob("*") if p.is_file())
    for leftover in ("req_", "msg_", "toolu_", "session_id", "signature", str(book["tmp"]), BOOK_KEY):
        assert leftover not in text


def test_reader_mode_never_reads_the_book_key(book, monkeypatch):
    monkeypatch.delenv("BOOK_MODE", raising=False)
    out = book["tmp"] / "my-run"
    assert claude_build.main(["a-test-build", "--out", str(out)]) == 0
    env, argv = book["seen"]()["env"], book["seen"]()["argv"]
    assert env["ANTHROPIC_API_KEY"] == READER_KEY
    assert "AIWAI_RECORDING_KEY" not in env and "ANTHROPIC_BASE_URL" not in env
    assert "--bare" not in argv
    assert (out / "generated" / "triage.py").exists()
    assert not (book["folder"] / "transcript.json").exists()


def test_record_mode_needs_the_book_key(book, monkeypatch):
    monkeypatch.setenv("BOOK_MODE", "record")
    monkeypatch.delenv("AIWAI_RECORDING_KEY")
    with pytest.raises(SystemExit, match="AIWAI_RECORDING_KEY"):
        claude_build.main(["a-test-build"])


def test_a_key_in_the_output_stops_the_build_before_anything_is_written(book, monkeypatch):
    monkeypatch.setenv("BOOK_MODE", "record")
    book["install"](leak=True)
    with pytest.raises(SystemExit, match="key appeared"):
        claude_build.main(["a-test-build"])
    assert not (book["folder"] / "transcript.json").exists()


def test_changed_tests_fail_the_build_and_the_check(book, monkeypatch):
    monkeypatch.setenv("BOOK_MODE", "record")
    book["install"](tamper=True)
    assert claude_build.main(["a-test-build"]) == 1
    problems = check_builds.check(book["folder"])
    assert any("changed the given tests" in p for p in problems)


def test_the_check_finds_planted_problems(book, monkeypatch):
    monkeypatch.setenv("BOOK_MODE", "record")
    claude_build.main(["a-test-build"])
    folder = book["folder"]
    (folder / "generated" / "triage.py").write_text("# edited by hand\n")
    record = json.loads((folder / "transcript.json").read_text())
    record["steps"][0]["session_id"] = "x"
    (folder / "transcript.json").write_text(json.dumps(record))
    (folder / "test-run.txt").write_text("rootdir: /root/build\n")
    problems = "\n".join(check_builds.check(folder))
    assert "differs from the file Claude Code wrote" in problems
    assert "step 1 has fields ['session_id']" in problems
    assert "test-run.txt: holds a machine path" in problems


def test_the_check_passes_with_no_builds(tmp_path, monkeypatch):
    monkeypatch.setattr(check_builds, "BUILDS", tmp_path / "builds")
    assert check_builds.main() == 0


def test_generated_hashes_match_the_files(book, monkeypatch):
    monkeypatch.setenv("BOOK_MODE", "record")
    claude_build.main(["a-test-build"])
    record = json.loads((book["folder"] / "transcript.json").read_text())
    data = (book["folder"] / "generated" / "triage.py").read_bytes()
    assert record["generated"]["triage.py"] == hashlib.sha256(data).hexdigest()
