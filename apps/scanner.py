from __future__ import annotations

import sys
from datetime import datetime, time, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

# Ensure project root is in sys.path so we can import src
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.strategies import get_strategy


def load_feature_up_to(features_root: Path, symbol_prefix: str, timeframe: str, max_ts: pd.Timestamp) -> pd.DataFrame:
    matches = sorted((features_root / timeframe).glob(f"{symbol_prefix}*_{timeframe}.parquet"))
    if not matches:
        return pd.DataFrame()
    df = pd.read_parquet(matches[0]).copy()
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_convert("UTC") if idx.tz is not None else idx.tz_localize("UTC")
    df.index = idx
    df = df.sort_index()
    # Return only rows up to max_ts
    return df.loc[:max_ts]


def build_synthetic_row(df_3m: pd.DataFrame, df_15m: pd.DataFrame, df_1h: pd.DataFrame) -> tuple[pd.Series | None, pd.Series | None]:
    if len(df_3m) < 2 or df_15m.empty or df_1h.empty:
        return None, None

    # Get the latest 3m bar and the one before it
    curr_3m = df_3m.iloc[-1]
    prev_3m = df_3m.iloc[-2]
    curr_ts = curr_3m.name

    # Get the latest 15m and 1h bars that completed AT OR BEFORE curr_ts
    df_15m_valid = df_15m.loc[:curr_ts]
    df_1h_valid = df_1h.loc[:curr_ts]

    if df_15m_valid.empty or df_1h_valid.empty:
        return None, None

    curr_15m = df_15m_valid.iloc[-1]
    curr_1h = df_1h_valid.iloc[-1]

    # Assemble the row dictionary expected by the strategies
    row_data = {
        "ts": curr_ts,
        "close": curr_3m["close"],
        "open": curr_3m["open"],
        "high": curr_3m["high"],
        "low": curr_3m["low"],
        "volume": curr_3m["volume"],
        "vol_sma_20": curr_3m["vol_sma_20"],
        "body_pct_of_range": curr_3m.get("body_pct_of_range", 0.0),
        "s15_pos20": curr_15m["position_in_20_range"],
        "h1_close": curr_1h["close"],
        "h1_close_sma_50": curr_1h["close_sma_50"],
        "h1_momentum_20": curr_1h["momentum_20"],
    }
    
    return pd.Series(row_data), prev_3m


def highlight_signals(val: str) -> str:
    if val == "LONG":
        return "background-color: #004d00; color: white; font-weight: bold;"
    elif val == "SHORT":
        return "background-color: #4d0000; color: white; font-weight: bold;"
    return ""


def main() -> None:
    st.set_page_config(page_title="Market Scanner", layout="wide")
    st.title("Market Scanner")
    st.caption("Cross-market monitor for strategy signals.")

    features_root = Path("data/features")
    if not features_root.exists():
        st.error("Features directory not found. Please build features first.")
        return

    # Discover available symbols
    symbol_options = sorted([p.name for p in (features_root / "3min").glob("*.parquet")]) if (features_root / "3min").exists() else []
    symbol_prefixes = sorted({"_".join(name.split("_")[:3]) for name in symbol_options})

    if not symbol_prefixes:
        st.warning("No symbols found in data/features/3min.")
        return

    # Sidebar controls
    st.sidebar.header("Scanner Settings")
    date_val = st.sidebar.date_input("Date (UTC)", value=datetime(2025, 1, 15).date())
    time_val = st.sidebar.time_input("Time (UTC)", value=time(14, 30))
    scan_ts = pd.Timestamp(datetime.combine(date_val, time_val)).tz_localize("UTC")

    st.sidebar.markdown(f"**Scanning as of:** `{scan_ts}`")

    # Load Strategies
    try:
        cfg_v1 = yaml.safe_load(open(PROJECT_ROOT / "config" / "strategy_v1.yaml"))
        strat_pullback = get_strategy(cfg_v1)
    except Exception as e:
        st.error(f"Failed to load V1 Pullback Strategy: {e}")
        return

    try:
        cfg_v2 = yaml.safe_load(open(PROJECT_ROOT / "config" / "strategy_v2_mean_reversion.yaml"))
        strat_mean_rev = get_strategy(cfg_v2)
    except Exception as e:
        st.error(f"Failed to load V2 Mean Reversion Strategy: {e}")
        return

    st.write(f"Monitoring **{len(symbol_prefixes)}** symbols: {', '.join(symbol_prefixes)}")

    # Build Scan Results
    results = []
    for sym in symbol_prefixes:
        df_3m = load_feature_up_to(features_root, sym, "3min", scan_ts)
        df_15m = load_feature_up_to(features_root, sym, "15min", scan_ts)
        df_1h = load_feature_up_to(features_root, sym, "1h", scan_ts)

        row, prev = build_synthetic_row(df_3m, df_15m, df_1h)
        if row is None or prev is None:
            results.append({
                "Symbol": sym,
                "Status": "Not enough data",
                "Price": None,
                "1h Trend": None,
                "15m Pos": None,
                "Pullback Signal": "NONE",
                "MeanRev Signal": "NONE",
            })
            continue

        # Evaluate Pullback Strategy
        pb_signal = "NONE"
        if strat_pullback.should_enter_long(row, prev):
            pb_signal = "LONG"
        elif strat_pullback.should_enter_short(row, prev):
            pb_signal = "SHORT"

        # Evaluate Mean Reversion Strategy
        mr_signal = "NONE"
        if strat_mean_rev.should_enter_long(row, prev):
            mr_signal = "LONG"
        elif strat_mean_rev.should_enter_short(row, prev):
            mr_signal = "SHORT"

        # Determine Trend context for display
        trend = "NEUTRAL"
        if row["h1_close"] > row["h1_close_sma_50"] and row["h1_momentum_20"] > 0:
            trend = "BULLISH"
        elif row["h1_close"] < row["h1_close_sma_50"] and row["h1_momentum_20"] < 0:
            trend = "BEARISH"

        results.append({
            "Symbol": sym,
            "Status": "Active",
            "Price": f"{row['close']:.2f}",
            "1h Trend": trend,
            "15m Pos": f"{row['s15_pos20']:.2f}",
            "Pullback Signal": pb_signal,
            "MeanRev Signal": mr_signal,
        })

    df_res = pd.DataFrame(results)

    # Display Styled DataFrame
    st.dataframe(
        df_res.style.applymap(highlight_signals, subset=["Pullback Signal", "MeanRev Signal"]),
        use_container_width=True,
        hide_index=True
    )


if __name__ == "__main__":
    main()
