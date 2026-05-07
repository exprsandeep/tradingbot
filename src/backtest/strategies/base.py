from __future__ import annotations

from typing import Any
import pandas as pd

class BaseStrategy:
    def __init__(self, config: dict[str, Any]):
        self.config = config

    def should_enter_long(self, row: pd.Series, prev: pd.Series) -> bool:
        """Return True if a long entry signal is present."""
        raise NotImplementedError

    def should_enter_short(self, row: pd.Series, prev: pd.Series) -> bool:
        """Return True if a short entry signal is present."""
        raise NotImplementedError
