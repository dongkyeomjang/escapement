#!/usr/bin/env python3
"""G-10 C post-hoc diagnosis: GTASK12 event replay (multiturn/replay.py, unchanged)
on the 20 judged C lifecycles. Separates rule mismatch (replay of the observed
admission sequence disagrees with the observed hit) from event-generation /
timing-input error (replay agrees with the observation, the simulator does not).

usage: replay_c.py --run-dir <abs> --out <abs json> [--jobs N]
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "multiturn"))
import replay as RP  # noqa: E402


def one(run: Path) -> dict:
    r = RP.analyse(run)
    win = [x for x in r["requests"] if x["in_window"]]
    st = Counter(x["status"] for x in win)
    cat = Counter(x.get("category") for x in win if x["status"] == "MISMATCH")
    dec = [x for x in win if x["status"] in ("MATCH", "MISMATCH")]
    return {"run": r["run"], "main_integrity": r["main_integrity"], "main_error": r["main_error"],
            "first_free_divergence_line": r["first_free_divergence_line"], "kv": r["kv"],
            "window_status": dict(st), "mismatch_category": dict(cat),
            "window_obs_hit_rate": sum(1 for x in dec if x["obs"] > 0) / len(dec) if dec else None,
            "window_replay_hit_rate": sum(1 for x in dec if x["pred"] > 0) / len(dec) if dec else None,
            "decided": len(dec)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--jobs", type=int, default=20)
    a = ap.parse_args()
    runs = sorted(d for d in a.run_dir.iterdir()
                  if d.is_dir() and (d / "windows.json").exists() and not d.name.endswith(".retry1"))
    with ProcessPoolExecutor(a.jobs) as ex:
        res = list(ex.map(one, runs))
    a.out.write_text(json.dumps({"lifecycles": res}, indent=1, default=str) + "\n")
    for x in res:
        print(x["run"], x["window_status"], x["mismatch_category"], x["decided"],
              x["window_obs_hit_rate"] and round(x["window_obs_hit_rate"], 4),
              x["window_replay_hit_rate"] and round(x["window_replay_hit_rate"], 4), x["main_error"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
