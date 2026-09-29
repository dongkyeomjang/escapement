#!/usr/bin/env python3
"""Offline checks for the multi-turn runner and the simulator's renewal option.

No device, no model server: ``fake_server.py`` answers the completions
endpoint. Checked:

1. renewal -- a slot's next session starts right after the previous one ends,
   and no more than N requests are ever in flight;
2. windows -- ``WindowRule`` recomputed from the recorded rows equals what the
   runner decided online, nothing is sent after the evaluation window, and the
   run stopped because of the window;
3. reproducibility -- two runs of one plan send byte-identical prompts for every
   (session, turn) both reached;
4. unobservable values -- without ``prompt_tokens_details`` every row has
   ``cached_tokens: null`` (never 0); streaming records one time per chunk;
5. provenance -- runner commit, arguments, plan SHA256 are in the run directory;
6. simulator renewal -- on the same plan each successor's first turn arrives
   exactly when its predecessor's last turn finishes, at most N in flight, and
   the default path (no renewal fields) is untouched.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/stage3"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))

import make_plan as MP  # noqa: E402
from continuum.sim import SimConfig, simulate  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402

TOKENIZER = REPO / "models/Qwen3-4B-rbln-b8-s8192-d4-mb"
LAUNCH = REPO / "experiments/npu/launch/run_isolated_python.sh"
RUNNER = REPO / "experiments/npu/stage3/multiturn_runner.py"


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def run_once(work: Path, plan_path: Path, label: str, *, stream: bool, details: bool,
             eval_s: float) -> dict:
    port = free_port()
    log = work / f"fake-{label}.jsonl"
    cmd = [sys.executable, str(REPO / "experiments/npu/stage3/fake_server.py"),
           "--port", str(port), "--log", str(log)]
    if not details:
        cmd.append("--no-details")
    srv = subprocess.Popen(cmd)       # stopped by its own PID (KNOWN_PITFALLS 2)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.05)
        out = work / label
        rc = subprocess.run(["bash", str(LAUNCH), str(RUNNER),
                             "--base-url", f"http://127.0.0.1:{port}",
                             "--tokenizer-dir", str(TOKENIZER), "--plan", str(plan_path),
                             "--label", label, "--output-dir", str(out),
                             "--eval-s", str(eval_s), "--max-run-s", "120"]
                            + (["--stream"] if stream else []),
                            capture_output=True, text=True).returncode
    finally:
        srv.send_signal(signal.SIGTERM)
        srv.wait(timeout=10)
    rows = [json.loads(l) for l in (out / f"requests.{label}.jsonl").read_text().splitlines()]
    fake = {json.loads(l)["id"]: json.loads(l)["sha"] for l in log.read_text().splitlines()}
    return {"rc": rc, "rows": rows, "fake": fake, "out": out,
            "windows": json.loads((out / f"windows.{label}.json").read_text()),
            "prov": json.loads((out / "provenance.json").read_text())}


def check_run(r: dict, plan: MultiTurnPlan, n: int) -> dict:
    rows = r["rows"]
    w = r["windows"]
    res = {"rc": r["rc"], "requests": len(rows), "stopped_by": w["stopped_by"]}
    # 1. renewal and concurrency
    gaps = []
    for slot in range(n):
        srows = sorted((x for x in rows if x["slot"] == slot), key=lambda x: x["sent_s"])
        for a, b in zip(srows, srows[1:]):
            if b["generation"] == a["generation"] + 1 and b["turn"] == 0:
                gaps.append(b["sent_s"] - a["done_s"])
    ev = sorted([(x["sent_s"], 1) for x in rows] + [(x["done_s"], -1) for x in rows],
                key=lambda e: (e[0], e[1]))
    cur = peak = 0
    for _, d in ev:
        cur += d
        peak = max(peak, cur)
    res["renewal_count"] = len(gaps)
    res["renewal_max_delay_s"] = max(gaps) if gaps else None
    res["peak_in_flight"] = peak
    # 2. windows
    rule = WindowRule(cycle_s=w["cycle_s"], eval_s=w["eval_s"])
    off = rule.warmup_end([(x["slot"], x["done_s"]) for x in rows], n)
    res["warmup_end_online"] = w["warmup_end_s"]
    res["warmup_end_offline"] = off
    res["sent_after_eval_end"] = sum(1 for x in rows if x["sent_s"] >= w["eval_end_s"] + 1e-6)
    res["labels"] = {k: sum(1 for x in rows if rule.classify(x["sent_s"], off) == k)
                     for k in ("warmup", "eval", "drain")}
    # 5. provenance
    p = r["prov"]
    res["provenance_ok"] = bool(p["runner_commit"]) and p["plan_content_sha256"] == plan.sha256()
    return res


def check_sim(plan: MultiTurnPlan) -> dict:
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    res = simulate(D, sessions, SimConfig(max_running_requests=8, session_start_s=start,
                                          successor=succ))
    by = {(r.session_index, r.turn): r for r in res.requests}
    bad = 0
    chained = 0
    for i, j in enumerate(succ):
        if j is None or (j, 0) not in by:
            continue
        last = max(t for (k, t) in by if k == i)
        chained += 1
        if abs(by[(j, 0)].arrival_s - by[(i, last)].finish_s) > 1e-12:
            bad += 1
    heads = [i for i in range(len(sessions)) if i not in {j for j in succ if j is not None}]
    head_ok = all(abs(by[(i, 0)].arrival_s - start[i]) < 1e-12 for i in heads)
    peak = max(s.running for s in res.decode_steps) if res.decode_steps else 0
    return {"chained": chained, "chain_mismatch": bad, "heads_at_offsets": head_ok,
            "peak_running": peak, "requests": len(res.requests)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    a = ap.parse_args()
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    n = 3
    # Short gaps and generations so a run takes seconds, not minutes.
    plan = MP.build(n=n, seed=20260929, plan_id="offline", cycle_s=0.4, turns=3,
                    sessions_per_slot=8, generation="uniform:32:64", gap="uniform:0:1")
    plan_path = work / "plan.json"
    MP.write(plan, plan_path)
    A = run_once(work, plan_path, "A", stream=False, details=True, eval_s=4.0)
    B = run_once(work, plan_path, "B", stream=False, details=True, eval_s=4.0)
    C = run_once(work, plan_path, "C", stream=True, details=False, eval_s=4.0)
    out = {"A": check_run(A, plan, n), "B": check_run(B, plan, n), "C": check_run(C, plan, n)}
    # 3. reproducibility
    def shas(r):
        return {(x["session"], x["turn"]): r["fake"].get(x["request_id"]) for x in r["rows"]}
    sa, sb = shas(A), shas(B)
    common = set(sa) & set(sb)
    out["repro_common"] = len(common)
    out["repro_identical"] = sum(1 for k in common if sa[k] == sb[k] and sa[k] is not None)
    # 4. null and chunks
    out["C_null_cached"] = all(x["cached_tokens"] is None and not x["details_present"]
                               for x in C["rows"])
    out["A_cached_present"] = all(x["cached_tokens"] == 0 and x["details_present"]
                                  for x in A["rows"])
    with gzip.open(C["out"] / "tokens.C.jsonl.gz", "rt") as fh:
        toks = {json.loads(l)["request_id"]: json.loads(l)["t"] for l in fh}
    out["C_chunk_counts_match"] = all(len(toks.get(x["request_id"], [])) == x["completion_tokens"]
                                      for x in C["rows"])
    out["sim"] = check_sim(plan)
    ok = (all(out[k]["rc"] == 0 and out[k]["stopped_by"] == "window"
              and out[k]["peak_in_flight"] <= n and out[k]["sent_after_eval_end"] == 0
              and abs(out[k]["warmup_end_online"] - out[k]["warmup_end_offline"]) < 1e-9
              and out[k]["provenance_ok"] and out[k]["renewal_count"] > 0
              and out[k]["renewal_max_delay_s"] < 0.25
              for k in ("A", "B", "C"))
          and out["repro_common"] > 0 and out["repro_identical"] == out["repro_common"]
          and out["C_null_cached"] and out["A_cached_present"] and out["C_chunk_counts_match"]
          and out["sim"]["chain_mismatch"] == 0 and out["sim"]["heads_at_offsets"]
          and out["sim"]["chained"] > 0)
    out["verdict"] = "PASS" if ok else "FAIL"
    (work / "offline_check.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
