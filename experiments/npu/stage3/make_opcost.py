#!/usr/bin/env python3
"""Freeze TASK92's operational step costs as the simulator input of directive
08 work C (``plans/main/OPCOST_SIM.json``): per artifact, the decode fit
``F[b] + beta n`` and the exclusive-prefill fit ``ceil(c/128)(a + d c)`` from
``stepcost_op_analyze.py``'s output, with that file's SHA256. Nothing else.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True, help="stepcost_op.json")
    ap.add_argument("--output", type=Path, default=HERE / "plans" / "main" / "OPCOST_SIM.json")
    a = ap.parse_args()
    raw = a.source.read_bytes()
    src = json.loads(raw)
    out = {"origin": "TASK92", "source": str(a.source), "source_sha256": hashlib.sha256(raw).hexdigest(),
           "artifacts": {}}
    for cfg, e in src["artifacts"].items():
        if e["prefill"] is None:
            raise SystemExit(f"{cfg}: no prefill fit")
        out["artifacts"][cfg] = {
            "grid": e["grid"], "batch": e["batch"],
            "decode": {"fixed_s_by_bucket": e["decode"]["fixed_s_by_bucket"],
                       "marginal_s_per_request": e["decode"]["marginal_s_per_request"]},
            "prefill": {"chunk_tokens": 128, "per_chunk_s": e["prefill"]["per_chunk_s"],
                        "drift_s_per_token": e["prefill"]["drift_s_per_token"]}}
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["artifacts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
