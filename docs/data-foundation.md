# Reliable Data Foundation (Apex + Tradovate Futures Bot)

## Goal
Build backtests on data quality that is reliable enough for prop-firm evaluation constraints.

## Recommendation
Use **Databento (CME Globex historical)** as the primary historical data source for backtesting, then execute live through Tradovate.

## Why this approach
- Tradovate is ideal for execution/account integration, but not the strongest single source for deep historical research.
- Databento provides exchange-grade CME history, including continuous symbols and multiple schemas.
- A separate historical source avoids overfitting to broker-specific quirks and gives repeatable datasets.

## Data design
- Source: `GLBX.MDP3` (CME/CBOT/NYMEX/COMEX)
- Default symbol style: continuous front contract (example `ES.c.0`)
- Stored format: Parquet files under `data/raw`
- Default backtest timeframe: `ohlcv-1m` (upgrade to tick/order-book later)

## Quality checks before using in strategy
- Validate trading session coverage (RTH vs ETH)
- Detect missing bars and duplicate timestamps
- Normalize to one timezone (recommend UTC in storage)
- Handle contract roll behavior consistently for continuous symbols

## Next implementation steps
1. Add validation job for gaps/duplicates and daily report.
2. Build roll-aware continuous contract logic for each instrument.
3. Add costs model (commission + slippage) specific to Apex account rules.
4. Integrate strategy engine and walk-forward testing.
