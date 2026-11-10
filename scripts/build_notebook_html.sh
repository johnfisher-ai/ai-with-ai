#!/usr/bin/env bash
# Render every chapter notebook to HTML (code + outputs) into chapters/notebooks/html/.
# These rendered pages are what the "View Notebook" buttons link to.
#
# Usage:  bash scripts/build_notebook_html.sh
# Requires: nbconvert at the versions deploy.yml pins, with no IPython (see the README)
set -euo pipefail

cd "$(dirname "$0")/.."          # repo root, which is the site root
SRC="chapters/notebooks"
OUT="chapters/notebooks/html"
mkdir -p "$OUT"

shopt -s nullglob
count=0
for nb in "$SRC"/*.ipynb; do
  name="$(basename "${nb%.ipynb}")"
  echo "Rendering $name ..."
  python3 -m nbconvert --to html --template lab --output-dir "$OUT" --output "$name.html" "$nb"
  count=$((count+1))
done

# Add the styled "Back to the book" card to each rendered HTML page
python3 "$(dirname "$0")/inject_notebook_backlinks.py"

echo "Done. Rendered $count notebook(s) to $OUT/"
