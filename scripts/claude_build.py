#!/usr/bin/env python3
"""Run a chapter's Claude Code build headless, and keep what it did under builds/<slug>/.

    BOOK_MODE=record python3 scripts/claude_build.py <slug>     # the book's own build, on the book's key
    python3 scripts/claude_build.py <slug> --out my-build        # a reader's run, with their own Claude Code

A build is the chapter's "Build it with Claude Code" section, run for real. The author writes, under
builds/<slug>/:

    build.json    what to run: the model, the commands Claude Code may run, the test command and a budget
    prompt.md     the prompt Claude Code is given, word for word
    given/        the files Claude Code starts from, usually spec.md and tests/

The script copies given/ into a new, empty folder, runs `claude -p` there with prompt.md on stdin, then runs
the test command on what Claude Code left. It writes:

    generated/       every file Claude Code created or changed, outside given/'s tests
    transcript.json  each step Claude Code took, with its version, model, date, cost and the test result
    test-run.txt     the test command's output

The transcript keeps the text, the tool calls and their results. It drops session, message, request and
event IDs, and replaces the build folder's path with ".", so nothing in it names a machine or an account.
scripts/check_builds.py checks all of this.

Keys. In record mode the book's key, AIWAI_RECORDING_KEY, goes to the one `claude` process as its
ANTHROPIC_API_KEY, with --bare so it reads no other credential, settings or instruction file, and with the
API's own address so no proxy setting can redirect it. It is never exported, written or printed. In a
reader's run, Claude Code uses the reader's own login or key as it normally would, and AIWAI_RECORDING_KEY is
never read. In both modes the process gets a short list of environment variables, a home folder of its own,
and no other key. Needs only the standard library and the `claude` command.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILDS = ROOT / "builds"
API = "https://api.anthropic.com"
# Proxy and certificate settings a process needs to reach the network from a managed machine. Nothing else
# from the caller's environment reaches the build.
PASS_THROUGH = ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "NO_PROXY", "no_proxy",
                "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "LANG", "LC_ALL", "TERM"]
CONFIG_FIELDS = {"format", "model", "allowed_commands", "test_command", "max_budget_usd", "timeout_s"}
# --bare runs Claude Code's simple mode, which offers only these three tools (Claude Code 2.1.322, November
# 2026). A reader's run uses the same three, so both runs see the same tools. Edit with an empty old_string
# creates a file.
TOOLS = "Read,Edit,Bash"
# In dontAsk mode Claude Code runs only what is listed here and refuses the rest without asking, apart from
# read-only shell commands such as ls and cat, which it treats as safe. Bash runs only the commands build.json
# names, so a file is written with Edit.
FILE_TOOLS = ["Read", "Edit"]


def load_config(build):
    config = json.loads((build / "build.json").read_text(encoding="utf-8"))
    extra = set(config) - CONFIG_FIELDS
    if config.get("format") != 1 or extra:
        raise SystemExit(f"{build}/build.json: format must be 1, unknown fields {sorted(extra)}")
    for field in ("model", "allowed_commands", "test_command", "max_budget_usd"):
        if field not in config:
            raise SystemExit(f"{build}/build.json: no {field}")
    return config


def child_env(mode, home, python_dir):
    """The environment the claude process and the test command get. Built from nothing."""
    env = {k: os.environ[k] for k in PASS_THROUGH if k in os.environ}
    env["PATH"] = os.pathsep.join([python_dir, os.environ.get("PATH", "")])
    env["HOME"] = str(home)
    env["DISABLE_AUTOUPDATER"] = "1"
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    if mode == "record":
        key = os.environ.get("AIWAI_RECORDING_KEY", "")
        if not key:
            raise SystemExit("record mode needs AIWAI_RECORDING_KEY, the book's key, in the session's environment")
        env["ANTHROPIC_API_KEY"] = key
        env["ANTHROPIC_BASE_URL"] = API
    else:
        # A reader's run uses the reader's own Claude Code login, which lives in their home folder, or the
        # reader's own ANTHROPIC_API_KEY. Never the book's.
        env["HOME"] = os.environ.get("HOME", str(home))
        if os.environ.get("ANTHROPIC_API_KEY"):
            env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
    return env


def claude_command(config, mode):
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose", "--no-session-persistence",
           "--model", config["model"], "--max-budget-usd", str(config["max_budget_usd"]),
           "--permission-mode", "dontAsk", "--tools", TOOLS]
    if mode == "record":
        cmd.insert(2, "--bare")
    # Each pattern is one argument, so a pattern with spaces stays whole. The prompt goes on stdin, because
    # --allowedTools takes every argument after it.
    cmd += ["--allowedTools", *FILE_TOOLS, *[f"Bash({c})" for c in config["allowed_commands"]]]
    return cmd


def file_hashes(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file() and not _skipped(p.relative_to(folder))}


def _skipped(rel):
    return any(part in ("__pycache__", ".pytest_cache") or part.endswith(".pyc") for part in rel.parts)


class Scrubber:
    """Replaces the build folder's and the private home's paths, and refuses any key it is shown."""

    def __init__(self, work, homes, secrets):
        self.pairs = []
        for path, label in [(work, ".")] + [(h, "~") for h in homes]:
            for p in {str(path), os.path.realpath(path)}:
                self.pairs += [(p + "/", label + "/"), (p, label)]
        self.pairs.sort(key=lambda pair: -len(pair[0]))
        self.secrets = [s for s in secrets if s]

    def text(self, s):
        for a, b in self.pairs:
            s = s.replace(a, b)
        for secret in self.secrets:
            if secret in s:
                raise SystemExit("a key appeared in the build's output; nothing was written")
        return s

    def value(self, v):
        if isinstance(v, str):
            return self.text(v)
        if isinstance(v, list):
            return [self.value(x) for x in v]
        if isinstance(v, dict):
            return {k: self.value(x) for k, x in v.items()}
        return v


def result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def transcript(events):
    """Keeps the steps a reader can follow, and drops every ID, timestamp and account field."""
    steps, ids, meta, result = [], {}, {}, {}

    def short(tool_use_id):
        return ids.setdefault(tool_use_id, f"t{len(ids) + 1}")

    for e in events:
        kind, sub = e.get("type"), e.get("subtype")
        if kind == "system" and sub == "init":
            meta = {"claude_code_version": e.get("claude_code_version"), "model": e.get("model"),
                    "permission_mode": e.get("permissionMode"), "tools": e.get("tools")}
        elif kind == "system" and sub == "permission_denied":
            steps.append({"role": "system", "denied": e.get("tool_name"), "id": short(e.get("tool_use_id"))})
        elif kind == "assistant":
            for b in e.get("message", {}).get("content", []):
                if b.get("type") == "text" and b.get("text"):
                    steps.append({"role": "assistant", "text": b["text"]})
                elif b.get("type") == "thinking" and b.get("thinking"):
                    steps.append({"role": "assistant", "thinking": b["thinking"]})
                elif b.get("type") == "tool_use":
                    steps.append({"role": "assistant", "tool": b.get("name"), "id": short(b.get("id")),
                                  "input": b.get("input")})
        elif kind == "user":
            content = e.get("message", {}).get("content", [])
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "tool_result":
                    steps.append({"role": "tool", "id": short(b.get("tool_use_id")),
                                  "is_error": bool(b.get("is_error")), "result": result_text(b.get("content"))})
        elif kind == "result":
            usage = e.get("usage") or {}
            result = {"outcome": e.get("subtype"), "is_error": e.get("is_error"), "turns": e.get("num_turns"),
                      "cost_usd": e.get("total_cost_usd"), "duration_ms": e.get("duration_ms"),
                      "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                      "cache_read_tokens": usage.get("cache_read_input_tokens"),
                      "cache_write_tokens": usage.get("cache_creation_input_tokens"),
                      "final_text": e.get("result")}
    return meta, steps, result


def build(slug, mode, out):
    source = BUILDS / slug
    config = load_config(source)
    prompt = (source / "prompt.md").read_text(encoding="utf-8")
    given = source / "given"
    if not given.is_dir():
        raise SystemExit(f"{given} is missing")
    secrets = [os.environ.get("AIWAI_RECORDING_KEY", ""), os.environ.get("ANTHROPIC_API_KEY", "")]
    with tempfile.TemporaryDirectory(prefix="claude-build-") as tmp:
        work, home = pathlib.Path(tmp) / "build", pathlib.Path(tmp) / "home"
        shutil.copytree(given, work, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
        home.mkdir()
        before = file_hashes(work)
        env = child_env(mode, home, os.path.dirname(sys.executable))
        run = subprocess.run(claude_command(config, mode), input=prompt, cwd=work, env=env, text=True,
                             capture_output=True, timeout=config.get("timeout_s", 1800))
        events = [json.loads(line) for line in run.stdout.splitlines() if line.strip().startswith("{")]
        if not events:
            raise SystemExit(f"claude printed no events (exit {run.returncode}): {run.stderr.strip()[:300]}")
        after = file_hashes(work)
        tests_env = {k: v for k, v in env.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL")}
        tests = subprocess.run(config["test_command"], cwd=work, env=tests_env, text=True, capture_output=True,
                               timeout=600)
        homes = [home] + ([pathlib.Path(env["HOME"])] if env["HOME"] != str(home) else [])
        scrub = Scrubber(work, homes, secrets)
        scrub.text(run.stdout + run.stderr)   # refuses a key anywhere in what claude printed
        meta, steps, result = transcript(scrub.value(events))
        given_tests = {f for f in before if f.startswith("tests/")}
        changed_tests = sorted(f for f in given_tests if after.get(f) != before[f])
        generated = sorted(f for f in after if f not in given_tests and after[f] != before.get(f))
        record = {
            "format": 1, "slug": slug, "mode": mode, "date": datetime.date.today().isoformat(),
            **meta, "command": claude_command(config, mode),
            "exit_code": run.returncode, "result": result,
            "generated": {f: after[f] for f in generated},
            "tests": {"command": config["test_command"], "exit_code": tests.returncode,
                      "passed": tests.returncode == 0, "changed_by_claude": changed_tests},
            "steps": steps,
        }
        out.mkdir(parents=True, exist_ok=True)
        if (out / "generated").exists():
            shutil.rmtree(out / "generated")
        for f in generated:
            target = out / "generated" / f
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(work / f, target)
            scrub.text(target.read_text(encoding="utf-8", errors="replace"))   # refuses a key in a file
        (out / "test-run.txt").write_text(scrub.text(tests.stdout + tests.stderr), encoding="utf-8")
        (out / "transcript.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                                             encoding="utf-8")
    cost = result.get("cost_usd")
    cost = f"{cost:.4f} USD" if isinstance(cost, (int, float)) else "unknown"
    verdict = "passed" if record["tests"]["passed"] else "FAILED"
    print(f"{slug}: {len(steps)} steps, {len(generated)} file(s) generated, tests {verdict}, cost {cost}")
    if changed_tests:
        print(f"  Claude Code changed the given tests: {', '.join(changed_tests)}")
    return 0 if record["tests"]["passed"] and not changed_tests and run.returncode == 0 else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("slug")
    p.add_argument("--out", help="where a reader's run is written (default: claude-build-<slug> here)")
    args = p.parse_args(argv)
    mode = "record" if os.environ.get("BOOK_MODE") == "record" else "reader"
    if mode == "record" and args.out:
        raise SystemExit("record mode writes to builds/<slug>/ only")
    out = BUILDS / args.slug if mode == "record" else pathlib.Path(args.out or f"claude-build-{args.slug}")
    if not re.fullmatch(r"[a-z0-9-]+", args.slug):
        raise SystemExit("a slug is lowercase words joined by hyphens")
    return build(args.slug, mode, out.resolve())


if __name__ == "__main__":
    sys.exit(main())
