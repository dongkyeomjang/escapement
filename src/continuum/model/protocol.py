"""Survival predictions read straight from a v2 descriptor.

The functions in ``survival`` take the window, the unit size, the lookup
order and the cacheable prefix as arguments. On a new substrate a caller had
to work those out from the substrate's rules -- GTASK04 did so in a wrapper
(generated tokens held and cached, release-order LRU equivalent to allocation
FIFO on a fresh pool, tail-first loss, hit blocks protected). Here the rules
come from ``SubstrateDescriptorV2`` fields, so the same model code runs on
either substrate with no wrapper.

Nothing here names an accelerator.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..substrate.v2 import NA, SubstrateDescriptorV2
from . import survival as S


@dataclass(frozen=True)
class SequentialPrediction:
    hit_tokens: int
    target_units: int
    background_units: tuple[int, ...]
    resume_units: int
    overflow_units: int
    cacheable_units_evicted: int
    """Units of the target's cacheable prefix lost by the lookup."""


def _require(value, label: str):
    if value is None:
        raise ValueError(f"descriptor does not establish {label}; no prediction")
    return value


def sequential_protocol(d: SubstrateDescriptorV2, *, target_prompt: int, target_generated: int,
                        backgrounds: Sequence[tuple[int, int]],
                        resume_prompt: int) -> SequentialPrediction:
    """TASK14/15 protocol on a fresh pool: the target, then background requests
    ``(prompt, generated)`` one at a time, then the resume. Nothing overlaps.

    Why a release-ordered LRU reduces to the allocation-FIFO window here: on a
    fresh pool whose never-used units are handed out first, every background
    allocation takes never-used units until they run out and only then the
    released ones, in release order; with nothing overlapping, release order is
    allocation order. The rule is therefore only applied when the descriptor
    says ``initial_free_order = never_used_first``.
    """
    sem = d.semantics
    layer = d.reuse_pool
    cap = _require(layer.capacity_units, "the reuse layer capacity")
    order = _require(layer.eviction_order, "the eviction order")
    if order == "release_lru":
        if _require(sem.initial_free_order, "initial_free_order") != "never_used_first":
            raise ValueError("release-order LRU without never-used-first has no FIFO "
                             "equivalent on a fresh pool")
        _require(sem.window_start, "window_start")
    loss = _require(sem.intra_request_loss, "intra_request_loss")
    granularity = {"all_or_nothing": "sequence", "tail_first": "block"}[loss]
    own_first = _require(sem.resume_allocates_first, "resume_allocates_first")
    if not own_first and _require(sem.hit_protection, "hit_protection") == NA:
        raise ValueError("lookup before allocation needs a hit-protection rule")
    if d.hit_formula is None:
        raise ValueError("descriptor has no hit formula")

    u_t = layer.units_for(sem.held_tokens(target_prompt, target_generated))
    u_bg = tuple(layer.units_for(sem.held_tokens(p, g)) for p, g in backgrounds)
    u_r = layer.units_for(resume_prompt)
    window = S.sequential_window(target_units=u_t, background_units=u_bg,
                                 resume_units=u_r, resume_allocates_first=own_first)
    cacheable = sem.cacheable_prefix(target_prompt, target_generated)
    hit = S.reusable_tokens(hit_formula=d.hit_formula, granularity=granularity, capacity=cap,
                            window=window, unit_tokens=layer.unit_tokens,
                            cached_prefix_tokens=cacheable, query_tokens=resume_prompt)
    over = max(0, S.overflow(cap, window))
    cached_units = cacheable // layer.unit_tokens
    if granularity == "block":
        # The tail goes first; units beyond the cacheable prefix go before it.
        lost = max(0, min(cached_units, over - (u_t - cached_units)))
    else:
        lost = cached_units if over > 0 else 0
    return SequentialPrediction(hit_tokens=hit, target_units=u_t, background_units=u_bg,
                                resume_units=u_r, overflow_units=over,
                                cacheable_units_evicted=lost)
