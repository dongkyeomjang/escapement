#!/usr/bin/env bash
# Assemble a self-contained directory for Overleaf upload, and check that the
# package carries nothing internal.
#
# The .tex sources reference ../figures/pdf/, which does not exist once this
# directory is uploaded on its own, so the PDFs are copied in. They are not
# committed twice: figures/ here is gitignored.
#
# arXiv publishes the TeX source, so the package is reader-facing. Internal
# record names (TASK*) must not appear in it; provenance lives in the
# repository (paper/figures/SOURCES.md, docs/research/) and the manuscript
# inherits it by citing the repository. The evidence trail that *does* ship is
# the CLAIMS id comments, which name no internal record.
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p figures
cp ../figures/pdf/*.pdf figures/
echo "copied $(ls figures/*.pdf | wc -l) figure PDFs into $(pwd)/figures"

fail=0

hits=$(grep -rl "TASK" main.tex refs.bib sections 2>/dev/null || true)
if [ -n "$hits" ]; then
  echo "FAIL: internal record names in the package:" >&2
  grep -rn "TASK" main.tex refs.bib sections >&2
  fail=1
else
  echo "ok: no internal record names in main.tex, refs.bib, sections/"
fi

# The figure PDFs are drawn by this project, so their text layer is checked too.
if ! env -u PYTHONPATH python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path("../figures").resolve()))
from verify_figures import pdf_check
bad = []
for f in sorted(Path("figures").glob("*.pdf")):
    _, texts = pdf_check(f)
    bad += [(f.name, t) for t in texts if "TASK" in t]
if bad:
    print("FAIL: internal record names drawn in figures:", bad, file=sys.stderr)
    raise SystemExit(1)
print(f"ok: no internal record names in {len(list(Path('figures').glob('*.pdf')))} figure PDFs")
PY
then fail=1; fi

# A published TeX source is read, not just compiled: non-ASCII in comments is
# internal working text leaking into a reader-facing package.
if LC_ALL=C grep -rlP "[^\x00-\x7F]" main.tex sections refs.bib >/dev/null 2>&1; then
  echo "FAIL: non-ASCII characters in the package:" >&2
  LC_ALL=C grep -rnP "[^\x00-\x7F]" main.tex sections refs.bib >&2
  fail=1
else
  echo "ok: package is ASCII-only"
fi

kept=$(grep -rc "^% CLAIMS" sections 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
echo "ok: $kept CLAIMS id comments retained (the evidence trail that ships)"

[ "$fail" -eq 0 ] || { echo "package check failed" >&2; exit 1; }

echo
echo "Upload to Overleaf:"
echo "  zip -r escapement.zip main.tex refs.bib sections figures"
echo "  then New Project > Upload Project, and set the compiler to pdfLaTeX."
echo
echo "After the first build, confirm the rendered PDF too:"
echo "  pdftotext main.pdf - | grep -c TASK    # expect 0"
