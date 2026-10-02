"""Model v1.2 B2: the engine as an explicit Markov chain with exclusive prefill.

Why the product form is not enough (TASK90 diagnosis)
-----------------------------------------------------
v0-v1.1 B2 solves a closed product-form network: the gap station is a
delay station, the engine a load-dependent processor-sharing station, and
exclusive prefill enters only as a uniform slowdown ``phi = 1 - X * E[P]``.
Product form makes the running count insensitive to the gap law. On the
development set (N = 12, 14, 16) that insensitivity is what fails: with
exponential gaps the step simulator agrees with B2 (BASE N14 6.62 vs 6.68,
N16 7.50 vs 7.31), with the plan's heavy-tailed gaps it does not (6.22,
7.05), and the change has the opposite sign when prefill is not exclusive.
The interaction is mechanical: an exclusive prefill freezes every decoder for
its whole duration while sessions keep returning, so admissions bunch, and a
heavy-tailed gap law sets how many return during each freeze.

The chain
---------
State ``(w, r, j, n_1..n_K)``: ``w`` sessions waiting for admission, ``r``
decoding, ``j`` the kind of the prefill in progress (0 = none), ``n_k``
sessions in gap phase ``k``. The engine follows the exclusive scheduler of
``engine.simulate``: whenever no prefill runs, someone waits and fewer than
``M`` decode, the next waiting request is admitted at once and its prefill
starts; a prefill of kind ``i`` lasts an exponential time of mean
``prefill_means[i]``; while it runs nothing decodes. Otherwise the ``r``
decoders each finish at rate ``1 / (G * t_step(r))``. A finished session
draws its gap: zero with probability ``zero_prob`` (back in the waiting line
at once), else phase ``k`` (mean ``theta_k``). Prefill kinds are the plan's
own mixture -- a session's first turn, a later turn that hits, a later turn
that misses -- with weights from the plan and the survival probability.

The stationary law gives the step-weighted running histogram (decode steps
run at ``1 / t_step(r)`` while no prefill does), the throughput (decode
completions) and the decode busy share; device time per turn is
``decode busy / X + E[P]`` as in v1. For B1 it also gives the others'
state seen by an arrival (the ``N - 1`` chain) and the share of time a
running request is not frozen, ``P(j = 0 | r)``.

Nothing here names an accelerator; the exclusive-prefill rule is the
descriptor's ``prefill.execution = exclusive``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve

from .survival_v11 import GapLaw, _compositions


@dataclass(frozen=True)
class EngineInputs:
    sessions: int
    max_running: int
    decode_steps: float
    """G, decode steps per request (generation - 1)."""
    t_step: Callable[[int], float]
    prefill_weights: tuple[float, ...]
    prefill_means: tuple[float, ...]
    gap: GapLaw
    first_turn_prefill_s: float | None = None
    """When set, a session that comes back through the zero atom of the gap law
    (the renewal: the next session's first turn) prefills for this mean, and one
    that comes back from a gap phase (a later turn) uses ``prefill_weights`` /
    ``prefill_means`` -- the plan's turn structure instead of an independent
    draw. The waiting line is then split by kind."""

    def __post_init__(self) -> None:
        if len(self.prefill_weights) != len(self.prefill_means) or not self.prefill_weights:
            raise ValueError("prefill weights and means must match")
        if abs(sum(self.prefill_weights) - 1) > 1e-9 or min(self.prefill_means) <= 0:
            raise ValueError("prefill weights sum to 1, means positive")


@dataclass
class EngineSolution:
    states: list[tuple]
    pi: np.ndarray
    step_share: dict[int, float]
    time_running: dict[int, float]
    throughput_per_s: float
    decode_busy: float
    mean_prefill_s: float
    active_share_by_r: dict[int, float]
    """P(no prefill running | r decoding)."""
    in_engine: list[float]
    """P(w + r + [j > 0] = m), m = 0..N."""
    notes: list[str] = field(default_factory=list)

    @property
    def mean_running_steps(self) -> float:
        return sum(r * p for r, p in self.step_share.items())

    @property
    def decode_per_turn_s(self) -> float:
        return self.decode_busy / self.throughput_per_s


def _kinds(inp: EngineInputs) -> list[float]:
    """Prefill means by kind index 1..J (the first-turn kind last, if split)."""
    means = list(inp.prefill_means)
    if inp.first_turn_prefill_s is not None:
        means.append(inp.first_turn_prefill_s)
    return means


def _space(inp: EngineInputs, sessions: int):
    """States (w_first, w_later, r, j, n_1..n_{K-1}); w_first = 0 when the line
    is not split."""
    k = len(inp.gap.probs)
    jmax = len(_kinds(inp))
    split = inp.first_turn_prefill_s is not None
    states = []
    for w1 in range((sessions if split else 0) + 1):
        for w2 in range(sessions - w1 + 1):
            w = w1 + w2
            for r in range(min(inp.max_running, sessions - w) + 1):
                for j in range(jmax + 1):
                    busy = 1 if j else 0
                    rest = sessions - w - r - busy
                    if rest < 0 or (j and r + 1 > inp.max_running):
                        continue
                    if j == 0 and w > 0 and r < inp.max_running:
                        continue          # vanishing: an admission starts at once
                    for ns in _compositions(rest, k):
                        states.append((w1, w2, r, j) + ns[:-1])
    return states, {s: i for i, s in enumerate(states)}


def _settle(inp: EngineInputs, w1: int, w2: int, r: int, j: int, ns: tuple[int, ...]):
    """Resolve a vanishing state: admit (a uniformly chosen waiting request) and
    start its prefill. Returns [(prob, state)]."""
    if not (j == 0 and w1 + w2 > 0 and r < inp.max_running):
        return [(1.0, (w1, w2, r, j) + ns[:-1])]
    out = []
    w = w1 + w2
    if w1:
        out.append((w1 / w, (w1 - 1, w2, r, len(_kinds(inp))) + ns[:-1]))
    if w2:
        for i, pw in enumerate(inp.prefill_weights):
            if pw > 0:
                out.append((w2 / w * pw, (w1, w2 - 1, r, i + 1) + ns[:-1]))
    return out


def solve_engine(inp: EngineInputs, *, sessions: int | None = None) -> EngineSolution:
    n_s = inp.sessions if sessions is None else sessions
    states, index = _space(inp, n_s)
    g = inp.gap
    means = _kinds(inp)
    split = inp.first_turn_prefill_s is not None
    rows, cols, vals = [], [], []

    def add(i: int, target: tuple, rate: float) -> None:
        w1, w2, r, j = target[:4]
        rest = list(target[4:])
        ns = tuple(rest) + (n_s - w1 - w2 - r - (1 if j else 0) - sum(rest),)
        for p, st in _settle(inp, w1, w2, r, j, ns):
            jdx = index[st]
            rows.extend((i, i))
            cols.extend((jdx, i))
            vals.extend((rate * p, -rate * p))

    for i, st in enumerate(states):
        w1, w2, r, j = st[:4]
        rest = list(st[4:])
        ns = rest + [n_s - w1 - w2 - r - (1 if j else 0) - sum(rest)]
        for kk, nk in enumerate(ns):          # a later turn returns from a gap phase
            if nk:
                nn = ns.copy()
                nn[kk] -= 1
                add(i, (w1, w2 + 1, r, j) + tuple(nn[:-1]), nk / g.means[kk])
        if j:                                 # prefill completes
            add(i, (w1, w2, r + 1, 0) + tuple(ns[:-1]), 1.0 / means[j - 1])
        elif r:                               # a decoder finishes
            rate = r / (inp.decode_steps * inp.t_step(r))
            if g.zero_prob > 0:               # back at once (renewal -> first turn)
                tgt = (w1 + 1, w2) if split else (w1, w2 + 1)
                add(i, tgt + (r - 1, 0) + tuple(ns[:-1]), rate * g.zero_prob)
            for kk, pk in enumerate(g.probs):
                nn = ns.copy()
                nn[kk] += 1
                add(i, (w1, w2, r - 1, 0) + tuple(nn[:-1]), rate * (1 - g.zero_prob) * pk)
    q = csr_matrix((vals, (rows, cols)), shape=(len(states), len(states)))
    a = q.T.tolil()
    a[0, :] = np.ones(len(states))
    b = np.zeros(len(states))
    b[0] = 1.0
    pi = spsolve(a.tocsr(), b)
    pi = np.clip(pi, 0.0, None)
    pi /= pi.sum()
    step_rate: dict[int, float] = {}
    time_running: dict[int, float] = {}
    active: dict[int, list[float]] = {}
    in_engine = [0.0] * (n_s + 1)
    x = 0.0
    busy = 0.0
    prefill_time = [0.0] * (len(means) + 1)
    for p, st in zip(pi, states):
        w1, w2, r, j = st[:4]
        in_engine[w1 + w2 + r + (1 if j else 0)] += p
        time_running[r] = time_running.get(r, 0.0) + p
        prefill_time[j] += p
        a_ = active.setdefault(r, [0.0, 0.0])
        a_[1] += p
        if j == 0 and r > 0:
            a_[0] += p
            step_rate[r] = step_rate.get(r, 0.0) + p / inp.t_step(r)
            x += p * r / (inp.decode_steps * inp.t_step(r))
            busy += p
    tot = sum(step_rate.values())
    # mean prefill per admitted request = time in prefill / admissions (= x in steady state)
    mean_p = sum(prefill_time[1:]) / x if x else 0.0
    return EngineSolution(states=states, pi=pi,
                          step_share={r: v / tot for r, v in sorted(step_rate.items())},
                          time_running=dict(sorted(time_running.items())),
                          throughput_per_s=x, decode_busy=busy, mean_prefill_s=mean_p,
                          active_share_by_r={r: v[0] / v[1] for r, v in sorted(active.items()) if v[1] > 0},
                          in_engine=in_engine)
