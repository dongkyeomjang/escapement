#!/usr/bin/env python3
"""GPU steady-state multi-turn runner: one serving lifecycle, one plan.

Same plan files, renewal rule and online window rule as the NPU runner
(``experiments/npu/stage3/multiturn_runner.py``; ``continuum.workload.multiturn``
imported unchanged). What differs on this substrate (directive G-03 3.2/3.3):

* prompts are **token-id lists**: turn 0 = opening segment ids; turn k =
  previous prompt ids + previous generated ids + new segment ids. The GPU
  caches generated tokens (GTASK02 H5), so re-tokenising text could split a
  boundary token and cut the hit short; ids avoid that.
* ``ignore_eos`` fixes the generated *length*; the generated *content* may
  differ between runs (GTASK03 finding 5), the hit arithmetic does not.
* segment ids are ``Random(turn.text_seed)`` draws in [1000, 150000) (the
  GTASK04 ``rand_ids`` rule), not tokenised words.
* the server is started here (``launch.lifecycle``: observation patch logs,
  KV events collector, GPU process checks) and every lifecycle checks the
  card uuid and ``vllm:num_preemptions_total`` (must not move).

``cached_tokens`` is recorded raw (``null`` when ``prompt_tokens_details`` is
absent, KNOWN_PITFALLS 6). The server runs with
``--enable-prompt-tokens-details``, under which vLLM omits the field exactly
when the value is 0 (TASK79, serving.py:586); the analysis reads absence as 0
only after checking that flag in the server log.

usage: gpu_mt_runner.py --plan <abs> --config <name> --out-dir <abs>
                        [--stream] [--eval-s 120] [--max-run-s 900]
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE.parent / "launch"))
sys.path.insert(0, str(HERE))

from continuum.workload.multiturn import MultiTurnPlan, WindowRule  # noqa: E402
from client import scrape  # noqa: E402
from lifecycle import Lifecycle, base_args, kv_events_args, patch_state  # noqa: E402
from configs import CARD_UUID, config_by_name  # noqa: E402

MODEL = "Qwen/Qwen3-4B"


def segment_ids(seed: int, n: int) -> list[int]:
    rng = random.Random(seed)
    return [rng.randrange(1000, 150000) for _ in range(n)]


def post(base: str, payload: dict, stream: bool, origin: float):
    """(status, usage, generated ids, request id, chunk times, error)."""
    req = urllib.request.Request(f"{base}/v1/completions", data=json.dumps(payload).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    times: list[float] = []
    try:
        with urllib.request.urlopen(req, timeout=3600) as resp:
            if not stream:
                body = json.loads(resp.read().decode())
                ch = body["choices"][0]
                return resp.status, body.get("usage"), ch.get("token_ids") or [], body.get("id"), times, None
            gen: list[int] = []
            usage = rid = None
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                obj = json.loads(data)
                rid = rid or obj.get("id")
                for ch in obj.get("choices") or []:
                    if ch.get("token_ids"):
                        times.append(time.perf_counter() - origin)
                        gen += ch["token_ids"]
                if obj.get("usage"):
                    usage = obj["usage"]
            return resp.status, usage, gen, rid, times, None
    except urllib.error.HTTPError as e:
        return e.code, None, [], None, times, e.read().decode("utf-8", "replace")[:500]


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True,
                          text=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--config", required=True)
    ap.add_argument("--n", type=int, default=None, help="N for per-N configurations")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--stream", action="store_true")
    ap.add_argument("--eval-s", type=float, default=120.0)
    ap.add_argument("--max-run-s", type=float, default=900.0)
    ap.add_argument("--exec-timing", action="store_true",
                    help="G-10: ESCAPEMENT_EXEC=1 (exec-timing layer must be applied)")
    a = ap.parse_args()
    for p in (a.plan, a.out_dir):
        if not p.is_absolute():
            raise SystemExit(f"path must be absolute (KNOWN_PITFALLS 1): {p}")
    ps = patch_state()
    if "state: patched" not in ps:
        raise SystemExit("observation patch must be applied")
    if a.exec_timing and "exec_layer: present" not in ps:
        raise SystemExit("--exec-timing needs the exec-timing layer (apply_exec.sh)")
    out = a.out_dir
    out.mkdir(parents=True, exist_ok=True)
    plan_bytes = a.plan.read_bytes()
    pj = json.loads(plan_bytes)
    plan = MultiTurnPlan.from_json(pj)
    if plan.sha256() != pj.get("_sha256"):
        raise SystemExit("plan SHA256 field does not match its content")
    cfg = config_by_name(a.config, a.n if a.n is not None else plan.n_slots)
    rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]), eval_s=a.eval_s)
    args = base_args(num_gpu_blocks=cfg.num_gpu_blocks, max_num_seqs=cfg.max_num_seqs,
                     max_num_batched_tokens=cfg.budget, capture_sizes=list(cfg.capture_sizes),
                     extra=kv_events_args())
    prov = {"runner": "experiments/gpu/multiturn/gpu_mt_runner.py",
            "runner_commit": _git("rev-parse", "HEAD"),
            "git_status_porcelain": _git("status", "--porcelain"),
            "argv": sys.argv, "config": cfg.__dict__ | {"capture_sizes": list(cfg.capture_sizes)},
            "plan_file_sha256": hashlib.sha256(plan_bytes).hexdigest(),
            "plan_content_sha256": plan.sha256(), "plan_id": plan.plan_id,
            "stream": a.stream, "exec_timing": a.exec_timing, "expected_card_uuid": CARD_UUID,
            "started_at_utc": datetime.now(timezone.utc).isoformat()}
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")

    rows_path = out / "requests.jsonl"
    rows_path.write_text("")
    ids_fh = gzip.open(out / "token_ids.jsonl.gz", "wt")
    lock = threading.Lock()
    completions: list[tuple[int, float]] = []
    state = {"warmup_end": None, "stop_at": None, "stopped_by": None, "exhausted": []}
    stop_evt = threading.Event()

    xenv = {"ESCAPEMENT_EXEC": "1"} if a.exec_timing else {}
    with Lifecycle(out, args, obs=True, kv_events=True, extra_env=xenv) as lc:
        base = lc.base
        m_pre = scrape(base)
        origin = time.perf_counter()
        origin_wall = time.time()

        def now() -> float:
            return time.perf_counter() - origin

        def should_stop() -> bool:
            t = now()
            if state["stop_at"] is not None and t >= state["stop_at"]:
                state["stopped_by"] = state["stopped_by"] or "window"
                stop_evt.set()
            if t >= a.max_run_s:
                state["stopped_by"] = state["stopped_by"] or "max_run_s"
                stop_evt.set()
            return stop_evt.is_set()

        def run_slot(sp) -> None:
            if stop_evt.wait(max(0.0, sp.start_s - now())):
                return
            for g, sess in enumerate(sp.sessions):
                ctx: list[int] = []
                for turn in sess.turns:
                    if should_stop():
                        return
                    prompt = ctx + segment_ids(turn.text_seed, turn.new_segment_tokens)
                    payload = {"model": MODEL, "prompt": prompt,
                               "max_tokens": turn.generation_tokens, "temperature": 0.0,
                               "top_p": 1.0, "seed": 20260929, "ignore_eos": True,
                               "return_token_ids": True, "stream": a.stream}
                    if a.stream:
                        payload["stream_options"] = {"include_usage": True}
                    sent = now()
                    status, usage, gen, rid, times, err = post(base, payload, a.stream, origin)
                    done = now()
                    details = (usage or {}).get("prompt_tokens_details")
                    row = {"plan_id": plan.plan_id, "config": cfg.name, "slot": sp.slot,
                           "generation": g, "session": sess.session_id, "turn": turn.index,
                           "turns_in_session": len(sess.turns), "request_id": rid,
                           "status": status, "sent_s": sent, "done_s": done,
                           "first_token_s": times[0] if times else None,
                           "requested_segment_tokens": turn.new_segment_tokens,
                           "requested_generation_tokens": turn.generation_tokens,
                           "gap_after_s": turn.gap_after_s, "sent_prompt_len": len(prompt),
                           "prompt_tokens": (usage or {}).get("prompt_tokens"),
                           "completion_tokens": (usage or {}).get("completion_tokens"),
                           "generated_ids": len(gen),
                           "details_present": isinstance(details, dict),
                           "cached_tokens": details.get("cached_tokens") if isinstance(details, dict) else None,
                           "error": err, "at_utc": datetime.now(timezone.utc).isoformat()}
                    with lock:
                        with rows_path.open("a") as fh:
                            fh.write(json.dumps(row) + "\n")
                        ids_fh.write(json.dumps({"request_id": rid, "prompt_sha256": hashlib.sha256(
                            json.dumps(prompt).encode()).hexdigest(), "gen": gen, "t": times}) + "\n")
                        completions.append((sp.slot, done))
                        if state["warmup_end"] is None:
                            w = rule.warmup_end(completions, plan.n_slots)
                            if w is not None:
                                state["warmup_end"] = w
                                state["stop_at"] = w + rule.eval_s
                    if status != 200 or len(gen) != turn.generation_tokens:
                        state["stopped_by"] = state["stopped_by"] or f"bad_response_{status}"
                        stop_evt.set()
                        return
                    ctx = prompt + gen
                    if turn.gap_after_s > 0 and stop_evt.wait(turn.gap_after_s):
                        return
            with lock:
                state["exhausted"].append(sp.slot)

        with ThreadPoolExecutor(max_workers=plan.n_slots) as pool:
            list(pool.map(run_slot, plan.slots))
        ids_fh.close()
        m_post = scrape(base)
        valid_lc, why = lc.valid()
        meta = dict(lc.meta)
    delta = {k: m_post.get(k, 0.0) - m_pre.get(k, 0.0) for k in set(m_pre) | set(m_post)}
    reasons = list(why)
    if meta.get("gpu0_uuid") != CARD_UUID:
        reasons.append(f"card uuid {meta.get('gpu0_uuid')} != {CARD_UUID}")
    if delta.get("vllm:num_preemptions_total", 0.0) != 0.0:
        reasons.append(f"preemptions {delta.get('vllm:num_preemptions_total')}")
    if state["stopped_by"] != "window":
        reasons.append(f"stopped_by {state['stopped_by']}")
    if state["exhausted"]:
        reasons.append(f"exhausted slots {sorted(state['exhausted'])}")
    win = {"cycle_s": rule.cycle_s, "eval_s": rule.eval_s, "warmup_cycles": rule.warmup_cycles,
           "min_turns": rule.min_turns, "warmup_end_s": state["warmup_end"],
           "eval_end_s": state["stop_at"], "stopped_by": state["stopped_by"],
           "exhausted_slots": sorted(state["exhausted"]), "completions": len(completions),
           "origin_wall": origin_wall, "metric_delta": delta,
           "valid": not reasons, "invalid_reasons": reasons}
    (out / "windows.json").write_text(json.dumps(win, indent=2) + "\n")
    print(f"{plan.plan_id} {cfg.name}: requests {len(completions)} stopped_by {state['stopped_by']} "
          f"valid {not reasons} {reasons}")
    return 0 if not reasons else 3


if __name__ == "__main__":
    raise SystemExit(main())
