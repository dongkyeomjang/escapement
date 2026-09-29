#!/usr/bin/env python3
"""Model v1 on the development set: calibration only, no verdict.

The development set is the 1,298 re-arrivals of TASK72 R5' (seven concurrent
runs). v1 was built after looking at them, so nothing computed here is a
validation -- it is reported to show how the approximation behaves, and the
blind test is the multi-turn steady-state experiment. These runs also start
every session at once and send two requests per session, which breaks the
renewal assumption both v0's count laws and v1's Poisson allocation stream
make (TASK72 R5).

Per re-arrival this computes:
* ``exact``    -- the d-rule applied to the logged events (should equal the
                  reference replay: a check, not a prediction);
* ``v1_log``   -- the v1 chain started from the logged state at T's allocation
                  (free slots, older active, older inactive), rates from B2;
* ``v1_ss``    -- the v1 chain in a full pool, initial state from the arrival
                  theorem (what v1 would say knowing only the workload);
* ``v0_bin``, ``v0_poi`` -- v0's probabilistic extension (as in TASK72 R5).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))

import model_v0_retro as R  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.model import survival as S  # noqa: E402
from continuum.model import survival_v1 as V1  # noqa: E402
from continuum.model.reference import FifoReplay  # noqa: E402
from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D  # noqa: E402

BINS = [i / 10 for i in range(11)]


def cell_model(meta: dict, C: int):
    import config_search as CS
    p = meta["plan"]
    n = p["session_count"]
    grid = tuple(meta.get("buckets") or (1, 2, 4, 8))
    if grid[-1] != C:
        grid = tuple(sorted(set(grid) | {C}))
    desc = CS.descriptor_for(D, grid, C)
    gens = [g for s in p["generation_tokens"] for g in s]
    gaps = [s[0] for s in p["gap_after_s"]]
    prompts0 = [s[0] for s in p["new_segment_tokens"]]
    zmean = statistics.mean(gaps)
    if zmean <= 0:
        return None
    ep = statistics.mean(D.prefill_cost_model.prefill_s(q) for q in prompts0)
    w = O.ClosedWorkload(sessions=n, decode_steps_per_request=statistics.mean(gens) - 1,
                         think_mean_s=zmean, prefill_mean_s=ep, max_running=C)
    occ = O.solve_occupancy(w, desc.step_time_s)
    arr = O.arrival_running_distribution(w, desc.step_time_s)
    t_run = desc.step_time_s(max(1, round(occ.mean_running)))
    service = ep + (statistics.mean(gens) - 1) * t_run / occ.phi
    return {"n": n, "desc": desc, "occ": occ, "arr": arr, "t_run": t_run,
            "lam": occ.throughput_per_s * (n - 1) / n, "mu": 1.0 / service,
            "cycle": zmean + occ.mean_response_s, "plan": p}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=REPO / "results/npu/stage3/model_v1_dev")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    recs = []
    for task, run in R.R5_RUNS:
        for tag, rows, server, meta_p in R._cells(run):
            meta = json.load(open(meta_p))
            C = R._capacity(meta)
            ev = R.parse_log(server)
            allocs = [e for e in ev if e[0] == "alloc"]
            sid_of = {}
            for a in allocs:
                sid_of.setdefault(a[1].rsplit("-", 2)[0], a[1])
            sess = {}
            joined = {}
            for r in rows:
                sid = sid_of.get(r["request_id"])
                if sid is not None:
                    sess[sid] = r["session"]
                    joined[(r["session"], r["turn"])] = sid
            ref = [("alloc", e[1]) if e[0] == "alloc" else ("free", e[1]) if e[0] == "free"
                   else ("decode", e[1]) if e[0] == "bucket" else ("skip",) for e in ev]
            rp = FifoReplay(capacity=C, ceiling=C).run(ref, session_of=lambda k: sess.get(k, k))
            cm = cell_model(meta, C)
            p = meta["plan"]
            idx = {s: i for i, s in enumerate(sorted({r["session"] for r in rows}))}
            for r in rows:
                if r["turn"] < 1:
                    continue
                rid = joined.get((r["session"], r["turn"]))
                t_key = joined.get((r["session"], r["turn"] - 1))
                if rid is None or t_key is None:
                    continue
                obs = (r["cached_tokens"] or 0) > 0
                t_pos = rp.lookups[t_key].pos
                r_pos = rp.lookups[rid].pos
                f0, a0, d0 = rp.lookups[t_key].state_at_alloc
                older = {e[1] for e in ref[:t_pos] if e[0] == "alloc"}
                seq = []
                for i in range(t_pos + 1, r_pos + 1):
                    for x in rp.evictions:
                        if x.pos == i:
                            seq.append("evict")
                    e = ref[i]
                    if e[0] == "free" and e[1] == t_key:
                        seq.append("target_release")
                    elif e[0] == "free" and e[1] in older:
                        seq.append("older_release")
                exact = V1.track_target(f0=f0, a0=a0, d0=d0, events=seq)
                rec = {"run": task, "cell": tag, "session": r["session"], "obs": obs,
                       "exact": exact, "f0": f0, "a0": a0, "d0": d0}
                if cm is not None:
                    si = r["session_index"] if "session_index" in r else idx[r["session"]]
                    prompt0 = p["new_segment_tokens"][si][0]
                    gen0 = p["generation_tokens"][si][0]
                    gap = p["gap_after_s"][si][0]
                    s_act = D.prefill_cost_model.prefill_s(prompt0) + \
                        (gen0 - 1) * cm["t_run"] / cm["occ"].phi
                    rec["v1_log"] = V1.survival_probability_v1(V1.V1Inputs(
                        capacity=C, f0=f0, a0=a0, d0=d0, lam=cm["lam"], mu=cm["mu"],
                        s_active=s_act, s_idle=gap))
                    rec["v1_ss"] = V1.steady_state_survival(
                        capacity=C, running_others_pmf=cm["arr"], lam=cm["lam"], mu=cm["mu"],
                        s_active=s_act, idle_samples=[(gap, 1.0)])
                    win = S.fifo_window_samples(residence_s=s_act, gap_samples=[(gap, 1.0)])
                    for law, key in (("binomial", "v0_bin"), ("poisson", "v0_poi")):
                        rec[key] = S.survival_probability(
                            capacity=C, target_units=1, resume_units=1, other_unit=1,
                            other_sessions=cm["n"] - 1, window_samples=win,
                            cycle_s=cm["cycle"], law=law)
                recs.append(rec)

    out = {"n_requests": len(recs),
           "exact_agree": sum(r["exact"] == r["obs"] for r in recs),
           "models": {}}
    scored = [r for r in recs if "v1_log" in r]
    out["n_scored"] = len(scored)
    out["n_unscored_zero_gap"] = len(recs) - len(scored)
    for key in ("v1_log", "v1_ss", "v0_bin", "v0_poi"):
        brier = statistics.mean((r[key] - r["obs"]) ** 2 for r in scored)
        bins = []
        for lo, hi in zip(BINS[:-1], BINS[1:]):
            sel = [r for r in scored if lo <= r[key] < hi or (hi == 1.0 and r[key] == 1.0)]
            bins.append({"lo": lo, "hi": hi, "n": len(sel),
                         "mean_pred": statistics.mean(r[key] for r in sel) if sel else None,
                         "obs_rate": statistics.mean(r["obs"] for r in sel) if sel else None})
        per_run = defaultdict(list)
        for r in scored:
            per_run[r["run"]].append(r)
        out["models"][key] = {
            "brier": brier, "bins": bins,
            "sum_pred": sum(r[key] for r in scored), "sum_obs": sum(r["obs"] for r in scored),
            "per_run": {k: {"n": len(v), "sum_pred": sum(r[key] for r in v),
                            "sum_obs": sum(r["obs"] for r in v),
                            "brier": statistics.mean((r[key] - r["obs"]) ** 2 for r in v)}
                        for k, v in per_run.items()}}
    base_rate = statistics.mean(r["obs"] for r in scored)
    out["brier_climatology"] = statistics.mean((base_rate - r["obs"]) ** 2 for r in scored)
    (args.out_dir / "dev.json").write_text(json.dumps({"summary": out, "requests": recs},
                                                      indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "models"}, ensure_ascii=False))
    for k, m in out["models"].items():
        print(k, "brier", round(m["brier"], 4), "pred", round(m["sum_pred"], 1), "obs", m["sum_obs"])
        print("   ", [(b["lo"], b["n"], None if b["obs_rate"] is None else round(b["obs_rate"], 2)) for b in m["bins"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
