"""Online tool-duration predictor, reproduced from a published design.

Source: Li, He, Mang, Zhang, Mao, Chen, Zhou, Cheung, Gonzalez, Stoica,
"Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache
Time-to-Live", arXiv:2511.02230, section 4.2. The paper predicts a tool call's
duration -- "the interval between finishing decoding and re-entering the
waiting queue" -- and uses an empirical Bernstein upper bound on the mean:

    with probability at least 1 - delta,
        mu <= mu_hat + sqrt(2 * sigma_hat^2 * ln(3/delta) / |S|)
                     + 3 * b * ln(3/delta) / |S|   =  B(delta)

with a per-tool bound B_f(delta) formed the same way, and a three-tier
fallback: below N global observations use a default timeout; at or above N
per-tool observations use B_f; otherwise use the global B.

**Where this reproduction differs from the paper, and why it matters here.**
The paper's B(delta) bounds the *mean* and is used as a cache time-to-live, so
being conservative is the point. This study needs something else -- an estimate
of *this individual call's* duration, to know when a peer will return. Those
are different quantities, and the difference is not a detail: the error of
B(delta) against an individual draw is dominated by the spread of the
population, not by the estimation error of its mean. Both are therefore
computed and reported separately:

  ``bound``  B(delta) exactly as published
  ``mean``   mu_hat, the same statistics without the confidence inflation

Nothing here is claimed as the paper's result. The estimator is the paper's;
the use it is put to, and the error it is judged by, are this study's.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math


@dataclass
class _Stats:
    n: int = 0
    _sum: float = 0.0
    _sumsq: float = 0.0
    _max: float = 0.0

    def observe(self, x: float) -> None:
        self.n += 1
        self._sum += x
        self._sumsq += x * x
        self._max = max(self._max, x)

    @property
    def mean(self) -> float:
        return self._sum / self.n if self.n else 0.0

    @property
    def var(self) -> float:
        if self.n < 2:
            return 0.0
        m = self.mean
        return max(0.0, self._sumsq / self.n - m * m)

    @property
    def std(self) -> float:
        return math.sqrt(self.var)

    @property
    def range_bound(self) -> float:
        """``b`` in the bound: the largest value seen, since the true support
        is unknown online. Using the observed maximum is the choice this
        reproduction makes; the paper does not fix it."""
        return self._max


@dataclass
class ToolDurationPredictor:
    """Per-tool and global statistics with an empirical Bernstein bound.

    Online in the strict sense: every call is predicted before it is observed,
    and the observation only ever updates state afterwards. No pass over
    future data is possible, which is what makes the convergence curve mean
    something.
    """

    delta: float = 0.1
    min_observations: int = 5
    """``N`` in the paper's fallback: how many samples a level needs before
    its own bound is trusted."""
    default_timeout_s: float = 1.0
    """``T_default``: what to say before any level has enough data."""

    _global: _Stats = field(default_factory=_Stats)
    _per_tool: dict[str, _Stats] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 < self.delta < 1:
            raise ValueError("delta must be in (0, 1)")
        if self.min_observations < 1:
            raise ValueError("min_observations must be positive")
        if self.default_timeout_s <= 0:
            raise ValueError("default_timeout_s must be positive")

    def _bernstein(self, s: _Stats) -> float:
        ln = math.log(3.0 / self.delta)
        return s.mean + math.sqrt(2 * s.var * ln / s.n) + 3 * s.range_bound * ln / s.n

    def predict(self, tool: str, *, estimator: str = "bound") -> float:
        """Predict this call's duration in seconds, before observing it.

        ``estimator='bound'`` is the paper's B(delta). ``'mean'`` is the same
        statistics without the confidence term, which is the fairer point
        estimate when the quantity wanted is an individual duration.
        """
        if estimator not in ("bound", "mean"):
            raise ValueError(f"unknown estimator {estimator!r}")
        if self._global.n < self.min_observations:
            return self.default_timeout_s
        s = self._per_tool.get(tool)
        if s is not None and s.n >= self.min_observations:
            return s.mean if estimator == "mean" else self._bernstein(s)
        return self._global.mean if estimator == "mean" else self._bernstein(self._global)

    def observe(self, tool: str, duration_s: float) -> None:
        if duration_s < 0:
            raise ValueError("duration must be non-negative")
        self._global.observe(duration_s)
        self._per_tool.setdefault(tool, _Stats()).observe(duration_s)

    def tier(self, tool: str) -> str:
        """Which fallback level a prediction for ``tool`` would come from."""
        if self._global.n < self.min_observations:
            return "default"
        s = self._per_tool.get(tool)
        return "per_tool" if s is not None and s.n >= self.min_observations else "global"

    def observations(self, tool: str) -> int:
        s = self._per_tool.get(tool)
        return s.n if s else 0
