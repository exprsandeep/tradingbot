from __future__ import annotations

import pandas as pd
from .base import BaseStrategy

class StructurePullbackStrategy(BaseStrategy):
    def _vol_ok(self, row: pd.Series) -> bool:
        return bool(
            not self.config["entry_logic"]["min_volume_filter"]["enabled"]
            or row["volume"] > row["vol_sma_20"]
        )

    def should_enter_long(self, row: pd.Series, prev: pd.Series) -> bool:
        trend_long = bool(row["h1_close"] > row["h1_close_sma_50"] and row["h1_momentum_20"] > 0)
        pullback_long = bool(row["s15_pos20"] <= 0.40)
        return trend_long and pullback_long and self._vol_ok(row) and row["close"] > prev["high"]

    def should_enter_short(self, row: pd.Series, prev: pd.Series) -> bool:
        trend_short = bool(row["h1_close"] < row["h1_close_sma_50"] and row["h1_momentum_20"] < 0)
        pullback_short = bool(row["s15_pos20"] >= 0.60)
        return trend_short and pullback_short and self._vol_ok(row) and row["close"] < prev["low"]
