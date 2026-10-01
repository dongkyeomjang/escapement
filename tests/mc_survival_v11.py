#!/usr/bin/env python3
"""Monte Carlo of model v1.1's own assumptions, entry by entry (TASK85 check).

Closed system of N sessions; others' gaps: zero atom + exponential phases
(the GapLaw); running others finish at the PS rate c(r) (exponential); FCFS
waiting above M; a FIFO pool of C entries with the reference rule (the oldest
inactive entry goes; an active entry is never taken). The tagged session T
runs for a deterministic ``s_active`` and then idles for a deterministic gap.
At each admission of T after the first, T's previous entry is looked up after
T's own allocation (allocate-before-lookup) and its survival recorded.

The chain (``survival_probability_v11``) computes the same quantity from the
arrival-theorem initial state; the two must agree within Monte Carlo error
(the only modelled difference: the chain's initial state is the stationary law
seen by an arrival, which the long simulation realises by itself).
"""

from __future__ import annotations

import heapq
import random


def simulate(*, n: int, m_run: int, cap: int, gap, c, s_active: float, s_idle: float,
             cycles: int, seed: int, warmup: int = 200, order: str = "random") -> float:
    rng = random.Random(seed)
    t = 0.0
    pool: list[list] = []          # [key, active] in allocation order
    running: list[int] = []
    queue: list[int] = []
    ev: list = []
    n_seq = [0]
    keys = [0]
    key_of: dict[int, tuple] = {}
    prev_t = [None]
    survived: list[bool] = []
    next_comp = [None]

    def push(at, kind, s):
        n_seq[0] += 1
        heapq.heappush(ev, (at, n_seq[0], kind, s))

    def draw_gap():
        if rng.random() < gap.zero_prob:
            return 0.0
        k = rng.choices(range(len(gap.probs)), weights=gap.probs)[0]
        return rng.expovariate(1.0 / gap.means[k])

    def admit(s):
        keys[0] += 1
        k = (s, keys[0])
        if len(pool) >= cap:
            for i, (_, act) in enumerate(pool):
                if not act:
                    del pool[i]
                    break
            else:
                raise RuntimeError("no inactive entry to evict")
        pool.append([k, True])
        key_of[s] = k
        running.append(s)
        if s == 0:
            if prev_t[0] is not None:
                survived.append(any(e[0] == prev_t[0] for e in pool))
            push(t + s_active, "t_done", 0)

    def release(s):
        running.remove(s)
        for e in pool:
            if e[0] == key_of[s]:
                e[1] = False
        if queue:
            admit(queue.pop(0))

    def arrive(s):
        if len(running) < m_run and not queue:
            admit(s)
        else:
            queue.append(s)

    def reschedule():
        others = sum(1 for s in running if s != 0)
        rate = others * c(len(running)) if others else 0.0
        next_comp[0] = t + rng.expovariate(rate) if rate > 0 else None

    for s in range(1, n):
        push(draw_gap(), "return", s)
    push(0.0, "return", 0)
    reschedule()
    while len(survived) < cycles + warmup:
        nxt = ev[0][0] if ev else float("inf")
        if next_comp[0] is not None and next_comp[0] < nxt:
            t = next_comp[0]
            others = [x for x in running if x != 0]
            s = rng.choice(others) if order == "random" else others[0]   # running is in admission order
            release(s)
            g = draw_gap()
            if g == 0.0:
                arrive(s)
            else:
                push(t + g, "return", s)
        else:
            t, _, kind, s = heapq.heappop(ev)
            if kind == "return":
                arrive(s)
            else:                               # T finishes: its entry is the target
                prev_t[0] = key_of[0]
                release(0)
                push(t + s_idle, "return", 0)
        reschedule()
    tail = survived[warmup:]
    return sum(tail) / len(tail)
