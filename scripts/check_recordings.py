#!/usr/bin/env python3
"""Check every recording the notebooks replay, in chapters/notebooks/recordings/.

    python3 scripts/check_recordings.py

A recording is what a notebook prints as a model's answer, so it has to say where it came from and
carry nothing it shouldn't. For each file it checks that:

  - it is a format-1 recording named for its notebook, and that notebook exists
  - every exchange names its model, the date it was recorded and the SDK version
  - every response keeps its status, its content type and its body, and no header or request ID
  - every exchange's key is the key book_client.py computes from the request it stores, so the
    notebook's request will find it

It needs only the standard library. The secret check in the companion repository looks for keys,
tokens and request IDs in these files as in every other. Exits 1 if anything is wrong.
"""
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "chapters" / "notebooks"
EXCHANGE_FIELDS = {"key", "call", "request", "response", "model", "recorded", "sdk"}
RESPONSE_FIELDS = {"status", "content_type"}


def request_key(method, path, query, body):
    """The same key as book_client.request_key, kept here so the check needs no SDK installed."""
    canonical = json.dumps({"method": method, "path": path, "query": query, "body": body},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def check(path):
    problems = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"not JSON: {e}"]
    if data.get("format") != 1:
        problems.append("format is not 1")
    if data.get("notebook") != path.stem:
        problems.append(f"names notebook {data.get('notebook')!r}, file is {path.stem}")
    if not (NOTEBOOKS / f"{path.stem}.ipynb").exists():
        problems.append(f"no notebook chapters/notebooks/{path.stem}.ipynb")
    exchanges = data.get("exchanges")
    if not isinstance(exchanges, list) or not exchanges:
        return problems + ["no exchanges"]
    for i, e in enumerate(exchanges, 1):
        where = f"exchange {i}"
        if set(e) != EXCHANGE_FIELDS:
            problems.append(f"{where}: fields {sorted(set(e))}, expected {sorted(EXCHANGE_FIELDS)}")
            continue
        if not e["model"] or not e["sdk"]:
            problems.append(f"{where}: no model or no SDK version")
        try:
            datetime.date.fromisoformat(e["recorded"])
        except (TypeError, ValueError):
            problems.append(f"{where}: recorded date {e['recorded']!r} is not YYYY-MM-DD")
        r = e["response"]
        body_fields = set(r) - RESPONSE_FIELDS
        if not RESPONSE_FIELDS <= set(r) or body_fields not in ({"body"}, {"text"}):
            problems.append(f"{where}: response fields {sorted(r)}, expected status, content_type and body or text")
        if isinstance(r.get("body"), dict) and "request_id" in r["body"]:
            problems.append(f"{where}: response body keeps a request_id")
        q = e["request"]
        if request_key(q.get("method"), q.get("path"), q.get("query"), q.get("body")) != e["key"]:
            problems.append(f"{where}: key does not match its request")
    return problems


def main():
    files = sorted((NOTEBOOKS / "recordings").glob("*.json"))
    bad = 0
    for f in files:
        for p in check(f):
            bad += 1
            print(f"  {f.relative_to(ROOT)}: {p}")
    print(f"recordings: {len(files)} file(s), {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
