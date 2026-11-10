# Building AI with AI: A Visual Handbook

A free, visual book on building software that uses a language model, and on using an AI assistant to help
build it. Each chapter is an HTML page with inline SVG figures and a companion Python notebook that runs in
Colab. By **John Fisher**. It is the second book in the Visual Handbook family, after
[*Statistics, Data Science and AI: A Visual Handbook*](https://johnfisher-ai.github.io/Statistics-Data-Science-AI-Visual-Book/).
Its chapters link to that book for statistics, and to the guides in
[*Python, Visually*](https://johnfisher-ai.github.io/Python-Visual-Guides/) for Python and its libraries.

🌐 **Live site:** https://johnfisher-ai.github.io/ai-with-ai/

The book is being written. The site has its title page, contents and introduction, and chapters appear in
the contents as they are published.

---

## How readers use it

1. **Read** a chapter (static HTML, works anywhere).
2. **View the notebook**, a rendered page with all the code and its saved outputs, with nothing to install.
3. **Open in Colab** to run and edit the code in the browser. A Google login is needed only to run it, and
   each reader gets a copy of their own, so the original in this repository never changes.
4. **Download or view on GitHub** to get the raw `.ipynb`.

### Notebooks that call a model

Most notebooks call a language model through Anthropic's Python SDK. By default each one replays responses
recorded from the API and kept in this repository, so it runs with no API key, makes no network call to the
model and prints the same thing every time. Each recording names the model and the date it came from. A
switch at the top of the notebook sends the same requests to the live API with your own key, stored in
Colab's secrets panel, and its answers will differ from the recorded ones.

The client every notebook uses is built by `chapters/notebooks/book_client.py`, and the recordings are in
`chapters/notebooks/recordings/`. `python3 -m pytest tests/` runs the helper's tests (after
`pip install -r tests/requirements.txt`), and `python3 scripts/check_recordings.py` checks that every
recording names its model, date and SDK version and keeps no response header.

## Project structure

```
.
├── index.html                  # Title page
├── introduction.html           # How the book works
├── toc.html                    # Contents, and the manifest: PARTS sets the order, AVAILABLE what is published
├── 404.html                    # Shown for an address that doesn't exist
├── sitemap.xml                 # Every published page, for search engines (scripts/build_sitemap.py)
├── chapters/
│   ├── <slug>.html             # Chapter pages, named by slug, with inline SVG figures
│   └── notebooks/
│       ├── <slug>.ipynb        # Companion notebooks, saved with their outputs
│       └── html/               # The rendered notebooks that "View notebook" opens
├── templates/chapter.html      # The chapter skeleton every new chapter starts from (not linked)
├── data/                       # The datasets, all written for the book
├── assets/                     # css/, js/ and img/
├── scripts/                    # Chapter numbering, notebook cards, link checks, rendering, the sitemap, recordings
├── tests/                      # Tests of the replay helper, and the SDK version the notebooks pin
├── requirements.txt            # The libraries the notebooks import, for running them outside Colab
└── .github/workflows/          # deploy.yml publishes, check-links.yml checks links, tests.yml tests the helper
```

Chapter numbers are computed from the order of `PARTS` in `toc.html`, so inserting a chapter renumbers
every chapter after it. `python3 scripts/apply_chapter_nav.py` then re-stamps the numbers on every page,
and `--check` reports drift without changing anything.

## Local preview

Open `index.html` in a browser, or serve the folder with `python3 -m http.server` and open
http://localhost:8000/. To render a notebook after editing it:

```bash
pip install nbconvert==7.17.2
python3 -m nbconvert --to html --template lab --output-dir chapters/notebooks/html chapters/notebooks/<slug>.ipynb
python3 scripts/inject_notebook_backlinks.py
```

The last step adds what rendering leaves out: the card with the way back to the chapter, the buttons to
open the notebook in Colab, download it or view it on GitHub, the tab title and link tags, and the styles
that keep the page readable. A new notebook needs an entry in that script's `MAP` first.
`bash scripts/build_notebook_html.sh` renders every notebook the same way. The deploy renders with
nbconvert and the libraries that shape its output pinned in `.github/workflows/deploy.yml`, and with no
IPython installed, so render with the same versions for the committed page to match. Rendering doesn't run
the code, so a notebook shows the outputs saved in it.

## Checking links

```bash
python3 scripts/check_links.py              # local and self-referencing links
python3 scripts/check_links.py --external   # also HTTP-check outside hosts
```

It resolves every `href` and `src` in every page: relative paths, in-page anchors, and the Colab,
`github.com/blob` and Pages addresses that point back into this repository, which it checks against the
local files with no network call. A broken Colab button is otherwise invisible, because the chapter page
loads and the notebook fails only when a reader clicks it. It also checks the card table in
`scripts/inject_notebook_backlinks.py`. `.github/workflows/check-links.yml` runs it on every push.

## Publishing

Every push to `main` runs `.github/workflows/deploy.yml`, which renders the notebooks the push changed,
adds each rendered page's card and publishes the repository to GitHub Pages in a few minutes. It never
runs a notebook, so a notebook's page shows the outputs saved in the `.ipynb`.

To add a chapter:

1. Copy `templates/chapter.html` to `chapters/<slug>.html`. A slug is made of words, never numbers or
   dates, and never changes once published.
2. Add the chapter to `PARTS` in `toc.html` where it belongs, and its slug to `AVAILABLE` to publish it. A
   chapter's title lives in the `PARTS` entry, the page's `<title>`, its `<h1>`, its link-preview tags, its
   neighbors' previous and next cards and the notebook card table, so change them together.
3. Run `python3 scripts/apply_chapter_nav.py` to re-stamp chapter numbers, and set the previous and next
   cards on the chapter and its two neighbors by hand.
4. Build and run the notebook, `chapters/notebooks/<slug>.ipynb`, so its outputs are saved, then render it
   and add its entry to the card table as above. Commit the rendered page with the notebook.
5. Run `python3 scripts/build_sitemap.py` and `python3 scripts/check_links.py`, then commit and push.

The book's `CLAUDE.md` is the technical manual for the Claude Code sessions that write and publish it.

---

## License

**The book, the figures and the datasets: [CC BY 4.0](LICENSE). The code: [MIT](LICENSE-CODE).**

Use any of it, including commercially, with credit. Teach from it, translate it, quote it, build on it. A
reasonable credit:

> John Fisher, *Building AI with AI: A Visual Handbook*.
> https://johnfisher-ai.github.io/ai-with-ai/

See **[LICENSES.md](LICENSES.md)** for which license covers which files. Every dataset in `data/` is
written for this book and describes no real organization or person; see [data/README.md](data/README.md).

© 2026 John Fisher.
