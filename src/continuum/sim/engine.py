"""Deterministic step-level simulator for a bucketed, prefill-exclusive engine.

The engine being modelled schedules in whole steps and never mixes the two
kinds of work: if any request is waiting to be admitted, exactly one is
admitted and its prefill owns the step, so every session already decoding
stops. Otherwise every running request advances by one token inside a padded
batch whose width is the smallest compiled bucket that fits them.

That is the whole scheduler. Everything interesting -- padding waste, the
serialization tax, whether a returning session still finds its prefix --
follows from those two rules plus the outer-block pool in ``cache.py``.

The simulator is deterministic by construction. Real runs are not: threads
start in whatever order the OS picks, so the admission order of requests that
arrive at the same instant is not reproducible. ``SimConfig.arrival_order``
names the tie-break used instead, and ``TASK24`` measures what that assumption
costs.

Nothing here names an accelerator: every constant comes from the descriptor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import itertools

from ..policy.lookahead import Context, Informed, Lookahead, PeerView
from ..policy.online import ReturnPolicy, ReturnState
from ..substrate.descriptor import SubstrateDescriptor
from ..substrate.v2 import SubstrateDescriptorV2
from ..workload.agentic import Session
from .cache import Eviction, GranularPool, OuterBlockPool


@dataclass(frozen=True)
class SimConfig:
    """Everything the simulator needs that the descriptor does not describe."""

    max_running_requests: int
    """Scheduler admission ceiling (``max_num_seqs``)."""

    client_overhead_s: float = 0.0
    """Time between a response arriving and the next turn being sent, on top of
    the tool gap. Measured at 0.6-5.6 ms; the default treats it as zero so it
    is not a fitted knob."""

    arrival_order: str = "session_index"
    """Tie-break for requests that arrive at the same instant."""

    return_policy: ReturnPolicy | None = None
    """Holds a session's return after its tool gap, if set. ``None`` reproduces
    the immediate-return behaviour every earlier task measured, bit for bit."""

    return_budget_s: float = 0.0
    reveal_peers: bool = False
    """Hand the policy exact peer ready times even with no noisy clock set.
    An information probe, like ``peer_clock``; never used by anything measured."""

    reveal_generation: bool = False
    """Hand the policy how long each running request will still decode for.
    The other half of the information decomposition, and equally undeployable."""

    peer_clock: object | None = None
    """Supplies the predicted tool-gap durations a lookahead policy is told.

    Set only for the information-value probe: it hands the policy knowledge no
    client has. ``None`` -- the default and the only setting used by anything
    measured -- means peers are invisible, exactly as on hardware."""
    """Latency budget the policy is bounded by. Ignored when no policy is set."""

    decode_cost_fn: object | None = None
    """Deprecated (kept so the committed TASK98/TASK101 scripts reproduce):
    ``(bucket, running, sum_ctx) -> seconds`` for a decode step. The supported
    form is ``SubstrateDescriptorV2.context_cost`` (TASK103). Setting both is
    an error. Not read by the paged engine."""

    cache_granularity: str = "outer"
    """``outer`` reproduces the measured pool: one block per sequence, whole
    blocks evicted. ``inner`` is an ablation -- many small blocks reclaimed one
    at a time, so a prefix decays instead of vanishing."""

    eviction_policy: str | None = None
    """Overrides the descriptor's policy. ``None`` uses what was measured."""

    prefill_exclusive: bool = True
    """Whether a prefill owns its whole step. The measured substrate does
    exactly this. Setting it false models a chunked-prefill engine that runs
    prefill alongside decode, so no session stops -- an ablation, not an
    observation."""

    fixed_arrivals: dict[tuple[int, int], float] | None = None
    """Re-arrival times to use instead of recomputing them from completion.

    Normally a session's next turn arrives at ``finish + tool gap``, so a
    configuration that finishes a turn earlier also starts the next one
    earlier and the two feed back into each other. Supplying a
    ``(session_index, turn) -> arrival_s`` map pins every re-arrival to a time
    measured elsewhere, which switches that feedback off: the arm is then
    scored on the same arrival series as whatever run the map came from.

    Turn 0 is not covered -- it is not a re-arrival. A missing key for a turn
    that does occur is an error rather than a silent fall-back to the computed
    time, because a half-pinned series is neither model.
    """

    dummy_block: bool = False
    """Charge the outer pool one extra slot while the decode batch is short.

    TASK63 watched this stack ask for a padding block on every decode step
    whose request count is strictly between zero and the execution ceiling, and
    stop asking at the ceiling; TASK58 had already traced a one-block
    difference in reclaim counts to it. Off by default -- the measured reclaim
    arithmetic closed without it, and switching it on changes what the pool can
    admit, so nothing produced before this switch existed is affected.
    """

    release_rule: str = "deferred"
    """When a finished request's outer block becomes evictable. ``deferred``
    is the behaviour every earlier task was computed with; ``immediate`` is
    the rule TASK72 found on the measured substrate. A switch, not a default."""

    dummy_mode: str = "off"
    """``off`` (every earlier task), ``reserved`` (same as ``dummy_block``:
    one slot held at admission while the batch is partial, TASK69) or
    ``pre_evict`` (TASK63's observed behaviour: on each decode step with
    ``0 < running < max_running_requests`` evict the oldest inactive block if
    none is free; the next admission takes it)."""

    session_start_s: tuple[float, ...] | None = None
    """Arrival time of each session's first turn, by session index. ``None``
    (every earlier task) starts every session at 0."""

    successor: tuple[int | None, ...] | None = None
    """Session renewal: ``successor[i] = j`` starts session ``j``'s first turn
    as soon as session ``i``'s last turn finishes. A session that is someone's
    successor is not started at the beginning. ``None`` (every earlier task)
    means no renewal. Used by the steady-state multi-turn workload (TASK77)."""

    admission_priority: tuple[int, ...] = ()
    """Session indices in the order simultaneous arrivals should be admitted.

    Real runs open their sessions from a thread pool, so the order in which
    requests that were issued at the same instant reach the server is set by
    the OS scheduler and is not reproducible. Left empty, the simulator uses
    session index, which is an assumption rather than a measurement; passing
    an observed order here is how that assumption's cost is measured.
    """

    semantics: str = "legacy"
    """Where the pool rules come from. ``legacy`` (every result before TASK84,
    and the default so they reproduce bit for bit) uses ``release_rule``,
    ``dummy_mode``/``dummy_block`` and ``eviction_policy`` from this config.
    ``descriptor`` reads them from the descriptor (v2 ``semantics`` and the
    reuse layer's eviction order, or the v1 fields of the same names) and
    refuses any rule this simulator does not implement; the config switches
    must then stay at their defaults. New predictions use ``descriptor``
    (directive 06 decision 4)."""

    window_rule: object | None = None
    """A ``WindowRule``: once the warm-up end is known, nothing new is issued
    after the evaluation window (the runner's rule). Read by the paged engine
    only (``paged.simulate_paged``); ``None`` issues the whole plan."""

    slot_of: tuple[int, ...] | None = None
    """Slot of each session, for ``window_rule``."""

    n_slots: int | None = None
    """Number of slots, for ``window_rule``."""

    def __post_init__(self) -> None:
        if self.window_rule is not None and (self.slot_of is None or self.n_slots is None):
            raise ValueError("window_rule needs slot_of and n_slots")
        if self.semantics not in ("legacy", "descriptor"):
            raise ValueError(f"unknown semantics {self.semantics!r}")
        if self.semantics == "descriptor" and (
                self.release_rule != "deferred" or self.dummy_mode != "off"
                or self.dummy_block or self.eviction_policy is not None):
            raise ValueError("semantics='descriptor' reads the pool rules from the "
                             "descriptor; leave the config switches at their defaults")
        if self.max_running_requests <= 0:
            raise ValueError("max_running_requests must be positive")
        if self.client_overhead_s < 0:
            raise ValueError("client_overhead_s must be non-negative")
        if self.arrival_order not in ("session_index", "arrival_time"):
            raise ValueError(f"unknown arrival_order {self.arrival_order!r}")
        if len(set(self.admission_priority)) != len(self.admission_priority):
            raise ValueError("admission_priority must not repeat a session")
        if self.return_budget_s < 0:
            raise ValueError("return_budget_s must be non-negative")
        if self.cache_granularity not in ("outer", "inner"):
            raise ValueError(f"unknown cache_granularity {self.cache_granularity!r}")
        if self.release_rule not in ("deferred", "immediate"):
            raise ValueError(f"unknown release_rule {self.release_rule!r}")
        if self.dummy_mode not in ("off", "reserved", "pre_evict"):
            raise ValueError(f"unknown dummy_mode {self.dummy_mode!r}")
        if self.dummy_block and self.dummy_mode not in ("off", "reserved"):
            raise ValueError("dummy_block=True is the 'reserved' mode; do not combine "
                             "it with another dummy_mode")
        if (self.release_rule != "deferred" or self.dummy_mode != "off") and \
                self.cache_granularity != "outer":
            raise ValueError("release_rule and dummy_mode describe the outer block pool")
        if self.dummy_block and self.cache_granularity != "outer":
            raise ValueError(
                "dummy_block describes the outer block pool; it has no meaning "
                "at inner granularity"
            )
        if self.fixed_arrivals is not None:
            for (idx, turn), at in self.fixed_arrivals.items():
                if turn < 1:
                    raise ValueError(
                        f"fixed_arrivals covers turn {turn} of session {idx}; "
                        "only re-arrivals (turn >= 1) have an arrival to pin"
                    )
                if at < 0:
                    raise ValueError(f"fixed arrival {at} is negative")


def _decode_s(descriptor, config: "SimConfig", running: list, actual: int, context_cost=None) -> float:
    """Decode step time. ``context_cost`` (``SubstrateDescriptorV2.context_cost``,
    unit ``s``) adds ``per_token * (sum_ctx - n * reference)``; ``sum_ctx`` sums
    each running request's prompt plus generated tokens."""
    if config.decode_cost_fn is not None:
        ctx = sum(r["prompt_tokens"] + r["generation_tokens"] - r["remaining"] for r in running)
        return config.decode_cost_fn(descriptor.bucket_for(actual), actual, ctx)
    if context_cost is None:
        return descriptor.step_time_s(actual)
    ctx = sum(r["prompt_tokens"] + r["generation_tokens"] - r["remaining"] for r in running)
    return descriptor.step_time_s(actual) + context_cost.term(ctx, actual)


@dataclass
class StepRecord:
    kind: str
    """``prefill`` or ``decode``."""
    start_s: float
    duration_s: float
    running: int
    """Requests in the decode set. For a prefill step these are the sessions
    that lose the whole duration."""
    bucket: int | None = None
    session: str | None = None
    computed_tokens: int | None = None


@dataclass
class RequestRecord:
    session: str
    session_index: int
    turn: int
    prompt_tokens: int
    generation_tokens: int
    arrival_s: float
    admit_s: float
    finish_s: float
    cached_tokens: int
    computed_tokens: int
    prefill_s: float
    ready_s: float = 0.0
    """When the return became ready. ``arrival_s - ready_s`` is the hold."""
    evicted_sessions: tuple[str, ...] = ()

    @property
    def held_s(self) -> float:
        return self.arrival_s - self.ready_s


@dataclass
class SimResult:
    steps: list[StepRecord]
    requests: list[RequestRecord]
    wall_clock_s: float
    evictions: list[Eviction] = field(default_factory=list)

    # -- aggregates ---------------------------------------------------------

    @property
    def decode_steps(self) -> list[StepRecord]:
        return [s for s in self.steps if s.kind == "decode"]

    @property
    def prefill_steps(self) -> list[StepRecord]:
        return [s for s in self.steps if s.kind == "prefill"]

    @property
    def utilization(self) -> float:
        """Slot occupancy over decode steps: ``sum(actual) / sum(bucket)``.

        Dimensionless. Not a time share: steps in different buckets cost
        different amounts, which is what ``busy_s`` is for.
        """
        d = self.decode_steps
        num = sum(s.running for s in d)
        den = sum(s.bucket or 0 for s in d)
        return num / den if den else 0.0

    @property
    def decode_busy_s(self) -> float:
        return sum(s.duration_s for s in self.decode_steps)

    @property
    def prefill_busy_s(self) -> float:
        return sum(s.duration_s for s in self.prefill_steps)

    @property
    def busy_s(self) -> float:
        return self.decode_busy_s + self.prefill_busy_s

    @property
    def stall_s(self) -> float:
        """Decode time lost to prefill, summed over the sessions that lost it.

        This is the TASK22 term: a prefill costs the system its duration times
        the number of sessions that were decoding at the time.
        """
        return sum(s.duration_s * s.running for s in self.prefill_steps)

    @property
    def reuse_hits(self) -> int:
        return sum(1 for r in self.requests if r.cached_tokens > 0)

    @property
    def resume_requests(self) -> int:
        return sum(1 for r in self.requests if r.turn > 0)

    def pair_histogram(self) -> dict[str, int]:
        """Decode steps by ``actual->bucket``, the shape the [BUCKET] log gives."""
        out: dict[str, int] = {}
        for s in self.decode_steps:
            out[f"{s.running}->{s.bucket}"] = out.get(f"{s.running}->{s.bucket}", 0) + 1
        return dict(sorted(out.items(), key=lambda kv: int(kv[0].split("->")[0])))


@dataclass
class _Pending:
    session: str
    session_index: int
    turn: int
    prompt_tokens: int
    generation_tokens: int
    gap_after_s: float
    gap_start_s: float
    """When this return's tool gap began. With the gap duration it gives the
    ready time, which is what a duration predictor would be estimating."""
    arrival_s: float
    """When the return is actually handed to the server."""
    ready_s: float
    """When the tool gap finished, i.e. the earliest a return could be sent.
    Equal to ``arrival_s`` with no policy; the difference is the hold."""
    seq: int


def _prompt_tokens(session: Session, turn_index: int) -> int:
    """Tokens turn ``turn_index`` sends.

    An agentic turn resends the whole transcript: every earlier turn's new
    segment and everything it generated, plus this turn's new segment.
    """
    return session.context_tokens_before(turn_index) + session.turns[turn_index].new_segment_tokens


def _descriptor_rules(descriptor, config: SimConfig):
    """(numeric v1 view, release rule, dummy mode, eviction policy) for ``config``.

    Accepts a v1 ``SubstrateDescriptor`` or a ``SubstrateDescriptorV2``. With
    ``semantics='descriptor'`` every rule the engine depends on is checked
    against what it implements -- a rule it cannot follow is an error, not a
    silent approximation."""
    v2 = isinstance(descriptor, SubstrateDescriptorV2)
    if config.semantics == "legacy":
        numeric = descriptor.legacy_view() if v2 else descriptor
        return (numeric, config.release_rule,
                config.dummy_mode if not config.dummy_block else "reserved",
                config.eviction_policy or numeric.outer_eviction_policy)
    if v2:
        sem = descriptor.semantics
        order = descriptor.eviction_order
        release, dummy = sem.evictable_when, sem.dummy_mode
        unsupported = []
        if order != "allocation_fifo":
            unsupported.append(f"eviction_order={order}")
        if sem.intra_request_loss != "all_or_nothing":
            unsupported.append(f"intra_request_loss={sem.intra_request_loss}")
        if sem.resume_allocates_first is not True:
            unsupported.append(f"resume_allocates_first={sem.resume_allocates_first}")
        if sem.cacheable_tokens != "prefill_only":
            unsupported.append(f"cacheable_tokens={sem.cacheable_tokens}")
        if sem.preemption != "none":
            unsupported.append(f"preemption={sem.preemption}")
        if descriptor.prefill.execution != "exclusive" and config.prefill_exclusive:
            unsupported.append(f"prefill.execution={descriptor.prefill.execution}")
        if unsupported:
            raise ValueError("simulator does not implement: " + ", ".join(unsupported))
        if descriptor.admission.max_running not in (None, config.max_running_requests):
            raise ValueError("config.max_running_requests differs from the descriptor's")
        if dummy != "none" and sem.dummy_ceiling is None \
                and descriptor.grid.sizes[-1] != config.max_running_requests:
            raise ValueError("dummy ceiling not established and the top grid size differs "
                             "from max_running: the trigger is ambiguous")
    else:
        release, dummy = descriptor.release_rule, descriptor.dummy_mode
        order = {"fifo": "allocation_fifo"}.get(descriptor.outer_eviction_policy)
        if order is None or descriptor.resume_allocates_first is not True:
            raise ValueError("descriptor rules are outside what the simulator implements")
    if release is None or dummy is None:
        raise ValueError("descriptor does not establish the release rule or dummy mode")
    numeric = descriptor.legacy_view() if v2 else descriptor
    return numeric, release, {"none": "off"}.get(dummy, dummy), "fifo"


def simulate(
    descriptor: SubstrateDescriptor | SubstrateDescriptorV2,
    sessions: list[Session],
    config: SimConfig,
) -> SimResult:
    """Run ``sessions`` against ``descriptor`` and return the step trace.

    With a v2 descriptor and ``semantics='descriptor'``, a descriptor whose
    prefill is ``mixed`` (chunked into decode steps) is simulated by the paged
    engine (``paged.simulate_paged``), which returns a ``PagedResult``; every
    other descriptor runs here. The choice reads a descriptor field, never a
    substrate name."""
    if (isinstance(descriptor, SubstrateDescriptorV2) and config.semantics == "descriptor"
            and descriptor.prefill.execution == "mixed"):
        from .paged import simulate_paged
        return simulate_paged(descriptor, sessions, config)
    if config.window_rule is not None:
        raise ValueError("window_rule is read by the paged engine only")
    context_cost = descriptor.context_cost if isinstance(descriptor, SubstrateDescriptorV2) else None
    if context_cost is not None:
        if config.decode_cost_fn is not None:
            raise ValueError("set either descriptor.context_cost or SimConfig.decode_cost_fn, not both")
        if context_cost.unit != "s":
            raise ValueError("this engine prices steps in seconds; context_cost.unit must be 's'")
    descriptor, release_rule, dummy_mode, policy_name = _descriptor_rules(descriptor, config)
    if descriptor.prefill_cost_model is None:
        raise ValueError(
            "descriptor has no prefill cost model; prefill is not free, it is "
            "unmeasured, so a simulation would silently understate the cost"
        )
    prefill_model = descriptor.prefill_cost_model
    if config.cache_granularity == "inner":
        pool = GranularPool(capacity=descriptor.inner_block_count,
                            block_tokens=descriptor.inner_block_tokens,
                            policy=policy_name)
    else:
        pool = OuterBlockPool(capacity=descriptor.outer_slot_count,
                              policy=policy_name,
                              immediate_release=release_rule == "immediate")
    reserved_dummy = dummy_mode == "reserved"
    pre_evict = dummy_mode == "pre_evict"

    def _padding_step(actual: int) -> None:
        # TASK63: the padding request exists only while the batch is partial.
        if pre_evict and 0 < actual < config.max_running_requests:
            pool.pre_evict()

    counter = itertools.count()
    pending: list[_Pending] = []
    if config.session_start_s is not None and len(config.session_start_s) != len(sessions):
        raise ValueError("session_start_s must give one time per session")
    if config.successor is not None and len(config.successor) != len(sessions):
        raise ValueError("successor must give one entry per session")
    followers = ({j for j in config.successor if j is not None}
                 if config.successor is not None else set())
    for idx, s in enumerate(sessions):
        if idx in followers:
            continue
        t0 = s.turns[0]
        start = config.session_start_s[idx] if config.session_start_s is not None else 0.0
        pending.append(_Pending(
            session=s.session_id, session_index=idx, turn=0,
            prompt_tokens=_prompt_tokens(s, 0),
            generation_tokens=t0.generation_tokens,
            gap_after_s=t0.gap_after_s, gap_start_s=start, arrival_s=start, ready_s=start,
            seq=next(counter),
        ))

    by_index = {i: s for i, s in enumerate(sessions)}
    waiting: list[_Pending] = []
    running: list[dict] = []
    steps: list[StepRecord] = []
    records: list[RequestRecord] = []
    t = 0.0

    rank = {s: i for i, s in enumerate(config.admission_priority)}

    def _sort_key(p: _Pending) -> tuple:
        if config.arrival_order == "session_index":
            return (round(p.arrival_s, 9),
                    rank.get(p.session_index, p.session_index), p.turn)
        return (p.arrival_s, p.seq)

    def _finish(r: dict, at: float) -> None:
        pool.release(r["session"])
        records.append(RequestRecord(
            session=r["session"], session_index=r["session_index"], turn=r["turn"],
            prompt_tokens=r["prompt_tokens"], generation_tokens=r["generation_tokens"],
            arrival_s=r["arrival_s"], admit_s=r["admit_s"], finish_s=at,
            cached_tokens=r["cached_tokens"], computed_tokens=r["computed_tokens"],
            prefill_s=r["prefill_s"], ready_s=r["ready_s"],
            evicted_sessions=r["evicted"],
        ))
        sess = by_index[r["session_index"]]
        nxt = r["turn"] + 1
        if nxt >= len(sess.turns) and config.successor is not None \
                and config.successor[r["session_index"]] is not None:
            j = config.successor[r["session_index"]]
            s2 = by_index[j]
            pending.append(_Pending(
                session=s2.session_id, session_index=j, turn=0,
                prompt_tokens=_prompt_tokens(s2, 0),
                generation_tokens=s2.turns[0].generation_tokens,
                gap_after_s=s2.turns[0].gap_after_s, gap_start_s=at,
                arrival_s=at + config.client_overhead_s,
                ready_s=at + config.client_overhead_s, seq=next(counter),
            ))
        if nxt < len(sess.turns):
            arrival = at + r["gap_after_s"] + config.client_overhead_s
            if config.fixed_arrivals is not None:
                key = (r["session_index"], nxt)
                if key not in config.fixed_arrivals:
                    raise RuntimeError(
                        f"fixed_arrivals has no entry for session "
                        f"{r['session_index']} turn {nxt}"
                    )
                arrival = config.fixed_arrivals[key]
            pending.append(_Pending(
                session=r["session"], session_index=r["session_index"], turn=nxt,
                prompt_tokens=_prompt_tokens(sess, nxt),
                generation_tokens=sess.turns[nxt].generation_tokens,
                gap_after_s=sess.turns[nxt].gap_after_s,
                gap_start_s=at,
                arrival_s=arrival,
                ready_s=arrival,
                seq=next(counter),
            ))

    policy = config.return_policy
    budget = config.return_budget_s
    clock = config.peer_clock

    def _context(now: float, me: _Pending) -> Context:
        """Both information channels, each supplied only if switched on.

        ``running_remaining_s`` is estimated at the current concurrency: the
        step cost changes as the batch drains, so this is what a policy could
        work out for itself, not a privileged exact answer.
        """
        peers = _peer_view(now, me).offsets_s if config.peer_clock is not None \
            or config.reveal_peers else None
        remaining = None
        if config.reveal_generation:
            step = descriptor.step_time_s(len(running)) if running else 0.0
            remaining = tuple(r["remaining"] * step for r in running)
        return Context(peer_offsets_s=peers, running_remaining_s=remaining,
                       prefill_s=prefill_model.prefill_s(me.prompt_tokens),
                       generation_tokens=me.generation_tokens)

    def _peer_view(now: float, me: _Pending) -> PeerView:
        """When the other sessions' tool gaps are predicted to finish.

        A running request has not started its gap yet, so its return time is
        not predictable from the gap alone and it is left out. What the policy
        sees is the cohort that is already counting down.
        """
        offsets = []
        for q in pending:
            if q is me or q.turn == 0:
                continue
            true_remaining = q.ready_s - now
            if clock is None:
                offsets.append(true_remaining)
            else:
                gap = q.ready_s - q.gap_start_s
                predicted = clock.perturb(gap)
                offsets.append(q.gap_start_s + predicted - now)
        return PeerView(offsets_s=tuple(offsets))

    def _release_ready(now: float) -> None:
        """Move returns whose hold has ended into the server's queue.

        Turn 0 is never held: a policy governs *returns*, and the opening turn
        of a session is not one. With no policy every ready return is released
        at once, which is the behaviour of every task before this one.
        """
        ready = [p for p in pending if p.ready_s <= now + 1e-12]
        if not ready:
            return
        if policy is None:
            release = ready
        else:
            in_flight = len(running) + len(waiting)
            held = len(ready)
            release = []
            for p in ready:
                waited = now - p.ready_s
                if p.turn == 0 or waited >= budget - 1e-12:
                    release.append(p)
                    continue
                st = ReturnState(now_s=now, in_flight=in_flight, held=held,
                                 waited_s=waited, budget_s=budget)
                if isinstance(policy, Informed):
                    if policy.release_with_context(st, _context(now, p)):
                        release.append(p)
                elif isinstance(policy, Lookahead):
                    if policy.release_with_view(st, _peer_view(now, p)):
                        release.append(p)
                elif policy.release(st):
                    release.append(p)
        for p in release:
            pending.remove(p)
            if policy is not None:
                # The hold ended now, so this is when the server sees it. With
                # no policy the scheduled time is left alone: it is the sort
                # key for simultaneous admissions, and rewriting it would
                # silently reorder runs that earlier tasks already published.
                p.arrival_s = now
            waiting.append(p)
        if release:
            waiting.sort(key=_sort_key)

    def _next_wakeup(now: float) -> float:
        """Earliest future time the release decision could change on its own."""
        candidates = [p.ready_s for p in pending if p.ready_s > now + 1e-12]
        if policy is not None:
            for p in pending:
                if p.turn == 0:
                    continue
                if p.ready_s <= now + 1e-12:
                    candidates.append(p.ready_s + budget)
                    st = ReturnState(now_s=now, in_flight=len(running) + len(waiting),
                                     held=1, waited_s=now - p.ready_s, budget_s=budget)
                    if isinstance(policy, Informed):
                        nxt = policy.next_check_with_context(st, _context(now, p))
                    elif isinstance(policy, Lookahead):
                        nxt = policy.next_check_with_view(st, _peer_view(now, p))
                    else:
                        nxt = policy.next_check_s(st)
                    if nxt is not None and nxt > now + 1e-12:
                        candidates.append(nxt)
        if not candidates:
            raise RuntimeError("no future event but work remains")
        return min(candidates)

    while pending or waiting or running:
        _release_ready(t)

        if not waiting and not running:
            t = _next_wakeup(t)
            continue

        if waiting and len(running) < config.max_running_requests:
            p = waiting[0]
            blocks = (pool.blocks_for(p.prompt_tokens)
                      if isinstance(pool, GranularPool)
                      else descriptor.outer_slots_for(p.prompt_tokens))
            if reserved_dummy:
                # The padding block is live exactly while the decode batch is
                # partial: not at an empty batch, not at the ceiling (TASK63).
                pool.reserved = int(0 < len(running) < config.max_running_requests)
            if not pool.can_admit(blocks):
                # No room: the scheduler leaves it waiting and decodes instead.
                # Releases that were deferred for this admission now land.
                pool.settle()
                if not running:
                    # No step can pass to make room, so the deferred releases
                    # are all there is. If they were not enough the workload
                    # genuinely does not fit and the run must fail loudly.
                    if not pool.can_admit(blocks):
                        raise RuntimeError(
                            "outer pool cannot admit and nothing is running; "
                            "the workload does not fit this substrate"
                        )
                    continue
                actual = len(running)
                _padding_step(actual)
                bucket = descriptor.bucket_for(actual)
                dur = _decode_s(descriptor, config, running, actual, context_cost)
                steps.append(StepRecord(kind="decode", start_s=t, duration_s=dur,
                                        running=actual, bucket=bucket))
                t += dur
                for r in running:
                    r["remaining"] -= 1
                for r in [r for r in running if r["remaining"] <= 0]:
                    running.remove(r)
                    _finish(r, t)
                continue
            waiting.pop(0)
            hit_prefix, evicted = pool.admit(
                session_key=p.session, blocks_needed=blocks,
                prompt_tokens=p.prompt_tokens,
            )
            cached = descriptor.hit_formula.hit_tokens(
                shared_prefix_tokens=hit_prefix, query_tokens=p.prompt_tokens,
            )
            computed = p.prompt_tokens - cached
            dur = prefill_model.prefill_s(computed)
            stalled = len(running) if config.prefill_exclusive else 0
            steps.append(StepRecord(
                kind="prefill", start_s=t, duration_s=dur, running=stalled,
                session=p.session, computed_tokens=computed,
            ))
            if config.prefill_exclusive:
                t += dur
            else:
                # Chunked prefill interleaves with decode instead of pre-empting
                # it. The prefill still costs the device its own time, but the
                # sessions that were decoding lose nothing, so the decode steps
                # that follow are not pushed back by it.
                pass
            r = {
                "session": p.session, "session_index": p.session_index, "turn": p.turn,
                "prompt_tokens": p.prompt_tokens,
                "generation_tokens": p.generation_tokens,
                "gap_after_s": p.gap_after_s, "arrival_s": p.arrival_s,
                "admit_s": t - dur, "cached_tokens": cached,
                "computed_tokens": computed, "prefill_s": dur,
                "ready_s": p.ready_s,
                # Prefill emits the first token, so only the rest are decode steps.
                "remaining": p.generation_tokens - 1,
                "evicted": tuple(e.victim_session for e in evicted),
            }
            if r["remaining"] <= 0:
                _finish(r, t)
            else:
                running.append(r)
            continue

        if running:
            actual = len(running)
            _padding_step(actual)
            bucket = descriptor.bucket_for(actual)
            dur = _decode_s(descriptor, config, running, actual, context_cost)
            steps.append(StepRecord(
                kind="decode", start_s=t, duration_s=dur, running=actual, bucket=bucket,
            ))
            t += dur
            for r in running:
                r["remaining"] -= 1
            done = [r for r in running if r["remaining"] <= 0]
            for r in done:
                running.remove(r)
                _finish(r, t)
            continue

        t = _next_wakeup(t)

    records.sort(key=lambda r: (r.session_index, r.turn))
    return SimResult(steps=steps, requests=records, wall_clock_s=t,
                     evictions=pool.evictions)
