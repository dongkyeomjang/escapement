"""Analytic model v0 of a bucketed, slot-pooled serving substrate.

Four parts, each computed from ``SubstrateDescriptor`` fields and workload
parameters only:

* ``survival``     -- whether a cached prefix outlasts a tool gap
* ``occupancy``    -- the running-count distribution of a steady closed load
* ``grid``         -- the best compiled bucket grid for a running-count histogram
* ``interference`` -- what exclusive prefill costs the sessions it stops

The specification, assumptions and what each part does not predict are in
``docs/research/MODEL_V0.md``. Nothing here names an accelerator.
"""

from . import grid, interference, occupancy, protocol, survival

__all__ = ["grid", "interference", "occupancy", "protocol", "survival"]
