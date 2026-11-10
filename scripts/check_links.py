#!/usr/bin/env python3
"""Resolve every link in the book and report the ones that go nowhere.

    python3 scripts/check_links.py              # local and self-referencing links
    python3 scripts/check_links.py --external   # also HTTP-check outside hosts

Three kinds of link get checked, and the third is the one that matters:

  relative      href="../data/foo.xlsx"   resolved against the file it appears in
  anchors       href="page.html#section"  the id has to exist in that page
  self-links    Colab, github.com/blob, and johnfisher-ai.github.io URLs all encode
                a path inside this repository, so they are checked against the local
                tree with no network call. A broken Colab button is invisible
                otherwise: the page loads, the notebook 404s only when clicked.

Outside hosts are only fetched with --external.
"""

import argparse
import collections
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
OWNER, REPO = "johnfisher-ai", "ai-with-ai"

LINK = re.compile(r'(?:href|src)="([^"]+)"')
# Links built inside <script> are template strings, not links. Scanning them
# reports things like href="${href}" as broken.
SCRIPT = re.compile(r"<script\b.*?</script>|<style\b.*?</style>", re.S | re.I)
ID = re.compile(r'\sid="([^"]+)"')
NAME = re.compile(r'<a[^>]+name="([^"]+)"')

SELF_PATTERNS = [
    re.compile(rf"^https://colab\.research\.google\.com/github/{OWNER}/{REPO}/blob/[^/]+/(.+)$"),
    re.compile(rf"^https://github\.com/{OWNER}/{REPO}/(?:blob|raw)/[^/]+/(.+)$"),
    re.compile(rf"^https://raw\.githubusercontent\.com/{OWNER}/{REPO}/[^/]+/(.+)$"),
    re.compile(rf"^https://{OWNER}\.github\.io/{REPO}/(.*)$"),
]

SKIP_PREFIX = ("mailto:", "data:", "javascript:", "tel:", "#!")
# templates/chapter.html is the chapter skeleton, whose notebook and neighbor links name a chapter
# that doesn't exist yet. Nothing links to it, and the validator and axe still check it.
SKIP_DIRS = ("templates",)


def html_files():
    for p in sorted(ROOT.rglob("*.html")):
        rel = p.relative_to(ROOT).parts
        if ".git" not in p.parts and rel[0] not in SKIP_DIRS:
            yield p


def anchors_in(path: Path, cache: dict) -> set:
    if path not in cache:
        try:
            s = path.read_text(errors="replace")
        except OSError:
            cache[path] = set()
        else:
            s = SCRIPT.sub(" ", s)
            cache[path] = set(ID.findall(s)) | set(NAME.findall(s))
    return cache[path]


def as_repo_path(url: str):
    """A URL that points back into this repository, as a path, else None."""
    for pat in SELF_PATTERNS:
        m = pat.match(url)
        if m:
            p = unquote(m.group(1).split("#")[0].split("?")[0])
            return p or "index.html"
    return None


def check_injector(problems: list) -> int:
    """Validate the backlink table in scripts/inject_notebook_backlinks.py.

    That script rewrites notebook HTML at deploy time, so a wrong anchor there
    survives any fix made to the rendered pages: the next re-render puts it
    straight back. Checking the table catches the cause, not the symptom.
    """
    src = ROOT / "scripts/inject_notebook_backlinks.py"
    if not src.exists():
        return 0
    seen, checked = set(), 0
    for page, frag in re.findall(r'"\.\./\.\./([^"#]+\.html)#([a-z-]+)"', src.read_text()):
        if (page, frag) in seen:
            continue
        seen.add((page, frag))
        checked += 1
        f = ROOT / "chapters" / page
        if not f.exists():
            problems.append(("scripts/inject_notebook_backlinks.py",
                             f"../../{page}#{frag}", f"chapters/{page} does not exist"))
        elif f'id="{frag}"' not in f.read_text(errors="replace"):
            problems.append(("scripts/inject_notebook_backlinks.py",
                             f"../../{page}#{frag}", f"no id {frag!r} in chapters/{page}"))
    return checked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--external", action="store_true", help="also HTTP-check outside hosts")
    args = ap.parse_args()

    cache: dict = {}
    problems = []
    counts = collections.Counter()
    external: set = set()

    for f in html_files():
        rel = f.relative_to(ROOT)
        markup = SCRIPT.sub(" ", f.read_text(errors="replace"))
        for raw in LINK.findall(markup):
            url = raw.strip()
            if not url or url.startswith(SKIP_PREFIX):
                continue

            # a link back into this repo, written as an absolute URL
            repo_path = as_repo_path(url)
            if repo_path is not None:
                counts["self"] += 1
                if not (ROOT / repo_path).exists():
                    problems.append((str(rel), url, f"repository has no {repo_path}"))
                continue

            if urlparse(url).scheme in ("http", "https"):
                counts["external"] += 1
                external.add(url)
                continue

            base, _, frag = url.partition("#")
            if not base:                                   # in-page anchor
                counts["anchor"] += 1
                if frag not in anchors_in(f, cache):
                    problems.append((str(rel), url, "no such id on this page"))
                continue

            counts["relative"] += 1
            target = (f.parent / unquote(base)).resolve()
            if not target.exists():
                problems.append((str(rel), url, "file does not exist"))
                continue
            if frag and target.suffix == ".html" and frag not in anchors_in(target, cache):
                problems.append((str(rel), url, f"no id {frag!r} in {base}"))

    injector = check_injector(problems)

    if args.external:
        import urllib.request
        import urllib.error
        print(f"  checking {len(external)} outside URLs ...")
        for url in sorted(external):
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "link-check"})
            try:
                urllib.request.urlopen(req, timeout=20)
            except urllib.error.HTTPError as e:
                if e.code not in (403, 405, 429, 999):     # bot blocks, not breakage
                    problems.append(("(external)", url, f"HTTP {e.code}"))
            except Exception as e:
                problems.append(("(external)", url, type(e).__name__))

    print(f"  {sum(1 for _ in html_files())} html files: "
          f"{counts['relative']} relative, {counts['anchor']} anchors, "
          f"{counts['self']} back into this repo, {counts['external']} outside")
    if injector:
        print(f"  backlink table: {injector} distinct targets")
    if problems:
        print()
        for where, url, why in problems:
            print(f"  BROKEN  {where}")
            print(f"          {url}")
            print(f"          {why}")
        print(f"\n  *** {len(problems)} broken ***")
        return 1
    print("  every link resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
