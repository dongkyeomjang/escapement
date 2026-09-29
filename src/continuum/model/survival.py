"""Whether a cached prefix is still there when its session comes back.

Deterministic core
------------------
A pool of ``capacity`` units holds cached prefixes. Every admitted request
takes units from it. What decides whether a returning session finds its
prefix is not how long it was away but how many units were handed out while
it was away -- *counted over the right window*.

Which window is right depends on the eviction order:

* **FIFO by allocation** (the measured substrate): an entry's position in the
  eviction queue is fixed when its slot is allocated. The window therefore
  runs from the target's *allocation* -- not from the start of its tool gap --
  to the returning request's *lookup*. The target's own prefill and decode sit
  inside the window. And because the returning request takes its own slot
  before it looks up (TASK15, TASK24), its own allocation is inside the window
  too.
* **LRU over a free queue** (vLLM's block pool): an entry joins the eviction
  queue when its request *releases* it, and blocks held by a running request
  are not in the queue at all. The window runs from the target's release to
  the lookup; whether the returning request allocates before or after it looks
  up is a stack parameter, not a law.

Within the window the law is one inequality::

    target_units + sum(window_units) + pinned_units + dummy_units <= capacity

``window_units`` are the units allocated in the window, the returning
request's own included when it allocates first. ``pinned_units`` are units
*older* than the target that are still held by a running request at the
moment an eviction has to pick a victim: they cannot be evicted, so the victim
moves on to the target sooner. ``dummy_units`` are units held at the lookup
instant by something that is not a request.

The inequality does not depend on how full the pool was when the target was
allocated. With FIFO, every entry older than the target is evicted before the
target is, so free slots and older entries buy the same thing: each is one
more allocation the target can outlast. That is why the measured threshold is
a count (TASK14, TASK15) and why the same count held at 500-4,000 token
background sizes (TASK29).

A "unit" is whatever one request consumes. With sequence slots (one slot per
request, the measured substrate) a request is one unit and the law is a
request count. With a block pool a request is ``ceil(tokens / block)`` units
and the law becomes a token budget. Both are instances of the same inequality;
only the consumption function differs.

Dummy block
-----------
TASK63 watched this stack ask for a padding block on every decode step whose
batch is partial, and watched the next admission take exactly the slot the
padding request was pointing at (74/74). So at an admission the padding slot is
*not* held: it was pre-evicted during the preceding decode step and is handed
to the admission. The effect is that the eviction an admission needs happens
one decode step early, plus one trailing eviction after the last admission of
a run (TASK58's ``max(0, ALLOC + 1 - 8)``). At the lookup instant nothing
extra is held, so under that reading ``dummy_units = 0`` and the survival
threshold is unchanged; what moves is *when* the victim is chosen, which
matters only through ``pinned_units``.

The simulator's TASK69 switch models the padding block differently -- as a
slot reserved at admission time whenever the batch is partial -- which makes
``dummy_units = 1`` at a lookup that happens while others are decoding.
``DummyMode`` names both readings so that the difference can be evaluated
rather than assumed.

Probabilistic extension
-----------------------
In a steady multi-session load the number of allocations in the window is a
random variable ``A``. Survival probability is then::

    P(survive) = P(target + A_units + resume + pinned + dummy <= capacity)

``A`` is counted from the other sessions' admissions during a window of random
length ``W`` (the target's own residence plus its tool gap plus any wait).
Two count laws are provided and they bracket the truth for cycle-time
variability up to exponential:

* ``binomial`` -- each other session is a renewal process with a fixed cycle,
  so over a window shorter than one cycle it is admitted at most once. Least
  dispersed; right when cycles are regular and sessions are few.
* ``poisson`` -- the infinite-population limit at the same total rate. More
  dispersed; right when many independent sessions each contribute rarely.

Mean-field (characteristic-time) forms are provided for both eviction orders.
For FIFO-by-allocation in which *every* admission allocates -- hit or miss,
which is what this stack does -- an entry lives exactly as long as it takes
``capacity`` units to be inserted after it, so the characteristic time is
``capacity / insertion_rate`` without the fixed point classical FIFO needs
(Martina, Garetto, Leonardi, INFOCOM 2014, treat insert-on-miss). For LRU the
Che approximation (Che, Tung, Wang, IEEE JSAC 2002) is solved with two
corrections a KV cache needs: blocks held by running requests are outside the
queue, and a request's whole context (generated tokens included) enters the
queue on release, not only the reusable prefix.

Nothing here names an accelerator. Capacities, unit sizes, the eviction order
and the dummy behaviour are all read from a descriptor or passed in.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
import math

from ..substrate.descriptor import HitFormula, SubstrateDescriptor


# -- consumption ------------------------------------------------------------

def units_for(tokens: int, unit_tokens: int) -> int:
    """Units of ``unit_tokens`` a request of ``tokens`` occupies (at least 1)."""
    if tokens <= 0:
        raise ValueError("tokens must be positive")
    if unit_tokens <= 0:
        raise ValueError("unit_tokens must be positive")
    return math.ceil(tokens / unit_tokens)


def sequence_slot_units(descriptor: SubstrateDescriptor, tokens: int) -> int:
    """Consumption on a sequence-slot pool: the descriptor's outer slots."""
    return descriptor.outer_slots_for(tokens)


def block_units(descriptor: SubstrateDescriptor, tokens: int) -> int:
    """Consumption on a block pool indexed at the inner block size."""
    return units_for(tokens, descriptor.inner_block_tokens)


class DummyMode(str, Enum):
    """How a non-request padding block is charged at a lookup.

    ``NONE``        no padding consumer.
    ``PRE_EVICT``   the observed behaviour (TASK63): the padding request points
                    at a free slot during a partial decode step and the next
                    admission takes that slot. Nothing extra is held at the
                    lookup; eviction timing moves one step earlier.
    ``RESERVED``    the simulator's TASK69 switch: one slot is reserved at an
                    admission whenever ``0 < running < ceiling``.
    """

    NONE = "none"
    PRE_EVICT = "pre_evict"
    RESERVED = "reserved"


def dummy_units_at_lookup(mode: DummyMode, *, running_at_admission: int,
                          ceiling: int) -> int:
    """Units a padding consumer holds when the returning request looks up."""
    if running_at_admission < 0 or ceiling <= 0:
        raise ValueError("running_at_admission must be >= 0 and ceiling > 0")
    if mode is DummyMode.RESERVED:
        return int(0 < running_at_admission < ceiling)
    return 0


# -- deterministic core -----------------------------------------------------

@dataclass(frozen=True)
class Window:
    """What is charged against the pool between the window's two ends."""

    target_units: int
    window_units: tuple[int, ...]
    """Units allocated inside the window, one entry per allocation. Includes
    the returning request's own allocation when it allocates before lookup."""
    pinned_units: int = 0
    """Units older than the target, still held by running requests when the
    eviction that would otherwise have spared the target picks its victim."""
    dummy_units: int = 0

    def __post_init__(self) -> None:
        if self.target_units <= 0:
            raise ValueError("target_units must be positive")
        if any(u <= 0 for u in self.window_units):
            raise ValueError("every allocation consumes at least one unit")
        if self.pinned_units < 0 or self.dummy_units < 0:
            raise ValueError("pinned and dummy units must be non-negative")

    @property
    def demand(self) -> int:
        return (self.target_units + sum(self.window_units)
                + self.pinned_units + self.dummy_units)


def overflow(capacity: int, window: Window) -> int:
    """Units that must have been evicted from the target by the lookup."""
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    return window.demand - capacity


def survives(capacity: int, window: Window) -> bool:
    """The whole target is still cached at the lookup."""
    return overflow(capacity, window) <= 0


def surviving_units(capacity: int, window: Window) -> int:
    """Target units still cached at the lookup, when units go one at a time.

    Meaningful for a block pool that evicts the tail of a chain first (vLLM's
    free queue documents that order); a prefix is usable up to its first hole,
    so losing ``k`` tail units leaves ``target_units - k`` usable ones.
    """
    return max(0, window.target_units - max(0, overflow(capacity, window)))


def reusable_tokens(*, hit_formula: HitFormula, granularity: str,
                    capacity: int, window: Window, unit_tokens: int,
                    cached_prefix_tokens: int, query_tokens: int) -> int:
    """Tokens the returning request is served from cache.

    ``granularity`` is ``"sequence"`` (all-or-nothing: the entry is either
    there or not) or ``"block"`` (tail-first partial loss).
    """
    if granularity == "sequence":
        shared = cached_prefix_tokens if survives(capacity, window) else 0
    elif granularity == "block":
        shared = min(cached_prefix_tokens,
                     surviving_units(capacity, window) * unit_tokens)
    else:
        raise ValueError(f"unknown granularity {granularity!r}")
    return hit_formula.hit_tokens(shared_prefix_tokens=shared,
                                  query_tokens=query_tokens)


def sequential_window(*, target_units: int, background_units: Iterable[int],
                      resume_units: int, resume_allocates_first: bool = True) -> Window:
    """The TASK14/TASK15 protocol: target, then background requests one at a
    time, then the resume. Nothing runs concurrently, so nothing is pinned and
    the padding consumer holds nothing at the resume's lookup under either
    dummy reading (no request is decoding when the resume is admitted)."""
    units = tuple(background_units)
    if resume_allocates_first:
        units = units + (resume_units,)
    return Window(target_units=target_units, window_units=units)


def sequential_threshold(*, capacity: int, target_units: int,
                         background_unit: int, resume_units: int,
                         resume_allocates_first: bool = True) -> int:
    """Largest number of equal background requests the target survives."""
    room = capacity - target_units - (resume_units if resume_allocates_first else 0)
    if room < 0:
        return -1
    return room // background_unit


def sequential_eviction_count(*, allocations: int, capacity_units: int,
                              trailing_dummy: bool) -> int:
    """Evictions a sequential run with one unit per request performs in total.

    With the padding consumer pre-evicting during the last request's decode,
    one eviction more than the allocations need is performed (TASK58's
    ``max(0, ALLOC + 1 - capacity)``); it happens after the last lookup, so it
    changes the count and never the survival of that lookup.
    """
    if allocations < 0:
        raise ValueError("allocations must be non-negative")
    return max(0, allocations + int(trailing_dummy) - capacity_units)


def block_pool_thresholds(*, capacity: int, target_units: int,
                          background_unit: int, resume_units: int,
                          full_hit_units: int,
                          resume_allocates_first: bool = True) -> tuple[int | None, int | None]:
    """(first B that loses any reusable token, first B that loses all of them).

    ``full_hit_units`` is how many leading target units the hit formula can use
    at all (``hit_tokens // unit``) -- losing tail units beyond it costs nothing.
    Returns ``None`` for a threshold the load never reaches.
    """
    own = resume_units if resume_allocates_first else 0
    # Lose something once more than (target_units - full_hit_units) units overflow.
    slack = target_units - full_hit_units
    first_loss = (capacity - target_units - own + slack) // background_unit + 1
    # Lose everything once overflow reaches target_units.
    need = capacity - own
    total_loss = math.ceil(need / background_unit) if need > 0 else 0
    return first_loss, total_loss


# -- probabilistic extension ------------------------------------------------

def _binomial_pmf(n: int, p: float) -> list[float]:
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be in [0, 1]")
    return [math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]


def _poisson_pmf(mean: float, upto: int) -> list[float]:
    if mean < 0:
        raise ValueError("mean must be non-negative")
    out = [math.exp(-mean)]
    for k in range(1, upto + 1):
        out.append(out[-1] * mean / k)
    return out


def admissions_in_window_pmf(*, other_sessions: int, window_s: float,
                             cycle_s: float, law: str,
                             upto: int) -> list[float]:
    """P(A_other = k), k = 0..upto, for other sessions' admissions in a window.

    Each other session is a stationary renewal process of mean cycle
    ``cycle_s`` (think + response). Whatever the cycle law, the mean count is
    ``window / cycle`` per session; the laws differ in dispersion.

    ``binomial``: fixed cycles. Each session contributes ``floor(w/c)``
    admissions surely and one more with probability ``frac(w/c)``.
    ``poisson``: the infinite-population limit at the same total rate.

    Probability mass beyond ``upto`` is folded into the last entry so the
    result sums to one.
    """
    if other_sessions < 0 or window_s < 0 or cycle_s <= 0 or upto < 0:
        raise ValueError("invalid arguments")
    x = window_s / cycle_s
    if law == "binomial":
        base = math.floor(x) * other_sessions
        pmf_extra = _binomial_pmf(other_sessions, x - math.floor(x))
        out = [0.0] * (upto + 1)
        for k, p in enumerate(pmf_extra):
            out[min(base + k, upto)] += p
        return out
    if law == "poisson":
        mean = other_sessions * x
        pmf = _poisson_pmf(mean, upto)
        tail = max(0.0, 1.0 - sum(pmf))
        pmf[-1] += tail
        return pmf
    raise ValueError(f"unknown count law {law!r}")


def survival_probability(*, capacity: int, target_units: int, resume_units: int,
                         other_unit: int, other_sessions: int,
                         window_samples: Sequence[tuple[float, float]],
                         cycle_s: float, law: str = "binomial",
                         pinned_units: int = 0, dummy_units: int = 0,
                         resume_allocates_first: bool = True) -> float:
    """P(whole target survives) averaged over a discrete window distribution.

    ``window_samples`` is ``[(window_s, weight), ...]``; weights need not sum
    to one. The window is allocation-to-lookup for FIFO and release-to-lookup
    for LRU; the caller builds it (see ``fifo_window_samples``).
    """
    if other_unit <= 0:
        raise ValueError("other_unit must be positive")
    own = resume_units if resume_allocates_first else 0
    room = capacity - target_units - own - pinned_units - dummy_units
    if room < 0:
        return 0.0
    max_others = room // other_unit
    total_w = sum(w for _, w in window_samples)
    if total_w <= 0:
        raise ValueError("window weights must sum to a positive value")
    acc = 0.0
    for window_s, weight in window_samples:
        pmf = admissions_in_window_pmf(other_sessions=other_sessions,
                                       window_s=window_s, cycle_s=cycle_s,
                                       law=law, upto=max_others + 1)
        acc += weight * sum(pmf[: max_others + 1])
    return acc / total_w


def fifo_window_samples(*, residence_s: float,
                        gap_samples: Sequence[tuple[float, float]],
                        wait_s: float = 0.0) -> list[tuple[float, float]]:
    """Allocation-to-lookup windows: the target's own residence (prefill plus
    decode after its slot was allocated), then its tool gap, then any wait
    before it is admitted again."""
    if residence_s < 0 or wait_s < 0:
        raise ValueError("residence and wait must be non-negative")
    return [(residence_s + g + wait_s, w) for g, w in gap_samples]


def lru_window_samples(*, gap_samples: Sequence[tuple[float, float]],
                       wait_s: float = 0.0) -> list[tuple[float, float]]:
    """Release-to-lookup windows for a free-queue LRU pool."""
    if wait_s < 0:
        raise ValueError("wait must be non-negative")
    return [(g + wait_s, w) for g, w in gap_samples]


# -- mean-field (characteristic time) ---------------------------------------

def fifo_characteristic_time(*, capacity_units: float, insertion_units_per_s: float,
                             pinned_units: float = 0.0) -> float:
    """Lifetime of an entry in a FIFO pool where every admission allocates.

    Each entry is evicted after ``capacity - pinned`` units have been inserted
    behind it, so in the mean-field limit it lives exactly that long. No fixed
    point is needed because insertion does not depend on hit or miss.
    """
    if insertion_units_per_s <= 0:
        raise ValueError("insertion rate must be positive")
    return max(0.0, capacity_units - pinned_units) / insertion_units_per_s


def lru_che_characteristic_time(*, capacity_units: float, active_units: float,
                                sessions: int, released_units_per_cycle: float,
                                cycle_s: float,
                                expected_min_gap: Callable[[float], float],
                                t_max: float = 1e6, tol: float = 1e-9) -> float:
    """Che characteristic time for a free-queue LRU block pool.

    The queue holds only released blocks, so its capacity is the pool minus the
    units held by running requests (``active_units``). A session in its tool
    gap has its released blocks in the queue for ``min(gap, T)``, so the
    queue's time-average content is::

        sessions * released_units_per_cycle * E[min(G, T)] / cycle

    and ``T`` solves content = capacity - active. ``expected_min_gap(T)``
    returns ``E[min(G, T)]`` for the gap law. ``released_units_per_cycle`` is
    the whole context a request releases -- generated tokens included -- not
    only the reusable prefix: that is one of the ways a KV cache differs from a
    classical object cache.

    Returns ``math.inf`` when the queue never fills.
    """
    room = capacity_units - active_units
    if room <= 0:
        return 0.0

    def content(t: float) -> float:
        return sessions * released_units_per_cycle * expected_min_gap(t) / cycle_s

    if content(t_max) < room:
        return math.inf
    lo, hi = 0.0, t_max
    while hi - lo > tol * max(1.0, hi):
        mid = 0.5 * (lo + hi)
        if content(mid) < room:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def empirical_expected_min(samples: Sequence[tuple[float, float]]) -> Callable[[float], float]:
    """``T -> E[min(G, T)]`` for a discrete distribution ``[(g, weight)]``."""
    total = sum(w for _, w in samples)
    if total <= 0:
        raise ValueError("weights must sum to a positive value")

    def f(t: float) -> float:
        return sum(w * min(g, t) for g, w in samples) / total

    return f


def hit_probability_characteristic(*, characteristic_s: float,
                                   window_samples: Sequence[tuple[float, float]]) -> float:
    """P(window < characteristic time): the mean-field survival probability."""
    total = sum(w for _, w in window_samples)
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    return sum(w for x, w in window_samples if x < characteristic_s) / total
