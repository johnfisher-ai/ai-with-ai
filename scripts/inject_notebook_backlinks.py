#!/usr/bin/env python3
"""Give each rendered notebook page its book card, links and head tags.

Run AFTER `nbconvert`. It changes only the View-Notebook HTML, never the .ipynb files, and is
wired into both scripts/build_notebook_html.sh and the GitHub Actions deploy workflow so it
survives every re-render. Each run rewrites what it added before, so a page always carries the
current design, and running it twice changes nothing the second time. On every page it sets:

  - the tab title, description, canonical address and link-preview tags, from the chapter's
    title and number in toc.html and the notebook's hero cell
  - the site icon, and styles that left-align tables, darken nbconvert's cell prompts so they
    can be read, and underline links in the notebook's text, as the chapters do
  - a card at the top with the way back to the chapter and buttons to open the notebook in Colab,
    download it and view it on GitHub, and the way back again at the bottom
  - an h1 for a page that has none: the hero cell's title, drawn as before. A heading that then
    skips a level (an h3 straight after the h1) moves up one, keeping its size, and the blank
    corner cell of a pandas table header becomes a plain cell, so screen readers get a sound outline
  - darker shades for the colors that read below 4.5:1 on the page: the code highlighting's
    comments, numbers, operators and errors, and the faint footer line many notebooks end with
  - on a phone, hero titles at 28 px and long words wrapped, so no text cell scrolls sideways

The notebooks themselves are left alone, so nothing changes for a reader in Colab, which has its
own highlighting and themes.

Add a chapter's notebooks to MAP as they ship.
"""
import html as htmllib, json, os, re, unicodedata

HTML_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "chapters", "notebooks", "html")

# notebook-html filename -> (relative href to the chapter section, kicker, title)
MAP = {
    # One entry per rendered notebook page, added as each chapter ships, in this form:
    # '<notebook>.html':
    #     ('../../<chapter-slug>.html#notebook', 'Back to the book', 'Chapter N · <chapter title>'),
    # (written with double quotes in a real entry, which check_links.py then validates)
    "what-building-ai-with-ai-means.html":
        ("../../what-building-ai-with-ai-means.html#notebook", "Back to the book", "Chapter 1 · What building AI with AI means"),
    "what-building-ai-with-ai-means--solutions.html":
        ("../../what-building-ai-with-ai-means.html#challenges", "Back to the book", "Chapter 1 · Practice challenges"),
}

BOOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://johnfisher-ai.github.io/ai-with-ai/"
REPO = "johnfisher-ai/ai-with-ai"
BOOK_SHORT = "Building AI with AI"
BOOK_FULL = "Building AI with AI: A Visual Handbook"

# Everything the script adds sits between these markers or in the two cards, so a later run can
# take it out again and put the current version in.
HEAD_START, HEAD_END = "<!-- book-head -->", "<!-- /book-head -->"

CSS = (
    "<style id=\"book-notebook-css\">"
    # left-align tables like Colab, where nbconvert centers them
    ".jp-RenderedHTMLCommon table{margin-left:0 !important;margin-right:auto !important;}"
    # nbconvert shows the In and Out prompts at half opacity in light blue and orange (about 2:1);
    # these shades of the same hues read at 5:1 or more on the white page and the gray code box
    ":root{--jp-cell-inprompt-font-color:#2766a0;--jp-cell-outprompt-font-color:#a64d32;"
    "--jp-cell-prompt-not-active-opacity:1;}"
    # code highlighting: these four of jupyterlab_pygments' colors read below 4.5:1 on the gray code box
    ":root{--jp-mirror-editor-comment-color:#3a7474;--jp-mirror-editor-number-color:#007e00;"
    "--jp-mirror-editor-operator-color:#a10bff;--jp-mirror-editor-error-color:#db0000;}"
    # the footer line in the last cell, #8b94b3 (3:1) on white, takes the chapters' faint ink
    ".jp-RenderedHTMLCommon [style*=\"color:#8b94b3\"]{color:#666f8e !important;}"
    # a heading moved up a level keeps the size of the level it had
    ".jp-RenderedHTMLCommon .book-was-h3{font-size:var(--jp-content-font-size3);}"
    ".jp-RenderedHTMLCommon .book-was-h4{font-size:var(--jp-content-font-size2);}"
    ".jp-RenderedHTMLCommon .book-was-h5{font-size:var(--jp-content-font-size1);}"
    ".jp-RenderedHTMLCommon .book-was-h6{font-size:var(--jp-content-font-size0);}"
    # links in the notebook's text are underlined, as in the chapters
    ".jp-RenderedHTMLCommon a:link,.jp-RenderedHTMLCommon a:visited{text-decoration:underline;}"
    # the card, in the look of the chapters' previous and next cards
    ".book-nav{max-width:760px;margin:18px auto;"
    "font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}"
    ".book-back{display:flex;align-items:center;gap:12px;text-decoration:none;border:1px solid #e6e9f2;"
    "border-radius:13px;padding:15px 20px;background:#ffffff;box-shadow:0 6px 18px rgba(20,30,80,0.06);}"
    ".book-back:hover{border-color:#7c3aed;}"
    ".book-back-arrow{font-size:22px;color:#0e7490;line-height:1;}"
    ".book-back-kicker{display:block;font-size:11px;font-weight:700;letter-spacing:0.08em;"
    "text-transform:uppercase;color:#666f8e;}"
    ".book-back-title{font-weight:700;color:#1a2138;font-size:15px;}"
    ".book-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;}"
    ".book-btn{display:inline-flex;align-items:center;gap:8px;padding:9px 18px;border-radius:8px;"
    "font-size:14px;font-weight:600;text-decoration:none;color:#1a2138;background:#ffffff;"
    "border:1px solid #cdd3e3;}"
    ".book-btn:hover{background:#f4f6fb;}"
    ".book-btn-colab{background:#f9ab00;border-color:#f9ab00;font-weight:700;}"
    ".book-btn-colab:hover{background:#ffbd2e;}"
    ".book-back:focus-visible,.book-btn:focus-visible{outline:2px solid #0e7490;outline-offset:2px;}"
    # the hero title made a heading is drawn as the div it was: inherited type and no heading margins,
    # with the hero's inline style on top
    ".jp-RenderedHTMLCommon h1.book-hero-title{font:inherit;color:inherit;letter-spacing:inherit;"
    "margin:0;border:0;padding:0;}"
    # on a phone the three buttons sit closer, so the first two share a line, hero titles of up to
    # 40 px come down to 28, and a long word wraps rather than pushing its cell sideways, as does code
    # in a table cell, which would otherwise widen the whole table
    "@media (max-width:480px){.book-actions{gap:8px;}.book-btn{padding:8px 13px;font-size:13px;}"
    "main>.jp-Cell:first-of-type [style*=\"font-weight:900\"]{font-size:28px !important;}"
    ".jp-RenderedMarkdown{overflow-wrap:break-word;}"
    ".jp-RenderedMarkdown td code,.jp-RenderedMarkdown th code{overflow-wrap:anywhere;}}"
    "</style>"
)

# What the first version of this script added, removed before the current version goes in.
OLD_PIECES = [
    '<link rel="icon" href="../../../assets/img/favicon.svg" type="image/svg+xml">\n'
    '<link rel="apple-touch-icon" href="../../../assets/img/apple-touch-icon.png">\n',
    '<style id="book-table-align">.jp-RenderedHTMLCommon table{margin-left:0 !important;'
    'margin-right:auto !important;}</style>\n',
]
# the first version's cards: one after <body ...> and a newline, one before a newline and </body>
OLD_TOP = re.compile(r'(<body[^>]*>)\n<a class="book-backlink" .*?</a>', re.S)
OLD_BOTTOM = re.compile(r'<a class="book-backlink" .*?</a>\n(?=</body>)', re.S)
# the current cards: one just before <main>, one just after </main>
NAV_TOP = re.compile(r'<nav class="book-nav" .*?</nav>\n(?=<main>)', re.S)
NAV_BOTTOM = re.compile(r'(?<=</main>)\n<nav class="book-nav" .*?</nav>', re.S)
# the hero cell's title, as nbconvert writes it and as this script makes it a heading
HERO_DIV = re.compile(r'<div (style="[^"]*font-weight:\s*900[^"]*")>(.*?)</div>', re.S)
HERO_H1 = re.compile(r'<h1 class="book-hero-title" (style="[^"]*")>(.*?)</h1>', re.S)
# a heading this script moved up a level, and a pandas header's blank corner cell
MOVED = re.compile(r'<h([1-6]) class="book-was-h([1-6])"([^>]*)>(.*?)</h\1>', re.S)
HEADING = re.compile(r'<h([1-6])((?:\s[^>]*)?)>(.*?)</h\1>', re.S)
THEAD = re.compile(r"<thead>.*?</thead>", re.S)
BLANK_TD = '<td class="book-blank-th"></td>'
HEAD_BLOCK = re.compile(re.escape(HEAD_START) + r".*?" + re.escape(HEAD_END) + r"\n", re.S)


def manifest():
    """Each chapter's number and title from toc.html, by slug. Numbers come from position."""
    toc = open(os.path.join(BOOK, "toc.html"), encoding="utf-8").read()
    parts = toc[toc.index("const PARTS ="):toc.index("const AVAILABLE")]
    found = re.findall(r'\{(?:n:\s*\d+,\s*)?slug:"([^"]+)",\s*t:"([^"]*)"', parts)
    return {slug: (i + 1, htmllib.unescape(t).strip()) for i, (slug, t) in enumerate(found)}


def plain(fragment):
    """Visible text of a bit of the hero's HTML, without tags, entities or emoji."""
    text = htmllib.unescape(re.sub(r"<[^>]+>", "", fragment))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "So" and ch not in "\ufe0f\u200d")
    return re.sub(r"\s+", " ", text).strip()


def hero(name):
    """The kicker, title and first line of text in the notebook's hero cell."""
    nb = json.load(open(os.path.join(BOOK, "chapters", "notebooks", name + ".ipynb"), encoding="utf-8"))
    src = "".join(nb["cells"][0]["source"])
    kicker = re.search(r'<div style="[^"]*text-transform:\s*uppercase[^"]*">(.*?)</div>', src, re.S)
    title = re.search(r'<(div|h1) style="([^"]*font-weight:\s*900[^"]*)">(.*?)</\1>', src, re.S)
    lines = [plain(t) for t in re.findall(r"<div[^>]*>(.*?)</div>", src[title.end():], re.S)] if title else []
    lines = [t for t in lines if t and "John Fisher" not in t]
    return (plain(kicker.group(1)) if kicker else "", plain(title.group(3)) if title else "", lines[0] if lines else "")


def describe(name, slug, chapters):
    """The page's tab title, link-preview title and description."""
    n, chapter = chapters[slug]
    kicker, title, line = hero(name)
    where = f"Chapter {n}, {chapter}, of {BOOK_FULL}"
    if name == slug:
        kind, lead = "Notebook", f"The companion notebook for {where}."
    elif name.endswith("--solutions"):
        kind, lead = "Solutions", f"Worked solutions to the practice challenges in {where}."
    elif name.endswith("--take-it-further"):
        kind, lead = "Take It Further", f"A take-it-further notebook that extends {where}."
    else:
        # one of several notebooks for a chapter, named in its hero ("Notebook 3 of 5", "Toolkit")
        kind = kicker.split("·")[-1].strip()
        if kind == "Toolkit":
            lead = f"A toolkit notebook for {where}."
        elif kind.startswith("Report"):
            lead = f"The notebook behind {kind.lower()} in {where}."
        else:
            lead = f"{kind} for {where}."
        chapter = title
    # no em dash in any title (handoff D8)
    tab = f"Ch {n} · {chapter} · {kind} · {BOOK_SHORT}"
    preview = f"{chapter} · Chapter {n} · {kind}"
    return tab, preview, (lead + " " + line).strip()


def head_block(name, preview, description):
    a = lambda v: htmllib.escape(v, quote=True)
    url = SITE + "chapters/notebooks/html/" + name + ".html"
    image = SITE + "assets/img/social-card.png"
    return "\n".join([
        HEAD_START,
        f'<meta name="description" content="{a(description)}">',
        '<meta name="author" content="John Fisher">',
        f'<link rel="canonical" href="{url}">',
        '<meta property="og:type" content="article">',
        f'<meta property="og:site_name" content="{a(BOOK_FULL)}">',
        f'<meta property="og:title" content="{a(preview)}">',
        f'<meta property="og:description" content="{a(description)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{image}">',
        '<meta property="og:image:width" content="2400">',
        '<meta property="og:image:height" content="1260">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{a(preview)}">',
        f'<meta name="twitter:description" content="{a(description)}">',
        f'<meta name="twitter:image" content="{image}">',
        '<link rel="icon" href="../../../assets/img/favicon.svg" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="../../../assets/img/apple-touch-icon.png">',
        CSS,
        HEAD_END,
    ]) + "\n"


def back_link(href, kicker, title):
    return ('<a class="book-back" href="' + href + '">'
            '<span class="book-back-arrow" aria-hidden="true">&#8592;</span>'
            '<span><span class="book-back-kicker">' + kicker + '</span>'
            '<span class="book-back-title">' + title + '</span></span></a>')


def top_card(name, href, kicker, title):
    ipynb = "blob/main/chapters/notebooks/" + name + ".ipynb"
    return ('<nav class="book-nav" aria-label="Notebook links">' + back_link(href, kicker, title) +
            '<div class="book-actions">'
            '<a class="book-btn book-btn-colab" href="https://colab.research.google.com/github/' + REPO + '/' + ipynb +
            '" target="_blank" rel="noopener"><span aria-hidden="true">&#9654;</span> Open in Colab</a>'
            '<a class="book-btn" href="../' + name + '.ipynb" download>'
            '<span aria-hidden="true">&#11015;</span> Download notebook</a>'
            '<a class="book-btn" href="https://github.com/' + REPO + '/' + ipynb +
            '" target="_blank" rel="noopener">View on GitHub</a>'
            '</div></nav>')


def bottom_card(href, kicker, title):
    return '<nav class="book-nav" aria-label="Back to the book">' + back_link(href, kicker, title) + '</nav>'


def strip(html):
    """The page as nbconvert wrote it: everything this script added, old or current, taken out."""
    html = HEAD_BLOCK.sub("", html)
    for piece in OLD_PIECES:
        html = html.replace(piece, "")
    html = html.replace(BLANK_TD, "<th></th>")
    html = MOVED.sub(r"<h\2\3>\4</h\2>", html)
    html = HERO_H1.sub(r"<div \1>\2</div>", html)
    html = OLD_BOTTOM.sub("", OLD_TOP.sub(r"\1", html))
    return NAV_BOTTOM.sub("", NAV_TOP.sub("", html))


def outline(html):
    """Move up any heading in <main> that skips a level, and turn blank header corners into plain cells."""
    start, end = html.index("<main>"), html.rindex("</main>")
    body, prev, pos, out = html[start:end], 0, 0, []
    for m in HEADING.finditer(body):
        level, attrs = int(m.group(1)), m.group(2)
        if prev and level > prev + 1 and "class=" not in attrs:
            out += [body[pos:m.start()], f'<h{prev + 1} class="book-was-h{level}"{attrs}>{m.group(3)}</h{prev + 1}>']
            pos, level = m.end(), prev + 1
        prev = level
    body = "".join(out) + body[pos:]
    body = THEAD.sub(lambda m: m.group(0).replace("<th></th>", BLANK_TD), body)
    return html[:start] + body + html[end:]


def inject(path, name, href, kicker, title, chapters):
    old = open(path, encoding="utf-8").read()
    html = strip(old)
    slug = re.match(r"\.\./\.\./([^#]+)\.html#", href).group(1)
    tab, preview, description = describe(name, slug, chapters)
    html = re.sub(r"<title>.*?</title>", lambda m: "<title>" + htmllib.escape(tab, quote=False) + "</title>",
                  html, count=1, flags=re.S)
    html = html.replace("</head>", head_block(name, preview, description) + "</head>", 1)
    if not re.search(r"<h1[\s>]", html):
        html = HERO_DIV.sub(r'<h1 class="book-hero-title" \1>\2</h1>', html, count=1)
    html = outline(html)
    html = html.replace("<main>", top_card(name, href, kicker, title) + "\n<main>", 1)
    end = html.rindex("</main>") + len("</main>")
    html = html[:end] + "\n" + bottom_card(href, kicker, title) + html[end:]
    if html == old:
        return "up to date"
    open(path, "w", encoding="utf-8").write(html)
    return "updated"


def main():
    if not os.path.isdir(HTML_DIR):
        print("No HTML dir yet:", HTML_DIR); return
    chapters = manifest()
    for fname, (href, kicker, title) in MAP.items():
        path = os.path.join(HTML_DIR, fname)
        if os.path.exists(path):
            print(f"{fname}: {inject(path, fname[:-5], href, kicker, title, chapters)}")
        else:
            print(f"{fname}: (not rendered yet, skipped)")

if __name__ == "__main__":
    main()
