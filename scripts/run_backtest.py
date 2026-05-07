from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.engine import run_backtest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run strategy backtest")
    parser.add_argument("--config", default="config/strategy_v1.yaml", help="Strategy config path")
    parser.add_argument("--features-dir", default="data/features", help="Feature datasets root dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    trades, summary = run_backtest(cfg, args.features_dir)

    trades_path = Path(cfg["outputs"]["trades_csv"])
    summary_path = Path(cfg["outputs"]["summary_json"])
    trades_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    trades.to_csv(trades_path, index=False)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Trades: {len(trades)}")
    print(f"Net PnL USD: {summary['net_pnl_usd']:.2f}")
    print(f"Win rate: {summary['win_rate']:.2%}")
    print(f"Trades report: {trades_path}")
    print(f"Summary report: {summary_path}")


if __name__ == "__main__":
    main()

