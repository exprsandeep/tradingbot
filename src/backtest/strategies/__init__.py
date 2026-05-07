from __future__ import annotations

from typing import Any
from .base import BaseStrategy
from .structure_pullback import StructurePullbackStrategy
from .mean_reversion import MeanReversionStrategy
from .top_down_zigzag import TopDownZigZagStrategy

def get_strategy(config: dict[str, Any]) -> BaseStrategy:
    name = config.get("name", "")
    if name == "mnq_structure_pullback_v1":
        return StructurePullbackStrategy(config)
    elif name == "mnq_mean_reversion_v1":
        return MeanReversionStrategy(config)
    elif name == "mnq_top_down_zigzag_v1":
        return TopDownZigZagStrategy(config)
    else:
        raise ValueError(f"Unknown strategy: {name}")
