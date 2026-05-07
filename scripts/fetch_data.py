from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.databento_downloader import DataRequest, DatabentoDownloader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch historical futures data for backtesting"
    )
    parser.add_argument("--dataset", default="GLBX.MDP3", help="Databento dataset")
    parser.add_argument(
        "--symbol",
        default="ES.c.0",
        help="Continuous futures symbol, e.g. ES.c.0, NQ.c.0, CL.c.0",
    )
    parser.add_argument(
        "--schema",
        default="ohlcv-1m",
        help="Data schema, e.g. ohlcv-1m, trades, mbp-1",
    )
    parser.add_argument("--start", required=True, help="Start date/time (ISO-8601)")
    parser.add_argument("--end", required=True, help="End date/time (ISO-8601)")
    parser.add_argument("--stype-in", default="continuous", help="Input symbol type")
    parser.add_argument("--out-dir", default="data/raw", help="Output parquet directory")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    api_key = os.getenv("DATABENTO_API_KEY")
    if not api_key:
        raise EnvironmentError("Set DATABENTO_API_KEY in your environment or .env")

    request = DataRequest(
        dataset=args.dataset,
        symbol=args.symbol,
        schema=args.schema,
        start=args.start,
        end=args.end,
        stype_in=args.stype_in,
        output_dir=args.out_dir,
    )

    downloader = DatabentoDownloader(api_key)
    output_path = downloader.fetch(request)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()

