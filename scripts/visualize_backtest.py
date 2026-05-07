from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize backtest trades with 1h/15m structure and 3m execution"
    )
    parser.add_argument("--symbol-prefix", default="MNQ_c_0", help="Feature file symbol prefix")
    parser.add_argument("--features-dir", default="data/features", help="Root features directory")
    parser.add_argument(
        "--trades-csv",
        default="reports/backtests/mnq_v1_trades.csv",
        help="Backtest trades CSV path",
    )
    parser.add_argument(
        "--trade-index",
        type=int,
        default=0,
        help="Trade index (0-based) to visualize",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=18,
        help="Hours before/after entry to include in chart",
    )
    parser.add_argument(
        "--out-html",
        default="reports/backtests/visualizations/trade_view.html",
        help="Output HTML file path",
    )
    return parser.parse_args()


def load_feature(features_dir: Path, timeframe: str, symbol_prefix: str) -> pd.DataFrame:
    matches = sorted((features_dir / timeframe).glob(f"{symbol_prefix}*_{timeframe}.parquet"))
    if not matches:
        raise FileNotFoundError(f"Could not find {timeframe} feature file for {symbol_prefix}")
    df = pd.read_parquet(matches[0]).copy()
    df.index = pd.DatetimeIndex(df.index)
    df = df.sort_index()
    return df


def slice_window(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return df.loc[(df.index >= start) & (df.index <= end)].copy()


def add_candles(fig: go.Figure, df: pd.DataFrame, row: int, title: str) -> None:
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=title,
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def main() -> None:
    args = parse_args()
    features_dir = Path(args.features_dir)
    trades = pd.read_csv(args.trades_csv, parse_dates=["entry_time", "exit_time"])
    if trades.empty:
        raise ValueError("Trades CSV is empty.")
    if args.trade_index < 0 or args.trade_index >= len(trades):
        raise IndexError(f"trade-index must be between 0 and {len(trades)-1}")

    trade = trades.iloc[args.trade_index]
    entry_time = pd.Timestamp(trade["entry_time"])
    exit_time = pd.Timestamp(trade["exit_time"])
    entry_time = entry_time.tz_convert("UTC") if entry_time.tzinfo is not None else entry_time.tz_localize("UTC")
    exit_time = exit_time.tz_convert("UTC") if exit_time.tzinfo is not None else exit_time.tz_localize("UTC")
    start = entry_time - pd.Timedelta(hours=args.window_hours)
    end = exit_time + pd.Timedelta(hours=args.window_hours)

    df_3m = slice_window(load_feature(features_dir, "3min", args.symbol_prefix), start, end)
    df_15m = slice_window(load_feature(features_dir, "15min", args.symbol_prefix), start, end)
    df_1h = slice_window(load_feature(features_dir, "1h", args.symbol_prefix), start, end)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.30, 0.30, 0.40],
        subplot_titles=("1h Structure", "15m Structure", "3m Execution"),
    )

    add_candles(fig, df_1h, 1, "1h")
    fig.add_trace(
        go.Scatter(
            x=df_1h.index,
            y=df_1h["close_sma_50"],
            mode="lines",
            name="1h SMA50",
            line=dict(width=1.5),
        ),
        row=1,
        col=1,
    )

    add_candles(fig, df_15m, 2, "15m")
    fig.add_trace(
        go.Scatter(
            x=df_15m.index,
            y=df_15m["position_in_20_range"],
            mode="lines",
            name="15m pos_in_20_range",
            line=dict(width=1),
        ),
        row=2,
        col=1,
    )

    add_candles(fig, df_3m, 3, "3m")

    fig.add_vline(x=entry_time, line_dash="dash", line_color="green", row="all", col=1)
    fig.add_vline(x=exit_time, line_dash="dash", line_color="red", row="all", col=1)

    fig.add_trace(
        go.Scatter(
            x=[entry_time],
            y=[trade["entry_price"]],
            mode="markers+text",
            marker=dict(size=10, color="green"),
            text=["ENTRY"],
            textposition="top center",
            name="Entry",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[exit_time],
            y=[trade["exit_price"]],
            mode="markers+text",
            marker=dict(size=10, color="red"),
            text=["EXIT"],
            textposition="bottom center",
            name="Exit",
        ),
        row=3,
        col=1,
    )

    fig.update_layout(
        title=(
            f"Trade #{args.trade_index} | {trade['side']} | "
            f"PnL ${trade['net_pnl_usd']:.2f} | Reason: {trade['exit_reason']}"
        ),
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=1100,
    )

    out_path = Path(args.out_html)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(out_path, include_plotlyjs="cdn")
    print(f"Saved visualization: {out_path}")


if __name__ == "__main__":
    main()

