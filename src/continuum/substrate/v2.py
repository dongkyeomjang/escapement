"""Substrate descriptor v2: layers, rule fields and where each value comes from.

v1 (``descriptor.py``) was cut from the first substrate measured: a fixed
outer/inner two-layer pool, eviction as a policy string, one step-cost curve
and an exclusive prefill model implied by its presence. A second substrate
(a paged GPU block pool) does not fit it -- one layer, eviction ordered by
release rather than allocation, tail-first loss inside a request, lookup before
allocation, generated tokens cached, prefill mixed into decode steps, a grid
keyed by scheduled tokens that falls back to eager above its top.

v2 carries those differences as data (docs/research/DESCRIPTOR_V2.md):

* ``layers`` -- the KV pool as a list of layers with the same fields, and
  ``reuse_layer`` naming the one that decides reuse;
* ``semantics`` -- *rules*, not values: which entry an eviction takes, which
  event starts a survival window, what a request loses first, whether lookup
  precedes allocation, which tokens are cacheable, non-request consumers,
  preemption;
* ``admission``, ``grid``, ``step_cost`` (by step mode), ``prefill``,
  ``pipeline``;
* ``value_source`` wherever a value is set by the compile artifact rather than
  a server argument -- it says what must be re-measured or re-compiled when a
  configuration changes.

Every leaf that holds a value needs a ``Provenance`` under its dotted path
(``"layers[1].capacity_units"``, ``"semantics.eviction_order"``). ``None``
means *not established*; it is never a default. A rule that does not arise on
a substrate is the value ``"not_applicable"`` and needs provenance like any
other value.

``legacy_view()`` returns the v1 ``SubstrateDescriptor`` every earlier script
used, field for field, so that manuscript-era results are reproduced from the
same source of truth.

Nothing here names an accelerator.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass, replace
import math

from .descriptor import (
    HitFormula,
    PrefillCostModel,
    Provenance,
    StepCostModel,
    SubstrateDescriptor,
)

NA = "not_applicable"

_VALUE_SOURCES = frozenset({"compile", "server_arg", "fixed"})
_EVICTION_ORDERS = frozenset({"allocation_fifo", "release_lru"})
_EVICTABLE_WHEN = frozenset({"immediate", "deferred"})
_WINDOW_STARTS = frozenset({"allocation", "release"})
_INTRA_LOSS = frozenset({"all_or_nothing", "tail_first"})
_INITIAL_FREE = frozenset({"never_used_first", NA})
_HIT_PROTECTION = frozenset({"touch_before_alloc", NA})
_CACHE_REG = frozenset({"at_allocation", "at_completion"})
_CACHEABLE = frozenset({"prefill_only", "computed"})
_DUMMY = frozenset({"none", "pre_evict", "reserved"})
_DUMMY_CEILING = frozenset({"max_running", "top_grid", NA})
_PREEMPTION = frozenset({"none", "recompute", "swap"})
_GRID_UNITS = frozenset({"requests", "tokens"})
_ABOVE_TOP = frozenset({"impossible", "eager"})
_MIXED_GRAPH = frozenset({"piecewise", "eager", NA})
_PREFILL_EXEC = frozenset({"exclusive", "mixed"})
_STEP_MODES = frozenset({"decode", "mixed", "eager"})


def _check(value, allowed: frozenset, label: str) -> None:
    if value is not None and value not in allowed:
        raise ValueError(f"unknown {label} {value!r}; expected one of {sorted(allowed)}")


# -- parts --------------------------------------------------------------------------

@dataclass(frozen=True)
class PoolLayer:
    """One layer of the KV pool. Every layer has the same fields."""

    name: str
    unit_tokens: int
    """Tokens one allocation unit holds."""
    capacity_units: int | None
    """Units requests can use: physical minus ``reserved_units``."""
    reserved_units: int | None
    """Units held permanently by something that is not a request."""
    value_source: str | None
    """Where the capacity is set: ``compile`` | ``server_arg`` | ``fixed``."""
    eviction_order: str | None
    """Which inactive entry an eviction in this layer takes:
    ``allocation_fifo`` -- the earliest allocated; ``release_lru`` -- the head
    of a free queue ordered by release."""

    def __post_init__(self) -> None:
        _check(self.eviction_order, _EVICTION_ORDERS, "eviction_order")
        if self.unit_tokens <= 0:
            raise ValueError("unit_tokens must be positive")
        if self.capacity_units is not None and self.capacity_units <= 0:
            raise ValueError("capacity_units must be positive")
        if self.reserved_units is not None and self.reserved_units < 0:
            raise ValueError("reserved_units must be non-negative")
        _check(self.value_source, _VALUE_SOURCES, "value_source")

    def units_for(self, tokens: int) -> int:
        """Units a request holding ``tokens`` of KV occupies. On a pool whose unit
        is a whole sequence slot this is 1 up to the slot size -- a *count*
        threshold; on a block pool it grows with tokens -- a *total* threshold."""
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        return math.ceil(tokens / self.unit_tokens)


@dataclass(frozen=True)
class Semantics:
    """Rules, not values. Each decides which entry is lost and when. The
    eviction order itself is per layer (``PoolLayer.eviction_order``); these
    rules apply to the reuse layer."""

    evictable_when: str | None
    """When a finished request's entry becomes a candidate: ``immediate`` or
    ``deferred`` (after the next admission has chosen its victim)."""
    window_start: str | None
    """Event that starts a cached prefix's survival window: ``allocation`` or
    ``release``."""
    intra_request_loss: str | None
    """``all_or_nothing`` (one unit per request) or ``tail_first``."""
    initial_free_order: str | None
    """Order never-used units are handed out: ``never_used_first`` or n/a."""
    active_pinned: bool | None
    """Whether a running request's units are exempt from eviction."""
    resume_allocates_first: bool | None
    """Whether an admitted request takes its own units before its lookup."""
    hit_protection: str | None
    """With lookup first: whether the hit units are protected from the same
    admission's allocation (``touch_before_alloc``) or n/a."""
    failed_admission_evicts: bool | None
    cache_registration: str | None
    """When a block being computed becomes hit-able: ``at_allocation`` or
    ``at_completion``."""
    kv_tokens_held: str | None
    """Tokens whose KV a request holds: ``computed`` = prompt + output - 1
    (the last sampled token is never fed back)."""
    cacheable_tokens: str | None
    """Tokens a finished request leaves as a reusable prefix:
    ``prefill_only`` (prompt) or ``computed`` (prompt + output - 1)."""
    dummy_mode: str | None
    """Non-request, time-varying consumer: ``none`` | ``pre_evict`` | ``reserved``."""
    dummy_ceiling: str | None
    """A partial decode step (``0 < n < ceiling``) triggers the dummy. The ceiling
    is ``max_running`` or ``top_grid``; ``None`` if the two were never told apart."""
    preemption: str | None
    """Path that ejects a running request: ``none`` | ``recompute`` | ``swap``."""
    preemption_trigger: str | None = None
    preemption_victim: str | None = None
    preemption_disableable: bool | None = None
    preempted_keeps_cache: bool | None = None

    def __post_init__(self) -> None:
        _check(self.evictable_when, _EVICTABLE_WHEN, "evictable_when")
        _check(self.window_start, _WINDOW_STARTS, "window_start")
        _check(self.intra_request_loss, _INTRA_LOSS, "intra_request_loss")
        _check(self.initial_free_order, _INITIAL_FREE, "initial_free_order")
        _check(self.hit_protection, _HIT_PROTECTION, "hit_protection")
        _check(self.cache_registration, _CACHE_REG, "cache_registration")
        _check(self.kv_tokens_held, frozenset({"computed"}), "kv_tokens_held")
        _check(self.cacheable_tokens, _CACHEABLE, "cacheable_tokens")
        _check(self.dummy_mode, _DUMMY, "dummy_mode")
        _check(self.dummy_ceiling, _DUMMY_CEILING, "dummy_ceiling")
        _check(self.preemption, _PREEMPTION, "preemption")

    # token accounting --------------------------------------------------------

    def held_tokens(self, prompt: int, generated: int) -> int:
        if self.kv_tokens_held is None:
            raise ValueError("kv_tokens_held is not established")
        return prompt + max(generated, 1) - 1

    def cacheable_prefix(self, prompt: int, generated: int) -> int:
        if self.cacheable_tokens is None:
            raise ValueError("cacheable_tokens is not established")
        if self.cacheable_tokens == "prefill_only":
            return prompt
        return prompt + max(generated, 1) - 1


@dataclass(frozen=True)
class Admission:
    max_running: int | None
    """Ceiling on concurrently running requests (the model's ``M``)."""
    max_running_source: str | None
    """``compile`` (a compile-time batch size) or ``server_arg``."""
    step_token_budget: int | None = None
    admission_requires_full_prompt: bool | None = None

    def __post_init__(self) -> None:
        if self.max_running is not None and self.max_running <= 0:
            raise ValueError("max_running must be positive")
        _check(self.max_running_source, _VALUE_SOURCES, "max_running_source")


@dataclass(frozen=True)
class Grid:
    sizes: tuple[int, ...]
    unit: str | None
    """What a step is mapped by: ``requests`` or scheduled ``tokens``."""
    value_source: str | None
    above_top: str | None
    """A step larger than the top: ``impossible`` or runs ``eager`` (no padding)."""
    mixed_step_graph: str | None
    """Graph a prefill+decode step uses: ``piecewise`` | ``eager`` | n/a."""

    def __post_init__(self) -> None:
        if not self.sizes:
            raise ValueError("grid sizes must not be empty")
        if list(self.sizes) != sorted(set(self.sizes)):
            raise ValueError("grid sizes must be ascending and unique")
        _check(self.unit, _GRID_UNITS, "grid unit")
        _check(self.value_source, _VALUE_SOURCES, "grid value_source")
        _check(self.above_top, _ABOVE_TOP, "above_top")
        _check(self.mixed_step_graph, _MIXED_GRAPH, "mixed_step_graph")

    def width_for(self, n: int) -> int | None:
        """Smallest grid size >= n. ``None`` = runs eager above the top."""
        for b in self.sizes:
            if b >= n:
                return b
        if self.above_top == "eager":
            return None
        raise ValueError(f"{n} exceeds the top grid size {self.sizes[-1]}")


@dataclass(frozen=True)
class PrefillSpec:
    execution: str | None
    """``exclusive``: a prefill stops every decoder for its duration.
    ``mixed``: prefill runs inside decode steps."""
    cost: PrefillCostModel | None
    """Exclusive-prefill duration model. ``None`` = not measured."""
    chunk_tokens: int | None

    def __post_init__(self) -> None:
        _check(self.execution, _PREFILL_EXEC, "prefill execution")
        if self.cost is not None and self.execution != "exclusive":
            raise ValueError("PrefillCostModel prices exclusive prefill only")


@dataclass(frozen=True)
class FullGraphDecodeCost:
    """``step_cost["decode"]`` of an engine whose grid is keyed by scheduled
    tokens: a decode-only step padded to capture width ``b`` costs
    ``F[b] + g * n``. Values in milliseconds, as measured; callers price in ms
    and convert once, so results match the channel the values came from bit
    for bit."""

    fixed_ms_by_width: Mapping[int, float]
    marginal_ms_per_request: float
    max_measured_requests: int
    """Decode widths above this were never measured; pricing them is refused."""


@dataclass(frozen=True)
class PiecewiseMixedCost:
    """``step_cost["mixed"]``: a step carrying prefill tokens whose total fits
    the grid (a piecewise graph) costs the decode baseline plus this constant."""

    increment_ms: float


@dataclass(frozen=True)
class EagerStepCost:
    """``step_cost["eager"]``: steps above the grid top run without a graph.

    * decode-only: ``decode_ms_by_n[n]`` (measured medians);
    * with ``p`` prefill tokens: the decode baseline plus ``increment(p)``,
      linear between measured ``(p, ms)`` points, through the origin below the
      first one and proportional to ``p`` above the last one."""

    decode_ms_by_n: Mapping[int, float]
    increment_points: tuple[tuple[int, float], ...]

    def increment_ms(self, p: int) -> float:
        xs = [x for x, _ in self.increment_points]
        ys = [y for _, y in self.increment_points]
        if p <= xs[0]:
            return ys[0] * p / xs[0]
        if p >= xs[-1]:
            return ys[-1] * p / xs[-1]
        i = bisect_left(xs, p)
        x0, x1 = xs[i - 1], xs[i]
        return ys[i - 1] + (p - x0) / (x1 - x0) * (ys[i] - ys[i - 1])


@dataclass(frozen=True)
class ContextCost:
    """Context-length term of a step that carries decoding requests:

        step += per_token * (sum_ctx - decodes * reference_tokens_per_decode)

    ``sum_ctx`` sums, over the step's decoding requests, the tokens already in
    each request's context (prompt plus tokens generated so far). The decode
    cost the term is added to was measured at ``reference_tokens_per_decode``
    tokens per request (0 when it was fitted jointly with this term, as the
    NPU F1 fit ``f(b) + beta n + c sum_ctx`` was). ``unit`` is the step-cost
    unit of the descriptor's engine (``s`` for an exclusive-prefill engine,
    ``ms`` for the paged engine), so the arithmetic matches the channel the
    values came from bit for bit. ``None`` on a descriptor = no context term
    (every judged prediction before TASK103)."""

    per_token: float
    unit: str
    reference_tokens_per_decode: float = 0

    def __post_init__(self) -> None:
        if self.unit not in ("s", "ms"):
            raise ValueError("ContextCost unit must be 's' or 'ms'")
        if self.per_token < 0 or self.reference_tokens_per_decode < 0:
            raise ValueError("ContextCost values must be non-negative")

    def term(self, sum_ctx: int, decodes: int) -> float:
        return self.per_token * (sum_ctx - decodes * self.reference_tokens_per_decode)


@dataclass(frozen=True)
class Pipeline:
    in_flight_batches: int | None = None
    startup_nonrequest_steps: int | None = None


@dataclass(frozen=True)
class SubstrateDescriptorV2:
    name: str
    layers: tuple[PoolLayer, ...]
    reuse_layer: int
    """Index of the layer whose eviction decides reuse (metrics may report another)."""
    semantics: Semantics
    admission: Admission
    grid: Grid
    hit_formula: HitFormula | None
    step_cost: Mapping[str, StepCostModel | None]
    """By step mode: ``decode`` (uniform decode), ``mixed``, ``eager``."""
    step_cost_measurement: str | None
    prefill: PrefillSpec
    pipeline: Pipeline = Pipeline()
    context_cost: ContextCost | None = None
    """Optional context-length step-cost term (TASK103). ``None`` = none, not
    "unknown": it is not listed by ``unknown_paths``."""
    provenance: Mapping[str, Provenance] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.layers:
            raise ValueError("at least one pool layer is required")
        if not 0 <= self.reuse_layer < len(self.layers):
            raise ValueError("reuse_layer out of range")
        for mode in self.step_cost:
            _check(mode, _STEP_MODES, "step-cost mode")
        missing = [p for p in self.value_paths() if p not in self.provenance
                   and not any(p.startswith(k + ".") for k in self.provenance)]
        if missing:
            raise ValueError(f"missing provenance for: {sorted(missing)}")
        stray = [k for k in self.provenance if not any(
            p == k or p.startswith(k + ".") for p in self.value_paths())]
        if stray:
            raise ValueError(f"provenance for fields with no value: {sorted(stray)}")

    # -- provenance bookkeeping ------------------------------------------------

    def value_paths(self) -> list[str]:
        """Dotted paths of every leaf that holds a value (``None`` excluded)."""
        out: list[str] = []

        def walk(obj, prefix: str) -> None:
            for f in fields(obj):
                if f.name in ("name", "provenance", "notes"):
                    continue
                v = getattr(obj, f.name)
                path = f"{prefix}{f.name}"
                if v is None:
                    continue
                if isinstance(v, tuple) and v and is_dataclass(v[0]):
                    for i, item in enumerate(v):
                        walk(item, f"{path}[{i}].")
                elif isinstance(v, Mapping):
                    for k, item in v.items():
                        if item is not None:
                            out.append(f"{path}.{k}")
                elif is_dataclass(v) and type(v) in (Semantics, Admission, Grid,
                                                     PrefillSpec, Pipeline):
                    walk(v, f"{path}.")
                else:
                    out.append(path)

        walk(self, "")
        return out

    def unknown_paths(self) -> list[str]:
        """Leaves left ``None``: not established on this substrate."""
        out: list[str] = []

        def walk(obj, prefix: str) -> None:
            for f in fields(obj):
                if f.name in ("name", "provenance", "notes"):
                    continue
                v = getattr(obj, f.name)
                path = f"{prefix}{f.name}"
                if v is None:
                    if path != "context_cost":
                        out.append(path)
                elif isinstance(v, tuple) and v and is_dataclass(v[0]):
                    for i, item in enumerate(v):
                        walk(item, f"{path}[{i}].")
                elif isinstance(v, Mapping):
                    out.extend(f"{path}.{k}" for k, item in v.items() if item is None)
                elif is_dataclass(v) and type(v) in (Semantics, Admission, Grid,
                                                     PrefillSpec, Pipeline):
                    walk(v, f"{path}.")

        walk(self, "")
        if self.semantics.preemption == "none":
            # The sub-fields describe a path that does not exist here.
            out = [p for p in out if not p.startswith("semantics.preempt")]
        return out

    def layer_summary(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for path, prov in self.provenance.items():
            grouped.setdefault(prov.layer, []).append(path)
        return {k: sorted(v) for k, v in sorted(grouped.items())}

    # -- derived quantities ----------------------------------------------------

    @property
    def reuse_pool(self) -> PoolLayer:
        return self.layers[self.reuse_layer]

    @property
    def eviction_order(self) -> str | None:
        """The reuse layer's eviction order."""
        return self.reuse_pool.eviction_order

    @property
    def max_running(self) -> int:
        if self.admission.max_running is None:
            raise ValueError("max_running is not established")
        return self.admission.max_running

    def step_time_s(self, running: int) -> float:
        """Uniform-decode step time with ``running`` requests on the grid."""
        model = self.step_cost.get("decode")
        if model is None:
            raise ValueError("decode step cost is not measured")
        width = self.grid.width_for(running)
        if width is None:
            raise ValueError("step above the top grid size runs eager; no decode curve for it")
        return model.step_time_s(bucket=width, actual=running)

    # -- configuration variants --------------------------------------------------

    def with_config(self, *, grid: tuple[int, ...] | None = None,
                    max_running: int | None = None,
                    reuse_capacity: int | None = None) -> "SubstrateDescriptorV2":
        """The same substrate under another configuration.

        Grid widths whose decode fixed cost was not measured are filled by the
        interpolation rule of ``config_search.descriptor_for`` (linear between
        measured neighbours, linear extrapolation from the outermost pair). The
        filled values are a model, and the provenance note says so.
        """
        d = self
        prov = dict(self.provenance)
        if grid is not None:
            grid = tuple(sorted(grid))
            model = self.step_cost.get("decode")
            costs = dict(self.step_cost)
            if model is not None:
                fixed = interpolate_fixed(model.fixed_s_by_bucket, grid)
                costs["decode"] = replace(model, fixed_s_by_bucket=fixed)
                filled = sorted(set(grid) - set(model.fixed_s_by_bucket))
                if filled:
                    p = prov["step_cost.decode"]
                    prov["step_cost.decode"] = replace(
                        p, note=f"{p.note} | widths {filled} interpolated (config variant)")
            d = replace(d, grid=replace(d.grid, sizes=grid), step_cost=costs)
        if max_running is not None:
            d = replace(d, admission=replace(d.admission, max_running=max_running))
        if reuse_capacity is not None:
            layers = list(d.layers)
            layers[d.reuse_layer] = replace(layers[d.reuse_layer], capacity_units=reuse_capacity)
            d = replace(d, layers=tuple(layers))
        return replace(d, provenance=prov)

    # -- v1 view -----------------------------------------------------------------

    def legacy_view(self) -> SubstrateDescriptor:
        """The v1 descriptor earlier scripts read. Defined only for substrates v1
        can express: two layers (inner block, outer slot), allocation-FIFO outer
        layer, exclusive prefill, a request-count grid."""
        if len(self.layers) != 2 or self.reuse_layer != 1:
            raise ValueError("v1 needs an inner/outer two-layer pool with reuse on the outer layer")
        if self.layers[1].eviction_order != "allocation_fifo":
            raise ValueError("v1 outer pool is allocation FIFO only")
        if self.grid.unit != "requests":
            raise ValueError("v1 bucket_for maps request counts")
        inner, outer = self.layers
        legacy_map = _LEGACY_PROVENANCE
        prov = {}
        for old, new in legacy_map.items():
            if new in self.provenance:
                prov[old] = self.provenance[new]
        return SubstrateDescriptor(
            name=self.name,
            bucket_sizes=self.grid.sizes,
            step_cost_model=self.step_cost["decode"],
            outer_slot_count=outer.capacity_units,
            outer_slot_tokens=outer.unit_tokens,
            inner_block_tokens=inner.unit_tokens,
            inner_block_count=inner.capacity_units,
            outer_eviction_policy="fifo",
            inner_eviction_policy={"release_lru": "lru", "allocation_fifo": "fifo"}[inner.eviction_order],
            hit_formula=self.hit_formula,
            kv_pool_tokens=outer.capacity_units * outer.unit_tokens,
            prefill_cost_model=self.prefill.cost,
            release_rule=self.semantics.evictable_when,
            dummy_mode=self.semantics.dummy_mode,
            resume_allocates_first=self.semantics.resume_allocates_first,
            provenance=prov,
            notes=self.notes,
        )


#: v1 field -> v2 path whose provenance it takes in ``legacy_view``.
_LEGACY_PROVENANCE = {
    "bucket_sizes": "grid.sizes",
    "step_cost_model": "step_cost.decode",
    "outer_slot_count": "layers[1].capacity_units",
    "outer_slot_tokens": "layers[1].unit_tokens",
    "inner_block_tokens": "layers[0].unit_tokens",
    "inner_block_count": "layers[0].capacity_units",
    "outer_eviction_policy": "layers[1].eviction_order",
    "inner_eviction_policy": "layers[0].eviction_order",
    "hit_formula": "hit_formula",
    "kv_pool_tokens": "layers[1].capacity_units",
    "prefill_cost_model": "prefill.cost",
    "release_rule": "semantics.evictable_when",
    "dummy_mode": "semantics.dummy_mode",
    "resume_allocates_first": "semantics.resume_allocates_first",
}


def interpolate_fixed(measured: Mapping[int, float], widths) -> dict[int, float]:
    """``config_search.descriptor_for``'s fill rule, restated (bit-identical)."""
    fixed = dict(measured)
    known = sorted(fixed)
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
