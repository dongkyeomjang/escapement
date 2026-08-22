"""Return policies that are told when their peers will come back.

These are not deployable. A real client cannot know that another session's
tool call will finish 0.4 s from now, so nothing here can be shipped. They
exist to answer a different question: *how much of the offline headroom is
buyable with that one piece of information, and how fast does the answer decay
as the information gets noisy?*

The offline bound in ``oracle.py`` knows everything -- generation lengths,
cache outcomes, the whole resulting schedule. A policy here knows only the
future ready times, and only through whatever noise it is given. Placing it
between the bound and the blind policies of ``online.py`` turns a single
number into a curve, and the curve is what says whether building a predictor
is worth anything.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .online import ReturnPolicy, ReturnState


@dataclass(frozen=True)
class PeerView:
    """Predicted times, relative to now, at which peers become ready.

    Negative or zero entries are peers already waiting. The view is supplied
    by the simulator, which is why these policies cannot run anywhere else.
    """

    offsets_s: tuple[float, ...]


class Lookahead(ReturnPolicy):
    """Wait for a cohort that is actually coming, and not a moment longer.

    At the instant a return becomes ready the policy looks at when its peers
    will be ready. Within the budget it finds the moment that gathers the
    largest group, and releases then -- but only if that group beats going now
    by at least ``min_gain`` sessions. Without that guard the rule degenerates
    into "always wait the full budget", which is the blind clustering that
    TASK27 measured as harmful.

    The count that matters is what the batch would be, so requests already in
    flight are included: joining four running sessions is a different trade
    from starting a batch of four.
    """

    def __init__(self, *, min_gain: int = 1) -> None:
        if min_gain < 1:
            raise ValueError("min_gain must be at least 1")
        self.min_gain = min_gain
        self.name = f"LOOKAHEAD(min_gain={min_gain})"

    def _best(self, state: ReturnState, view: PeerView) -> tuple[float, int]:
        """(offset to release at, resulting batch size)."""
        remaining = state.budget_s - state.waited_s
        now_count = state.in_flight + state.held
        best_off, best_count = 0.0, now_count
        # Candidate release moments are exactly the peer arrival instants: the
        # batch size only changes when someone arrives, so nothing between two
        # arrivals can ever be better than the later one.
        for off in sorted(o for o in view.offsets_s if 0.0 < o <= remaining):
            count = now_count + sum(1 for o2 in view.offsets_s if 0.0 < o2 <= off)
            if count > best_count:
                best_off, best_count = off, count
        return best_off, best_count

    def release_with_view(self, state: ReturnState, view: PeerView) -> bool:
        off, count = self._best(state, view)
        if off <= 0.0:
            return True
        if count - (state.in_flight + state.held) < self.min_gain:
            return True
        return False

    def next_check_with_view(self, state: ReturnState, view: PeerView) -> float | None:
        off, _ = self._best(state, view)
        return state.now_s + off if off > 0.0 else None

    # The plain interface exists so the type checks; without a peer view this
    # policy has nothing to reason about and releases at once.
    def release(self, state: ReturnState) -> bool:
        return True


@dataclass
class NoisyClock:
    """Corrupts predicted tool-gap durations with multiplicative noise.

    Multiplicative rather than additive because that is the shape prediction
    error actually has here. Measured tool latencies span four orders of
    magnitude (TraceLab: median 0.115 s, p99 240 s), so an additive error
    scaled to the global spread would be larger than most gaps entirely and
    would say nothing about predicting the short ones. A relative error is
    also what a duration predictor's own error looks like.

    The draw is median-preserving, so noise degrades the prediction without
    also biasing it: a policy fed noisier information should get worse, not
    systematically early or late.
    """

    sigma_log: float
    seed: int
    _rng: random.Random | None = None

    def __post_init__(self) -> None:
        if self.sigma_log < 0:
            raise ValueError("sigma_log must be non-negative")
        self._rng = random.Random(self.seed)

    def perturb(self, true_gap_s: float) -> float:
        if self.sigma_log == 0.0 or true_gap_s <= 0.0:
            return true_gap_s
        z = self._rng.gauss(0.0, self.sigma_log)
        return true_gap_s * math.exp(z - self.sigma_log ** 2 / 2.0)


def sigma_log_for_relative_error(gaps: list[float], target_ratio: float, *,
                                 seed: int = 0, samples: int = 4000,
                                 tol: float = 1e-3) -> float:
    """Find the noise scale whose absolute error matches ``target_ratio``.

    The grid is specified in units of the gap distribution's own standard
    deviation, so that "noise equal to the spread of the thing being
    predicted" is one grid point regardless of workload. The noise itself is
    multiplicative, so the scale that achieves a given absolute error has to
    be solved for rather than written down.
    """
    if target_ratio <= 0:
        return 0.0
    if len(gaps) < 2:
        raise ValueError("need at least two gaps to define a spread")
    mean = sum(gaps) / len(gaps)
    std = (sum((g - mean) ** 2 for g in gaps) / (len(gaps) - 1)) ** 0.5
    if std <= 0:
        raise ValueError("gap spread is zero; a relative grid is undefined")
    target = target_ratio * std

    def achieved(s: float) -> float:
        rng = random.Random(seed)
        errs = []
        for i in range(samples):
            g = gaps[i % len(gaps)]
            z = rng.gauss(0.0, s)
            errs.append(g * math.exp(z - s * s / 2.0) - g)
        m = sum(errs) / len(errs)
        return (sum((e - m) ** 2 for e in errs) / (len(errs) - 1)) ** 0.5

    lo, hi = 0.0, 0.5
    while achieved(hi) < target and hi < 8.0:
        hi *= 2
    for _ in range(60):
        mid = (lo + hi) / 2
        if achieved(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2
