#!/usr/bin/env python3
"""Audit of three loose ends behind the paper's KV-survival section.

Definitions are fixed in docs/research/LAYER_AUDIT_PLAN.md, committed before
any of this ran. Nothing here re-adjudicates a past verdict: the cliff, its
reproduction, and the capacity intervention keep the numbers their own tasks
printed. This recomputes from the stored logs and rows so that three specific
questions can be answered from evidence rather than from recollection.

  §2  The eviction count came out one higher than "allocations minus pool" in
      every trial that evicted at all, and that gap has been UNKNOWN since it
      was first seen. The per-trial [PFX] event stream is replayed here in
      file order, outer-block ids are tagged with an allocation generation so
      a reused id is never read as one surviving KV, and each eviction is
      checked for whether an allocation followed it.

  §3  The capacity intervention's paper table, recomputed from the client rows
      and the stored step histograms. Per-request values come from the
      response rows only -- never from a difference of cumulative counters,
      which under concurrency mixes in other requests' work.

Run with --run-dir overrides to point at other stored runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PFX_RE = re.compile(r"\[PFX\] \[([A-Z-]+)\](.*)")
OB_ALLOC_RE = re.compile(r"OB_COUNT=(\d+) OB=\[([^\]]*)\]")
REQ_RE = re.compile(r"REQUEST=(\S+)")
EVICT_OB_RE = re.compile(r"OB=(\d+)")
FREE_AFTER_RE = re.compile(r"FREE_BLOCKS_AFTER=(\d+)")
MATCHED_RE = re.compile(r"MATCHED_OB=(\S+)")

#: TASK14 source reading; also derivable from the artifact config.
POOL_OB = 8


# --------------------------------------------------------------- §2 helpers
def events(log: Path) -> list[dict]:
    """[PFX] lines in file order, with an allocation generation per OB id."""
    gen: dict[int, int] = {}
    out: list[dict] = []
    for line in log.read_text(errors="replace").splitlines():
        m = PFX_RE.search(line)
        if not m:
            continue
        kind, rest = m.group(1), m.group(2)
        e: dict = {"kind": kind, "obs": [], "req": None, "raw": rest.strip()}
        r = REQ_RE.search(rest)
        if r:
            e["req"] = r.group(1)
        if kind == "ALLOC":
            a = OB_ALLOC_RE.search(rest)
            if a and a.group(2).strip():
                ids = [int(x) for x in a.group(2).split(",")]
                for ob in ids:
                    gen[ob] = gen.get(ob, 0) + 1
                e["obs"] = [(ob, gen[ob]) for ob in ids]
        elif kind in ("EVICTION", "MAPPING-REMOVE"):
            a = EVICT_OB_RE.search(rest)
            if a:
                ob = int(a.group(1))
                e["obs"] = [(ob, gen.get(ob, 0))]
            f = FREE_AFTER_RE.search(rest)
            if f:
                e["free_after"] = int(f.group(1))
        elif kind in ("CACHE-HIT", "CACHE-PARTIAL"):
            a = re.search(r"OB_COUNT=\d+ OB=\[([^\]]*)\]", rest)
            if a and a.group(1).strip():
                ids = [int(x) for x in a.group(1).split(",")]
                e["obs"] = [(ob, gen.get(ob, 0)) for ob in ids]
        elif kind == "MAPPING-SEARCH":
            a = MATCHED_RE.search(rest)
            if a:
                e["matched"] = a.group(1)
        elif kind == "FREE-REQUEST":
            e["preemption"] = "PREEMPTION=True" in rest
            a = re.search(r"OUTER_BLOCKS=\[([^\]]*)\]", rest)
            if a and a.group(1).strip():
                ids = [int(x) for x in a.group(1).split(",")]
                e["obs"] = [(ob, gen.get(ob, 0)) for ob in ids]
        out.append(e)
    return out


def audit_trial(log: Path, m: int) -> dict:
    ev = events(log)
    allocs = [e for e in ev if e["kind"] == "ALLOC"]
    evicts = [e for e in ev if e["kind"] == "EVICTION"]
    frees = [e for e in ev if e["kind"] == "FREE-REQUEST"]
    # The target KV is the first allocation's outer block, that generation.
    target = allocs[0]["obs"][0] if allocs and allocs[0]["obs"] else None

    # Was an ALLOC emitted after each eviction? An eviction whose freed block
    # is never allocated afterwards cannot have been made room for a request.
    idx = {id(e): i for i, e in enumerate(ev)}
    per_evict = []
    for e in evicts:
        i = idx[id(e)]
        later_alloc = any(x["kind"] == "ALLOC" for x in ev[i + 1:])
        freed = e["obs"][0][0] if e["obs"] else None
        realloc = any(x["kind"] == "ALLOC" and any(o[0] == freed for o in x["obs"])
                      for x in ev[i + 1:])
        per_evict.append({"ob": e["obs"][0] if e["obs"] else None,
                          "free_after": e.get("free_after"),
                          "alloc_follows": later_alloc,
                          "freed_block_reallocated": realloc})

    # Target-KV timeline: every event naming that (ob, generation).
    timeline = []
    for i, e in enumerate(ev):
        if target and any(o == target for o in e["obs"]):
            timeline.append({"i": i, "kind": e["kind"],
                             "req": e["req"], "free_after": e.get("free_after")})
    search = [e for e in ev if e["kind"] == "MAPPING-SEARCH"]
    hit = [e for e in ev if e["kind"] == "CACHE-HIT"]
    partial = [e for e in ev if e["kind"] == "CACHE-PARTIAL"]

    n_alloc = len(allocs)
    return {
        "m": m, "log": log.name,
        "n_alloc": n_alloc, "n_evict": len(evicts), "n_free": len(frees),
        "preemption_any": any(f.get("preemption") for f in frees),
        "target": target,
        "arith_alloc_only": max(0, n_alloc - POOL_OB),
        "arith_with_dummy": max(0, n_alloc + 1 - POOL_OB),
        "evicts": per_evict,
        "evicts_without_later_alloc": sum(1 for p in per_evict if not p["alloc_follows"]),
        "evicts_freed_block_never_realloc": sum(
            1 for p in per_evict if not p["freed_block_reallocated"]),
        "target_timeline": timeline,
        "search_matched": [e.get("matched") for e in search],
        "hit_obs": [e["obs"] for e in hit],
        "partial": len(partial),
        "order": [e["kind"] for e in ev],
    }


# --------------------------------------------------------------- §3 helpers
def rows_of(run: Path, arm: str, n: int, blk: int) -> list[dict]:
    p = run / "probe" / f"requests.{arm}.n{n}.b{blk}.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def plan_hash(run: Path, arm: str, n: int, blk: int) -> tuple[str, float]:
    meta = json.loads((run / "probe" / f"meta.{arm}.n{n}.b{blk}.json").read_text())
    h = hashlib.sha256(json.dumps(meta["plan"], sort_keys=True,
                                  separators=(",", ":")).encode()).hexdigest()
    return h, meta["total_gap_s"]


def cell(run: Path, arm: str, n: int, blk: int) -> dict:
    rows = rows_of(run, arm, n, blk)
    util = json.loads((run / f"util.{arm}.n{n}.b{blk}.json").read_text())
    if not util.get("valid", True):
        raise SystemExit(f"INVALID {arm}.n{n}.b{blk}")
    t2 = [r for r in rows if r["turn"] > 0]
    by_bucket: dict[int, int] = {}
    max_actual = 0
    for key, c in util["pair_histogram"].items():
        a, b = (int(x) for x in key.split("->"))
        by_bucket[b] = by_bucket.get(b, 0) + c
        max_actual = max(max_actual, a)
    h, gap = plan_hash(run, arm, n, blk)
    return {
        "arm": arm, "block": blk,
        "resume_requests": len(t2),
        "reuse_hits": sum(1 for r in t2 if (r.get("cached_tokens") or 0) > 0),
        "cached_tokens": sum(r.get("cached_tokens") or 0 for r in t2),
        "prefill_computed_all": sum((r["prompt_tokens"] or 0) - (r.get("cached_tokens") or 0)
                                    for r in rows),
        "prefill_computed_resume": sum((r["prompt_tokens"] or 0) - (r.get("cached_tokens") or 0)
                                       for r in t2),
        "steps_by_bucket": dict(sorted(by_bucket.items())),
        "decode_steps": util["decode_steps"],
        "max_actual_batch": max_actual,
        "plan_sha256": h, "total_gap_s": gap,
        "requested_segment": [r["requested_segment_tokens"] for r in
                              sorted(rows, key=lambda x: (x["session_index"], x["turn"]))],
        "requested_generation": [r["requested_generation_tokens"] for r in
                                 sorted(rows, key=lambda x: (x["session_index"], x["turn"]))],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("/home/rebel/continuum-npu"))
    ap.add_argument("--pilot", type=Path,
                    default=Path("results/npu/stage2/20260819-200800-gap-turnover"))
    ap.add_argument("--repro", type=Path,
                    default=Path("results/npu/stage2/20260819-204900-cliff-repro"))
    ap.add_argument("--capacity", type=Path,
                    default=Path("results/npu/stage2/20260823-183505-final-confirm"))
    ap.add_argument("--sessions", type=int, default=8)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    import os
    os.chdir(args.repo)
    out: dict = {}

    # ------------------------------------------------------------------ §2
    print("=" * 96)
    print("§2  회수 사건 감사 — [PFX] 이벤트를 파일 등장 순서로 재생")
    print("=" * 96)
    trials = []
    for m in (0, 3, 6, 7, 8, 9, 16, 33, 49):
        p = args.pilot / f"server-B{m}.log"
        if p.exists():
            trials.append(audit_trial(p, m))
    for m in (5, 6, 7, 8):
        for r in range(3):
            p = args.repro / f"server-B{m}r{r}.log"
            if p.exists():
                trials.append(audit_trial(p, m))
    out["evictions"] = trials

    print(f"{'log':<14}{'m':>3}{'ALLOC':>7}{'EVICT':>7}{'FREE':>6}"
          f"{'alloc−8':>9}{'alloc+1−8':>11}{'선점':>6}{'후속ALLOC없음':>15}{'회수블록 미재할당':>18}")
    ok_a = ok_d = 0
    for t in trials:
        ok_a += t["n_evict"] == t["arith_alloc_only"]
        ok_d += t["n_evict"] == t["arith_with_dummy"]
        print(f"{t['log']:<14}{t['m']:>3}{t['n_alloc']:>7}{t['n_evict']:>7}{t['n_free']:>6}"
              f"{t['arith_alloc_only']:>9}{t['arith_with_dummy']:>11}"
              f"{str(t['preemption_any']):>6}{t['evicts_without_later_alloc']:>15}"
              f"{t['evicts_freed_block_never_realloc']:>18}")
    print(f"\n  회수 건수 = max(0, ALLOC − 8)          와 일치: {ok_a}/{len(trials)}")
    print(f"  회수 건수 = max(0, ALLOC + 1 − 8)      와 일치: {ok_d}/{len(trials)}")
    print(f"  FREE-REQUEST의 PREEMPTION=True: {sum(t['preemption_any'] for t in trials)}/{len(trials)}"
          f"  → 선점 경로의 회수는 0건")

    for m in (6, 7):
        t = next(x for x in trials if x["m"] == m and x["log"].startswith("server-B"))
        print()
        print(f"  ── m={m} 대상 KV(OB{t['target'][0]}#{t['target'][1]}) 사건 순서 "
              f"[{t['log']}]")
        print(f"     {'#':>4}{'사건':<18}{'free_after':>11}")
        for e in t["target_timeline"]:
            print(f"     {e['i']:>4}{e['kind']:<18}"
                  f"{'' if e['free_after'] is None else e['free_after']:>11}")
        print(f"     MAPPING-SEARCH MATCHED_OB={t['search_matched']}  "
              f"CACHE-HIT OB={t['hit_obs']}  CACHE-PARTIAL {t['partial']}건")

    # ------------------------------------------------------------------ §3
    print()
    print("=" * 96)
    print(f"§3  용량 개입 — N={args.sessions}, BASE → BATCHONLY (반복별)")
    print("=" * 96)
    cells = [cell(args.capacity, arm, args.sessions, b)
             for arm in ("BASE", "BATCHONLY") for b in range(3)]
    out["capacity"] = cells
    print(f"{'구성':<11}{'반복':>4}{'재도착':>7}{'재사용':>7}{'cached tok':>12}"
          f"{'prefill 계산(전체)':>19}{'(재도착)':>11}{'최대 batch':>11}{'step':>7}")
    for c in cells:
        print(f"{c['arm']:<11}{c['block']:>4}{c['resume_requests']:>7}{c['reuse_hits']:>7}"
              f"{c['cached_tokens']:>12,}{c['prefill_computed_all']:>19,}"
              f"{c['prefill_computed_resume']:>11,}{c['max_actual_batch']:>11}"
              f"{c['decode_steps']:>7}")
    agg = {}
    for arm in ("BASE", "BATCHONLY"):
        cs = [c for c in cells if c["arm"] == arm]
        agg[arm] = {k: sum(c[k] for c in cs) for k in
                    ("resume_requests", "reuse_hits", "cached_tokens",
                     "prefill_computed_all", "prefill_computed_resume", "decode_steps")}
        agg[arm]["steps_by_bucket"] = {}
        for c in cs:
            for b, n in c["steps_by_bucket"].items():
                agg[arm]["steps_by_bucket"][b] = agg[arm]["steps_by_bucket"].get(b, 0) + n
        agg[arm]["max_actual_batch"] = max(c["max_actual_batch"] for c in cs)
    out["capacity_pooled"] = agg
    print()
    for arm in ("BASE", "BATCHONLY"):
        a = agg[arm]
        print(f"  합산 {arm:<11} 재사용 {a['reuse_hits']}/{a['resume_requests']}  "
              f"cached {a['cached_tokens']:,} tok  "
              f"prefill 계산 {a['prefill_computed_all']:,} tok  "
              f"step {a['decode_steps']}  최대 batch {a['max_actual_batch']}")
    print()
    print("  선택 bucket별 step 수 (3반복 합산)")
    buckets = sorted(set(agg["BASE"]["steps_by_bucket"]) | set(agg["BATCHONLY"]["steps_by_bucket"]))
    print(f"    {'구성':<12}" + "".join(f"{('b'+str(b)):>9}" for b in buckets) + f"{'합':>9}")
    for arm in ("BASE", "BATCHONLY"):
        h = agg[arm]["steps_by_bucket"]
        print(f"    {arm:<12}" + "".join(f"{h.get(b, 0):>9}" for b in buckets)
              + f"{sum(h.values()):>9}")
    print(f"    {'BASE 비중':<12}" + "".join(
        f"{100*agg['BASE']['steps_by_bucket'].get(b,0)/sum(agg['BASE']['steps_by_bucket'].values()):>8.1f}%"
        for b in buckets))
    print(f"    {'BATCH 비중':<12}" + "".join(
        f"{100*agg['BATCHONLY']['steps_by_bucket'].get(b,0)/sum(agg['BATCHONLY']['steps_by_bucket'].values()):>8.1f}%"
        for b in buckets))

    print()
    print("  입력 계획 동일성")
    for b in range(3):
        cb = next(c for c in cells if c["arm"] == "BASE" and c["block"] == b)
        cc = next(c for c in cells if c["arm"] == "BATCHONLY" and c["block"] == b)
        same_h = cb["plan_sha256"] == cc["plan_sha256"]
        same_seg = cb["requested_segment"] == cc["requested_segment"]
        same_gen = cb["requested_generation"] == cc["requested_generation"]
        print(f"    b{b}: plan sha256 {'동일' if same_h else '다름'} "
              f"({cb['plan_sha256'][:16]} / {cc['plan_sha256'][:16]})  "
              f"total_gap_s {cb['total_gap_s']:.3f}/{cc['total_gap_s']:.3f}  "
              f"요청 세그먼트 {'동일' if same_seg else '다름'}  "
              f"생성 길이 {'동일' if same_gen else '다름'}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"\n  → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
