"""Analytic model v1, GPU instance (directive G-03 5.1 predictor 1).

Imports the neutral model code unchanged and supplies only GPU inputs:

* B2 -- ``continuum.model.occupancy``: closed network of ``N`` sessions, the
  engine as processor sharing with ``max_num_seqs`` servers. Decode step time
  ``t(r)`` is ``gpu_cost.decode_ms`` on the capture grid. The GPU mixes
  prefill into decode steps instead of stopping the decoders; the time a
  step spends on prefill is the increment ``gpu_cost`` prices, which is what
  B2's ``phi = 1 - X * E[P]`` removes from decode, so ``E[P]`` is the mean
  prefill *increment* per request.
* B1 v1, LRU form -- ``continuum.model.survival_v1.lru_block_survival``: the
  released session's ``u`` blocks join the free queue tail behind ``d0``
  blocks; the queue head is consumed by allocations (``lam_blocks``, Poisson)
  and, on this stack, also by returning sessions touching their own cached
  blocks that sit ahead of it (hit blocks leave the queue without an
  eviction). The wrapper folds the second stream into ``d0``:
  ``d0 = E[free] - u - E[blocks touched ahead during the idle time]``.
  Returning sessions that were idle when T was released are exactly the ones
  whose blocks are ahead of T; each returns within ``s`` with the
  equilibrium-residual probability of the gap law.
* B3 -- ``continuum.model.grid.optimal_grid`` with ``F[b]`` from GTASK05.
* B4 -- interference per turn ``E[P] * E[K_arr]``: the extra step time a
  prefill adds, paid by every request running when it arrives.

Reuse and the prefill increment are solved together (a miss prefills more,
which lowers decode throughput, which changes the allocation rate).
Only plan files and GTASK01-05 constants are read.
"""

from __future__ import annotations

from bisect import bisect_right
import math
from pathlib import Path
import statistics
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from continuum.model import grid as G  # noqa: E402
from continuum.model import occupancy as O  # noqa: E402
from continuum.model.survival_v1 import lru_block_survival  # noqa: E402
from continuum.workload.multiturn import MultiTurnPlan  # noqa: E402
import gpu_cost as C  # noqa: E402
from gpu_mt_sim import BLOCK, GpuConfig  # noqa: E402


def plan_samples(plans: list[MultiTurnPlan]) -> dict:
    """Per-request quantities the analytic path needs, from the plan files."""
    first, later, gens, gaps = [], [], [], []
    for plan in plans:
        for s in plan.slots:
            for x in s.sessions:
                ctx = 0
                prev_fed = 0
                prev_gap = 0.0
                for t in x.turns:
                    prompt = ctx + t.new_segment_tokens
                    gens.append(t.generation_tokens)
                    gaps.append(t.gap_after_s)
                    if t.index == 0:
                        first.append((prompt, t.generation_tokens))
                    else:
                        u = min(prev_fed // BLOCK, (prompt - 1) // BLOCK)
                        later.append((prompt, t.generation_tokens, u, prev_gap))
                    prev_fed = prompt + t.generation_tokens - 1
                    prev_gap = t.gap_after_s
                    ctx = prompt + t.generation_tokens
    return {"first": first, "later": later, "gen_mean": statistics.mean(gens),
            "think_mean_s": statistics.mean(gaps),
            "idle_gaps": sorted(g for g in gaps if g > 0),
            "share_first": len(first) / (len(first) + len(later))}


def lru_survival(*, target_blocks: int, d0_blocks: int, lam_blocks: float,
                 s_idle: float) -> list[float]:
    """``lru_block_survival`` with the Poisson pmf evaluated in log space.

    The neutral function builds the pmf from ``exp(-mean)``, which underflows
    to 0 for ``mean > ~745``; every mass then lands on the last entry and the
    target is reported lost whatever ``d0`` is. The GPU inputs reach such
    means (allocation rate x a tool gap of tens of seconds), so the same
    formula -- ``lost = min(u, max(0, N_ev - d0))``, ``N_ev ~ Poisson`` -- is
    evaluated here; below the underflow it defers to the neutral function
    (checked equal in ``_self_check``).
    """
    mean = lam_blocks * s_idle
    if mean < 600:
        return lru_block_survival(target_blocks=target_blocks, d0_blocks=d0_blocks,
                                  lam_blocks=lam_blocks, s_idle=s_idle)
    out = [0.0] * (target_blocks + 1)
    lm = math.log(mean)
    # P(N_ev <= d0) survives whole; d0 < N_ev < d0 + u partial; beyond: lost
    def lp(k: int) -> float:
        return -mean + k * lm - math.lgamma(k + 1)
    cdf_d0 = sum(math.exp(lp(k)) for k in range(max(0, d0_blocks - 4000), d0_blocks + 1))
    out[target_blocks] = cdf_d0
    acc = cdf_d0
    for j in range(1, target_blocks):
        pk = math.exp(lp(d0_blocks + j))
        out[target_blocks - j] += pk
        acc += pk
    out[0] += max(0.0, 1.0 - acc)
    return out


def _self_check() -> None:
    for u, d0, lam, s in ((140, 150, 42.0, 3.0), (100, 500, 30.0, 12.0), (50, 0, 10.0, 0.5)):
        a = lru_block_survival(target_blocks=u, d0_blocks=d0, lam_blocks=lam, s_idle=s)
        # force the log-space branch on the same inputs
        mean = lam * s
        lm = math.log(mean)
        lp = lambda k: -mean + k * lm - math.lgamma(k + 1)  # noqa: E731
        b = [0.0] * (u + 1)
        b[u] = sum(math.exp(lp(k)) for k in range(0, d0 + 1))
        acc = b[u]
        for j in range(1, u):
            b[u - j] += math.exp(lp(d0 + j)); acc += math.exp(lp(d0 + j))
        b[0] += max(0.0, 1.0 - acc)
        assert max(abs(x - y) for x, y in zip(a, b)) < 1e-9, (u, d0, lam, s)


def _residual_cdf(gaps_sorted: list[float]):
    """P(R <= s) for the equilibrium residual of the gap law (samples)."""
    mean = statistics.mean(gaps_sorted)
    n = len(gaps_sorted)
    prefix = [0.0]
    for g in gaps_sorted:
        prefix.append(prefix[-1] + g)

    def cdf(s: float) -> float:
        # integral_0^s P(G > x) dx = sum_i min(g_i, s) / n
        k = bisect_right(gaps_sorted, s)
        return min(1.0, (prefix[k] + (n - k) * s) / n / mean)
    return cdf


def _chunks_inc(p: int, running: float, grid, bound: str, budget: int = 2048) -> float:
    """Prefill increment of a ``p``-token prompt remainder, chunked by the budget."""
    tot, left = 0.0, p
    d = max(0, round(running))
    while left > 0:
        c = min(left, budget - d)
        tot += C.prefill_increment_ms(c, d + c, grid, bound) / 1e3
        left -= c
    return tot


def analytic(n: int, cfg: GpuConfig, st: dict, *, bound: str, iters: int = 60) -> dict:
    grid = tuple(sorted(cfg.capture_sizes))
    cap = cfg.num_gpu_blocks - 1
    t_step = lambda r: C.decode_ms(r, grid) / 1e3  # noqa: E731
    later = st["later"]
    res_cdf = _residual_cdf(st["idle_gaps"])
    u_mean = statistics.mean(u for _, _, u, _ in later)
    run_blocks = statistics.mean([(p + g / 2) / BLOCK for p, g in st["first"]] +
                                 [(p + g / 2) / BLOCK for p, g, _, _ in later])
    # (u rounded to 4 blocks, gap quantised to 2 %) -> weight: same arithmetic, fewer calls
    groups: dict[tuple[int, float], int] = {}
    for _, _, u, gap in later:
        key = (4 * round(u / 4), round(gap, 2) if gap < 1 else float(f"{gap:.2g}"))
        groups[key] = groups.get(key, 0) + 1
    p_hit = 0.9
    tok_ratio = 0.9
    running = 1.0
    occ = None
    for _ in range(iters):
        # expected prefill increment per request at the current reuse
        e_first = statistics.mean(_chunks_inc(p, running, grid, bound) for p, _ in st["first"])
        e_later = statistics.mean(
            tok_ratio * _chunks_inc(p - u * BLOCK, running, grid, bound)
            + (1 - tok_ratio) * _chunks_inc(p, running, grid, bound)
            for p, _, u, _ in later)
        ep = st["share_first"] * e_first + (1 - st["share_first"]) * e_later
        w = O.ClosedWorkload(sessions=n, decode_steps_per_request=st["gen_mean"] - 1,
                             think_mean_s=st["think_mean_s"], prefill_mean_s=ep,
                             max_running=cfg.max_num_seqs)
        occ = O.solve_occupancy(w, t_step)
        running = occ.mean_running
        x = occ.throughput_per_s
        service = ep + (st["gen_mean"] - 1) * t_step(max(1, round(running))) / occ.phi
        wait = max(0.0, occ.mean_response_s - service)
        free = max(0.0, cap - running * run_blocks)
        new_blocks = st["share_first"] * statistics.mean((p + g - 1) / BLOCK for p, g in st["first"]) + \
            (1 - st["share_first"]) * statistics.mean(
                (p + g - 1) / BLOCK - tok_ratio * u for p, g, u, _ in later)
        lam = x * new_blocks
        idle_others = max(0.0, (n - 1) - running * (n - 1) / n)
        hits = toks = 0.0
        for (u, gap), wgt in groups.items():
            s_idle = gap + wait
            touched = idle_others * res_cdf(s_idle) * p_hit * u_mean
            d0 = max(0, int(round(free - u - touched)))
            dist = lru_survival(target_blocks=u, d0_blocks=d0, lam_blocks=lam, s_idle=s_idle)
            hits += wgt * (1.0 - dist[0])
            toks += wgt * (sum(k * pk for k, pk in enumerate(dist)) / u if u else 0.0)
        new_p = hits / len(later)
        new_t = toks / len(later)
        if abs(new_p - p_hit) < 1e-7 and abs(new_t - tok_ratio) < 1e-7:
            p_hit, tok_ratio = new_p, new_t
            break
        p_hit, tok_ratio = 0.5 * (p_hit + new_p), 0.5 * (tok_ratio + new_t)
    x = occ.throughput_per_s
    h = occ.step_share
    decode_s_per_s = sum(h[r] * t_step(r) for r in h) * occ.steps_per_s
    pads = [(r, C.padded(grid, r) or r) for r in h]
    pad = sum(h[r] * (b - r) for r, b in pads) / sum(h[r] * b for r, b in pads)
    arr = O.arrival_running_distribution(w, t_step)
    e_k = sum(k * p for k, p in arr.items())
    return {"reuse_rate": p_hit, "token_reuse_ratio": tok_ratio,
            "h": {int(k): v for k, v in h.items()}, "padding": pad,
            "decode_per_turn_s": decode_s_per_s / x, "prefill_per_turn_s": ep,
            "device_per_turn_s": decode_s_per_s / x + ep,
            "interference_per_turn_s": ep * e_k, "throughput_per_s": x,
            "cycle_s": st["think_mean_s"] + occ.mean_response_s,
            "mean_running": occ.mean_running, "phi": occ.phi, "bound": bound}


def dp_grid(h: dict[int, float], *, top: int, k: int, extra: tuple[int, ...] = (16,)) -> tuple[int, ...]:
    """B3 DP over decode widths 1..top with GTASK05 ``F[b]``, plus ``extra``
    capture sizes kept for mixed steps (the default grid's 16)."""
    fixed = {b: C.F_MS[b] for b in range(1, top + 1)}
    hh = {r: v for r, v in h.items() if 1 <= r <= top and v > 0}
    g = G.optimal_grid(hh, top=top, max_buckets=k, fixed=fixed).grid
    return tuple(sorted(set(g) | set(extra)))
