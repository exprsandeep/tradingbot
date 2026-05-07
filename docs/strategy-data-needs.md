# Strategy Data Needs (Apex Futures / Tradovate)

## Your planned timeframe model
- **Entry timeframe**: `1m` or `3m`
- **Market-structure timeframe**: `15m` and `1h`
- **Asset class**: CME futures (for Apex-funded execution through Tradovate)

---

## 1) Core market data required

### A) OHLCV candles (mandatory)
You need historical candles for:
- `1m` (primary entry model)
- `3m` (alternate entry model)
- `15m` (local structure)
- `1h` (higher-timeframe bias)

Minimum fields per bar:
- `timestamp` (UTC)
- `open`, `high`, `low`, `close`
- `volume`
- `symbol`
- `contract` (or continuous symbol + roll reference)

### B) Session metadata (mandatory)
To avoid false signals around session boundaries:
- Session open/close definitions (RTH and ETH)
- Trading day boundary and timezone mapping
- Holiday / early-close calendar

### C) Contract and roll data (mandatory for futures)
Because futures expire, you need:
- Contract expiration dates
- Roll schedule/rule (e.g., volume-based roll or fixed days before expiry)
- Continuous-series method used (`.c.0`, back-adjusted, forward-adjusted, etc.)

Without consistent roll handling, backtests will be misleading.

---

## 2) Data quality requirements (for strategy reliability)

Before strategy generation/backtest, validate:
- Missing bars (especially during liquid sessions)
- Duplicate timestamps
- Out-of-order timestamps
- Extreme bad ticks / candle spikes
- Bar alignment across timeframes (1m -> 3m/15m/1h aggregation consistency)

Quality target:
- No missing bars during defined active session unless exchange halt/news halt
- Deterministic resampling rules across all timeframes

---

## 3) Execution realism data (for realistic backtesting)

### A) Cost model inputs (mandatory)
- Commission per side (Apex/Tradovate routing equivalent used in your account)
- Exchange + NFA fees
- Slippage model (ticks) by instrument and time-of-day

### B) Tick size/value (mandatory)
Per instrument:
- `tick_size` (e.g., ES = 0.25)
- `tick_value` (e.g., ES = $12.50 per tick)
- Contract multiplier

This is required for accurate PnL and drawdown calculations.

### C) Margin/risk constraints (Apex-specific)
- Max contracts by account size
- Trailing drawdown behavior (EOD vs intraday where applicable)
- Daily loss limits and consistency rules
- Allowed trading windows (if your plan imposes them)

---

## 4) Recommended historical depth

For robust strategy development:
- **Minimum**: 12 months of `1m` data
- **Preferred**: 24-36 months of `1m` data
- Derive `3m`, `15m`, and `1h` from the same 1m base to keep signal consistency

Also include:
- Different volatility regimes (trend, chop, high-vol news periods)
- At least one major stress period per instrument

---

## 5) Storage format and schema standard

Recommended storage:
- Parquet files partitioned by `symbol` and `date`
- UTC timestamps only

Suggested canonical schema:
- `ts_utc`, `symbol`, `contract`, `open`, `high`, `low`, `close`, `volume`
- Optional later: `trade_count`, `vwap`, `bid`, `ask`, `spread`

---

## 6) What you need right now (checklist)

- [ ] Reliable `1m` CME futures historical data source (Databento primary)
- [ ] Continuous-contract roll policy documented and fixed
- [ ] Candle quality validator (gaps, duplicates, outliers)
- [ ] Timeframe builder (3m/15m/1h from 1m source)
- [ ] Backtest cost engine (commission + fees + slippage)
- [ ] Apex rule engine (drawdown and account constraints)

---

## 7) Nice-to-have data after v1

- Tick/trade data for entry refinement and slippage calibration
- Depth/order-book snapshots for advanced execution modeling
- Economic event calendar (CPI, FOMC, NFP) for risk filters
- Market internals or correlated assets for regime filters

