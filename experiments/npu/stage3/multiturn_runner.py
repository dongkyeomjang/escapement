#!/usr/bin/env python3
"""Steady-state multi-turn runner: renewal slots, windows, optional streaming.

Reads a pre-generated plan (``continuum.workload.multiturn``), keeps ``N``
slots busy by starting the next session of a slot as soon as the previous one
finishes, and records one row per request. ``WindowRule`` -- the same function
analysis uses -- decides online when warm-up ends; issuing stops when the
evaluation window closes, requests already in flight are allowed to finish.

Differences from ``stage2/session_runner.py`` (which is left untouched):

* ``cached_tokens`` is ``null`` when the response has no
  ``usage.prompt_tokens_details`` (KNOWN_PITFALLS 6) -- never 0.
* The run directory gets the runner's git commit and dirty state, every
  argument, and the plan's SHA256 (TASK72 left the runner commit PARTIAL).
* ``--stream`` records the arrival time of every streamed chunk.

Paths passed in must be absolute (KNOWN_PITFALLS 1): the isolated launcher
runs this from a temporary directory.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/stage2"))

from continuum.workload.multiturn import MultiTurnPlan, WindowRule  # noqa: E402


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True,
                              text=True, timeout=30).stdout.strip()
    except Exception as e:  # pragma: no cover - provenance must not kill a run
        return f"<error {e}>"


def post(base: str, payload: dict, stream: bool, origin: float):
    """Returns (status, body_or_None, usage, text, request_id, chunk_times)."""
    req = urllib.request.Request(
        f"{base}/v1/completions", data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    chunks: list[float] = []
    try:
        with urllib.request.urlopen(req, timeout=3600) as resp:
            if not stream:
                body = json.loads(resp.read().decode())
                text = body.get("choices", [{}])[0].get("text", "")
                return resp.status, body, body.get("usage"), text, body.get("id"), chunks
            text_parts: list[str] = []
            usage = None
            rid = None
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                obj = json.loads(data)
                rid = rid or obj.get("id")
                ch = obj.get("choices") or []
                if ch and ch[0].get("text"):
                    chunks.append(time.perf_counter() - origin)
                    text_parts.append(ch[0]["text"])
                if obj.get("usage"):
                    usage = obj["usage"]
            return resp.status, None, usage, "".join(text_parts), rid, chunks
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:1000], None, "", None, chunks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--tokenizer-dir", required=True, type=Path)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--label", required=True, help="recorded on every row")
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--stream", action="store_true")
    ap.add_argument("--eval-s", type=float, default=120.0)
    ap.add_argument("--max-run-s", type=float, default=900.0,
                    help="hard stop on issuing, whatever the window says")
    ap.add_argument("--sampling-seed", type=int, default=20260819)
    args = ap.parse_args()
    for p in (args.tokenizer_dir, args.plan, args.output_dir):
        if not p.is_absolute():
            raise SystemExit(f"path must be absolute (KNOWN_PITFALLS 1): {p}")

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    plan_bytes = args.plan.read_bytes()
    plan = MultiTurnPlan.from_json(json.loads(plan_bytes))
    if plan.sha256() != json.loads(plan_bytes).get("_sha256", plan.sha256()):
        raise SystemExit("plan file SHA256 field does not match its content")
    rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]), eval_s=args.eval_s)

    base = args.base_url.rstrip("/")
    (out / "provenance.json").write_text(json.dumps({
        "runner": "experiments/npu/stage3/multiturn_runner.py",
        "runner_commit": _git("rev-parse", "HEAD"),
        "git_status_porcelain": _git("status", "--porcelain"),
        "argv": sys.argv, "args": {k: str(v) for k, v in vars(args).items()},
        "plan_file_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "plan_content_sha256": plan.sha256(),
        "plan_id": plan.plan_id, "python": sys.version, "host": platform.node(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    }, indent=2, ensure_ascii=False) + "\n")

    from session_runner import build_exact  # same text construction as stage2
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(args.tokenizer_dir))
    with urllib.request.urlopen(f"{base}/v1/models", timeout=30) as r:
        model_id = json.loads(r.read().decode())["data"][0]["id"]

    rows_path = out / f"requests.{args.label}.jsonl"
    rows_path.write_text("")
    tok_path = out / f"tokens.{args.label}.jsonl.gz"
    lock = threading.Lock()
    completions: list[tuple[int, float]] = []
    state = {"warmup_end": None, "stop_at": None, "stopped_by": None,
             "exhausted_slots": []}
    stop_evt = threading.Event()
    origin = time.perf_counter()
    tok_fh = gzip.open(tok_path, "wt") if args.stream else None

    def now() -> float:
        return time.perf_counter() - origin

    def should_stop() -> bool:
        t = now()
        if state["stop_at"] is not None and t >= state["stop_at"]:
            state["stopped_by"] = state["stopped_by"] or "window"
            stop_evt.set()
        if t >= args.max_run_s:
            state["stopped_by"] = state["stopped_by"] or "max_run_s"
            stop_evt.set()
        return stop_evt.is_set()

    def emit(row: dict, times: list[float]) -> None:
        with lock:
            with rows_path.open("a") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            if tok_fh is not None:
                tok_fh.write(json.dumps({"request_id": row["request_id"], "slot": row["slot"],
                                         "t": times}) + "\n")

    def run_slot(sp) -> None:
        if stop_evt.wait(max(0.0, sp.start_s - now())):
            return
        for g, sess in enumerate(sp.sessions):
            context = ""
            for turn in sess.turns:
                if should_stop():
                    return
                segment = build_exact(tok, turn.new_segment_tokens, turn.text_seed)
                prompt = (context + " " + segment).strip() if context else segment
                payload = {"model": model_id, "prompt": prompt,
                           "max_tokens": turn.generation_tokens, "temperature": 0.0,
                           "top_p": 1.0, "seed": args.sampling_seed, "stream": args.stream}
                if args.stream:
                    payload["stream_options"] = {"include_usage": True}
                sent = now()
                status, body, usage, text, rid, times = post(base, payload, args.stream, origin)
                done = now()
                details = (usage or {}).get("prompt_tokens_details")
                cached = details.get("cached_tokens") if isinstance(details, dict) else None
                emit({"label": args.label, "plan_id": plan.plan_id, "slot": sp.slot,
                      "generation": g, "session": sess.session_id, "turn": turn.index,
                      "turns_in_session": len(sess.turns), "request_id": rid,
                      "status": status, "sent_s": sent,
                      "first_token_s": times[0] if times else None, "done_s": done,
                      "requested_segment_tokens": turn.new_segment_tokens,
                      "requested_generation_tokens": turn.generation_tokens,
                      "gap_after_s": turn.gap_after_s,
                      "prompt_tokens": (usage or {}).get("prompt_tokens"),
                      "completion_tokens": (usage or {}).get("completion_tokens"),
                      "details_present": isinstance(details, dict),
                      "cached_tokens": cached,
                      "error": None if status == 200 else str(body)[:300],
                      "at_utc": datetime.now(timezone.utc).isoformat()}, times)
                with lock:
                    completions.append((sp.slot, done))
                    if state["warmup_end"] is None:
                        w = rule.warmup_end(completions, plan.n_slots)
                        if w is not None:
                            state["warmup_end"] = w
                            state["stop_at"] = w + rule.eval_s
                if status != 200:
                    state["stopped_by"] = state["stopped_by"] or f"http_{status}"
                    stop_evt.set()
                    return
                context = prompt + text
                if turn.gap_after_s > 0 and stop_evt.wait(turn.gap_after_s):
                    return
        with lock:
            state["exhausted_slots"].append(sp.slot)

    with ThreadPoolExecutor(max_workers=plan.n_slots) as pool:
        list(pool.map(run_slot, plan.slots))
    if tok_fh is not None:
        tok_fh.close()
    (out / f"windows.{args.label}.json").write_text(json.dumps({
        "cycle_s": rule.cycle_s, "eval_s": rule.eval_s, "warmup_cycles": rule.warmup_cycles,
        "min_turns": rule.min_turns, "warmup_end_s": state["warmup_end"],
        "eval_end_s": state["stop_at"], "stopped_by": state["stopped_by"],
        "exhausted_slots": sorted(state["exhausted_slots"]),
        "wall_s": now(), "completions": len(completions),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    }, indent=2) + "\n")
    ok = state["stopped_by"] == "window" and not state["exhausted_slots"]
    print(f"{args.label}: requests {len(completions)}, stopped_by {state['stopped_by']}, "
          f"warmup_end {state['warmup_end']}, exhausted {state['exhausted_slots']}")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
