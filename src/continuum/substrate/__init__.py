"""Accelerator-neutral description of an inference substrate."""

from .descriptor import (
    HitFormula,
    Layer,
    PrefillCostModel,
    Provenance,
    StepCostModel,
    SubstrateDescriptor,
)
from .v2 import (
    NA,
    Admission,
    Grid,
    Pipeline,
    PoolLayer,
    PrefillSpec,
    Semantics,
    SubstrateDescriptorV2,
)

__all__ = [
    "HitFormula",
    "Layer",
    "PrefillCostModel",
    "Provenance",
    "StepCostModel",
    "SubstrateDescriptor",
    "NA",
    "Admission",
    "Grid",
    "Pipeline",
    "PoolLayer",
    "PrefillSpec",
    "Semantics",
    "SubstrateDescriptorV2",
]
