"""Reference semantics of a FIFO-by-allocation slot pool (model v1, B1).

The rule
--------
An eviction removes the oldest *inactive* entry in the pool at that moment.
A target entry T is therefore evicted at an eviction instant inside its window
if and only if, at that instant, T is inactive and every entry older than T
still in the pool is active.

This module replays that rule over an ordered stream of three kinds of event
and nothing else:

* ``("alloc", key, session)`` -- an admission. When no slot is free it evicts
  first (admission path), then takes its own slot, *then* looks up the
  session's earlier entry when the substrate allocates before it looks up.
* ``("free", key)`` -- a request finished. Its entry becomes inactive at once
  (``release="immediate"``) or only after the next admission has chosen its
  victim (``release="deferred"``).
* ``("decode", n)`` -- a decode step with ``n`` running requests. Under
  ``dummy="pre_evict"`` a padding request is issued when ``0 < n < ceiling``;
  if no slot is free it evicts the oldest inactive entry, and the slot it
  points at is taken by the next admission without a further eviction.

TASK72 ran this replay (``release="immediate"``, ``dummy="pre_evict"``,
allocate-then-look-up) over server logs of seven concurrent runs and matched
all 1,298 re-arrivals, and over 36 sequential trials and matched all 140
evictions. The other settings exist to be compared against, not because they
describe the measured substrate.

The replay does not read outcome lines: which entry was evicted and whether a
lookup hit are what it predicts. Nothing here names an accelerator; capacity,
ceiling and the three semantic choices come from a descriptor or the caller.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

RELEASE_RULES = ("immediate", "deferred")
DUMMY_MODES = ("none", "pre_evict", "reserved")


@dataclass
class Lookup:
    pos: int
    """Index of the admission in the event stream."""
    predicted_hit: bool
    """The session's earlier entry is still in the pool at lookup."""
    prior_key: str | None
    pinned_older_at_lookup: int | None
    """Active entries older than the session's earliest resident entry, at the
    lookup instant. Only a by-product; the rule does not use it."""
    state_at_alloc: tuple[int, int, int] = (0, 0, 0)
    """(free slots, active older entries, inactive older entries) seen by *this*
    admission's own entry right after it was placed. Used as the initial state
    of the v1 approximation when this entry is later a target."""


@dataclass
class Eviction:
    key: str
    pos: int
    path: str
    """``admission`` or ``dummy``."""


@dataclass
class FifoReplay:
    capacity: int
    ceiling: int
    release: str = "immediate"
    dummy: str = "pre_evict"
    allocate_before_lookup: bool = True
    entries: list[dict] = field(default_factory=list)
    """Resident entries in allocation order."""
    evictions: list[Eviction] = field(default_factory=list)
    lookups: dict[str, Lookup] = field(default_factory=dict)
    undefined: list[int] = field(default_factory=list)
    """Positions where an eviction was required but no entry was inactive."""
    _pending: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.capacity <= 0 or self.ceiling <= 0:
            raise ValueError("capacity and ceiling must be positive")
        if self.release not in RELEASE_RULES:
            raise ValueError(f"unknown release rule {self.release!r}")
        if self.dummy not in DUMMY_MODES:
            raise ValueError(f"unknown dummy mode {self.dummy!r}")

    @classmethod
    def for_descriptor(cls, descriptor, *, capacity: int | None = None,
                       ceiling: int | None = None) -> "FifoReplay":
        """Build from a descriptor's measured semantics; refuses unmeasured ones.

        Accepts a v1 descriptor or a v2 one (``semantics`` + the reuse layer)."""
        if hasattr(descriptor, "semantics"):
            if descriptor.eviction_order != "allocation_fifo":
                raise ValueError("FifoReplay is the allocation-FIFO rule; the descriptor "
                                 f"says {descriptor.eviction_order!r}")
            sem = descriptor.semantics
            rules = {"release_rule": sem.evictable_when, "dummy_mode": sem.dummy_mode,
                     "resume_allocates_first": sem.resume_allocates_first}
            pool = descriptor.reuse_pool.capacity_units
        else:
            rules = {n: getattr(descriptor, n)
                     for n in ("release_rule", "dummy_mode", "resume_allocates_first")}
            pool = descriptor.outer_slot_count
        for name, value in rules.items():
            if value is None:
                raise ValueError(f"descriptor has no measured {name}")
        cap = capacity if capacity is not None else pool
        return cls(capacity=cap, ceiling=ceiling if ceiling is not None else cap,
                   release=rules["release_rule"], dummy=rules["dummy_mode"],
                   allocate_before_lookup=rules["resume_allocates_first"])

    # -- helpers ----------------------------------------------------------------

    def _active_count(self) -> int:
        return sum(1 for e in self.entries if e["active"])

    def _evict_oldest_inactive(self, pos: int, path: str) -> bool:
        for i, e in enumerate(self.entries):
            if not e["active"]:
                self.evictions.append(Eviction(e["key"], pos, path))
                del self.entries[i]
                return True
        self.undefined.append(pos)
        return False

    def _lookup(self, session) -> list[dict]:
        return [x for x in self.entries if x["session"] == session]

    # -- events -------------------------------------------------------------------

    def alloc(self, pos: int, key: str, session) -> None:
        need = 1
        if self.dummy == "reserved":
            need += int(0 < self._active_count() < self.ceiling)
        prior_before = self._lookup(session) if not self.allocate_before_lookup else None
        while self.capacity - len(self.entries) < need:
            if not self._evict_oldest_inactive(pos, "admission"):
                break
        if self.release == "deferred":
            for k in self._pending:
                for x in self.entries:
                    if x["key"] == k:
                        x["active"] = False
            self._pending.clear()
        prior = self._lookup(session) if self.allocate_before_lookup else prior_before
        pinned = None
        if prior:
            first = self.entries.index(prior[0])
            pinned = sum(1 for x in self.entries[:first] if x["active"])
        active_older = self._active_count()
        inactive_older = len(self.entries) - active_older
        self.entries.append({"key": key, "session": session, "active": True})
        free = self.capacity - len(self.entries)
        self.lookups[key] = Lookup(pos=pos, predicted_hit=bool(prior),
                                   prior_key=prior[-1]["key"] if prior else None,
                                   pinned_older_at_lookup=pinned,
                                   state_at_alloc=(free, active_older, inactive_older))

    def free(self, pos: int, key: str) -> None:
        if self.release == "immediate":
            for x in self.entries:
                if x["key"] == key:
                    x["active"] = False
        else:
            self._pending.append(key)

    def decode(self, pos: int, n: int) -> None:
        if self.dummy != "pre_evict":
            return
        if 0 < n < self.ceiling and len(self.entries) >= self.capacity:
            if any(not x["active"] for x in self.entries):
                self._evict_oldest_inactive(pos, "dummy")

    def run(self, events: Iterable[tuple], *,
            session_of: Callable[[str], object] | None = None) -> "FifoReplay":
        """Replay ``("alloc", key[, session])``, ``("free", key)``,
        ``("decode", n)``. Other event kinds are ignored, so a parsed log can be
        passed in whole; ``session_of`` maps a key to its session when the alloc
        events do not carry one."""
        for pos, e in enumerate(events):
            kind = e[0]
            if kind == "alloc":
                if session_of is not None:
                    sess = session_of(e[1])
                else:
                    sess = e[2] if len(e) > 2 else e[1]
                self.alloc(pos, e[1], sess)
            elif kind == "free":
                self.free(pos, e[1])
            elif kind == "decode":
                self.decode(pos, e[1])
        return self
