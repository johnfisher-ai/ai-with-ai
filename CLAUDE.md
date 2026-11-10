# Building AI with AI: A Visual Handbook

A visual HTML book with companion Jupyter notebooks, on building software that uses a language model
and on using an AI assistant to build it. Public repository, published to GitHub Pages on every push to
`main`. The second book in the Visual Handbook family, after johnfisher-ai/Statistics-Data-Science-AI-Visual-Book.

**Author: John Fisher.** Started November 10, 2026. The part outline, 12 parts and 66 chapters with their
slugs, was approved on November 10 and is in the companion repository's punch list. No chapter is
written yet.

---

## Hard rules

These cost the first book real time when broken. They are not preferences.

- **Read the companion repository first.** The workflow, the 12 writing rules, the checks and the
  punch list live in the private repository `johnfisher-ai/visual-book-notes`. Read its CLAUDE.md and
  the files it lists for this book (`project-files/building-ai-with-ai/`) before changing anything.
- **Push to `main` once the checks pass.** One commit per chapter or round of edits, and the author
  reads each change on the live site. If a push to `main` is refused, push to a branch named for the
  work and tell the author.
- **Never `git commit --amend`, rebase, force-push or rewrite history.** Make a new follow-up commit,
  and undo a pushed change with `git revert`. Treat every existing commit as published.
- **No `Co-Authored-By` trailer** on commits.
- **The repository is public.** Never commit an API key, a bearer token, a request or organization
  ID, or a path under `/home` or `/Users`, in a file or in a notebook's saved output. The author's key
  for building the book reaches a session only as the `AIWAI_RECORDING_KEY` environment variable, which
  the author sets in the book's cloud environment (the punch list's Q7), never through a file in this
  repository, a command line or the chat. Only record mode reads it. Never copy it into
  `ANTHROPIC_API_KEY`, the name other programs, Claude Code among them, read for their own key.
- **Never edit the first book or Python, Visually from a session on this one.** Both are references.
  Clone either read-only to compare or to read a guide, with pushing disabled in the clone, as the
  companion repository's file 3 explains.
- **On resume:** `git log --oneline -5`. A cloud session clones from GitHub, so everything in it is
  already pushed.

---

## Layout

| Path | What it is |
|---|---|
| `chapters/*.html` | The chapter pages, one file per chapter, named by slug. |
| `chapters/notebooks/*.ipynb` | Companion notebooks, saved with their outputs. Source of truth. |
| `chapters/notebooks/html/*.html` | **Generated.** Never hand-edit; rebuilt on deploy. |
| `chapters/notebooks/book_client.py` | The client every notebook replays, calls or records its model responses through. |
| `chapters/notebooks/recordings/<notebook>.json` | The recorded model responses each notebook replays. Checked by `scripts/check_recordings.py`. |
| `tests/` | The helper's tests and `requirements.txt`, which pins the SDK. |
| `templates/chapter.html` | The chapter skeleton. Every new chapter starts as a copy. Not linked, marked noindex, and skipped by the link check. |
| `data/` | Datasets, all written for the book. Workbooks have `Data`, `Codebook` and `Notes` sheets. |
| `assets/css/`, `assets/js/` | `book.css`, `chapter.css`, `challenges.css`, `report.css`, and the dark theme: `theme.css` (**generated**) and `theme.js`. |
| `assets/img/` | The favicon, the iPhone icon, the link-preview card (`social-card.png`, 2400 × 1260) and chapter figures. |
| `toc.html` | **The manifest.** Single source of truth for structure. |
| `scripts/` | `apply_chapter_nav.py`, `inject_notebook_backlinks.py`, `check_links.py`, `build_notebook_html.sh` and `build_sitemap.py`, copied from the first book with this book's names, and `check_recordings.py`. |

The repository root is the site root, so a `book/` segment inside any URL is a dead link.

---

## Structure is computed from the manifest

`toc.html` holds a `PARTS` array and an `AVAILABLE` set.

- **Chapter numbers are positional**, computed from order in `PARTS`. The `n:` fields are cosmetic.
  Inserting a chapter shifts every number after it.
- **`AVAILABLE` gates publication.** A chapter in `PARTS` but not in `AVAILABLE` shows as coming soon.
- After any structural change run `python3 scripts/apply_chapter_nav.py`. It re-stamps only chapter
  **numbers** (title tag, crumb, hero, footer, previous and next cards, the "Up next" callout). It never
  touches titles or hrefs, so the previous and next wiring stays manual.
- `python3 scripts/apply_chapter_nav.py --check` reports drift without changing anything.
- The contents page computes its part and chapter counts from the manifest. Never type a count of
  chapters, notebooks or datasets into a page. Count it from the repository.

**Editing `AVAILABLE` safely:** slice the block by index and replace inside the slice. A document-wide
`s.replace('"slug"', ...)` hits the `slug:"..."` field in `PARTS` first and corrupts the manifest. Always
assert the manifest's slug count is unchanged.

A chapter title lives in the `PARTS` `t:` field, the page `<title>` and the page `<h1>`, and the same words
appear in `og:title`, `twitter:title`, the neighbors' previous and next cards and the notebook card table
in `scripts/inject_notebook_backlinks.py`. Change them all together.

**Titles carry no em dash.** A chapter's tab title is `Ch N · Title · Building AI with AI`, and other
pages use the same middle dot. `apply_chapter_nav.py` relies on the `Ch N ·` form.

**No quizzes.** The author decided on November 10, 2026 that this book has no quizzes, so the first book's
`quiz.js` and its quiz styles were left out, and a chapter ends with its practice challenges.

---

## House style

- **Voice and audience.** The author set this on November 10, 2026, after reviewing Chapter 1. The reader is an
  aspiring AI engineer who already programs in Python and other languages and wants to build AI systems with AI.
  Write for an engineer, in a mix of three registers:
  - **Technical and precise,** above all in a chapter's opening paragraph. Chapter 1's lead is the model: "Traditional
    code executes deterministically. A language model is a fundamentally different building block. You send text in,
    get text back, and identical inputs can yield entirely different outputs."
  - **Direct and natural** for explanation.
  - **Lean and conversational** where a sentence only needs to move the reader on.

  Use engineering vocabulary where it is the accurate word: engineering, discipline, practices, process, component,
  building block, system, deterministic and non-deterministic, validate, verify, mindset. Avoid these:
  - "part" for a piece of a system. Say component, building block, element or system, and keep "Part" for the
    book's twelve parts.
  - "habits" for engineering practice. Say engineering discipline, practices or rigorous craft.
  - "while it builds" and "while you build it". Say "while building" or "throughout the process".
  - Soft or folksy phrasing ("earns its place", "a different kind of part"). Say what happens: the function is
    accepted, the output is validated, the test fails.
- **The 12 writing rules** in the companion repository's CLAUDE.md apply to every page, caption,
  challenge, notebook cell and commit message from the first draft. Run its `style_scan.py` on a new chapter before
  its first commit, and read the opening and closing paragraphs aloud.
- **Fixed book-wide headings,** word for word, approved by the author on November 10, 2026: "In brief"
  (the takeaways box), "Practice challenges", "Run the notebook" (the notebook block's heading),
  "Where <topic> goes wrong" (a concept chapter's last numbered section, naming its own topic), and for a
  case study or capstone "What this does not settle" followed by "What to watch". Every other
  heading is the chapter's own, in sentence case with no colon or comma device.
- **Chapter titles are in sentence case** ("Your first model call"), as the author decided on November 10,
  2026. A case study's title has no "Case study:" prefix. Its slug starts `case-study-`, and its hero's
  kicker says "Case study". Parallel chapters (case studies, capstones) get their own words, so check each
  new chapter's h2 headings against the register in the punch list.
- **American English**, strictly.
- **No prose em dashes,** in any form, and none in `<title>` either. Use commas or parentheses.
- **Named entities in prose limited to** `&amp; &lt; &gt; &quot; &nbsp; &middot;`. Numeric entities are
  fine, and required inside `<svg>`.
- **Keep `$` and `~` out of notebook markdown prose.** Two `$` on a line render as MathJax, and two `~`
  as strikethrough. Write "12 dollars" and "about 0.89".
- **Dated claims.** A claim about a model, a price, a context window, a library or a tool can go stale.
  Write "as of <month year>" with it, and add it to the punch list's dated-claims list.
- **Honest data.** Every dataset is written for the book and describes no real organization or person. A
  downloadable dataset says so in its workbook's `Notes` sheet and carries a short "Teaching dataset" tag on its
  card, and never calls itself real data.
- **State provenance once.** The author decided on November 10, 2026, after reviewing Chapter 1, that the
  introduction explains once that the examples' records are written for the book and that the notebooks replay
  recorded responses, with a live option. Chapters and notebooks don't repeat either. Describe the data and the
  outputs precisely, as an engineer would ("The triage routine evaluates ticket payloads and invokes a large
  language model (LLM) to perform categorical classification. The sample output below illustrates the input
  tickets alongside the model's inferred category assignments."), and leave out "written for the book", "no
  customer wrote them" and "recorded on <date>". The notebook's Setup output already names the recording's model
  and date. A dated claim such as a price keeps its "as of <month year>".
- **Public information only.** Where the book names a company's product, describe only what the company
  has published, with no roadmap and no claim that one product is best.
- **The accent is coral `#ff7a59`.** It replaces the first book's cyan in the logo, the top bar and the
  dark hero, and the CSS keeps the first book's variable name `--cyan` for it so the shared theme tools
  and the copied components work unchanged. Per-chapter color lives only in inline SVG colors.
- **Text contrast.** Small text on the light pages needs 4.5:1, so color it with the tokens in
  `chapter.css` (`--ink-faint`, `--c-cyan-text`, `--c-green-text`, `--c-amber-text`) and give a link a
  plain `<a>`, which `--link` colors and underlines. Coral is for the dark hero, panels and top bar only.
- **Two themes from the first page.** The chapters, the introduction and the 404 page follow the reader's
  device setting, and the switch in the top bar overrides it. A color a dark page has to change is written
  `var(--p-bg-ecfdf5, #ecfdf5)`, with the role `fg`, `bg` or `bd`. After writing or editing a page, run the
  companion repository's `tools/theme/tokenize.py`, then `tools/theme/build_theme.py`, which rewrites
  `assets/css/theme.css`. Never edit `theme.css` by hand. Figures (`figure`, `.svg-wrap`, `.nb-fig`) keep
  their light panels in the dark theme, so SVG colors need no tokens.
- **Phone width from the first page.** Every page passes axe at 375 px in the dark theme with no sideways
  scroll, as well as at 1280 px in the light theme.

---

## The rule that matters most

**Verify every prose claim against executed output.** Narration written before execution is often
wrong in its specifics. Run the notebook, print the numbers, read them, look at each figure, then write
the words. For this book the rule has a second half: **a sentence about what a model said quotes the
recording the committed notebook replays**, and the notebook names that recording's model and date.
Never describe a live answer that isn't recorded.

Check every "Section N", "Step N" and "Chapter N" pointer before the first commit, and every claim about a
later chapter against the part outline.

---

## Notebooks that call a model

Decided by the author on November 10, 2026, and built in round 1 the same day. Every model call goes
through Anthropic's Python SDK, so the code a reader sees is the code they would write, and the SDK's
client is built by `chapters/notebooks/book_client.py`, which changes only the transport under it.

| Mode | How it is chosen | What happens |
|---|---|---|
| replay | The default | Each request is answered from `chapters/notebooks/recordings/<notebook>.json`. No key, no network, and every run prints the same. A request with no recording raises the SDK's `NotFoundError` with a message that starts "book_client: no recorded response", never an invented answer |
| live | `LIVE = True` in Setup | The real API with the reader's own key from Colab's secrets panel (`ANTHROPIC_API_KEY`), or that environment variable elsewhere. It never reads `AIWAI_RECORDING_KEY`. Nothing is written |
| record | `BOOK_MODE=record` in a session | The real API with the author's key from `AIWAI_RECORDING_KEY`, and each exchange is written to the recording |

- **Models, by chapter.** The author decided on November 10, 2026 to mix models by chapter. A notebook
  uses `claude-sonnet-5-5` by default, `claude-opus-5-5` where the chapter needs harder reasoning, and
  `claude-haiku-5-5` where the chapter is about choosing a cheaper model. Each notebook names its model
  in its requests, and its recording and its replay line name it again. Readers who switch to live mode
  pay for that model with their own key, so the chapter states the model and its price as of the
  recording's month.
- **The pin.** SDK 2.7.0, in `tests/requirements.txt`, `requirements.txt` and every Setup cell. Colab
  doesn't ship the SDK, and installing it there keeps Colab's own `httpx2` (2.16.0) and `pydantic`
  (checked on the replica, November 10). Change the pin in all three places together, and record the
  notebooks again.
- **A recording** names the notebook and holds each exchange's request (method, path, query, body), its
  response (status, content type, and the JSON body or the event-stream text), the model, the date and
  the SDK version. Every response header but the content type is dropped, so no request ID or
  organization ID is stored, and the key never is. `scripts/check_recordings.py` checks all of this.
- **Matching.** A request is found by a hash of its method, path, query and body, so a notebook's call
  must be the same as when it was recorded. The same request made twice gets its recorded answers in
  order, starting again from the first when a cell is re-run.
- **The notebook names its source.** `make_client` prints "Replaying N recorded responses from <model>,
  recorded <date>. Set LIVE = True in Setup to call the API yourself.", and a note when the runtime's
  SDK differs from the recording's.
- **Record, then replay twice.** Record with `BOOK_MODE=record`, then replay the notebook twice on the
  Colab replica, and commit only replayed output. Never commit a live run's output.
- **Tests.** `tests/test_book_client.py` covers replay, recording, streaming, errors, repeated requests,
  the missing-request message, the recording check, and that live mode sends only the reader's key and
  record mode only the book's, against a fake API whose responses are fixtures
  written for the tests and say so. `.github/workflows/tests.yml` runs them and the recording check on
  every push.

Every notebook that calls a model starts its Setup with this cell, with `NOTEBOOK` replaced by the
notebook's file name without `.ipynb`. In Colab the notebook arrives alone, so the cell fetches the
helper and the recording from `main` on every run, and reloads the helper so a runtime that outlives a
push uses the current copy. GitHub caches raw files for five minutes after a push.

```python
# Set LIVE = True to send these requests to the Anthropic API with your own key, saved in
# Colab's secrets panel as ANTHROPIC_API_KEY. Left False, the notebook replays the answers
# recorded for the book, with no key and no cost.
LIVE = False
%pip install -q --disable-pip-version-check anthropic==2.7.0
import importlib, pathlib, sys, urllib.request
if "google.colab" in sys.modules:
    BASE = "https://raw.githubusercontent.com/johnfisher-ai/ai-with-ai/main/chapters/notebooks/"
    pathlib.Path("recordings").mkdir(exist_ok=True)
    for name in ["book_client.py", "recordings/NOTEBOOK.json"]:
        urllib.request.urlretrieve(BASE + name, name)
import book_client
importlib.reload(book_client)
client = book_client.make_client("NOTEBOOK", mode="live" if LIVE else None)
```

`--disable-pip-version-check` keeps pip's upgrade notice, with its terminal color codes, out of the
saved output. `%pip` still prints "Note: you may need to restart the kernel to use updated packages.",
as it does in Colab.

## Notebook pipeline

Build → record → replay → verify → render → wire.

1. **Build** the `.ipynb`.
2. **Record** the model responses it needs with `BOOK_MODE=record`, into its recording file.
3. **Replay** with `nbclient` on the Colab replica kernel (`aiwai-colab`, which the companion repository's
   file 3 builds), cwd `chapters/notebooks`, twice, so the saved outputs are what a Colab reader gets and
   nothing moves between runs.
4. **Verify** every prose claim against the printed output, and look at every figure at its rendered
   width. The companion repository's `quote_check.py` lists every number the chapter and the notebook's
   markdown still quote from an older run.
5. **Render**: `python3 -m nbconvert --to html --template lab --output-dir html <name>.ipynb`, in an
   environment holding only the renderer libraries `deploy.yml` pins, with no IPython.
6. **Wire**: add the notebook to `MAP` in `scripts/inject_notebook_backlinks.py` and run it. It adds the
   card, the Colab, download and GitHub buttons, the tab title and link tags, and the contrast and heading
   fixes.

Commit the rendered HTML in the same commit as its notebook. The deploy re-renders only the notebooks a
push changes and publishes the committed HTML for all the others. It never executes a notebook, so step 3
is always yours.

---

## Standing requests

1. **Visual first.** Chapters carry two or more editable inline SVGs, and notebooks carry plots where a
   number has a shape.
2. **Library first.** Use the SDK and well-known libraries over hand-rolled code. Show a mechanism once
   by hand for teaching, then the library call.
3. **A realistic dataset** in `data/` where a chapter works on records, with its `Data`, `Codebook` and
   `Notes` sheets, a dataset card and a download button, labeled as written for the book.
4. **Embed notebook figures** in the chapter as PNGs in `assets/img/` with `.nb-fig`.
5. **Link the companions** instead of re-teaching what they cover. Statistics goes to the first book's
   chapter, by slug (`https://johnfisher-ai.github.io/Statistics-Data-Science-AI-Visual-Book/chapters/<slug>.html`).
   Python and its libraries go to the guide in *Python, Visually*
   (`https://johnfisher-ai.github.io/Python-Visual-Guides/<guide-slug>.html`), johnfisher-ai/Python-Visual-Guides,
   whose `manifest.json` lists every guide's slug and whether it is published. Link only a published guide,
   and name a guide by its title, never its number. The punch list maps the guides to this book's parts.

---

## Traps carried over from the first book

- **Chapter-embedded PNGs are independent copies.** Fixing a figure in a notebook doesn't fix the
  chapter page. Rebuild by replaying the source cell at `dpi = existing_pixel_width / figsize_w`.
- **Old stored outputs hide broken code.** Re-executing is the only way a removed argument surfaces.
- **Figure titles overflow their panel** when matplotlib's titles are left-aligned. Measure them.
- **Renumbering notebook steps orphans `Step N` references** in prose. Sweep first.
- **A colon-free `.replace()` on a slug** hits `toc.html`'s `PARTS` before `AVAILABLE`.
- **The cloud image makes Inter matplotlib's default font**, and Colab draws in DejaVu Sans. The companion
  repository's file 3 says how to run with Colab's default.

---

## Validate before every commit

```
notebooks replay with 0 errors, twice    · every .ipynb has a rendered .html
quoted answers match the recordings      · each recording names its model and date
0 broken local references                · check_links.py
chapter count matches the manifest       · apply_chapter_nav.py --check reports 0 drift
sitemap up to date                       · build_sitemap.py --check
theme.css up to date                     · tokenize.py and build_theme.py --check
validator 0 errors, axe 0 violations     · 1280 px light and 375 px dark, no sideways scroll
no em dashes, entities, British spelling · prose_check.py
no key, token or machine path            · secret_check.py and path_check.py
recordings name model, date and SDK      · check_recordings.py, and the helper's tests pass
```

The companion repository's `tools/checks/run-ai-with-ai.sh` runs these checks on the changed pages,
with the style scan and the naming scan.
