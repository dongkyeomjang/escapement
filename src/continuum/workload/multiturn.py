"""Steady-state multi-turn workload: renewal slots, staggered starts, windows.

A run holds ``N`` *slots*. Each slot runs sessions back to back: when a session
has sent all of its turns and the last one has finished, the next session in
that slot starts at once with a fresh opening prompt. The number of active
sessions therefore stays at ``N`` for as long as the run issues work, which is
what the steady-state models (B2, v1) assume and what the two-request,
all-start-together workload of the manuscript never provided (TASK72 R4/R5).

Two things keep the slots from moving in lock step:

* slot ``i`` opens at ``i * stagger_s``;
* the first session of each slot has a random number of turns in ``1..K``, so
  the first generation ends at different times and later generations inherit
  the spread.

The plan is generated in full before the run -- every session of every slot,
with its token counts, tool gaps and text seeds -- so the runner only pops
the next session from a list and a replicate is reproducible from
``(base_seed, plan_id)``.

``WindowRule`` is the single definition of the warm-up / evaluation / drain
boundaries. The runner applies it online to decide when to stop issuing, and
analysis applies the same function to the recorded completions to check it.

Nothing here names an accelerator.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
import hashlib
import json
import random

from .agentic import Distribution, Session, Turn, derive_block_seed


@dataclass(frozen=True)
class SlotPlan:
    slot: int
    start_s: float
    sessions: tuple[Session, ...]


@dataclass(frozen=True)
class MultiTurnPlan:
    plan_id: str
    base_seed: int
    n_slots: int
    turns: int
    stagger_s: float
    slots: tuple[SlotPlan, ...]
    spec: dict

    def to_json(self) -> dict:
        return {
            "plan_id": self.plan_id, "base_seed": self.base_seed,
            "n_slots": self.n_slots, "turns": self.turns, "stagger_s": self.stagger_s,
            "spec": self.spec,
            "slots": [{"slot": s.slot, "start_s": s.start_s,
                       "sessions": [{"session_id": x.session_id,
                                     "turns": [asdict(t) for t in x.turns]}
                                    for x in s.sessions]}
                      for s in self.slots],
        }

    def sha256(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_json(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    @classmethod
    def from_json(cls, d: dict) -> "MultiTurnPlan":
        slots = tuple(
            SlotPlan(slot=s["slot"], start_s=s["start_s"], sessions=tuple(
                Session(session_id=x["session_id"],
                        turns=tuple(Turn(**t) for t in x["turns"]))
                for x in s["sessions"]))
            for s in d["slots"])
        return cls(plan_id=d["plan_id"], base_seed=d["base_seed"], n_slots=d["n_slots"],
                   turns=d["turns"], stagger_s=d["stagger_s"], slots=slots, spec=d["spec"])


def generate_plan(*, n_slots: int, turns: int, sessions_per_slot: int,
                  first_segment: Distribution, later_segment: Distribution,
                  generation: Distribution, gap_sampler: Callable[[random.Random], float],
                  stagger_s: float, base_seed: int, plan_id: str,
                  spec: dict | None = None) -> MultiTurnPlan:
    """Every session of every slot, drawn from per-session generators.

    The first session of slot ``i`` has ``1 + rng.randrange(turns)`` turns;
    every later one has ``turns``. A session's final turn has no gap after it:
    the next session starts as soon as it finishes.
    """
    if n_slots <= 0 or turns <= 0 or sessions_per_slot <= 0:
        raise ValueError("n_slots, turns and sessions_per_slot must be positive")
    if stagger_s < 0:
        raise ValueError("stagger_s must be non-negative")
    slots = []
    for i in range(n_slots):
        sessions = []
        for g in range(sessions_per_slot):
            sid = f"{plan_id}/slot{i}/g{g}"
            rng = random.Random(derive_block_seed(base_seed, sid))
            k_turns = (1 + rng.randrange(turns)) if g == 0 else turns
            ts = []
            for k in range(k_turns):
                seg = (first_segment if k == 0 else later_segment).draw(rng)
                gen = generation.draw(rng)
                gap = 0.0 if k == k_turns - 1 else float(gap_sampler(rng))
                ts.append(Turn(index=k, new_segment_tokens=seg, generation_tokens=gen,
                               gap_after_s=gap,
                               text_seed=derive_block_seed(base_seed, f"{sid}/t{k}")))
            sessions.append(Session(session_id=sid, turns=tuple(ts)))
        slots.append(SlotPlan(slot=i, start_s=i * stagger_s, sessions=tuple(sessions)))
    return MultiTurnPlan(plan_id=plan_id, base_seed=base_seed, n_slots=n_slots, turns=turns,
                         stagger_s=stagger_s, slots=tuple(slots), spec=spec or {})


def max_context_tokens(plan: MultiTurnPlan) -> int:
    """Largest prompt + generation any request of the plan can reach."""
    worst = 0
    for s in plan.slots:
        for x in s.sessions:
            ctx = 0
            for t in x.turns:
                ctx += t.new_segment_tokens
                worst = max(worst, ctx + t.generation_tokens)
                ctx += t.generation_tokens
    return worst


@dataclass(frozen=True)
class WindowRule:
    """Warm-up ends at ``max(warmup_cycles * cycle_s, first time every slot
    has completed at least min_turns turns)``; evaluation lasts ``eval_s``;
    after that nothing new is issued (drain) and nothing is counted."""

    cycle_s: float
    eval_s: float = 120.0
    warmup_cycles: float = 3.0
    min_turns: int = 2

    def warmup_end(self, completions: Iterable[tuple[int, float]], n_slots: int) -> float | None:
        """``completions``: ``(slot, finish_time_s)`` in any order. ``None``
        while the condition has not been met."""
        per_slot: dict[int, list[float]] = {}
        for slot, t in completions:
            per_slot.setdefault(slot, []).append(t)
        if len(per_slot) < n_slots:
            return None
        nth = []
        for slot in range(n_slots):
            ts = sorted(per_slot.get(slot, []))
            if len(ts) < self.min_turns:
                return None
            nth.append(ts[self.min_turns - 1])
        return max(self.warmup_cycles * self.cycle_s, max(nth))

    def classify(self, t: float, warmup_end: float) -> str:
        if t < warmup_end:
            return "warmup"
        if t < warmup_end + self.eval_s:
            return "eval"
        return "drain"


def to_sim_inputs(plan: MultiTurnPlan) -> tuple[list[Session], tuple[float, ...],
                                                 tuple[int | None, ...], tuple[int, ...]]:
    """Flatten a plan for the simulator's renewal option.

    Returns ``(sessions, session_start_s, successor, slot_of)``: every session
    of every slot as one list, the first session of each slot starting at the
    slot's offset, each later one chained to its predecessor.
    """
    sessions: list[Session] = []
    start: list[float] = []
    succ: list[int | None] = []
    slot_of: list[int] = []
    for s in plan.slots:
        base = len(sessions)
        for g, x in enumerate(s.sessions):
            sessions.append(x)
            start.append(s.start_s if g == 0 else 0.0)
            succ.append(base + g + 1 if g + 1 < len(s.sessions) else None)
            slot_of.append(s.slot)
    return sessions, tuple(start), tuple(succ), tuple(slot_of)
