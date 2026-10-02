"""Step classes shared by G-05 tasks B and D (dispatch / price ratio by mode)."""
EAGER_P_BINS = (128, 256, 512, 1024)


def step_class(mode: str, d: int, p: int) -> str:
    if p == 0:
        return "DEC_FULL" if mode == "FULL" else "DEC_EAGER"
    if mode == "PIECEWISE":
        return "MIX_PIECEWISE"
    for b in EAGER_P_BINS:
        if p <= b:
            return f"MIX_EAGER_p<={b}"
    return "MIX_EAGER_p>1024"
