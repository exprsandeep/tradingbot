# tradingbot
For Apex Trader EOD Drawdown

## First milestone: reliable historical data for backtesting

This project starts with a clean futures data pipeline:
- **Historical source**: Databento (exchange-grade CME history)
- **Execution target**: Tradovate (Apex account)
- **Storage format**: local Parquet files in `data/raw`

Read the rationale in `docs/data-foundation.md`.
Detailed strategy data requirements are in `docs/strategy-data-needs.md`.
Machine-readable config is in `config/data_requirements.yaml`.
Execution roadmap is tracked in `docs/execution-roadmap-checklist.md`.
Initial strategy spec is in `config/strategy_v1.yaml`.

## Setup

1. Install dependencies:
   - `pip install -r requirements.txt`
2. Create environment file:
   - Copy `.env.example` to `.env`
   - Set `DATABENTO_API_KEY`

## Download sample data

Run:

`python scripts/fetch_data.py --symbol ES.c.0 --schema ohlcv-1m --start 2025-01-01T00:00:00 --end 2025-02-01T00:00:00`

This saves a parquet file under `data/raw`.

## Next phases
- Data validation (gaps, duplicates, session coverage)
- Strategy module
- Backtest engine with slippage/commission
- Live execution bridge to Tradovate for Apex account

## Data curation and validation

Curate raw files into a backtest-ready minute series:

`python scripts/curate_bars.py --data-dir data/raw --glob "*.parquet" --out-dir data/curated`

Validate curated files against `config/data_requirements.yaml`:

`python scripts/validate_data.py --config config/data_requirements.yaml --data-dir data/curated --glob "*_curated.parquet"`

Validation reports are written to `reports/data_quality`.

## Multi-timeframe feature datasets

Build strategy-ready datasets from curated 1m bars:

`python scripts/build_multi_timeframe_features.py --data-dir data/curated --glob "*_curated.parquet" --timeframes 3min 15min 1h --out-dir data/features`

Outputs are saved in:
- `data/features/3min`
- `data/features/15min`
- `data/features/1h`

## Run strategy backtest

Run v1 strategy against generated features:

`python scripts/run_backtest.py --config config/strategy_v1.yaml --features-dir data/features`

Outputs:
- Trades CSV: `reports/backtests/mnq_v1_trades.csv`
- Summary JSON: `reports/backtests/mnq_v1_summary.json`

## Visualize strategy mapping (1h/15m -> 3m trade)

Generate an interactive chart for a specific trade index:

`python scripts/visualize_backtest.py --symbol-prefix MNQ_c_0 --features-dir data/features --trades-csv reports/backtests/mnq_v1_trades.csv --trade-index 0 --window-hours 18 --out-html reports/backtests/visualizations/trade_0.html`
