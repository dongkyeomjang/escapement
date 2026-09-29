"""GPU step cost model for the multi-turn predictions (GTASK05 values only).

One A6000 (uuid 4485e769...), vLLM 0.22.0, Qwen3-4B bf16, server arguments of
GTASK05. Every number below is copied from
``results/gpu/stepcost/20260929T1607Z/{summary.json, window_explore.json}``
(summary SHA256 709f5941...). Nothing measured in a multi-turn run is used.

Step kinds (``[GSTEP]`` mode):

* decode-only, padded width in the capture grid -> FULL:
  ``F[b] + g * n`` (GTASK05 FULL fit, G1+G3, max |resid| 0.035 ms).
* decode-only, more requests than the largest capture size -> eager:
  the G2 eager medians for n = 9..16 (19.31-19.54 ms).
* mixed (a prefill chunk rides along), total tokens <= largest capture
  size -> PIECEWISE: decode baseline + an increment in [0, 1.5] ms
  (directive G-03 2.1: below the dispatch channel's resolution, propagated
  as an interval).
* mixed, total tokens > largest capture size -> eager: decode baseline +
  an increment in [lo(p), hi(p)] where ``lo`` is the preregistered lag-1
  increment clamped at 0 and ``hi`` the exploratory 3-step-window increment
  (GTASK05 finding 3/4: lag 1 under-attributes small eager steps, the window
  includes the ~4 ms dispatch delay). d = 4 values, linear in p between the
  measured prompt sizes, through (0, 0) below p = 32.

``bound`` selects which end of both intervals a caller prices with: ``"lo"``
or ``"hi"``. Predictions are registered at both ends.
"""

from __future__ import annotations

from bisect import bisect_left

# GTASK05 FULL fit t = F[b] + g * n (ms), b = padded capture size <= 16.
F_MS = {1: 13.366891568454307, 2: 13.203783136905722, 3: 13.168174705461539,
        4: 13.189185751128225, 5: 13.181207842360454, 6: 13.235599410916409,
        7: 13.219990979421716, 8: 13.294612665659505, 9: 13.247774116368662,
        10: 13.236915684861987, 11: 13.357057253394052, 12: 13.319698821755331,
        13: 13.578090390307826, 14: 13.577731958803067, 15: 13.625873527289544,
        16: 13.717213549315915}
G_MS = 0.04060843151682825
# GTASK05 G2 eager decode-only medians (ms), n = 9..16.
EAGER_DECODE_MS = {9: 19.3385, 10: 19.311, 11: 19.483, 12: 19.5295, 13: 19.448,
                   14: 19.4765, 15: 19.508, 16: 19.5405}
PIECEWISE_INC_MS = (0.0, 1.5)
# eager mixed increments, d = 4, grid G3 (ms): p -> (lag-1 clamped, window-3)
_EAGER_P = (32, 64, 128, 256, 512, 1024, 2048)
_EAGER_LO = (0.0, 0.0, 1.973, 12.734, 31.784, 75.750, 139.024)
_EAGER_HI = (0.821, 1.728, 5.647, 16.726, 35.561, 79.168, 145.642)

MAX_MEASURED_DECODE = 16


def padded(grid: tuple[int, ...], tokens: int) -> int | None:
    """Smallest capture size >= tokens, ``None`` = eager."""
    i = bisect_left(grid, tokens)
    return grid[i] if i < len(grid) else None


def decode_ms(n: int, grid: tuple[int, ...]) -> float:
    if n < 1 or n > MAX_MEASURED_DECODE:
        raise ValueError(f"decode width {n} outside the measured range 1..16")
    b = padded(grid, n)
    if b is None:
        if n not in EAGER_DECODE_MS:
            raise ValueError(f"eager decode at n={n} was not measured")
        return EAGER_DECODE_MS[n]
    if b > MAX_MEASURED_DECODE:
        raise ValueError(f"FULL decode padded to {b} was not measured")
    return F_MS[b] + G_MS * n


def _interp(p: int, ys: tuple[float, ...]) -> float:
    if p <= _EAGER_P[0]:
        return ys[0] * p / _EAGER_P[0]
    if p >= _EAGER_P[-1]:
        return ys[-1] * p / _EAGER_P[-1]
    i = bisect_left(_EAGER_P, p)
    x0, x1 = _EAGER_P[i - 1], _EAGER_P[i]
    return ys[i - 1] + (p - x0) / (x1 - x0) * (ys[i] - ys[i - 1])


def prefill_increment_ms(p: int, total_tokens: int, grid: tuple[int, ...], bound: str) -> float:
    """Extra time a step pays for carrying ``p`` prefill tokens."""
    if p <= 0:
        return 0.0
    k = 0 if bound == "lo" else 1
    if padded(grid, total_tokens) is not None:
        return PIECEWISE_INC_MS[k]
    return _interp(p, _EAGER_LO if k == 0 else _EAGER_HI)


def step_ms(*, decodes: int, prefill_tokens: int, grid: tuple[int, ...], bound: str) -> float:
    """Cost of one engine step with ``decodes`` one-token requests and
    ``prefill_tokens`` prompt tokens scheduled (all prefill requests summed).

    A step with prefill but no decoder is priced on the width-1 baseline: its
    cost alone was not measurable (GTASK05: the engine idles between them).
    """
    if bound not in ("lo", "hi"):
        raise ValueError("bound is 'lo' or 'hi'")
    if prefill_tokens == 0:
        return decode_ms(decodes, grid)
    base = decode_ms(max(decodes, 1), grid)
    return base + prefill_increment_ms(prefill_tokens, decodes + prefill_tokens, grid, bound)


def mode(decodes: int, prefill_tokens: int, grid: tuple[int, ...]) -> str:
    """The ``[GSTEP]`` mode this step is expected to run in."""
    if padded(grid, decodes + prefill_tokens) is None:
        return "NONE"
    return "FULL" if prefill_tokens == 0 else "PIECEWISE"
