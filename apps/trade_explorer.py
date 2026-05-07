from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


def load_feature(features_root: Path, symbol_prefix: str, timeframe: str) -> pd.DataFrame:
    matches = sorted((features_root / timeframe).glob(f"{symbol_prefix}*_{timeframe}.parquet"))
    if not matches:
        raise FileNotFoundError(f"No feature dataset for {symbol_prefix} @ {timeframe}")
    df = pd.read_parquet(matches[0]).copy()
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_convert("UTC") if idx.tz is not None else idx.tz_localize("UTC")
    df.index = idx
    return df.sort_index()


def build_chart(df_macro: pd.DataFrame, df_intermediate: pd.DataFrame, df_entry: pd.DataFrame, entry_ts: pd.Timestamp | None, exit_ts: pd.Timestamp | None, zigzag_points: pd.Series | None = None) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.30, 0.30, 0.40],
        subplot_titles=("Macro Structure", "Intermediate Structure", "Entry Execution"),
    )

    fig.add_trace(
        go.Candlestick(x=df_macro.index, open=df_macro["open"], high=df_macro["high"], low=df_macro["low"], close=df_macro["close"], name="Macro"),
        row=1,
        col=1,
    )
    if "close_sma_50" in df_macro.columns:
        fig.add_trace(
            go.Scatter(x=df_macro.index, y=df_macro["close_sma_50"], mode="lines", name="Macro SMA50", line=dict(width=1.5)),
            row=1,
            col=1,
        )
    if zigzag_points is not None and not zigzag_points.empty:
        fig.add_trace(
            go.Scatter(x=zigzag_points.index, y=zigzag_points.values, mode="lines+markers", name="Macro ZigZag", line=dict(color="magenta", width=2), marker=dict(size=6, color="magenta")),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Candlestick(x=df_intermediate.index, open=df_intermediate["open"], high=df_intermediate["high"], low=df_intermediate["low"], close=df_intermediate["close"], name="Intermediate"),
        row=2,
        col=1,
    )
    if "position_in_20_range" in df_intermediate.columns:
        fig.add_trace(
            go.Scatter(x=df_intermediate.index, y=df_intermediate["position_in_20_range"], mode="lines", name="Int pos20", line=dict(width=1)),
            row=2,
            col=1,
        )

    fig.add_trace(
        go.Candlestick(x=df_entry.index, open=df_entry["open"], high=df_entry["high"], low=df_entry["low"], close=df_entry["close"], name="Entry"),
        row=3,
        col=1,
    )

    if entry_ts is not None:
        fig.add_vline(x=entry_ts, line_dash="dash", line_color="green", row="all", col=1)
    if exit_ts is not None:
        fig.add_vline(x=exit_ts, line_dash="dash", line_color="red", row="all", col=1)

    fig.update_layout(
        template="plotly_dark",
        height=1000,
        xaxis_rangeslider_visible=False,
        dragmode="pan",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="Trade Explorer", layout="wide")
    st.title("Multi-Timeframe Trade Explorer")
    st.caption("Scroll/zoom charts, jump to historical trades, inspect 1h/15m/3m mapping.")

    default_root = Path("data/features")
    trades_csv = Path("reports/backtests/mnq_v1_trades.csv")

    features_root = Path(st.sidebar.text_input("Features directory", str(default_root)))
    window_hours = st.sidebar.slider("Window +/- hours", min_value=2, max_value=72, value=18, step=2)

    symbol_options = sorted([p.name for p in (features_root / "1min").glob("*.parquet")]) if (features_root / "1min").exists() else []
    symbol_prefixes = sorted({"_".join(name.split("_")[:3]) for name in symbol_options})
    if not symbol_prefixes:
        st.error("No feature files found. Build features first in data/features.")
        return
    symbol_prefix = st.sidebar.selectbox("Symbol", symbol_prefixes, index=0)

    tf_entry = st.sidebar.selectbox("Entry Timeframe", ["1min", "3min", "5min"], index=0)
    tf_intermediate = st.sidebar.selectbox("Intermediate Timeframe", ["3min", "5min", "15min"], index=1)
    tf_macro = st.sidebar.selectbox("Macro Timeframe", ["15min", "1h", "4h"], index=0)

    mode = st.sidebar.radio("Navigation mode", ["Jump to trade", "Jump to date/time"])

    entry_ts = None
    exit_ts = None
    center_ts = None

    if mode == "Jump to trade":
        if not trades_csv.exists():
            st.error(f"Trades CSV not found: {trades_csv}")
            return
        trades = pd.read_csv(trades_csv, parse_dates=["entry_time", "exit_time"])
        if trades.empty:
            st.error("Trades CSV is empty.")
            return

        trade_labels = [
            f"#{i} | {r.side} | {r.entry_time} -> {r.exit_time} | PnL {r.net_pnl_usd:.2f}"
            for i, r in trades.reset_index().iterrows()
        ]
        selected = st.sidebar.selectbox("Trade", options=list(range(len(trade_labels))), format_func=lambda i: trade_labels[i])
        tr = trades.iloc[selected]
        entry_ts = pd.Timestamp(tr["entry_time"])
        exit_ts = pd.Timestamp(tr["exit_time"])
        entry_ts = entry_ts.tz_convert("UTC") if entry_ts.tzinfo is not None else entry_ts.tz_localize("UTC")
        exit_ts = exit_ts.tz_convert("UTC") if exit_ts.tzinfo is not None else exit_ts.tz_localize("UTC")
        center_ts = entry_ts
        st.sidebar.markdown(f"**Entry:** `{entry_ts}`")
        st.sidebar.markdown(f"**Exit:** `{exit_ts}`")
        st.sidebar.markdown(f"**PnL (USD):** `{tr['net_pnl_usd']:.2f}`")
    else:
        date_val = st.sidebar.date_input("Date (UTC)", value=datetime.now(timezone.utc).date())
        time_val = st.sidebar.time_input("Time (UTC)", value=time(14, 0))
        center_ts = pd.Timestamp(datetime.combine(date_val, time_val)).tz_localize("UTC")

    start = center_ts - timedelta(hours=window_hours)
    end = center_ts + timedelta(hours=window_hours)

    df_macro_full = load_feature(features_root, symbol_prefix, tf_macro)
    df_macro = df_macro_full.loc[start:end]
    df_intermediate = load_feature(features_root, symbol_prefix, tf_intermediate).loc[start:end]
    df_entry = load_feature(features_root, symbol_prefix, tf_entry).loc[start:end]

    zigzag_points = None
    if "swing_high_val" in df_macro_full.columns:
        ph = df_macro_full["swing_high_val"].shift(-2).dropna()
        pl = df_macro_full["swing_low_val"].shift(-2).dropna()
        zz = pd.concat([ph, pl]).sort_index()
        zigzag_points = zz.loc[start:end]

    if df_entry.empty:
        st.warning("No data in selected window. Expand window or choose another date/trade.")
        return

    fig = build_chart(df_macro, df_intermediate, df_entry, entry_ts, exit_ts, zigzag_points)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Window stats")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{tf_entry} bars", len(df_entry))
    c2.metric(f"{tf_intermediate} bars", len(df_intermediate))
    c3.metric(f"{tf_macro} bars", len(df_macro))


if __name__ == "__main__":
    main()

