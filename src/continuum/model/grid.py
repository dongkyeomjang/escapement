"""Best bucket grid for a given running-count histogram.

Problem
-------
Given a histogram ``h(n)`` of decode steps by running count ``n`` (a count or
a share; only ratios matter) and a step cost ``t_step(b, n)``, choose a set of
compiled widths ``G`` that contains ``1`` and ``top`` (the batch size, which is
also the KV pool size) and has at most ``k`` members, to minimise::

    cost(G) = sum_n h(n) * t_step(b_G(n), n),   b_G(n) = min{b in G : b >= n}

With the step-cost shape the descriptor uses,
``t_step(b, n) = fixed(b) + intercept + marginal * n``, only ``fixed(b)``
depends on ``G``; the other two terms are the same for every grid and are
added back for reporting.

Dynamic programme
-----------------
Sort the grid ``1 = b_1 < ... < b_j = top``. Width ``b_i`` serves the
running counts ``b_{i-1} < n <= b_i``. With ``H(a, b] = sum_{a<n<=b} h(n)``::

    F[1][1]  = h(1) * fixed(1)
    F[j][b]  = min_{b' < b} F[j-1][b'] + fixed(b) * H(b', b]
    optimum  = min_{j <= k} F[j][top]

``O(k * top^2)``. Ties are broken towards the lexicographically smallest grid
so the result is reproducible and comparable with exhaustive enumeration.

Unmeasured widths
-----------------
Costs for widths a substrate has not measured follow the rule already used by
the compile-configuration search (``config_search.descriptor_for``): linear
interpolation between the nearest measured widths on either side, linear
extrapolation from the outermost measured pair beyond the range. No new rule
is introduced; ``interpolated_fixed_costs`` restates it and the self-check
confirms it gives the same numbers as that function.

What this does not model
------------------------
The histogram is taken as given. In a real run it moves with the grid: a
cheaper grid finishes steps sooner, sessions return at other times and the
running counts change (TASK68). The optimum here is the best response to one
histogram, not a fixed point of grid and histogram.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import itertools
import math


def interpolated_fixed_costs(measured: Mapping[int, float],
                             widths: Iterable[int]) -> dict[int, float]:
    """Fixed cost for every width in ``widths``, measured or not.

    Identical to the rule in ``experiments/npu/analysis/config_search.py``
    (``descriptor_for``): measured widths keep their value; an unmeasured
    width inside the range is interpolated between its nearest measured
    neighbours; below the range it uses the first two measured widths, above
    it the last two.
    """
    fixed = dict(measured)
    known = sorted(measured)
    if len(known) < 2:
        raise ValueError("need at least two measured widths")
    for b in widths:
        if b in fixed:
            continue
        lo = max((x for x in known if x < b), default=None)
        hi = min((x for x in known if x > b), default=None)
        if lo is None:
            lo, hi = known[0], known[1]
        elif hi is None:
            lo, hi = known[-2], known[-1]
        fixed[b] = fixed[lo] + (b - lo) / (hi - lo) * (fixed[hi] - fixed[lo])
    return fixed


def bucket_of(grid: tuple[int, ...], n: int) -> int:
    for b in grid:
        if b >= n:
            return b
    raise ValueError(f"{n} exceeds the largest width {grid[-1]}")


def grid_fixed_cost(grid: tuple[int, ...], h: Mapping[int, float],
                    fixed: Mapping[int, float]) -> float:
    """Grid-dependent part of the objective, summed per running count."""
    return sum(w * fixed[bucket_of(grid, n)] for n, w in h.items() if w)


def grid_total_cost(grid: tuple[int, ...], h: Mapping[int, float],
                    fixed: Mapping[int, float], *, intercept: float = 0.0,
                    marginal: float = 0.0) -> float:
    """Full ``sum h(n) t_step(b(n), n)`` including the grid-independent terms."""
    return (grid_fixed_cost(grid, h, fixed)
            + sum(w * (intercept + marginal * n) for n, w in h.items()))


@dataclass(frozen=True)
class GridSolution:
    grid: tuple[int, ...]
    fixed_cost: float


def _validate(h: Mapping[int, float], top: int, max_buckets: int) -> None:
    if top < 1:
        raise ValueError("top must be >= 1")
    if max_buckets < (1 if top == 1 else 2):
        raise ValueError("max_buckets must allow both 1 and top")
    for n, w in h.items():
        if not 1 <= n <= top:
            raise ValueError(f"running count {n} outside 1..{top}")
        if w < 0:
            raise ValueError("histogram weights must be non-negative")


def optimal_grid(h: Mapping[int, float], *, top: int, max_buckets: int,
                 fixed: Mapping[int, float]) -> GridSolution:
    """Dynamic programme described in the module docstring."""
    _validate(h, top, max_buckets)
    if top == 1:
        return GridSolution((1,), grid_fixed_cost((1,), h, fixed))
    prefix = [0.0] * (top + 1)
    for n in range(1, top + 1):
        prefix[n] = prefix[n - 1] + h.get(n, 0.0)

    def seg(a: int, b: int) -> float:
        return prefix[b] - prefix[a]

    # best[j][b] = (cost, grid) using j widths, the largest being b.
    best: list[dict[int, tuple[float, tuple[int, ...]]]] = [dict() for _ in range(max_buckets + 1)]
    best[1][1] = (h.get(1, 0.0) * fixed[1], (1,))
    for j in range(2, max_buckets + 1):
        for b in range(2, top + 1):
            cand = None
            for bp, (c, g) in best[j - 1].items():
                if bp >= b:
                    continue
                val = (c + fixed[b] * seg(bp, b), g + (b,))
                if cand is None or _better(val, cand):
                    cand = val
            if cand is not None:
                best[j][b] = cand
    finals = [best[j][top] for j in range(2, max_buckets + 1) if top in best[j]]
    win = finals[0]
    for f in finals[1:]:
        if _better(f, win):
            win = f
    return GridSolution(win[1], win[0])


def _better(a: tuple[float, tuple[int, ...]], b: tuple[float, tuple[int, ...]]) -> bool:
    """Lower cost wins; within floating tolerance the smaller grid tuple wins."""
    tol = 1e-12 * max(1.0, abs(a[0]), abs(b[0]))
    if a[0] < b[0] - tol:
        return True
    if a[0] > b[0] + tol:
        return False
    return a[1] < b[1]


def enumerate_grids(top: int, max_buckets: int) -> Iterable[tuple[int, ...]]:
    """Every grid containing 1 and ``top`` with at most ``max_buckets`` widths."""
    if top == 1:
        yield (1,)
        return
    inner = range(2, top)
    for k in range(0, max_buckets - 1):
        for mid in itertools.combinations(inner, k):
            yield (1,) + mid + (top,)


def brute_force_grid(h: Mapping[int, float], *, top: int, max_buckets: int,
                     fixed: Mapping[int, float]) -> tuple[GridSolution, list[GridSolution]]:
    """Exhaustive optimum and every grid tied with it (within tolerance)."""
    _validate(h, top, max_buckets)
    scored = [GridSolution(g, grid_fixed_cost(g, h, fixed))
              for g in enumerate_grids(top, max_buckets)]
    lo = min(s.fixed_cost for s in scored)
    tol = 1e-12 * max(1.0, abs(lo))
    ties = sorted((s for s in scored if s.fixed_cost <= lo + tol), key=lambda s: s.grid)
    return ties[0], ties


def count_grids(top: int, max_buckets: int) -> int:
    if top == 1:
        return 1
    return sum(math.comb(top - 2, k) for k in range(0, max_buckets - 1))
