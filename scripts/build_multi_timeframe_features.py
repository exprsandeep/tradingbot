from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


AGG = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
    "is_synthetic": "max",
    "symbol": "last",
    "contract": "last",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build 3m/15m/1h strategy datasets from curated 1m bars"
    )
    parser.add_argument("--data-dir", default="data/curated", help="Input curated data dir")
    parser.add_argument("--glob", default="*_curated.parquet", help="Input file glob")
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=["1min", "3min", "5min", "15min", "1h"],
        help="Pandas resample rules",
    )
    parser.add_argument("--out-dir", default="data/features", help="Output features dir")
    return parser.parse_args()


def calculate_swing_points(df: pd.DataFrame, n: int = 2) -> pd.DataFrame:
    """Calculates N-bar fractal swing points and ZigZag trend without lookahead bias."""
    out = df.copy()
    
    highs = out["high"].values
    lows = out["low"].values
    
    is_swing_high = np.zeros(len(out), dtype=bool)
    is_swing_low = np.zeros(len(out), dtype=bool)
    
    for i in range(n, len(out) - n):
        window_highs = highs[i-n:i+n+1]
        if highs[i] == np.max(window_highs) and np.sum(window_highs == highs[i]) == 1:
            is_swing_high[i] = True
            
        window_lows = lows[i-n:i+n+1]
        if lows[i] == np.min(window_lows) and np.sum(window_lows == lows[i]) == 1:
            is_swing_low[i] = True

    out["confirmed_swing_high"] = pd.Series(is_swing_high, index=out.index).shift(n).fillna(False)
    out["confirmed_swing_low"] = pd.Series(is_swing_low, index=out.index).shift(n).fillna(False)
    
    out["swing_high_val"] = out["high"].shift(n).where(out["confirmed_swing_high"])
    out["swing_low_val"] = out["low"].shift(n).where(out["confirmed_swing_low"])
    
    out["last_swing_high"] = out["swing_high_val"].ffill()
    out["last_swing_low"] = out["swing_low_val"].ffill()
    
    out["prev_swing_high"] = out["swing_high_val"].dropna().shift(1).reindex(out.index).ffill()
    out["prev_swing_low"] = out["swing_low_val"].dropna().shift(1).reindex(out.index).ffill()
    
    out["zigzag_trend"] = 0
    uptrend = (out["last_swing_high"] > out["prev_swing_high"]) & (out["last_swing_low"] > out["prev_swing_low"])
    downtrend = (out["last_swing_high"] < out["prev_swing_high"]) & (out["last_swing_low"] < out["prev_swing_low"])
    
    out.loc[uptrend, "zigzag_trend"] = 1
    out.loc[downtrend, "zigzag_trend"] = -1
    
    return out


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["bar_range"] = out["high"] - out["low"]
    out["body"] = out["close"] - out["open"]
    out["body_pct_of_range"] = (out["body"] / out["bar_range"].replace(0, pd.NA)).fillna(0.0)
    out["ret_1"] = out["close"].pct_change().fillna(0.0)
    out["ret_5"] = out["close"].pct_change(5).fillna(0.0)
    out["ret_20"] = out["close"].pct_change(20).fillna(0.0)
    out["vol_sma_20"] = out["volume"].rolling(20, min_periods=1).mean()
    out["close_sma_20"] = out["close"].rolling(20, min_periods=1).mean()
    out["close_sma_50"] = out["close"].rolling(50, min_periods=1).mean()
    out["momentum_20"] = (out["close"] / out["close_sma_20"] - 1.0).fillna(0.0)
    out["hh_20"] = out["high"].rolling(20, min_periods=1).max()
    out["ll_20"] = out["low"].rolling(20, min_periods=1).min()
    out["position_in_20_range"] = (
        (out["close"] - out["ll_20"]) / (out["hh_20"] - out["ll_20"]).replace(0, pd.NA)
    ).fillna(0.5)
    out["ts_utc"] = out.index
    out = calculate_swing_points(out, n=2)
    return out


def build_for_file(path: Path, timeframes: list[str], out_dir: Path) -> list[Path]:
    base = pd.read_parquet(path).copy()
    if base.empty:
        raise ValueError(f"Input file is empty: {path}")

    if not isinstance(base.index, pd.DatetimeIndex):
        raise ValueError(f"Expected DatetimeIndex in {path}")

    ts = base.index.tz_convert("UTC") if base.index.tz is not None else base.index.tz_localize("UTC")
    base.index = ts
    base = base.sort_index()

    outputs: list[Path] = []
    source_stem = path.stem.replace("_curated", "")

    for tf in timeframes:
        resampled = base.resample(tf).agg(AGG).dropna(subset=["open", "high", "low", "close"])
        features = add_features(resampled)
        tf_dir = out_dir / tf
        tf_dir.mkdir(parents=True, exist_ok=True)
        out_path = tf_dir / f"{source_stem}_{tf}.parquet"
        features.to_parquet(out_path, index=True)
        outputs.append(out_path)

    return outputs


def main() -> None:
    args = parse_args()
    in_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    files = sorted(in_dir.glob(args.glob))
    if not files:
        raise FileNotFoundError(f"No files found in {in_dir} matching {args.glob}")

    total = 0
    for f in files:
        built = build_for_file(f, args.timeframes, out_dir)
        total += len(built)
        for out in built:
            print(f"Built: {out}")
    print(f"Done. Generated {total} feature datasets.")


if __name__ == "__main__":
    main()

