from __future__ import annotations

import pandas as pd
from .base import BaseStrategy

class MeanReversionStrategy(BaseStrategy):
    def _vol_ok(self, row: pd.Series) -> bool:
        filter_cfg = self.config.get("entry_logic", {}).get("min_volume_filter", {})
        if not filter_cfg.get("enabled", False):
            return True
        return bool(row["volume"] > row["vol_sma_20"])

    def should_enter_long(self, row: pd.Series, prev: pd.Series) -> bool:
        is_oversold = bool(row["intermediate_pos20"] <= 0.10)
        h1_mom_exhausted = bool(row["macro_momentum_20"] < -0.002)
        
        reversal_bar = bool(row["close"] > row["open"] and row["body_pct_of_range"] > 0.6)
        
        return is_oversold and h1_mom_exhausted and reversal_bar and self._vol_ok(row)

    def should_enter_short(self, row: pd.Series, prev: pd.Series) -> bool:
        is_overbought = bool(row["intermediate_pos20"] >= 0.90)
        h1_mom_exhausted = bool(row["macro_momentum_20"] > 0.002)
        
        reversal_bar = bool(row["close"] < row["open"] and row["body_pct_of_range"] < -0.6)
        
        return is_overbought and h1_mom_exhausted and reversal_bar and self._vol_ok(row)
