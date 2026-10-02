"""GPU multi-turn configurations, read from the blind selection (GTASK08).

``CARD_UUID`` is the one card every GPU measurement runs on after GTASK05
(directive G-03 section 1). Configurations are server arguments, not
artifacts: BASE and POOL are the same for every N; POOL+GRID has a per-N
capture grid.
"""

from __future__ import annotations

import json
from pathlib import Path

from gpu_mt_sim import GpuConfig

CARD_UUID = "GPU-4485e769-430a-430d-3383-b9c4ce92a175"
SELECTION = Path(__file__).resolve().parent / "selection" / "selection.json"
# G-07 C blind cells: POOL+GRID grids for N outside the GTASK08 selection,
# chosen by the same rule 6 on the blind plans (predict_blind.py)
BLIND_GRIDS = Path(__file__).resolve().parent / "selection" / "blind_grids.json"


def config_by_name(name: str, n: int) -> GpuConfig:
    sel = json.loads(SELECTION.read_text())
    base_grid = tuple(sel["base_grid"])
    if name == "BASE":
        return GpuConfig("BASE", sel["base_pool"], sel["max_num_seqs"], base_grid)
    if name == "POOL":
        return GpuConfig("POOL", sel["pool_pool"], sel["max_num_seqs"], base_grid)
    if name == "POOL+GRID":
        g = sel["per_n_grid"].get(str(n))
        if g is None and BLIND_GRIDS.exists():
            g = json.loads(BLIND_GRIDS.read_text())["per_n_grid"].get(str(n))
        if g is None:
            raise SystemExit(f"no POOL+GRID grid selected for N={n}")
        return GpuConfig("POOL+GRID", sel["pool_pool"], sel["max_num_seqs"], tuple(g["grid"]))
    raise SystemExit(f"unknown configuration {name!r}")
