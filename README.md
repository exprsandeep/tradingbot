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
