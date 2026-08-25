#!/usr/bin/env python3
"""Check the draft against CLAIMS.md, and collect what is still missing.

Three things the writing rules ask for are mechanical, so they are checked
mechanically rather than by rereading:

  1. every ``<!-- CLAIMS x.y -->`` cites an id that exists in CLAIMS.md,
  2. every claim in CLAIMS.md is cited somewhere (an uncited claim is either
     dead weight in the table or a gap in the draft),
  3. every ``[NEEDS-EVIDENCE]`` is listed with its section and its note.

    env -u PYTHONPATH python3 paper/draft/check_claims.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLAIMS = HERE.parent / "CLAIMS.md"
CLAIM_RE = re.compile(r"^\| (\d+\.\d+) \|", re.M)
CITE_RE = re.compile(r"CLAIMS ([\d.,\s–-]+?)-->")
NEED_RE = re.compile(r"<!--\s*NEEDS-EVIDENCE:\s*(.+?)\s*-->", re.S)


def main() -> int:
    claims = set(CLAIM_RE.findall(CLAIMS.read_text()))
    used: dict[str, set[str]] = {}
    needs: list[tuple[str, str]] = []
    for f in sorted(HERE.glob("[0-9]*.md")):
        text = f.read_text()
        for m in CITE_RE.finditer(text):
            for cid in re.findall(r"\d+\.\d+", m.group(1)):
                used.setdefault(cid, set()).add(f.name)
        for m in NEED_RE.finditer(text):
            needs.append((f.name, " ".join(m.group(1).split())))

    key = lambda c: tuple(int(x) for x in c.split("."))  # noqa: E731
    missing = sorted(set(used) - claims, key=key)
    uncited = sorted(claims - set(used), key=key)

    print(f"CLAIMS.md 항목 {len(claims)}개, 본문이 인용한 항목 {len(used)}개")
    print(f"  존재하지 않는 id 인용: {missing or '없음'}")
    print(f"  인용되지 않은 주장   : {uncited or '없음'}")
    print(f"  [NEEDS-EVIDENCE]     : {len(needs)}건")
    for where, what in needs:
        print(f"    - {where}: {what[:88]}")
    return 1 if (missing or uncited) else 0


if __name__ == "__main__":
    raise SystemExit(main())
