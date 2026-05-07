from __future__ import annotations

import pandas as pd
from .base import BaseStrategy

class TopDownZigZagStrategy(BaseStrategy):
    def _vol_ok(self, row: pd.Series) -> bool:
        filter_cfg = self.config.get("entry_logic", {}).get("min_volume_filter", {})
        if not filter_cfg.get("enabled", False):
            return True
        return bool(row["volume"] > row["vol_sma_20"])

    def should_enter_long(self, row: pd.Series, prev: pd.Series) -> bool:
        # Top-down trend filter (1 = Uptrend)
        if row.get("h1_zigzag_trend", 0) != 1:
            return False
            
        # 15m pullback filter (only buy dips)
        if row.get("s15_pos20", 1.0) > 0.40:
            return False
            
        # Entry trigger: 3m closes higher than previous high
        trigger = row["close"] > prev["high"]
        
        return trigger and self._vol_ok(row)

    def should_enter_short(self, row: pd.Series, prev: pd.Series) -> bool:
        # Top-down trend filter (-1 = Downtrend)
        if row.get("h1_zigzag_trend", 0) != -1:
            return False
            
        # 15m pullback filter (only sell rips)
        if row.get("s15_pos20", 0.0) < 0.60:
            return False
            
        # Entry trigger: 3m closes lower than previous low
        trigger = row["close"] < prev["low"]
        
        return trigger and self._vol_ok(row)
