"""How many requests are running, in a steady multi-turn load.

Model
-----
``N`` sessions alternate between two states: *in service* (their request is
waiting or running in the engine) and *in a tool gap*. This is a closed
two-station network -- a delay (infinite-server) station for the gaps and one
load-dependent station for the engine.

The engine runs every admitted request in one padded decode step, so while
``n <= max_running`` each request advances one token per step: the station is
processor sharing with aggregate token rate ``r(n) / t_step(r(n))``, where
``r(n) = min(n, max_running)``. A request needs ``decode_steps`` tokens of
that service. Its completion rate in state ``n`` is therefore::

    mu(n) = phi * r(n) / (decode_steps * t_step(r(n)))

``phi`` is the share of wall time left for decode after exclusive prefill:
every admission's prefill stops every decoder for its whole duration, so with
throughput ``X`` and mean prefill ``E[P]`` the engine spends ``X * E[P]`` of
its time on prefill. ``phi = 1 - X * E[P]`` depends on ``X``, which depends
on the distribution, so the two are solved by fixed-point iteration.

The stationary distribution of the number in service is the birth-death
product form::

    pi(n+1) / pi(n) = ((N - n) / Z) / mu(n+1)

with ``Z`` the mean gap (think time). Because the gap station is a delay
station and the engine is processor sharing while ``n <= max_running``, the
product form is insensitive to the gap distribution beyond its mean
(BCMP). When ``n`` can exceed ``max_running`` the waiting requests are served
FCFS and insensitivity no longer holds; the formula is then an approximation.

Two histograms come out of it and they must not be confused:

* ``time_share[r]`` -- fraction of wall time with ``r`` requests running.
* ``step_share[r]`` -- fraction of *decode steps* with ``r`` running. A state
  with a slow step produces fewer steps per second, so
  ``step_share[r] ~ time_share[r] * phi / t_step(r)``. This is what a
  per-step log such as ``[BUCKET]`` counts, and what a grid is priced on.

Limits stated before use
------------------------
* Only steady state is modelled. A workload whose sessions all start at once
  and send two requests each (the arXiv manuscript's) never reaches steady
  state; its histogram is dominated by the start-up ramp and the drain.
* Prefill is spread uniformly over time (``phi``). The real engine stops all
  decoders at once and restarts them together; that synchronisation widens the
  batch right after a prefill and is not in the mean (TASK29's "batching
  subsidy" is only partly represented -- see ``interference``).
* Step cost is taken as known for every running count; for unmeasured bucket
  widths it is a model twice over (interpolated cost, then this).

Nothing here names an accelerator.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math


@dataclass(frozen=True)
class ClosedWorkload:
    sessions: int
    decode_steps_per_request: float
    """Decode steps one request needs after its prefill (generation - 1)."""
    think_mean_s: float
    """Mean time a session spends outside the engine between requests:
    tool gap plus client overhead."""
    prefill_mean_s: float
    """Mean exclusive prefill time per admitted request. Depends on reuse, so
    it may be updated by the caller from a survival model."""
    max_running: int

    def __post_init__(self) -> None:
        if self.sessions <= 0 or self.max_running <= 0:
            raise ValueError("sessions and max_running must be positive")
        if self.decode_steps_per_request <= 0:
            raise ValueError("decode_steps_per_request must be positive")
        if self.think_mean_s < 0 or self.prefill_mean_s < 0:
            raise ValueError("times must be non-negative")


@dataclass
class Occupancy:
    in_service: list[float]
    """P(n sessions in the engine), n = 0..N, time-stationary."""
    time_share: dict[int, float]
    """P(r running), r = 0..max_running, time-stationary."""
    step_share: dict[int, float]
    """Share of decode steps with r running, r >= 1."""
    phi: float
    throughput_per_s: float
    steps_per_s: float
    iterations: int
    converged: bool
    notes: list[str] = field(default_factory=list)

    @property
    def mean_running(self) -> float:
        return sum(r * p for r, p in self.time_share.items())

    @property
    def mean_response_s(self) -> float:
        """Little's law on the engine station."""
        n_bar = sum(n * p for n, p in enumerate(self.in_service))
        return n_bar / self.throughput_per_s if self.throughput_per_s else math.inf


def _distribution(w: ClosedWorkload, t_step: Callable[[int], float],
                  phi: float, sessions: int) -> list[float]:
    """Unnormalised-then-normalised birth-death stationary law."""
    if w.think_mean_s == 0:
        # Sessions return instantly: everyone is always in the engine.
        out = [0.0] * (sessions + 1)
        out[sessions] = 1.0
        return out
    logs = [0.0]
    for n in range(sessions):
        r = min(n + 1, w.max_running)
        mu = phi * r / (w.decode_steps_per_request * t_step(r))
        lam = (sessions - n) / w.think_mean_s
        logs.append(logs[-1] + math.log(lam) - math.log(mu))
    m = max(logs)
    un = [math.exp(x - m) for x in logs]
    s = sum(un)
    return [x / s for x in un]


def _throughput(w: ClosedWorkload, pi: list[float]) -> float:
    """Arrival rate into the engine = rate sessions leave their gaps."""
    if w.think_mean_s == 0:
        return math.inf
    n_sessions = len(pi) - 1
    return sum(p * (n_sessions - n) for n, p in enumerate(pi)) / w.think_mean_s


def solve_occupancy(w: ClosedWorkload, t_step: Callable[[int], float], *,
                    tol: float = 1e-12, max_iter: int = 10_000,
                    sessions: int | None = None) -> Occupancy:
    """Fixed point of (distribution, prefill share).

    ``t_step(r)`` is the decode step time with ``r`` running requests, i.e.
    ``descriptor.step_time_s``. ``sessions`` overrides ``w.sessions``; the
    arrival theorem uses it with ``N - 1``.
    """
    n_sessions = w.sessions if sessions is None else sessions
    if n_sessions < 0:
        raise ValueError("sessions must be non-negative")
    if w.think_mean_s == 0:
        raise ValueError("think_mean_s = 0 has no steady state with finite throughput")
    notes = []
    if n_sessions > w.max_running:
        notes.append("sessions exceed max_running: FCFS waiting breaks insensitivity; "
                     "the product form is an approximation here")
    phi = 1.0
    converged = False
    it = 0
    pi: list[float] = [1.0]
    x = 0.0
    for it in range(1, max_iter + 1):
        pi = _distribution(w, t_step, phi, n_sessions)
        x = _throughput(w, pi)
        new_phi = 1.0 - x * w.prefill_mean_s
        if new_phi <= 0:
            raise ValueError("prefill alone saturates the engine; no steady state")
        # Damped update: the map is monotone decreasing in phi.
        nxt = 0.5 * (phi + new_phi)
        if abs(nxt - phi) < tol:
            phi = nxt
            converged = True
            break
        phi = nxt
    pi = _distribution(w, t_step, phi, n_sessions)
    x = _throughput(w, pi)
    time_share: dict[int, float] = {}
    for n, p in enumerate(pi):
        r = min(n, w.max_running)
        time_share[r] = time_share.get(r, 0.0) + p
    rate = {r: (time_share[r] * phi / t_step(r)) for r in time_share if r >= 1}
    total = sum(rate.values())
    step_share = {r: v / total for r, v in sorted(rate.items())} if total else {}
    return Occupancy(in_service=pi, time_share=dict(sorted(time_share.items())),
                     step_share=step_share, phi=phi, throughput_per_s=x,
                     steps_per_s=total, iterations=it, converged=converged,
                     notes=notes)


def arrival_running_distribution(w: ClosedWorkload,
                                 t_step: Callable[[int], float]) -> dict[int, float]:
    """Running count an arriving request finds (arrival theorem).

    In a product-form closed network an arriving customer sees the
    time-stationary law of the network without itself. The prefill of that
    arrival stops exactly the requests running then, so this is the law of
    ``K_j`` in the interference term.
    """
    if w.sessions <= 1:
        return {0: 1.0}
    # The prefill share is a property of the full system the arrival joins,
    # so it is taken from the N-session solution and only the population is
    # reduced.
    phi = solve_occupancy(w, t_step).phi
    pi = _distribution(w, t_step, phi, w.sessions - 1)
    out: dict[int, float] = {}
    for n, p in enumerate(pi):
        r = min(n, w.max_running)
        out[r] = out.get(r, 0.0) + p
    return dict(sorted(out.items()))
