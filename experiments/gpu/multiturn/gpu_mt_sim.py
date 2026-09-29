"""Step simulator of vLLM 0.22.0 serving the steady-state multi-turn plans.

GPU wrapper for directive G-03 (5.1 predictors 2 and 3). ``continuum.sim``
models a prefill-exclusive engine that caches prompt tokens only and holds
one outer slot per sequence; none of that is true here, so the engine and the
block pool are restated in this file from the GTASK01 source-read and the
GTASK02-04 facts. The plan, the renewal chain and the window rule come from
``continuum.workload.multiturn`` unchanged; the step cost from ``gpu_cost``.

Engine (``vllm/v1/core/sched/scheduler.py``), one step at a time:

1. running requests first, in admission order: a request still prefilling
   takes ``min(remaining prompt, budget left)`` tokens (chunked prefill),
   a decoding one takes 1 token;
2. then waiting requests, FCFS by arrival, while the budget is positive and
   fewer than ``max_num_seqs`` are running: lookup (hit blocks are touched,
   i.e. taken out of the free queue) *before* new blocks are allocated
   (scheduler.py:594 -> 721, kv_cache_manager.py:397 -> 404);
3. blocks for every scheduled token are allocated from the free queue head;
   a popped block that carried a hash is evicted from the cache;
4. every block that is full of computed tokens is registered in the cache
   (generated tokens included, the last sampled token is never computed --
   GTASK02 H5, GTASK04 (ii));
5. a finished request returns its blocks to the free queue tail, tail block
   first (single_type_kv_cache_manager.py:350).

The free queue starts in block-id order; block 0 is the null block and is
never handed out (block_pool.py:176). Preemption is not modelled: the
configurations are chosen so it cannot happen (directive G-02 2.4), and the
simulator raises if an allocation would need it.

``eviction="fifo"`` is the counterfactual of directive G-03 5.1 (3): the only
change is the order in which free blocks are reclaimed -- by the admission
that first allocated them, tail block first within one admission (the same
key as ``continuum.sim.cache.GranularPool`` with ``policy="fifo"``). Hits do
not refresh that order.

Timing: a step's duration is ``gpu_cost.step_ms`` at the chosen ``bound``.
A request that arrives during a step is considered at the next step
boundary. Client overhead is zero (not a fitted knob).

Content: sessions share no text, so a block is identified by
``(session, block index)``; within a session the context is append-only,
so that key names the same tokens every time it is computed.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import heapq
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuum.workload.multiturn import MultiTurnPlan, WindowRule, to_sim_inputs  # noqa: E402
import gpu_cost as C  # noqa: E402

BLOCK = 16


@dataclass(frozen=True)
class GpuConfig:
    name: str
    num_gpu_blocks: int          # --num-gpu-blocks-override (usable = this - 1)
    max_num_seqs: int
    capture_sizes: tuple[int, ...]
    budget: int = 2048           # --max-num-batched-tokens


class PreemptionNeeded(RuntimeError):
    pass


class BlockPool:
    def __init__(self, num_gpu_blocks: int, eviction: str):
        if eviction not in ("lru", "fifo"):
            raise ValueError(eviction)
        self.eviction = eviction
        self.key: dict[int, tuple | None] = {b: None for b in range(1, num_gpu_blocks)}
        self.cache: dict[tuple, int] = {}
        self.ref: dict[int, int] = {b: 0 for b in range(1, num_gpu_blocks)}
        self.evictions = 0
        if eviction == "lru":
            self.free: OrderedDict[int, None] = OrderedDict((b, None) for b in range(1, num_gpu_blocks))
        else:
            # never-used blocks first (by id), then (admission stamp, -position)
            self.order: dict[int, tuple] = {b: (-1, b) for b in range(1, num_gpu_blocks)}
            self.heap = [(self.order[b], b) for b in range(1, num_gpu_blocks)]
            heapq.heapify(self.heap)
            self.in_free = set(range(1, num_gpu_blocks))

    def free_count(self) -> int:
        return len(self.free) if self.eviction == "lru" else len(self.in_free)

    def _remove_free(self, b: int) -> None:
        if self.eviction == "lru":
            del self.free[b]
        else:
            self.in_free.discard(b)   # lazy heap deletion

    def pop(self, stamp: int, pos: int) -> int:
        if self.eviction == "lru":
            if not self.free:
                raise PreemptionNeeded("free queue empty")
            b, _ = self.free.popitem(last=False)
        else:
            while True:
                if not self.heap:
                    raise PreemptionNeeded("free queue empty")
                o, b = heapq.heappop(self.heap)
                if b in self.in_free and self.order[b] == o:
                    self.in_free.discard(b)
                    break
            self.order[b] = (stamp, -pos)
        k = self.key[b]
        if k is not None:
            if self.cache.get(k) == b:
                del self.cache[k]
                self.evictions += 1
            self.key[b] = None
        self.ref[b] = 1
        return b

    def touch(self, b: int) -> None:
        if self.ref[b] == 0:
            self._remove_free(b)
        self.ref[b] += 1

    def release(self, blocks: list[int]) -> None:
        for b in reversed(blocks):
            self.ref[b] -= 1
            if self.ref[b] == 0:
                if self.eviction == "lru":
                    self.free[b] = None
                else:
                    self.in_free.add(b)
                    heapq.heappush(self.heap, (self.order[b], b))

    def register(self, b: int, key: tuple) -> None:
        if self.key[b] is None and key not in self.cache:
            self.cache[key] = b
            self.key[b] = key


@dataclass
class Req:
    idx: int
    session: int
    slot: int
    turn: int
    arrival_s: float
    prompt: int                 # prompt tokens
    gen: int                    # generated tokens
    reusable: int               # hit if nothing had been evicted (turn >= 1)
    stamp: int = -1
    admit_s: float | None = None
    first_token_s: float | None = None
    finish_s: float | None = None
    hit: int = 0
    computed: int = 0           # KV-computed tokens
    produced: int = 0           # sampled tokens
    blocks: list = field(default_factory=list)


@dataclass
class Step:
    start_s: float
    duration_s: float
    decodes: int
    prefill_tokens: int
    reqs: int
    mode: str
    padded: int | None


def _fed(r: Req) -> int:
    """Tokens whose KV the request will compute: prompt + output - 1."""
    return r.prompt + r.gen - 1


def simulate(plan: MultiTurnPlan, cfg: GpuConfig, *, eviction: str = "lru",
             bound: str = "lo", horizon_s: float | None = None) -> dict:
    sessions, start, succ, slot_of = to_sim_inputs(plan)
    grid = tuple(sorted(cfg.capture_sizes))
    pool = BlockPool(cfg.num_gpu_blocks, eviction)
    # per-session cumulative context
    ctx_len = [0] * len(sessions)
    prev_fed = [0] * len(sessions)
    pending: list[tuple[float, int, int]] = []   # (arrival, session, turn)
    for i, s0 in enumerate(start):
        if not any(j == i for j in succ if j is not None):
            heapq.heappush(pending, (s0, i, 0))
    waiting: list[Req] = []
    running: list[Req] = []
    done: list[Req] = []
    steps: list[Step] = []
    now = 0.0
    stamp = 0
    nreq = 0
    rule = WindowRule(cycle_s=float(plan.spec["cycle_s"]))
    comp: list[tuple[int, float]] = []
    stop_issue = None      # evaluation end: nothing new is issued after it

    def make(i: int, k: int, at: float) -> Req:
        nonlocal nreq
        t = sessions[i].turns[k]
        prompt = ctx_len[i] + t.new_segment_tokens
        reusable = 0
        if k > 0:
            reusable = min(prev_fed[i] // BLOCK, (prompt - 1) // BLOCK) * BLOCK
        r = Req(idx=nreq, session=i, slot=slot_of[i], turn=k, arrival_s=at,
                prompt=prompt, gen=t.generation_tokens, reusable=reusable)
        nreq += 1
        return r

    while True:
        while pending and pending[0][0] <= now + 1e-12:
            at, i, k = heapq.heappop(pending)
            if stop_issue is not None and at >= stop_issue:
                continue
            waiting.append(make(i, k, at))
        if not running and not waiting:
            if not pending:
                break
            now = pending[0][0]
            continue
        budget = cfg.budget
        decodes = 0
        pre_tok = 0
        sched: list[tuple[Req, int]] = []
        for r in running:
            if budget <= 0:
                break
            if r.computed < r.prompt:
                n = min(r.prompt - r.computed, budget)
                pre_tok += n
            else:
                n = 1
                decodes += 1
            budget -= n
            sched.append((r, n))
        waiting.sort(key=lambda r: (r.arrival_s, r.idx))
        while waiting and budget > 0 and len(running) < cfg.max_num_seqs:
            r = waiting.pop(0)
            r.stamp = stamp
            stamp += 1
            r.admit_s = now
            # lookup, then touch hit blocks before allocating new ones
            limit = (r.prompt - 1) // BLOCK
            for j in range(limit):
                b = pool.cache.get((r.session, j))
                if b is None:
                    break
                pool.touch(b)
                r.blocks.append(b)
            r.hit = len(r.blocks) * BLOCK
            r.computed = r.hit
            n = min(r.prompt - r.computed, budget)
            pre_tok += n
            budget -= n
            running.append(r)
            sched.append((r, n))
        # allocate for scheduled tokens and register full blocks
        for r, n in sched:
            need = -(-(r.computed + n) // BLOCK)
            while len(r.blocks) < need:
                r.blocks.append(pool.pop(r.stamp, len(r.blocks)))
            r.computed += n
            for j in range(min(r.computed, _fed(r)) // BLOCK):
                pool.register(r.blocks[j], (r.session, j))
        reqs = len(sched)
        dur = C.step_ms(decodes=decodes, prefill_tokens=pre_tok, grid=grid, bound=bound) / 1e3
        steps.append(Step(start_s=now, duration_s=dur, decodes=decodes, prefill_tokens=pre_tok,
                          reqs=reqs, mode=C.mode(decodes, pre_tok, grid),
                          padded=C.padded(grid, decodes + pre_tok)))
        now += dur
        still = []
        for r in running:
            took = next((n for q, n in sched if q is r), 0)
            if took and r.computed >= r.prompt:
                r.produced += 1
                if r.first_token_s is None:
                    r.first_token_s = now
            if r.produced >= r.gen:
                r.finish_s = now
                pool.release(r.blocks)
                done.append(r)
                i, k = r.session, r.turn
                ctx_len[i] = r.prompt + r.gen
                prev_fed[i] = _fed(r)
                comp.append((r.slot, now))
                turns = sessions[i].turns
                if k + 1 < len(turns):
                    heapq.heappush(pending, (now + turns[k].gap_after_s, i, k + 1))
                elif succ[i] is not None:
                    heapq.heappush(pending, (now, succ[i], 0))
                if stop_issue is None:
                    w0 = rule.warmup_end(comp, plan.n_slots)
                    if w0 is not None:
                        stop_issue = w0 + rule.eval_s
            else:
                still.append(r)
        running = still
        if horizon_s is not None and now > horizon_s:
            break
    w0 = rule.warmup_end(comp, plan.n_slots)
    return {"requests": done, "steps": steps, "warmup_end_s": w0,
            "eval_end_s": None if w0 is None else w0 + rule.eval_s,
            "evictions": pool.evictions, "wall_s": now}


def window_metrics(res: dict, cfg: GpuConfig, bound: str) -> dict:
    """Per-lifecycle metrics over the evaluation window (the runner's definition:
    a request belongs to the window by its send = arrival time)."""
    w0, w1 = res["warmup_end_s"], res["eval_end_s"]
    if w0 is None:
        raise RuntimeError("simulated run never left warm-up")
    grid = tuple(sorted(cfg.capture_sizes))
    reqs = [r for r in res["requests"] if w0 <= r.arrival_s < w1]
    later = [r for r in reqs if r.turn > 0]
    steps = [s for s in res["steps"] if w0 <= s.start_s < w1]
    h: dict[int, int] = {}
    for s in steps:
        h[s.reqs] = h.get(s.reqs, 0) + 1
    pad_num = sum((s.padded or (s.decodes + s.prefill_tokens)) - (s.decodes + s.prefill_tokens)
                  for s in steps)
    pad_den = sum((s.padded or (s.decodes + s.prefill_tokens)) for s in steps)
    device = sum(s.duration_s for s in steps)
    mixed = [s for s in steps if s.prefill_tokens > 0]
    # decode delay caused by prefill: extra step time x decoders stalled by it
    interference = sum((s.duration_s - C.decode_ms(max(s.decodes, 1), grid) / 1e3) * s.decodes
                       for s in mixed)
    hits = sum(1 for r in later if r.hit > 0)
    full = sum(1 for r in later if r.reusable > 0 and r.hit >= r.reusable)
    zero = sum(1 for r in later if r.hit == 0)
    n = len(reqs)
    return {
        "requests_in_window": n, "turn_ge1": len(later),
        "reuse": [hits, len(later)],
        "reuse_rate": hits / len(later) if later else None,
        "hit_tokens": sum(r.hit for r in later), "reusable_tokens": sum(r.reusable for r in later),
        "token_reuse_ratio": (sum(r.hit for r in later) / sum(r.reusable for r in later)
                              if later else None),
        "hit_shape": {"zero": zero, "partial": len(later) - zero - full, "full": full},
        "h_counts": {str(k): v for k, v in sorted(h.items())},
        "padding": pad_num / pad_den if pad_den else None,
        "device_s": device, "device_per_turn_s": device / n if n else None,
        "mixed_steps": len(mixed),
        "interference_per_turn_s": interference / n if n else None,
        "max_running": max((s.reqs for s in res["steps"]), default=0),
        "evictions": res["evictions"], "warmup_end_s": w0,
        "throughput_per_s": n / (w1 - w0), "bound": bound,
    }
