#!/usr/bin/env python3
"""Write sitemap.xml from the manifest, so search engines find every published page.

It lists the title page, the introduction, the contents, every chapter in AVAILABLE in the order of
PARTS, every report and every rendered notebook. It leaves out the 404 page and the chapter skeleton
in templates/, which nothing links to. Run it after adding or removing a page:

    python3 scripts/build_sitemap.py           # write sitemap.xml
    python3 scripts/build_sitemap.py --check   # exit 1 if sitemap.xml is out of date

The sitemap carries no dates, so it changes only when a page is added or removed.
"""
import glob, os, re, sys

BOOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://johnfisher-ai.github.io/ai-with-ai/"


def pages():
    toc = open(os.path.join(BOOK, "toc.html"), encoding="utf-8").read()
    parts = toc[toc.index("const PARTS ="):toc.index("const AVAILABLE")]
    order = re.findall(r'\{(?:n:\s*\d+,\s*)?slug:"([^"]+)",\s*t:"', parts)
    avail = toc[toc.index("const AVAILABLE"):]
    ready = set(re.findall(r'"([a-z0-9-]+)"', avail[:avail.index("]")]))
    out = ["", "introduction.html", "toc.html"]
    out += [f"chapters/{s}.html" for s in order if s in ready]
    for folder in ("reports", "chapters/notebooks/html"):
        out += sorted(os.path.relpath(p, BOOK) for p in glob.glob(os.path.join(BOOK, folder, "*.html")))
    missing = [p for p in out if p and not os.path.exists(os.path.join(BOOK, p))]
    if missing:
        sys.exit(f"pages in the manifest with no file: {missing}")
    return out


def sitemap():
    urls = "".join(f"  <url><loc>{SITE}{p}</loc></url>\n" for p in pages())
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n')


if __name__ == "__main__":
    path = os.path.join(BOOK, "sitemap.xml")
    new = sitemap()
    if "--check" in sys.argv:
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        ok = old == new
        print("sitemap: up to date" if ok else "sitemap: out of date, run python3 scripts/build_sitemap.py")
        sys.exit(0 if ok else 1)
    open(path, "w", encoding="utf-8").write(new)
    print(f"wrote sitemap.xml with {new.count('<url>')} pages")
