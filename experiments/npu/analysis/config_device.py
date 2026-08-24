#!/usr/bin/env python3
"""Device-time effect of a compile configuration, on two channels.

Channel A' reconstructs device time from two measured cost models: the
``[BUCKET]`` step trace priced by TASK13's decode step cost, plus each
request's actually computed prefill tokens priced by TASK22's
``PrefillCostModel``. TASK34 learned the hard way that a decode-only channel
misses the whole effect of a configuration whose lever is cache survival, so
the prefill term is part of the channel and not an afterthought.

Channel B is the union of the intervals in which at least one request was in
flight, taken from the client's own send/finish stamps. It depends on no cost
model at all.

The two share nothing but the run. What channel B has and channel A' cannot
have is the queueing, HTTP and scheduler overhead that no cost model of the
device describes; call that residual ``r = B - A'``. TASK35 measured it at a
roughly N-independent 1.2-1.7 s, which is a few percent of a large run and
6.1 % of a small one -- and a ratio requirement stated as a fixed 0.02 band is
therefore structurally harder to meet at small N, which is what put TASK35's
N=6 cells on hold.

This module states the tolerance so that it carries that residual explicitly:

    tau(N) = max(0.02, r_BASE / B_BASE)

``r_BASE / B_BASE`` is an upper bound on the channel gap that a residual lying
anywhere in ``[0, r_BASE]`` can induce, whatever it does between arms. Writing
out the two extremes, with ``q = A'_arm / A'_BASE``:

    r_arm = 0       ->  |A'ratio - Bratio| = q * r_BASE / B_BASE
    r_arm = r_BASE  ->  |A'ratio - Bratio| = (1 - q) * r_BASE / B_BASE

both of which are at most ``r_BASE / B_BASE`` for ``0 <= q <= 1``. The 0.02
floor keeps the tolerance from collapsing on a run whose residual is tiny.

Whether ``r_arm`` actually lies in ``[0, r_BASE]`` is reported per cell as a
diagnostic. It is not a gate: gating on it would be a post-hoc tightening of
what the preregistration fixed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "substrate"))

from config_search import descriptor_for  # noqa: E402

#: Arm label -> (compiled bucket set, compile batch_size). The batch size is
#: also the scheduler's admission ceiling, because TASK08 established
#: kvcache_num_blocks = batch_size for eager attention.
ARMS: dict[str, tuple[tuple[int, ...], int]] = {
    "BASE": ((1, 2, 4, 8), 8),
    "BATCHONLY": ((1, 2, 4, 8, 16), 16),
    "TUNED": ((1, 4, 6, 8, 10, 16), 16),
}

CHANNEL_FLOOR = 0.02


def load_cell(run: Path, label: str) -> tuple[dict, list[dict]]:
    util = json.loads((run / f"util.{label}.json").read_text())
    if not util.get("valid", True):
        raise SystemExit(f"INVALID {label}: {util['invariant_violations']}")
    rows = [json.loads(l) for l in
            (run / "probe" / f"requests.{label}.jsonl").read_text().splitlines()
            if l.strip()]
    return util, rows


def channel_a_prime(util: dict, rows: list[dict], descriptor) -> tuple[float, float, float]:
    """(total_s, decode_s, prefill_s) from the two measured cost models."""
    decode = 0.0
    for key, count in util["pair_histogram"].items():
        actual, bucket = (int(x) for x in key.split("->"))
        decode += descriptor.step_cost_model.step_time_s(bucket=bucket, actual=actual) * count
    pm = descriptor.prefill_cost_model
    prefill = sum(
        pm.prefill_s(max((r.get("prompt_tokens") or 0) - (r.get("cached_tokens") or 0), 0))
        for r in rows
    )
    return decode + prefill, decode, prefill


def channel_b(rows: list[dict]) -> float:
    """Union of the in-flight intervals: elapsed time with the tool gaps out."""
    spans = sorted((r["sent_s"], r["done_s"]) for r in rows
                   if r.get("sent_s") is not None and r.get("done_s") is not None)
    total = 0.0
    cur_start = cur_end = None
    for s, e in spans:
        if cur_start is None:
            cur_start, cur_end = s, e
        elif s <= cur_end:
            cur_end = max(cur_end, e)
        else:
            total += cur_end - cur_start
            cur_start, cur_end = s, e
    if cur_start is not None:
        total += cur_end - cur_start
    return total


def aggregate(run: Path, arm: str, n: int, blocks: list[int]) -> dict:
    buckets, batch = ARMS[arm]
    d = descriptor_for_arm(arm)
    tot = dec = pre = b_tot = 0.0
    reuse = resume = 0
    per_block = []
    for blk in blocks:
        util, rows = load_cell(run, f"{arm}.n{n}.b{blk}")
        a, ad, ap = channel_a_prime(util, rows, d)
        b = channel_b(rows)
        turn2 = [r for r in rows if r["turn"] > 0]
        tot += a; dec += ad; pre += ap; b_tot += b
        reuse += sum(1 for r in turn2 if (r.get("cached_tokens") or 0) > 0)
        resume += len(turn2)
        per_block.append({"block": blk, "a_prime_s": a, "decode_s": ad,
                          "prefill_s": ap, "b_s": b})
    return {"arm": arm, "buckets": list(buckets), "batch_size": batch,
            "a_prime_s": tot, "decode_s": dec, "prefill_s": pre, "b_s": b_tot,
            "residual_s": b_tot - tot, "reuse": reuse, "resume": resume,
            "per_block": per_block}


def descriptor_for_arm(arm: str):
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D
    buckets, batch = ARMS[arm]
    return descriptor_for(D, buckets, batch)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--baseline-arm", default="BASE")
    p.add_argument("--arms", default="BATCHONLY,TUNED")
    p.add_argument("--sessions", default="6")
    p.add_argument("--blocks", default="0,1,2")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    blocks = [int(x) for x in args.blocks.split(",")]
    arms = args.arms.split(",")
    out = []
    for n in (int(x) for x in args.sessions.split(",")):
        base = aggregate(args.run, args.baseline_arm, n, blocks)
        tol = max(CHANNEL_FLOOR, base["residual_s"] / base["b_s"])
        print(f"\nN={n}  {args.baseline_arm}: A'={base['a_prime_s']:.3f} s "
              f"(decode {base['decode_s']:.3f} + prefill {base['prefill_s']:.3f}), "
              f"B={base['b_s']:.3f} s")
        print(f"      절대 잔차 r_BASE = {base['residual_s']:.3f} s "
              f"({100 * base['residual_s'] / base['b_s']:.1f} % of B) "
              f"→ 채널 허용차 tau = {tol:.4f}")
        row = {"N": n, "blocks": blocks, "baseline": base,
               "channel_tolerance": tol,
               "residual_share": base["residual_s"] / base["b_s"], "arms": []}
        for arm in arms:
            a = aggregate(args.run, arm, n, blocks)
            ra = a["a_prime_s"] / base["a_prime_s"]
            rb = a["b_s"] / base["b_s"]
            gap = abs(ra - rb)
            inside = 0.0 <= a["residual_s"] <= base["residual_s"]
            a.update({"a_prime_ratio": ra, "b_ratio": rb, "channel_gap": gap,
                      "channel_pass": gap <= tol,
                      "channel_pass_fixed_002": gap <= CHANNEL_FLOOR,
                      "residual_in_range": inside,
                      "prefill_ratio": a["prefill_s"] / base["prefill_s"],
                      "decode_ratio": a["decode_s"] / base["decode_s"],
                      "X_a_prime": 1.0 - ra, "X_b": 1.0 - rb})
            row["arms"].append(a)
            print(f"      {arm:<10} A′ {ra:.4f}  B {rb:.4f}  차 {gap:.4f} "
                  f"{'통과' if gap <= tol else '보류'}"
                  f" (고정 0.02 기준 {'통과' if gap <= CHANNEL_FLOOR else '보류'})"
                  f"  prefill비 {a['prefill_ratio']:.4f}  decode비 {a['decode_ratio']:.4f}"
                  f"  r_arm {a['residual_s']:.3f} s {'∈' if inside else '∉'} [0, r_BASE]"
                  f"  재사용 {a['reuse']}/{a['resume']}")
        out.append(row)
    if args.output:
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
