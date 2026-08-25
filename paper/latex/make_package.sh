#!/usr/bin/env bash
# Assemble a self-contained directory for Overleaf upload.
#
# The .tex sources reference ../figures/pdf/, which does not exist once this
# directory is uploaded on its own, so the PDFs are copied in. They are not
# committed twice: figures/ here is gitignored.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p figures
cp ../figures/pdf/*.pdf figures/
echo "copied $(ls figures/*.pdf | wc -l) figure PDFs into $(pwd)/figures"
echo
echo "Upload to Overleaf:"
echo "  zip -r escapement.zip main.tex refs.bib sections figures"
echo "  then New Project > Upload Project, and set the compiler to pdfLaTeX."
