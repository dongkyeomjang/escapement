"""Prefill interference: what one session's prefill costs everyone else.

Formulation only. No measured data validates the expectation forms below yet
(the per-injection measurement of TASK22 fixes the per-event law, not its
distribution under a steady load), so this module states the terms and
computes them from the occupancy model without claiming accuracy.

Per event (TASK22, reconstructed; the manuscript's equation numbers are not
available in this repository)::

    stall_j = P(q_j) * K_j

``P(q)`` is the exclusive prefill time for ``q`` computed tokens (the
descriptor's ``PrefillCostModel``), ``q_j = L_j - H_j`` the prompt length
minus the tokens served from cache, and ``K_j`` the number of requests
decoding when prefill ``j`` starts -- all of them stop for its whole duration.
Summed over a run, ``W = sum_j P(q_j) K_j`` is the session time lost; the
device time of the prefills themselves is ``sum_j P(q_j)`` and is charged
once.

Expectation per unit time, assuming ``q_j`` independent of ``K_j``::

    E[W] / time = X * E[P(q)] * E[K]

with throughput ``X`` and ``E[K]`` from the arrival theorem
(``occupancy.arrival_running_distribution``). ``E[P(q)]`` mixes hits and
misses through the survival probability ``p_s``::

    E[P(q)] = p_s * P(L - H) + (1 - p_s) * P(L)

A reuse failure therefore costs ``P(L) - P(L - H)`` of device time (the
incremental definition, which is what the simulator charges by passing
``q = L - H``; TASK66, TASK67) plus that difference times ``K`` of session
time.

Chunked prefill
---------------
On a stack that interleaves prefill chunks with decode (vLLM's default,
TASK29 citation 3) nobody stops: ``K_j`` is replaced by 0 and the stall term
vanishes. The prefill work does not vanish -- it is carried inside the decode
steps. TASK29's ablation found that device time *rises* by 3-10 % when the
stall goes away, because exclusive prefill had been holding decoders together
and releasing them as wider batches. In the occupancy model the mean part of
that shows up through ``phi``: exclusive prefill stretches every request's
stay in the engine, which raises the mean running count and so the batch
width. The synchronisation part -- everyone restarting in the same step -- is
a correlation the product form does not carry, so the model is expected to
get the sign of the chunked-prefill change and not its full size. That
expectation is a hypothesis, not a result.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class InterferenceTerms:
    prefill_device_s_per_s: float
    """Share of wall time the device spends in prefill (``X * E[P]``)."""
    stall_session_s_per_s: float
    """Session time lost to other sessions' prefills per second of wall time."""
    mean_concurrent_at_arrival: float


def expected_prefill_s(*, prefill_s: Callable[[int], float], prompt_tokens: int,
                       hit_tokens: int, survival_probability: float) -> float:
    if not 0.0 <= survival_probability <= 1.0:
        raise ValueError("survival_probability must be in [0, 1]")
    if not 0 <= hit_tokens <= prompt_tokens:
        raise ValueError("need 0 <= hit_tokens <= prompt_tokens")
    return (survival_probability * prefill_s(prompt_tokens - hit_tokens)
            + (1.0 - survival_probability) * prefill_s(prompt_tokens))


def reuse_failure_cost_s(*, prefill_s: Callable[[int], float], prompt_tokens: int,
                         hit_tokens: int, concurrent: float) -> tuple[float, float]:
    """(device seconds, session seconds) one failed reuse adds."""
    extra = prefill_s(prompt_tokens) - prefill_s(prompt_tokens - hit_tokens)
    return extra, extra * concurrent


def interference(*, throughput_per_s: float, mean_prefill_s: float,
                 arrival_running: Mapping[int, float],
                 exclusive: bool = True) -> InterferenceTerms:
    """Expectation form of the stall term. ``exclusive=False`` is the
    chunked-prefill substrate: the stall is zero by construction."""
    e_k = sum(k * p for k, p in arrival_running.items())
    stall = throughput_per_s * mean_prefill_s * e_k if exclusive else 0.0
    return InterferenceTerms(prefill_device_s_per_s=throughput_per_s * mean_prefill_s,
                             stall_session_s_per_s=stall,
                             mean_concurrent_at_arrival=e_k)
