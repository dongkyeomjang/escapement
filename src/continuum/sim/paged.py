"""Step simulator for a paged block-pool engine that mixes prefill into decode.

``engine.simulate`` models one family of engines: prefill owns its step and
stops every decoder, the pool is one slot per sequence, and only prompt
tokens are cached. A second family -- a paged pool of small blocks, chunked
prefill mixed into decode steps under a token budget, generated tokens cached,
lookup before allocation -- cannot be expressed by switches on that engine.
This module simulates it, and every rule it follows is read from a
``SubstrateDescriptorV2`` field (directive 07 work B); nothing branches on a
substrate name. ``engine.simulate`` dispatches here when the descriptor says
prefill is ``mixed``.

One step at a time (the rules and the descriptor fields that set them):

1. running requests first, in admission order: one still prefilling takes
   ``min(remaining prompt, budget left)`` tokens, a decoding one takes 1
   (``admission.step_token_budget``, ``prefill.execution = mixed``);
2. waiting requests FCFS by arrival while the budget is positive and fewer
   than ``admission.max_running`` run; each looks up its cached prefix and,
   when ``semantics.resume_allocates_first`` is false and
   ``semantics.hit_protection = touch_before_alloc``, takes the hit blocks out
   of the free queue before any new block is allocated;
3. blocks for the scheduled tokens come from the free queue head; a popped
   block that still carried a cached key is evicted. The queue order is
   ``layers[reuse].eviction_order``: ``release_lru`` -- by release, a
   request's blocks returned tail first (``intra_request_loss = tail_first``);
   ``allocation_fifo`` -- by the admission that first allocated them, tail
   first within it, unaffected by hits. Never-used blocks go first, by id
   (``initial_free_order = never_used_first``). ``reserved_units`` blocks
   (the null block) are never handed out;
4. every block full of tokens that ``semantics.cacheable_tokens`` covers is
   registered (``computed`` = prompt + output - 1, ``prefill_only`` = prompt);
5. a finished request releases its blocks.

The step is priced from ``step_cost`` by mode: decode-only on the grid
(``decode``), mixed within the grid (``mixed``), anything above the top
(``eager``); the grid maps scheduled tokens (``grid.unit = tokens``). Prices
are in milliseconds as measured and are converted once. With
``context_cost`` set, a step carrying ``decodes`` decoding requests adds
``per_token * (sum_ctx - decodes * reference)`` ms before the conversion,
``sum_ctx`` being the decoders' computed tokens (TASK103, GTASK18).

Preemption is not simulated: an allocation that would need it raises
``PreemptionNeeded`` -- a configuration that preempts is outside what the
simulator claims to predict.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import OrderedDict
from dataclasses import dataclass, field
import heapq

from ..substrate.v2 import (
    EagerStepCost,
    FullGraphDecodeCost,
    PiecewiseMixedCost,
    SubstrateDescriptorV2,
)


class PreemptionNeeded(RuntimeError):
    pass


# -- step pricing -----------------------------------------------------------------------

def _padded(grid: tuple[int, ...], tokens: int) -> int | None:
    i = bisect_left(grid, tokens)
    return grid[i] if i < len(grid) else None


def _decode_ms(d: SubstrateDescriptorV2, n: int) -> float:
    full: FullGraphDecodeCost = d.step_cost["decode"]
    if n < 1 or n > full.max_measured_requests:
        raise ValueError(f"decode width {n} outside the measured range")
    b = _padded(d.grid.sizes, n)
    if b is None:
        eager: EagerStepCost = d.step_cost["eager"]
        if n not in eager.decode_ms_by_n:
            raise ValueError(f"eager decode at n={n} was not measured")
        return eager.decode_ms_by_n[n]
    if b > full.max_measured_requests:
        raise ValueError(f"decode padded to {b} was not measured")
    return full.fixed_ms_by_width[b] + full.marginal_ms_per_request * n


def step_ms(d: SubstrateDescriptorV2, *, decodes: int, prefill_tokens: int) -> float:
    """One step with ``decodes`` one-token requests and ``prefill_tokens`` prompt
    tokens. A prefill-only step is priced on the width-1 decode baseline."""
    if prefill_tokens == 0:
        return _decode_ms(d, decodes)
    base = _decode_ms(d, max(decodes, 1))
    if _padded(d.grid.sizes, decodes + prefill_tokens) is not None:
        mixed: PiecewiseMixedCost = d.step_cost["mixed"]
        return base + mixed.increment_ms
    eager: EagerStepCost = d.step_cost["eager"]
    return base + eager.increment_ms(prefill_tokens)


def step_mode(d: SubstrateDescriptorV2, decodes: int, prefill_tokens: int) -> str:
    if _padded(d.grid.sizes, decodes + prefill_tokens) is None:
        return "NONE"
    return "FULL" if prefill_tokens == 0 else "PIECEWISE"


# -- block pool -----------------------------------------------------------------------------

class BlockPool:
    def __init__(self, first_id: int, capacity: int, order: str):
        if order not in ("release_lru", "allocation_fifo"):
            raise ValueError(order)
        ids = range(first_id, first_id + capacity)
        self.order_rule = order
        self.key: dict[int, tuple | None] = {b: None for b in ids}
        self.cache: dict[tuple, int] = {}
        self.ref: dict[int, int] = {b: 0 for b in ids}
        self.evictions = 0
        if order == "release_lru":
            self.free: OrderedDict[int, None] = OrderedDict((b, None) for b in ids)
        else:
            self.order: dict[int, tuple] = {b: (-1, b) for b in ids}
            self.heap = [(self.order[b], b) for b in ids]
            heapq.heapify(self.heap)
            self.in_free = set(ids)

    def _remove_free(self, b: int) -> None:
        if self.order_rule == "release_lru":
            del self.free[b]
        else:
            self.in_free.discard(b)

    def pop(self, stamp: int, pos: int) -> int:
        if self.order_rule == "release_lru":
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
                if self.order_rule == "release_lru":
                    self.free[b] = None
                else:
                    self.in_free.add(b)
                    heapq.heappush(self.heap, (self.order[b], b))

    def register(self, b: int, key: tuple) -> None:
        if self.key[b] is None and key not in self.cache:
            self.cache[key] = b
            self.key[b] = key


# -- records ----------------------------------------------------------------------------------

@dataclass
class PagedRequest:
    idx: int
    session: int
    slot: int
    turn: int
    arrival_s: float
    prompt: int
    gen: int
    reusable: int
    """Tokens the lookup would hit if nothing had been evicted (turn >= 1)."""
    stamp: int = -1
    admit_s: float | None = None
    first_token_s: float | None = None
    finish_s: float | None = None
    hit: int = 0
    computed: int = 0
    produced: int = 0
    blocks: list = field(default_factory=list)


@dataclass
class PagedStep:
    start_s: float
    duration_s: float
    decodes: int
    prefill_tokens: int
    reqs: int
    mode: str
    padded: int | None


@dataclass
class PagedResult:
    requests: list[PagedRequest]
    steps: list[PagedStep]
    warmup_end_s: float | None
    eval_end_s: float | None
    evictions: int
    wall_s: float


# -- engine ---------------------------------------------------------------------------------------

def check_descriptor(d: SubstrateDescriptorV2) -> None:
    """Refuse rules this engine does not implement."""
    sem = d.semantics
    layer = d.reuse_pool
    bad = []
    if d.prefill.execution != "mixed":
        bad.append(f"prefill.execution={d.prefill.execution}")
    if layer.eviction_order not in ("release_lru", "allocation_fifo"):
        bad.append(f"eviction_order={layer.eviction_order}")
    if sem.evictable_when != "immediate":
        bad.append(f"evictable_when={sem.evictable_when}")
    if sem.intra_request_loss != "tail_first":
        bad.append(f"intra_request_loss={sem.intra_request_loss}")
    if sem.initial_free_order != "never_used_first":
        bad.append(f"initial_free_order={sem.initial_free_order}")
    if not (sem.resume_allocates_first is False and sem.hit_protection == "touch_before_alloc"):
        bad.append("lookup order other than lookup-then-touch-then-allocate")
    if sem.cacheable_tokens not in ("computed", "prefill_only"):
        bad.append(f"cacheable_tokens={sem.cacheable_tokens}")
    if sem.kv_tokens_held != "computed":
        bad.append(f"kv_tokens_held={sem.kv_tokens_held}")
    if sem.dummy_mode != "none":
        bad.append(f"dummy_mode={sem.dummy_mode}")
    if d.grid.unit != "tokens":
        bad.append(f"grid.unit={d.grid.unit}")
    for key, cls in (("decode", FullGraphDecodeCost), ("mixed", PiecewiseMixedCost),
                     ("eager", EagerStepCost)):
        if not isinstance(d.step_cost.get(key), cls):
            bad.append(f"step_cost[{key!r}] is not a {cls.__name__}")
    for name, v in (("admission.max_running", d.admission.max_running),
                    ("admission.step_token_budget", d.admission.step_token_budget),
                    ("reuse capacity", layer.capacity_units), ("reserved_units", layer.reserved_units)):
        if v is None:
            bad.append(f"{name} not established")
    if bad:
        raise ValueError("paged simulator does not implement: " + ", ".join(bad))


def simulate_paged(d: SubstrateDescriptorV2, sessions, config) -> PagedResult:
    """``sessions``, ``config.session_start_s`` and ``config.successor`` as for
    ``engine.simulate``. With ``config.window_rule`` and ``config.slot_of`` set,
    nothing new is issued after the evaluation window ends (the runner's rule)."""
    check_descriptor(d)
    if config.max_running_requests != d.admission.max_running:
        raise ValueError("config.max_running_requests differs from the descriptor's")
    block = d.reuse_pool.unit_tokens
    budget0 = d.admission.step_token_budget
    ctx_cost = d.context_cost
    if ctx_cost is not None and ctx_cost.unit != "ms":
        raise ValueError("the paged engine prices steps in ms; context_cost.unit must be 'ms'")
    max_running = d.admission.max_running
    prompt_only = d.semantics.cacheable_tokens == "prefill_only"
    pool = BlockPool(d.reuse_pool.reserved_units, d.reuse_pool.capacity_units,
                     d.reuse_pool.eviction_order)
    start = config.session_start_s or tuple(0.0 for _ in sessions)
    succ = config.successor or tuple(None for _ in sessions)
    slot_of = config.slot_of or tuple(range(len(sessions)))
    rule = config.window_rule
    ctx_len = [0] * len(sessions)
    prev_fed = [0] * len(sessions)
    pending: list[tuple[float, int, int]] = []
    for i, s0 in enumerate(start):
        if not any(j == i for j in succ if j is not None):
            heapq.heappush(pending, (s0, i, 0))
    waiting: list[PagedRequest] = []
    running: list[PagedRequest] = []
    done: list[PagedRequest] = []
    steps: list[PagedStep] = []
    now = 0.0
    stamp = 0
    nreq = 0
    comp: list[tuple[int, float]] = []
    stop_issue = None

    def fed(r: PagedRequest) -> int:
        return r.prompt + r.gen - 1

    def make(i: int, k: int, at: float) -> PagedRequest:
        nonlocal nreq
        t = sessions[i].turns[k]
        prompt = ctx_len[i] + t.new_segment_tokens
        reusable = 0
        if k > 0:
            reusable = min(prev_fed[i] // block, (prompt - 1) // block) * block
        r = PagedRequest(idx=nreq, session=i, slot=slot_of[i], turn=k, arrival_s=at,
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
        budget = budget0
        decodes = 0
        pre_tok = 0
        dctx = 0                # summed context of this step's decoders (context_cost only)
        sched: list[tuple[PagedRequest, int]] = []
        for r in running:
            if budget <= 0:
                break
            if r.computed < r.prompt:
                n = min(r.prompt - r.computed, budget)
                pre_tok += n
            else:
                n = 1
                decodes += 1
                dctx += r.computed
            budget -= n
            sched.append((r, n))
        waiting.sort(key=lambda r: (r.arrival_s, r.idx))
        while waiting and budget > 0 and len(running) < max_running:
            r = waiting.pop(0)
            r.stamp = stamp
            stamp += 1
            r.admit_s = now
            limit = (r.prompt - 1) // block
            for j in range(limit):
                b = pool.cache.get((r.session, j))
                if b is None:
                    break
                pool.touch(b)
                r.blocks.append(b)
            r.hit = len(r.blocks) * block
            r.computed = r.hit
            n = min(r.prompt - r.computed, budget)
            pre_tok += n
            budget -= n
            running.append(r)
            sched.append((r, n))
        for r, n in sched:
            need = -(-(r.computed + n) // block)
            while len(r.blocks) < need:
                r.blocks.append(pool.pop(r.stamp, len(r.blocks)))
            r.computed += n
            upto = min(r.computed, r.prompt if prompt_only else fed(r))
            for j in range(upto // block):
                pool.register(r.blocks[j], (r.session, j))
        reqs = len(sched)
        if ctx_cost is not None and decodes:
            dur = (step_ms(d, decodes=decodes, prefill_tokens=pre_tok) + ctx_cost.term(dctx, decodes)) / 1e3
        else:
            dur = step_ms(d, decodes=decodes, prefill_tokens=pre_tok) / 1e3
        steps.append(PagedStep(start_s=now, duration_s=dur, decodes=decodes, prefill_tokens=pre_tok,
                               reqs=reqs, mode=step_mode(d, decodes, pre_tok),
                               padded=_padded(d.grid.sizes, decodes + pre_tok)))
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
                prev_fed[i] = fed(r)
                comp.append((r.slot, now))
                turns = sessions[i].turns
                if k + 1 < len(turns):
                    heapq.heappush(pending, (now + turns[k].gap_after_s, i, k + 1))
                elif succ[i] is not None:
                    heapq.heappush(pending, (now, succ[i], 0))
                if rule is not None and stop_issue is None:
                    w0 = rule.warmup_end(comp, config.n_slots)
                    if w0 is not None:
                        stop_issue = w0 + rule.eval_s
            else:
                still.append(r)
        running = still
    w0 = rule.warmup_end(comp, config.n_slots) if rule is not None else None
    return PagedResult(requests=done, steps=steps, warmup_end_s=w0,
                       eval_end_s=None if w0 is None else w0 + rule.eval_s,
                       evictions=pool.evictions, wall_s=now)
