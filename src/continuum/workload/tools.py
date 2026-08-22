"""Tool-latency distributions read off a measured agent trace.

The tool gap in earlier tasks was ``uniform:1:5`` seconds -- a shape chosen to
make sessions desynchronise, not because anything behaves that way. Real agent
tool calls do not: most finish in well under a second and a small minority run
for minutes. Since every conclusion about return scheduling is a claim about
when sessions come back, the gap law is not a detail of the harness, it is the
independent variable.

What is reconstructed here is a *population* of tool calls: draw a tool by how
often it is actually called, then draw its latency from a curve that passes
through that tool's measured quantiles. Nothing is fitted -- the quantiles are
matched exactly, and the only assumed shape is below the median, where the
values are small enough not to matter.

Provenance: ``/home/rebel/vllm-continuum/results/tracelab/summary.json``,
recomputed by that repository from a public coding-agent trace
(665,453 rows / 743,819 tool calls / 8,058 sessions). Read-only; nothing in
that repository is modified.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import random

#: Tools whose latency is a human waiting, not a tool running. Excluded, which
#: matches the conservative "tool wait only" reading the source analysis used.
HUMAN_IN_THE_LOOP = frozenset({
    "AskUserQuestion", "ExitPlanMode", "request_user_input", "TaskOutput",
})

#: Latency bands, by measured median. Used for reporting a mix, not for drawing.
BANDS = (
    (0.0, 0.010, "instant"),
    (0.010, 0.200, "fast"),
    (0.200, 5.0, "medium"),
    (5.0, 60.0, "slow"),
    (60.0, float("inf"), "very_slow"),
)


@dataclass(frozen=True)
class ToolLatency:
    """One tool's latency law, defined by the quantiles that were measured.

    The inverse CDF is log-linear between the measured points, so ``p50``,
    ``p90`` and ``p99`` are reproduced exactly. Below the median a log-normal
    with the same log-spread as the 50-90 segment fills in; above ``p99`` the
    draw is capped, because the far tail is both unmeasured and, for a serving
    experiment, a session that has effectively left.
    """

    name: str
    calls: int
    p50_s: float
    p90_s: float
    p99_s: float

    def __post_init__(self) -> None:
        if self.calls <= 0:
            raise ValueError("calls must be positive")
        if not 0 < self.p50_s <= self.p90_s <= self.p99_s:
            raise ValueError(
                f"{self.name}: quantiles must be positive and ascending, got "
                f"{self.p50_s}/{self.p90_s}/{self.p99_s}")

    @property
    def band(self) -> str:
        for lo, hi, name in BANDS:
            if lo <= self.p50_s < hi:
                return name
        return BANDS[-1][2]

    def quantile(self, q: float) -> float:
        if not 0.0 < q < 1.0:
            raise ValueError("q must be in (0, 1)")
        if q >= 0.99:
            return self.p99_s
        if q >= 0.9:
            f = (q - 0.9) / 0.09
            return self.p90_s * (self.p99_s / self.p90_s) ** f
        if q >= 0.5:
            f = (q - 0.5) / 0.4
            return self.p50_s * (self.p90_s / self.p50_s) ** f
        # Below the median: log-normal with the log-spread of the 50-90 leg.
        sigma = math.log(self.p90_s / self.p50_s) / 1.2816 if self.p90_s > self.p50_s else 0.0
        if sigma == 0.0:
            return self.p50_s
        return self.p50_s * math.exp(sigma * _probit(q))

    def draw(self, rng: random.Random) -> float:
        return self.quantile(min(max(rng.random(), 1e-6), 1 - 1e-9))


def _probit(q: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation)."""
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    pl, ph = 0.02425, 1 - 0.02425
    if q < pl:
        t = math.sqrt(-2 * math.log(q))
        return (((((c[0]*t+c[1])*t+c[2])*t+c[3])*t+c[4])*t+c[5]) / \
               ((((d[0]*t+d[1])*t+d[2])*t+d[3])*t+1)
    if q > ph:
        t = math.sqrt(-2 * math.log(1 - q))
        return -(((((c[0]*t+c[1])*t+c[2])*t+c[3])*t+c[4])*t+c[5]) / \
                ((((d[0]*t+d[1])*t+d[2])*t+d[3])*t+1)
    t = q - 0.5
    r = t * t
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*t / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


@dataclass(frozen=True)
class ToolMix:
    """A population of tools with their call frequencies."""

    tools: tuple[ToolLatency, ...]
    cap_s: float
    """Draws are clipped here. A gap longer than this is a session that has
    left for the purposes of a serving experiment, and the far tail is
    unmeasured anyway. The clipped fraction is reported, never hidden."""

    def __post_init__(self) -> None:
        if not self.tools:
            raise ValueError("mix must not be empty")
        if self.cap_s <= 0:
            raise ValueError("cap_s must be positive")

    @property
    def total_calls(self) -> int:
        return sum(t.calls for t in self.tools)

    def draw(self, rng: random.Random) -> tuple[str, float]:
        """(tool name, latency in seconds), latency clipped at ``cap_s``."""
        pick = rng.random() * self.total_calls
        acc = 0
        chosen = self.tools[-1]
        for t in self.tools:
            acc += t.calls
            if pick <= acc:
                chosen = t
                break
        return chosen.name, min(chosen.draw(rng), self.cap_s)

    def band_mix(self) -> dict[str, float]:
        total = self.total_calls
        out: dict[str, float] = {}
        for t in self.tools:
            out[t.band] = out.get(t.band, 0.0) + t.calls / total
        return out

    def prob_under(self, seconds: float, *, rng_seed: int = 0,
                   samples: int = 200_000) -> float:
        """Share of draws below ``seconds``. Used to check the reconstruction
        against a statistic the source reports but this class never reads."""
        rng = random.Random(rng_seed)
        hit = sum(1 for _ in range(samples) if self.draw(rng)[1] < seconds)
        return hit / samples


def load_mix(summary_path: str | Path, *, cap_s: float = 60.0,
             exclude: frozenset[str] = HUMAN_IN_THE_LOOP) -> ToolMix:
    """Build the mix from a TraceLab summary. Latencies there are milliseconds."""
    data = json.loads(Path(summary_path).read_text())
    tools = []
    for name, v in data["tool_by_name"].items():
        if name in exclude or v["n"] <= 0:
            continue
        # A measured median of 0 ms means "below timer resolution", not zero.
        p50 = max(v["p50"], 0.5) / 1000.0
        p90 = max(v["p90"] / 1000.0, p50)
        p99 = max(v["p99"] / 1000.0, p90)
        tools.append(ToolLatency(name=name, calls=v["n"],
                                 p50_s=p50, p90_s=p90, p99_s=p99))
    return ToolMix(tools=tuple(sorted(tools, key=lambda t: -t.calls)), cap_s=cap_s)
