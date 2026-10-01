"""Model v1.1 survival: the v1 state (a, d) joined with the engine load and
the sessions' gap phases.

Why v1 is not enough once the load moves
----------------------------------------
v1 lets other sessions allocate as a Poisson stream of constant rate ``lam``
and lets older active entries finish independently at rate ``mu``. On the
declared development set (TASK82 N = 12, TASK85) three things outside that
decide survival:

* **Load persistence from the gap shape.** Tool gaps are heavy tailed (median
  0.1-0.2 s, mean 3-4 s, CV about 2.7, 13 % exactly zero). A session that
  finishes draws a fresh gap and is usually back within a second; a session
  already out is, length-biased, in a long gap. The allocations that follow a
  moment therefore come mostly from sessions that are in the engine at that
  moment: a loaded moment is followed by many, a quiet one by few. A
  memoryless gap gets this backwards (a quiet moment has many sessions out,
  all "about to return").
* **Coupling under a running ceiling.** While requests queue, an allocation
  happens exactly when a running request finishes. If that request was older
  than the target T, its entry is the oldest inactive one and the allocation
  takes it straight back, so its release buys T no margin.
* **Waiting.** T and the returning request R may wait for a place; every
  queued allocation ahead of R is charged before R's lookup.

The chain
---------
Others: ``m`` in the engine (``min(m, M_T)`` running, the rest waiting FCFS;
``M_T = M - 1`` while T runs, ``M`` after) and ``n_k`` in gap phase ``k``.
A gap is zero with probability ``zero_prob`` (the session is back at once)
and otherwise exponential of mean ``mean_k`` with probability ``prob_k``
(a hyperexponential fitted to the plan's gaps). Pool: ``(a, d)`` as v1 --
older active and older inactive entries, the pool full.

* A session leaves phase ``k`` at rate ``n_k / mean_k`` and enters the engine:
  admitted and allocating if a place is free, otherwise queued.
* Each running other finishes at rate ``c(r)`` (B2's processor-sharing rate
  with ``r`` running in total), older than T with probability ``a / R``:
  ``(a, d) -> (a - 1, d + 1)``. The queue head, if any, is admitted and
  allocates. The finished session then draws its gap: zero (back at once,
  admitted if a place is free, else queued) or phase ``k``.
* An allocation follows the v1 d-rule: ``d > 0`` -> ``d - 1``; ``d = 0`` with
  T active -> a newer inactive entry goes; ``d = 0`` with T inactive -> T is
  evicted.

T arrives seeing the stationary state of the others (arrival theorem: ``m``
from B2 with ``N - 1`` sessions; gap phases multinomial with the time shares
``prob_k * mean_k / Z``, product form being insensitive to the gap law at the
delay station). With a free place it is allocated at once (``a0 = m``,
``d0 = C - 1 - m``); otherwise it waits behind the queue and is allocated with
``a0 = M - 1``, ``d0 = C - M``. It runs for ``s_active``, then its gap
(deterministic per sample). When it finishes a queued request takes its place
at once. R then enters a free place or waits; each queued allocation ahead of
it applies the d-rule, and R's own allocation is one more if the substrate
allocates before looking up.

With one gap phase and no zero atom the gap is memoryless; with ``N <= M``
there is never a queue. Neither reduces to v1 exactly: v1's allocation stream
does not depend on the load at all. TASK85 reports the difference.

Scope: allocation-FIFO pools (the d-rule). A release-ordered LRU block pool
needs its own form (block consumption during decode, touch on hit);
``check_substrate`` refuses it rather than approximating.

Nothing here names an accelerator.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import math

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm_multiply


# -- gap law ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GapLaw:
    """``zero_prob`` of an exactly-zero gap, else exponential phase ``k`` with
    probability ``probs[k]`` (summing to 1) and mean ``means[k]``."""

    zero_prob: float
    probs: tuple[float, ...]
    means: tuple[float, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.zero_prob < 1:
            raise ValueError("zero_prob must be in [0, 1)")
        if len(self.probs) != len(self.means) or not self.probs:
            raise ValueError("probs and means must have the same, positive length")
        if abs(sum(self.probs) - 1) > 1e-9 or min(self.probs) <= 0 or min(self.means) <= 0:
            raise ValueError("phase probabilities must be positive and sum to 1; means positive")

    @property
    def mean(self) -> float:
        return (1 - self.zero_prob) * sum(p * m for p, m in zip(self.probs, self.means))

    def time_shares(self) -> tuple[float, ...]:
        w = [p * m for p, m in zip(self.probs, self.means)]
        s = sum(w)
        return tuple(x / s for x in w)


def fit_gap_law(gaps: Sequence[float], phases: int, *, iters: int = 500) -> GapLaw:
    """Zero atom by count; positive gaps by EM for a mixture of exponentials,
    started deterministically at quantiles. A workload input, fitted to the
    plan -- never to a measurement."""
    zero = sum(1 for g in gaps if g <= 0) / len(gaps)
    x = np.array(sorted(g for g in gaps if g > 0), dtype=float)
    if phases == 1:
        return GapLaw(zero, (1.0,), (float(x.mean()),))
    means = np.array([np.quantile(x, (k + 0.5) / phases) for k in range(phases)])
    means = np.maximum(means, 1e-6)
    probs = np.full(phases, 1.0 / phases)
    for _ in range(iters):
        dens = probs[None, :] / means[None, :] * np.exp(-x[:, None] / means[None, :])
        resp = dens / np.maximum(dens.sum(axis=1, keepdims=True), 1e-300)
        nk = resp.sum(axis=0)
        probs = nk / nk.sum()
        means = (resp * x[:, None]).sum(axis=0) / np.maximum(nk, 1e-300)
    order = np.argsort(means)
    return GapLaw(zero, tuple(float(p) for p in probs[order]),
                  tuple(float(m) for m in means[order]))


# -- inputs ------------------------------------------------------------------------------

@dataclass(frozen=True)
class LoadChainInputs:
    sessions: int
    """N, including the target's session."""
    max_running: int
    """M, the running ceiling."""
    capacity: int
    """C, entries of the reuse layer (one per request on a slot pool)."""
    gap: GapLaw
    completion_rate: Callable[[int], float]
    """c(r): completion rate of one running request when ``r`` run in total."""
    others_at_arrival: Sequence[float]
    """P(m others in the engine) seen by an arrival, m = 0..N-1 (arrival theorem)."""
    s_active: float
    own_alloc: bool = True
    completion_order: str = "random"
    """Which running request a completion is. ``random`` (exponential service:
    any of the ``R`` running, so older than T with probability ``a / R``),
    ``admission`` (service lengths alike under processor sharing: requests
    admitted earlier finish earlier, so an older entry finishes first
    whenever one runs) or ``pairwise`` (model v1.2: an older request finishes
    before a newer one with probability ``rho``, so with ``a`` older among
    ``R`` running the finisher is older with probability
    ``a*rho / (a*rho + (R - a)*(1 - rho))``; ``rho`` = 1/2 is ``random``,
    ``rho`` = 1 is ``admission``)."""
    rho: float | None = None
    """For ``pairwise``: P(an older running request finishes before a newer
    one), from the plan's decode-length law (``pairwise_rho``)."""

    def __post_init__(self) -> None:
        if self.completion_order not in ("random", "admission", "pairwise"):
            raise ValueError(f"unknown completion_order {self.completion_order!r}")
        if self.completion_order == "pairwise" and (self.rho is None or not 0.5 <= self.rho <= 1):
            raise ValueError("pairwise completion needs rho in [0.5, 1]")
        if self.sessions < 1 or self.max_running < 1 or self.capacity < 1:
            raise ValueError("sessions, max_running and capacity must be positive")
        if len(self.others_at_arrival) != self.sessions:
            raise ValueError("others_at_arrival must cover m = 0..N-1")
        if self.s_active < 0:
            raise ValueError("s_active must be non-negative")
        if self.capacity < self.max_running:
            raise ValueError("v1.1 assumes every running request holds its own entry (C >= M)")


# -- state space -------------------------------------------------------------------------

class _Space:
    """States (m, n_0..n_{K-2}, a, d); the last phase count is implied. DEAD last."""

    def __init__(self, n_others: int, phases: int, m_cap: int, cap: int):
        self.n_others, self.k = n_others, phases
        self.load = []
        for m in range(n_others + 1):
            for ns in _compositions(n_others - m, phases):
                self.load.append((m,) + ns[:-1])
        self.states = [ld + (a, d) for ld in self.load
                       for a in range(min(ld[0], m_cap) + 1) for d in range(cap - a)]
        self.index = {s: i for i, s in enumerate(self.states)}
        self.dead = len(self.states)
        self.size = self.dead + 1

    def phases_of(self, ld: tuple) -> tuple[int, ...]:
        m, rest = ld[0], ld[1:]
        return rest + (self.n_others - m - sum(rest),)

    def at(self, m: int, ns: Sequence[int], a: int, d: int) -> int:
        return self.index[(m,) + tuple(ns[:-1]) + (a, d)]


def _compositions(total: int, parts: int):
    """All tuples of ``parts`` non-negative ints summing to ``total``."""
    if parts == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for rest in _compositions(total - first, parts - 1):
            yield (first,) + rest


def _p_older(inp: LoadChainInputs, a: int, run: int) -> float:
    """P(the request that finishes is older than T), ``a`` older among ``run``."""
    if inp.completion_order == "random":
        return a / run
    if inp.completion_order == "admission":
        return float(a > 0)
    num = a * inp.rho
    den = num + (run - a) * (1 - inp.rho)
    return num / den if den else 0.0


def pairwise_rho(decode_lengths: Sequence[float]) -> float:
    """P(an older running request finishes first) under processor sharing:
    the older one's remaining work is the equilibrium residual of the
    decode-length law, the newer one's is a fresh draw. 1/2 for an exponential
    law, 1 for a constant one. A workload quantity (the plan's lengths)."""
    xs = sorted(float(x) for x in decode_lengths)
    n = len(xs)
    mean = sum(xs) / n
    pref = [0.0]
    for x in xs:
        pref.append(pref[-1] + x)
    from bisect import bisect_right

    def residual_cdf(y: float) -> float:
        k = bisect_right(xs, y)
        return (pref[k] + (n - k) * y) / n / mean
    return sum(residual_cdf(y) for y in xs) / n


def _expm(q, p):
    """``expm_multiply`` with its 1-norm estimator's random start fixed.

    SciPy's ``onenormest`` draws its start vectors from the global
    ``np.random`` state, so the same call can choose a different evaluation
    order and differ in the last digits from run to run (TASK90). The global
    state is saved and restored."""
    state = np.random.get_state()
    try:
        np.random.seed(20261001)
        return expm_multiply(q, p)
    finally:
        np.random.set_state(state)


def _evict(d: int, active: bool):
    if d > 0:
        return d - 1, False
    return d, not active


def _generator(inp: LoadChainInputs, sp: _Space, active: bool) -> csr_matrix:
    g = inp.gap
    m_t = inp.max_running - (1 if active else 0)
    rows, cols, vals = [], [], []

    def add(i: int, j: int, rate: float) -> None:
        if rate <= 0:
            return
        rows.extend((i, i))
        cols.extend((j, i))
        vals.extend((rate, -rate))

    for i, st in enumerate(sp.states):
        m, a, d = st[0], st[-2], st[-1]
        ns = list(sp.phases_of(st[:-2]))
        run = min(m, m_t)
        queued = m - run
        # returns from gap phases
        for k, nk in enumerate(ns):
            if nk == 0:
                continue
            rate = nk / g.means[k]
            nn = ns.copy()
            nn[k] -= 1
            if queued == 0 and run < m_t:
                nd, dead = _evict(d, active)
                add(i, sp.dead if dead else sp.at(m + 1, nn, a, nd), rate)
            else:
                add(i, sp.at(m + 1, nn, a, d), rate)
        # completions of running others
        if run > 0:
            rate = run * inp.completion_rate(run + (1 if active else 0))
            p_old = _p_older(inp, a, run)
            for older, po in ((True, p_old), (False, 1 - p_old)):
                if po <= 0:
                    continue
                na, nd = (a - 1, d + 1) if older else (a, d)
                dead = False
                if queued > 0:                       # queue head takes the place
                    nd, dead = _evict(nd, active)
                if dead:
                    add(i, sp.dead, rate * po)
                    continue
                # the finished session's next gap
                if g.zero_prob > 0:                  # back at once
                    if queued == 0:                  # its own place is free: admitted
                        nd2, dead2 = _evict(nd, active)
                        add(i, sp.dead if dead2 else sp.at(m, ns, na, nd2),
                            rate * po * g.zero_prob)
                    else:                            # joins the queue
                        add(i, sp.at(m, ns, na, nd), rate * po * g.zero_prob)
                for k, pk in enumerate(g.probs):
                    nn = ns.copy()
                    nn[k] += 1
                    add(i, sp.at(m - 1, nn, na, nd), rate * po * (1 - g.zero_prob) * pk)
    q = csr_matrix((vals, (rows, cols)), shape=(sp.size, sp.size))
    return q.T.tocsr()


# -- T's arrival and admission -------------------------------------------------------------

def _phase_split(inp: LoadChainInputs, gap_total: int):
    """Multinomial split of ``gap_total`` sessions over the phases (time shares)."""
    shares = inp.gap.time_shares()
    for ns in _compositions(gap_total, len(shares)):
        coef = math.factorial(gap_total)
        p = 1.0
        for n, s in zip(ns, shares):
            coef //= math.factorial(n)
            p *= s ** n
        yield ns, coef * p


def _waiting_admission(inp: LoadChainInputs, m0: int, ns0: tuple[int, ...]) -> dict:
    """Load state when a request that found ``m0`` others (no free place) is
    admitted: embedded jump chain on (m, phases, queued ahead)."""
    g = inp.gap
    mm = inp.max_running
    comp = mm * inp.completion_rate(mm)
    out: dict = {}
    cur = {(m0, ns0, m0 - mm): 1.0}
    for _ in range(100_000):
        nxt: dict = {}
        for (m, ns, q), p in cur.items():
            rets = [nk / mk for nk, mk in zip(ns, g.means)]
            tot = comp + sum(rets)
            pc = comp / tot
            # a completion: queue head (or the waiting request) is admitted
            branches = [(g.zero_prob, None)] + [((1 - g.zero_prob) * pk, k)
                                                for k, pk in enumerate(g.probs)]
            for pb, k in branches:
                if pb <= 0:
                    continue
                nn = list(ns)
                if k is None:                   # back at once, behind the waiting request
                    m2 = m
                else:
                    nn[k] += 1
                    m2 = m - 1
                w = p * pc * pb
                if q == 0:
                    key = (m2, tuple(nn))
                    out[key] = out.get(key, 0.0) + w
                else:
                    key = (m2, tuple(nn), q - 1)
                    nxt[key] = nxt.get(key, 0.0) + w
            # a return from a gap joins behind
            for k, r in enumerate(rets):
                if r <= 0:
                    continue
                nn = list(ns)
                nn[k] -= 1
                key = (m + 1, tuple(nn), q)
                nxt[key] = nxt.get(key, 0.0) + p * r / tot
        cur = {k: v for k, v in nxt.items() if v > 1e-14}
        if not cur:
            break
    return out


def _initial(inp: LoadChainInputs, sp: _Space) -> np.ndarray:
    p0 = np.zeros(sp.size)
    mm, cap, n_oth = inp.max_running, inp.capacity, inp.sessions - 1
    for m_seen, pm in enumerate(inp.others_at_arrival):
        if pm <= 0:
            continue
        for ns, pn in _phase_split(inp, n_oth - m_seen):
            if pn <= 0:
                continue
            if m_seen < mm:
                a0 = m_seen
                p0[sp.at(m_seen, ns, a0, cap - 1 - a0)] += pm * pn
            else:
                for (m_adm, ns_adm), pa in _waiting_admission(inp, m_seen, ns).items():
                    a0 = mm - 1
                    p0[sp.at(m_adm, ns_adm, a0, cap - 1 - a0)] += pm * pn * pa
    return p0 / p0.sum()


def _target_finishes(inp: LoadChainInputs, sp: _Space, p: np.ndarray) -> np.ndarray:
    """T releases its place; a queued request takes it at once (T inactive)."""
    out = np.zeros_like(p)
    out[sp.dead] = p[sp.dead]
    for i, st in enumerate(sp.states):
        if p[i] == 0:
            continue
        m, a, d = st[0], st[-2], st[-1]
        if m > inp.max_running - 1:
            nd, dead = _evict(d, active=False)
            j = sp.dead if dead else sp.index[st[:-1] + (nd,)]
            out[j] += p[i]
        else:
            out[i] += p[i]
    return out


def _returning(inp: LoadChainInputs, sp: _Space, p: np.ndarray) -> float:
    """P(T still cached at R's lookup) from the state at R's return. Returns
    and zero-gap re-entries during R's wait queue behind R and do not matter."""
    mm = inp.max_running
    agg: dict = {}
    for i, st in enumerate(sp.states):
        if p[i] > 0:
            key = (st[0], st[-2], st[-1])
            agg[key] = agg.get(key, 0.0) + p[i]
    alive = 0.0
    for (m, a, d), pi in agg.items():
        if m < mm:
            alive += pi * (d > 0 or not inp.own_alloc)
            continue
        dist = {(a, d): pi}
        for step in range(m - mm + 1):
            nxt: dict = {}
            last = step == m - mm
            for (aa, dd), w in dist.items():
                p_old = _p_older(inp, aa, mm)
                for older, q in ((True, p_old), (False, 1 - p_old)):
                    if q <= 0:
                        continue
                    na, nd = (aa - 1, dd + 1) if older else (aa, dd)
                    if not last or inp.own_alloc:
                        if nd == 0:
                            continue
                        nd -= 1
                    nxt[(na, nd)] = nxt.get((na, nd), 0.0) + w * q
            dist = nxt
        alive += sum(dist.values())
    return alive


def survival_probability_v11(inp: LoadChainInputs,
                             idle_samples: Sequence[tuple[float, float]]) -> float:
    """P(T survives to R's lookup), averaged over T's idle-time samples ``(s, weight)``."""
    sp = _Space(inp.sessions - 1, len(inp.gap.probs), inp.max_running, inp.capacity)
    p = _initial(inp, sp)
    if inp.s_active > 0:
        p = np.clip(_expm(_generator(inp, sp, active=True) * inp.s_active, p), 0.0, None)
    p = _target_finishes(inp, sp, p)
    q_idle = _generator(inp, sp, active=False)
    tot_w = sum(w for _, w in idle_samples)
    acc = 0.0
    t_prev = 0.0
    for s_idle, w in sorted(idle_samples):
        if s_idle > t_prev:
            p = np.clip(_expm(q_idle * (s_idle - t_prev), p), 0.0, None)
            t_prev = s_idle
        acc += w * _returning(inp, sp, p)
    return acc / tot_w


def check_substrate(descriptor) -> None:
    """Refuse substrates outside v1.1's scope (reads a v2 descriptor)."""
    if descriptor.eviction_order != "allocation_fifo":
        raise NotImplementedError("v1.1 is the allocation-FIFO d-rule; a release-ordered "
                                  "LRU pool needs its own queue-aware form")
    sem = descriptor.semantics
    if sem.evictable_when != "immediate":
        raise NotImplementedError("v1.1 assumes an entry is evictable at release")
    if sem.intra_request_loss != "all_or_nothing":
        raise NotImplementedError("v1.1 counts whole entries")
    if sem.resume_allocates_first is None or descriptor.admission.max_running is None:
        raise ValueError("descriptor must establish resume_allocates_first and max_running")
    if descriptor.reuse_pool.capacity_units is None:
        raise ValueError("descriptor must establish the reuse layer capacity")

