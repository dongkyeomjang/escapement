#!/usr/bin/env python3
"""Freeze TASK97's context-length decode cost (form F1,
``t = f(b) + beta n + c sum_ctx``) as the input of the post-hoc re-prediction
(TASK98): ``plans/main/CTXCOST_SIM.json``, with the source file's SHA256.

BASE and TUNED take their own fit. BATCHONLY (grid 1,2,4,8,16) was not
measured in TASK97; its rule, fixed here before the re-prediction runs: f(b)
from the TUNED fit for b in {1, 4, 8, 16} and from the BASE fit for b = 2;
beta and c = the mean of the BASE and TUNED fits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True, help="ctxcost.json")
    ap.add_argument("--output", type=Path, default=HERE / "plans" / "main" / "CTXCOST_SIM.json")
    a = ap.parse_args()
    raw = a.source.read_bytes()
    src = json.loads(raw)
    arts = {}
    for cfg in ("BASE", "TUNED"):
        f1 = src["artifacts"][cfg]["fits"]["F1"]
        arts[cfg] = {"f_s_by_bucket": {b: v / 1e3 for b, v in f1["f_by_bucket_ms"].items()},
                     "beta_s": f1["beta_ms"] / 1e3, "c_s_per_token": f1["c_ms_per_token"][0] / 1e3,
                     "rule": "TASK97 F1 fit"}
    b, t = arts["BASE"], arts["TUNED"]
    arts["BATCHONLY"] = {"f_s_by_bucket": {"1": t["f_s_by_bucket"]["1"], "2": b["f_s_by_bucket"]["2"],
                                           "4": t["f_s_by_bucket"]["4"], "8": t["f_s_by_bucket"]["8"],
                                           "16": t["f_s_by_bucket"]["16"]},
                         "beta_s": (b["beta_s"] + t["beta_s"]) / 2, "c_s_per_token": (b["c_s_per_token"] + t["c_s_per_token"]) / 2,
                         "rule": "not measured: f(b) TUNED for 1,4,8,16, BASE for 2; beta, c = mean of BASE and TUNED"}
    out = {"origin": "TASK97", "form": "F1", "source": str(a.source), "source_sha256": hashlib.sha256(raw).hexdigest(),
           "artifacts": arts}
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["artifacts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
