#!/usr/bin/env python3
"""Re-stamp every chapter page's NUMBER from the single-source manifest (toc.html PARTS).

Chapter numbers are POSITION-based (running order over all manifest chapters), so after inserting
or moving a chapter in PARTS, re-running this fixes every page's number automatically -- no manual
renumbering when a chapter is added to any section.

    python3 scripts/apply_chapter_nav.py            # rewrite in place
    python3 scripts/apply_chapter_nav.py --check     # report drift only, change nothing (exit 1 if any)

Rewrites ONLY numbers, never links or titles:
  <title>Ch N ·, crumb <span>Chapter N</span>, hero <b>Chapter N</b>, footer 'Chapter N',
  and each prev/next card's 'Chapter N · Previous/Next' (N taken from the chapter the card already
  links to, so the number always matches the target). Hrefs and neighbour titles are left exactly
  as authored -- prev/next wiring stays the author's job, as today.
"""
import os, re, sys

BOOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = "--check" in sys.argv

toc = open(os.path.join(BOOK, "toc.html"), encoding="utf-8").read()
parts_blob = toc[toc.index("const PARTS ="):toc.index("const AVAILABLE")]
slugs_in_order = re.findall(r'\{(?:n:\s*\d+,\s*)?slug:"([^"]+)",\s*t:"', parts_blob)
num_of = {slug: i+1 for i, slug in enumerate(slugs_in_order)}     # position-based number
avail = toc[toc.index("const AVAILABLE"):]
ready = set(re.findall(r'"([a-z0-9-]+)"', avail[:avail.index("]")]))
print(f"manifest: {len(slugs_in_order)} chapters, {len(ready)} ready")

def set_upnext_num(html, n_next):
    """In the 'Up next' callout, restamp the hardcoded 'Chapter N ·' to the immediate next
    chapter's number (this chapter + 1). Numbering is contiguous, so the next chapter is always
    this+1; the callout's title is left untouched. No-op if there is no Up-next number (e.g. the
    last published chapter's coming-soon callout)."""
    m = re.search(r'ctitle">Up next.*?</div>\s*</div>', html, re.DOTALL)
    if not m:
        return html
    seg = m.group(0)
    newseg = re.sub(r'(Chapter )\d+(\s*(?:&#183;|&middot;|·))',
                    lambda mm: mm.group(1)+str(n_next)+mm.group(2), seg, count=1)
    if newseg == seg:
        return html
    return html[:m.start()] + newseg + html[m.end():]

def set_card_num(html, kind):
    """In the prev/next card, set 'Chapter N' from the number of the slug it links to."""
    word = "Previous" if kind == "prev" else "Next"
    m = re.search(r'<a class="cn-btn '+kind+r'" href="([a-z0-9-]+)\.html"(.*?)</a>', html, re.DOTALL)
    if not m:
        return html
    target = m.group(1)
    if target not in num_of:
        return html
    n = num_of[target]
    block = m.group(0)
    newblock = re.sub(r'(<span class="cn-dir">Chapter )\d+( (?:·|&#183;) '+word+r'</span>)',
                      lambda mm: mm.group(1)+str(n)+mm.group(2), block, count=1)
    return html[:m.start()] + newblock + html[m.end():]

changed, missing = 0, []
for slug in slugs_in_order:
    if slug not in ready:
        continue
    fp = os.path.join(BOOK, "chapters", slug + ".html")
    if not os.path.exists(fp):
        missing.append(slug); continue
    html = open(fp, encoding="utf-8").read(); orig = html
    n = num_of[slug]
    html = re.sub(r'(<title>Ch )\d+( ·)', lambda m: m.group(1)+str(n)+m.group(2), html, count=1)
    html = re.sub(r'(<span>Chapter )\d+(</span>)', lambda m: m.group(1)+str(n)+m.group(2), html, count=1)
    html = re.sub(r'(<b>Chapter )\d+(</b>)', lambda m: m.group(1)+str(n)+m.group(2), html, count=1)
    # the footer separator/copyright appear both as literals and as numeric entities
    html = re.sub(r'(Chapter )\d+( &nbsp;(?:·|&#183;)&nbsp; (?:©|&#169;))',
                  lambda m: m.group(1)+str(n)+m.group(2), html, count=1)
    html = set_card_num(html, "prev")
    html = set_card_num(html, "next")
    if n + 1 <= len(slugs_in_order):
        html = set_upnext_num(html, n + 1)
    if html != orig:
        changed += 1
        if not CHECK:
            open(fp, "w", encoding="utf-8").write(html)

if missing:
    print("READY but no page file:", missing)
if CHECK:
    print(f"pages that WOULD change: {changed}")
    sys.exit(1 if changed else 0)
print(f"re-stamped {changed} pages" + (" (all already in sync)" if changed == 0 else ""))
