#!/usr/bin/env python3
"""GTASK04 blind predictions: sequential survival on the A6000 substrate.

Two independent computations must agree on every trial before anything is
written:

(1) MODEL — ``continuum.model.survival`` (import only, NPU-built model v0/v1
    code): ``sequential_window(..., resume_allocates_first=False)`` +
    ``reusable_tokens(granularity="block")``. The GPU wrapper supplies only
    inputs the model does not derive itself (see ``gpu_inputs``).
(2) REPLAY — ``gpu_pool_replay.GpuPoolReplay``, a block-exact replay of the
    vLLM free queue rules read in GTASK01.

Why (1) applies: on a fresh pool under a strictly sequential protocol, every
block the background requests take comes from the never-used prefix of the
queue until it is exhausted, and only then from T's released blocks (tail
first), because later releases queue behind T. The release-order LRU of the
free queue therefore evicts in exactly the order FIFO-by-allocation would,
with ``d0`` = never-used blocks = ``C - u_T``. Model v1's LRU form
(``lru_block_survival``: ``lost = min(u_T, max(0, N_ev - d0))``) has the same
deterministic core; its Poisson layer does not apply to a fixed request plan.

usage: predict.py --out-dir <abs>   (writes predictions.json, predictions.md)
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuum.model import survival as S  # noqa: E402
from continuum.substrate import HitFormula  # noqa: E402
from gpu_pool_replay import GpuPoolReplay  # noqa: E402

# ---- substrate parameters (GTASK01/02 only) ---------------------------------
NUM_GPU_BLOCKS = 801          # --num-gpu-blocks-override
CAPACITY = NUM_GPU_BLOCKS - 1  # null block (block_pool.py:176)
BLOCK = 16                     # --block-size 16, GTASK02 hit 5/5
BUDGET = 2048                  # --max-num-batched-tokens
HIT = HitFormula(block_tokens=BLOCK, reserve_last_query_token=True)

# ---- protocol (NPU TASK14/15 lengths) ---------------------------------------
TARGET_PROMPT = 2000
BG_GEN = 8
SUFFIX = 8
TARGET_GEN = {"i": 8, "ii": 24}   # (ii) needs >= 17 generated tokens to fill a block
BG_SIZES = (500, 1000, 2000, 4000)
M_GRID = {
    500: (10, 20, 21, 22, 23, 24, 25, 26, 30, 40),
    1000: (5, 10, 11, 12, 13, 14, 20),
    2000: (3, 5, 6, 7, 8, 10),
    4000: (2, 3, 4, 5),
}
REPEATS = {("i", 2000, 6): 3, ("i", 500, 23): 3}   # determinism probes


def gpu_inputs(tokens_prompt: int, generated: int) -> tuple[int, int]:
    """(units occupied, cacheable prefix tokens) of a finished request.

    Wrapper additions (not in src/continuum/model): generated tokens occupy and
    fill KV slots, the last sampled token is never computed (GTASK02 H5), so
    the request ends with ``P + g - 1`` computed tokens.
    """
    computed = tokens_prompt + generated - 1
    return math.ceil(computed / BLOCK), (computed // BLOCK) * BLOCK


def resume_len(cond: str) -> int:
    return TARGET_PROMPT + (TARGET_GEN["ii"] if cond == "ii" else 0) + SUFFIX


def model_prediction(cond: str, bg: int, m: int) -> dict:
    u_t, cacheable_t = gpu_inputs(TARGET_PROMPT, TARGET_GEN[cond])
    u_bg, _ = gpu_inputs(bg, BG_GEN)
    w = S.sequential_window(target_units=u_t, background_units=[u_bg] * m,
                            resume_units=math.ceil(resume_len(cond) / BLOCK),
                            resume_allocates_first=False)
    hit = S.reusable_tokens(hit_formula=HIT, granularity="block", capacity=CAPACITY,
                            window=w, unit_tokens=BLOCK, cached_prefix_tokens=cacheable_t,
                            query_tokens=resume_len(cond))
    overflow = max(0, S.overflow(CAPACITY, w))
    hashed_t = cacheable_t // BLOCK
    lost_hashed = max(0, min(hashed_t, overflow - (u_t - hashed_t)))
    return {"hit": hit, "u_target": u_t, "u_bg": u_bg, "overflow_units": overflow,
            "target_hashed_blocks_evicted": lost_hashed}


def replay_prediction(cond: str, bg: int, m: int) -> dict:
    pool = GpuPoolReplay(NUM_GPU_BLOCKS, BLOCK, BUDGET)
    tgt = [("T", i) for i in range(TARGET_PROMPT)]
    tgen = [("Tg", i) for i in range(TARGET_GEN[cond])]
    pool.run(tgt, tgen)
    for k in range(m):
        pool.run([("B", k, i) for i in range(bg)], [("Bg", k, i) for i in range(BG_GEN)])
    t_keys_evicted = [key for key in pool.evictions if key[0][0] == "T"]
    resume = tgt + (tgen if cond == "ii" else []) + [("S", i) for i in range(SUFFIX)]
    hit_blocks = pool.lookup(resume)
    return {"hit": len(hit_blocks) * BLOCK, "target_hashed_blocks_evicted": len(t_keys_evicted)}


def trial_plan() -> list[dict]:
    """Every trial, in execution order, with its content seed."""
    plan = []
    for cond in ("i", "ii"):
        cells = [(cond, 0, 0)] + [(cond, bg, m) for bg in BG_SIZES for m in M_GRID[bg]]
        for (c, bg, m) in cells:
            for rep in range(REPEATS.get((c, bg, m), 1)):
                plan.append({"cond": c, "bg": bg, "m": m, "rep": rep,
                             "seed": 20261001 + len(plan) * 1000})
    return plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out = Path(a.out_dir)
    if not out.is_absolute():
        raise SystemExit("--out-dir must be absolute")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for t in trial_plan():
        mp = model_prediction(t["cond"], t["bg"], t["m"])
        rp = replay_prediction(t["cond"], t["bg"], t["m"])
        if (mp["hit"], mp["target_hashed_blocks_evicted"]) != (rp["hit"], rp["target_hashed_blocks_evicted"]):
            raise SystemExit(f"MODEL/REPLAY disagree on {t}: {mp} vs {rp}")
        rows.append({**t, "resume_query_tokens": resume_len(t["cond"]),
                     "pred_hit": mp["hit"], "pred_target_blocks_evicted": mp["target_hashed_blocks_evicted"],
                     "u_target": mp["u_target"], "u_bg": mp["u_bg"], "overflow_units": mp["overflow_units"]})
    (out / "predictions.json").write_text(json.dumps({
        "num_gpu_blocks": NUM_GPU_BLOCKS, "capacity": CAPACITY, "block": BLOCK, "budget": BUDGET,
        "target_prompt": TARGET_PROMPT, "target_gen": TARGET_GEN, "bg_gen": BG_GEN, "suffix": SUFFIX,
        "trials": rows}, indent=1))
    lines = ["| cond | bg | m | reps | u_T | u_bg | overflow | T blocks evicted | **pred hit** |",
             "|---|---|---|---|---|---|---|---|---|"]
    seen = set()
    for r in rows:
        k = (r["cond"], r["bg"], r["m"])
        if k in seen:
            continue
        seen.add(k)
        reps = sum(1 for x in rows if (x["cond"], x["bg"], x["m"]) == k)
        lines.append(f"| {r['cond']} | {r['bg']} | {r['m']} | {reps} | {r['u_target']} | {r['u_bg']} | "
                     f"{r['overflow_units']} | {r['pred_target_blocks_evicted']} | **{r['pred_hit']}** |")
    (out / "predictions.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"trials: {len(rows)}; MODEL == REPLAY on all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
