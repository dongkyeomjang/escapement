#!/usr/bin/env python3
"""G-05 task D (report only): where the direct-dispatch vs price-channel gap
comes from, from the existing ``[GSTEP]`` lines (obs_dynamics output).

Two attributions of a step's time: lag 0 (gap to the next dispatch, the
GTASK11 direct channel, capped at 2 * price_hi + 5 ms) and lag 1 (gap after
the next dispatch; async scheduling dispatches one step ahead, GTASK05).
Excess = attributed time - price_lo, split by step class, decode width,
waiting-queue length; idle fragments = lag-1 gaps above the cap.

usage: channel_report.py --obs <abs obs.json> --out <abs json>
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from step_classes import step_class  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--obs", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    obs = json.loads(a.obs.read_text())
    tot = defaultdict(float)
    by_cls = defaultdict(lambda: defaultdict(float))
    by_d = defaultdict(lambda: defaultdict(list))
    by_q = defaultdict(list)
    idle_frag = []
    per_life = []
    for L in obs:
        st, ql = L["steps"], L["queue_len"]
        lt = defaultdict(float)
        for i, s in enumerate(st):
            if i + 1 >= len(st) or st[i + 1]["dt"] is None or s["dt"] is None:
                continue
            x0 = min(s["dt"], s["cap"])
            x1 = st[i + 1]["dt"]
            c = step_class(s["mode"], s["d"], s["p"])
            for k, v in (("price", s["lo"]), ("lag0_capped", x0), ("lag1", x1),
                         ("lag1_capped", min(x1, s["cap"]))):
                tot[k] += v
                lt[k] += v
                by_cls[c][k] += v
            by_cls[c]["n"] += 1
            if x1 > s["cap"]:
                idle_frag.append(x1 - s["cap"])
            if c == "DEC_FULL":
                by_d[s["d"]]["ratio"].append(x1 / s["lo"])
                by_q[min(ql[i], 12)].append(x1 / s["lo"])
        per_life.append({"run": L["run"], "lag0_capped_over_price": lt["lag0_capped"] / lt["price"],
                         "lag1_over_price": lt["lag1"] / lt["price"]})
    ex1 = tot["lag1"] - tot["price"]
    out = {
        "total": {k: v for k, v in tot.items()},
        "lag0_capped_over_price": tot["lag0_capped"] / tot["price"],
        "lag1_over_price": tot["lag1"] / tot["price"],
        "lifecycle_median": {
            "lag0_capped": statistics.median(x["lag0_capped_over_price"] for x in per_life),
            "lag1": statistics.median(x["lag1_over_price"] for x in per_life)},
        "idle_fragments": {"count": len(idle_frag), "sum_ms": sum(idle_frag),
                           "share_of_lag1_excess": sum(idle_frag) / ex1},
        "by_class": {c: {"n": int(v["n"]), "price_s": v["price"] / 1e3,
                         "lag1_over_price": v["lag1"] / v["price"],
                         "lag0_capped_over_price": v["lag0_capped"] / v["price"],
                         "share_of_lag1_excess": (v["lag1"] - v["price"]) / ex1,
                         "share_of_lag0_excess": (v["lag0_capped"] - v["price"])
                         / (tot["lag0_capped"] - tot["price"])}
                     for c, v in by_cls.items()},
        "dec_full_by_width": {d: {"n": len(v["ratio"]), "median_ratio": statistics.median(v["ratio"])}
                              for d, v in sorted(by_d.items())},
        "dec_full_by_waiting": {q: {"n": len(v), "median_ratio": statistics.median(v)}
                                for q, v in sorted(by_q.items())},
        "per_lifecycle": per_life,
    }
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "per_lifecycle"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
