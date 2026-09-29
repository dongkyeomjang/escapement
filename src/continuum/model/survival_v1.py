"""Model v1 survival: one state variable instead of a window count.

Why v0's closed form fell short
-------------------------------
v0 wrote survival as ``1 + A + K_pin + D <= C`` with ``A`` the allocations in
the window and ``K_pin`` counted at the lookup. Under concurrent load that
matched 83.3 % of 1,298 re-arrivals (TASK72) while the event replay matched
all of them. Two things were missing, and both are about *which* entry an
eviction takes:

* While T itself is active it cannot be evicted, so an eviction that would
  otherwise have reached it falls on a newer inactive entry instead. Counting
  every allocation in the window against T overstates the danger.
* Entries older than T that are still running are skipped by an eviction, so
  they push the victim towards T. What matters is how many of them are active
  *at each eviction*, not at the lookup.

The state variable
------------------
Let ``d`` be the number of entries older than T that are in the pool and
inactive. The reference rule (``reference.py``) then reads:

* an eviction with ``d > 0`` removes one of them: ``d -> d - 1``;
* an eviction with ``d = 0`` removes T if T is inactive, and otherwise a newer
  inactive entry (T is protected while it runs);
* an older active entry that finishes joins them: ``d -> d + 1``, ``a -> a - 1``
  (``a`` = older active entries, which only ever decreases: no entry created
  after T is older than T);
* an allocation while slots are free consumes a slot and evicts nothing:
  ``f -> f - 1``.

Right after T is placed, with ``f0`` free slots and ``k`` other requests
running (all older than T)::

    a0 = k,   d0 = (C - f0 - 1) - k

In a full pool (``f0 = 0``) this is ``d0 = C - 1 - k``. ``track_target`` applies
these transitions to an observed event sequence and is exact (it reproduces
the reference replay; see the self-check). ``survival_probability_v1`` is the
approximation: allocations by other sessions arrive as a Poisson process of
rate ``lam``, each older active entry finishes at rate ``mu``, T is active for
``s_active`` seconds and then inactive for ``s_idle`` seconds, and finally the
returning request's own allocation (taken before its lookup) is one more
allocation. Survival is the probability of not being absorbed -- a finite
birth-death chain on ``(f, a, d)``, solved by uniformization.

Degenerate case: with ``s_active = 0``, ``a0 = 0``, ``f0 = 0`` and ``d0 = C - 1``
the chain survives iff the Poisson count ``N`` of other allocations satisfies
``N + 1 <= C - 1``, i.e. v0's ``1 + A <= C`` with ``A = N + 1`` -- the same
probability v0 gives with its Poisson count law.

Block pools with LRU over a free queue
--------------------------------------
There the queue holds only released blocks and is ordered by release. T enters
it on release, so there is no protection phase to model and no older active
entries can join *ahead* of T later: every release after T's goes behind it.
``d`` becomes a pure death process in blocks, and with lookup before
allocation the returning request's own blocks do not count. ``lru_block_survival``
computes the distribution of surviving leading blocks (tail first).

Nothing here names an accelerator.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import math


# -- exact tracker ---------------------------------------------------------------

def initial_state(*, capacity: int, free_after: int, running_others: int) -> tuple[int, int, int]:
    """(f0, a0, d0) right after T is placed."""
    if not 0 <= free_after < capacity:
        raise ValueError("free_after must be in [0, capacity)")
    resident_older = capacity - free_after - 1
    if running_others > resident_older:
        raise ValueError("more running requests than older resident entries")
    return free_after, running_others, resident_older - running_others


def track_target(*, f0: int, a0: int, d0: int, events: Iterable[str]) -> bool:
    """Apply the d-rule to T's window and report whether T survives.

    ``events`` in order, each one of:
    ``"alloc"``         an allocation by someone else (consumes a free slot or
                        causes an eviction);
    ``"evict"``         an eviction not tied to an allocation (padding path);
    ``"older_release"`` an older active entry finished;
    ``"target_release"`` T finished;
    ``"own_alloc"``     the returning request's own allocation (last event when
                        the substrate allocates before looking up).
    """
    f, a, d = f0, a0, d0
    active = True
    for e in events:
        if e in ("alloc", "own_alloc", "evict"):
            if e != "evict" and f > 0:
                f -= 1
                continue
            if d > 0:
                d -= 1
            elif not active:
                return False
            # else: T protected, a newer inactive entry goes
        elif e == "older_release":
            if a <= 0:
                raise ValueError("older_release with no older active entry")
            a -= 1
            d += 1
        elif e == "target_release":
            active = False
        else:
            raise ValueError(f"unknown event {e!r}")
    return True


# -- approximation -----------------------------------------------------------------

@dataclass(frozen=True)
class V1Inputs:
    capacity: int
    f0: int
    a0: int
    d0: int
    lam: float
    """Allocation rate of the other sessions, per second."""
    mu: float
    """Completion rate of one older active entry, per second."""
    s_active: float
    """How long T stays active after it is placed (its own prefill + decode)."""
    s_idle: float
    """Tool gap plus any wait before the returning request is admitted."""
    own_alloc: bool = True

    def __post_init__(self) -> None:
        if min(self.f0, self.a0, self.d0) < 0:
            raise ValueError("state must be non-negative")
        if self.f0 + self.a0 + self.d0 > self.capacity - 1:
            raise ValueError("state exceeds the pool")
        if self.lam < 0 or self.mu < 0 or self.s_active < 0 or self.s_idle < 0:
            raise ValueError("rates and durations must be non-negative")


_DEAD = ("dead",)


def _step(dist: dict, *, lam: float, mu: float, active: bool, big: float) -> dict:
    """One uniformized jump: each state moves with probability rate/big."""
    out: dict = {}

    def add(s, p):
        out[s] = out.get(s, 0.0) + p

    for s, p in dist.items():
        if s == _DEAD:
            add(s, p)
            continue
        f, a, d = s
        stay = 1.0
        if lam > 0:
            q = lam / big
            stay -= q
            if f > 0:
                add((f - 1, a, d), p * q)
            elif d > 0:
                add((f, a, d - 1), p * q)
            elif active:
                add(s, p * q)
            else:
                add(_DEAD, p * q)
        if a > 0 and mu > 0:
            q = a * mu / big
            stay -= q
            add((f, a - 1, d + 1), p * q)
        add(s, p * stay)
    return out


def _evolve(dist: dict, *, t: float, lam: float, mu: float, a_max: int,
            active: bool, tol: float = 1e-13) -> dict:
    if t <= 0:
        return dict(dist)
    big = lam + a_max * mu
    if big <= 0:
        return dict(dist)
    x = big * t
    # Poisson weights of the number of uniformized jumps.
    k = 0
    w = math.exp(-x) if x < 700 else 0.0
    if w == 0.0:
        # Very long horizon: split it to keep the weights representable.
        half = _evolve(dist, t=t / 2, lam=lam, mu=mu, a_max=a_max, active=active, tol=tol)
        return _evolve(half, t=t / 2, lam=lam, mu=mu, a_max=a_max, active=active, tol=tol)
    acc: dict = {s: w * p for s, p in dist.items()}
    cur = dict(dist)
    cum = w
    while 1.0 - cum > tol:
        k += 1
        cur = _step(cur, lam=lam, mu=mu, active=active, big=big)
        w *= x / k
        cum += w
        for s, p in cur.items():
            acc[s] = acc.get(s, 0.0) + w * p
        if k > 100000:
            break
    return acc


def survival_probability_v1(inp: V1Inputs) -> float:
    dist = {(inp.f0, inp.a0, inp.d0): 1.0}
    dist = _evolve(dist, t=inp.s_active, lam=inp.lam, mu=inp.mu, a_max=inp.a0, active=True)
    dist = _evolve(dist, t=inp.s_idle, lam=inp.lam, mu=inp.mu, a_max=inp.a0, active=False)
    alive = 0.0
    for s, p in dist.items():
        if s == _DEAD:
            continue
        f, a, d = s
        if inp.own_alloc and f == 0 and d == 0:
            continue    # the returning request's own allocation evicts T
        alive += p
    return min(1.0, max(0.0, alive))


def steady_state_survival(*, capacity: int, running_others_pmf: dict[int, float],
                          lam: float, mu: float, s_active: float,
                          idle_samples: Sequence[tuple[float, float]],
                          own_alloc: bool = True) -> float:
    """v1 in a full pool, averaged over the running count an arrival sees
    (arrival theorem, from ``occupancy.arrival_running_distribution``) and over
    the idle-time distribution."""
    tot_w = sum(w for _, w in idle_samples)
    acc = 0.0
    for k, pk in running_others_pmf.items():
        if pk <= 0:
            continue
        k_eff = min(k, capacity - 1)
        for s_idle, w in idle_samples:
            acc += pk * w * survival_probability_v1(V1Inputs(
                capacity=capacity, f0=0, a0=k_eff, d0=capacity - 1 - k_eff,
                lam=lam, mu=mu, s_active=s_active, s_idle=s_idle, own_alloc=own_alloc))
    return acc / (tot_w * sum(running_others_pmf.values()))


# -- LRU / block pool ----------------------------------------------------------------

def lru_block_survival(*, target_blocks: int, d0_blocks: int, lam_blocks: float,
                       s_idle: float, upto: int | None = None) -> list[float]:
    """P(k leading target blocks survive), k = 0..target_blocks.

    Free-queue LRU: T's blocks enter the queue at release, behind the
    ``d0_blocks`` released earlier; later releases queue behind T. Blocks are
    evicted from the front at the rate other admissions need them
    (``lam_blocks``, Poisson), tail of a chain first. Lookup precedes the
    returning request's allocation, so its own blocks are not charged.
    """
    mean = lam_blocks * s_idle
    top = upto if upto is not None else d0_blocks + target_blocks + 1
    pmf = [math.exp(-mean)]
    for n in range(1, top + 1):
        pmf.append(pmf[-1] * mean / n)
    pmf[-1] += max(0.0, 1.0 - sum(pmf))
    out = [0.0] * (target_blocks + 1)
    for n, p in enumerate(pmf):
        lost = min(target_blocks, max(0, n - d0_blocks))
        out[target_blocks - lost] += p
    return out
