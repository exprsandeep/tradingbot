from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Curate raw 1m bars for backtesting")
    parser.add_argument("--data-dir", default="data/raw", help="Input parquet directory")
    parser.add_argument("--glob", default="*.parquet", help="Input file glob")
    parser.add_argument("--out-dir", default="data/curated", help="Output directory")
    return parser.parse_args()


def curate_file(path: Path, out_dir: Path) -> Path:
    df = pd.read_parquet(path).copy()
    if df.empty:
        raise ValueError(f"File is empty: {path}")

    ts = pd.DatetimeIndex(df.index)
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    df.index = ts
    df = df.sort_index()

    symbol = str(df["symbol"].iloc[0]) if "symbol" in df.columns else path.stem

    full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq="1min", tz="UTC")

    base = df.reindex(full_index)
    base["is_synthetic"] = base["open"].isna()

    close_ffill = base["close"].ffill()
    base["open"] = base["open"].fillna(close_ffill)
    base["high"] = base["high"].fillna(base["open"])
    base["low"] = base["low"].fillna(base["open"])
    base["close"] = base["close"].fillna(base["open"])
    base["volume"] = base["volume"].fillna(0)
    base["symbol"] = base["symbol"].fillna(symbol)
    base["contract"] = symbol
    base["ts_utc"] = base.index

    for col in ["rtype", "publisher_id", "instrument_id"]:
        if col in base.columns:
            base[col] = base[col].ffill().bfill()

    curated_name = path.name.replace(".parquet", "_curated.parquet")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / curated_name
    base.to_parquet(out_path, index=True)
    return out_path


def main() -> None:
    args = parse_args()
    in_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    files = sorted(in_dir.glob(args.glob))
    if not files:
        raise FileNotFoundError(f"No files found in {in_dir} matching {args.glob}")

    for path in files:
        out = curate_file(path, out_dir)
        print(f"Curated: {out}")


if __name__ == "__main__":
    main()

