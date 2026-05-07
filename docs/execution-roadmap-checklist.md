# Automated Trading Bot Roadmap (Checklist)

## Objective
Ship a reliable automated futures trading bot for Apex/Tradovate with realistic backtesting first, then controlled live rollout.

## Phase 1: Strategy Definition (Start Here)
- [ ] Choose v1 symbol (recommended: `MNQ.c.0`)
- [ ] Freeze market structure logic using `15m` and `1h`
- [ ] Freeze entry logic using `3m`
- [ ] Freeze exit logic (stop, target, time-based exit)
- [ ] Define risk limits (max trades/day, max concurrent positions)
- [ ] Define allowed trading session windows (RTH/ETH rules)
- [ ] Write strategy config in `config/strategy_v1.yaml`

## Phase 2: Backtest Engine
- [ ] Implement deterministic backtest engine
- [ ] Ensure strict no-lookahead execution
- [ ] Generate trade ledger with reason codes
- [ ] Add equity curve and drawdown tracking
- [ ] Add performance metrics (PF, expectancy, win rate, avg R multiple)

## Phase 3: Execution Realism
- [ ] Add commission model
- [ ] Add exchange fee model
- [ ] Add slippage model by session/liquidity
- [ ] Add tick-size rounding and contract multiplier handling

## Phase 4: Apex Constraints
- [ ] Add trailing drawdown enforcement
- [ ] Add daily loss lockout
- [ ] Add max contracts constraints
- [ ] Add trading window restrictions
- [ ] Reject orders that violate constraints

## Phase 5: Validation & Robustness
- [ ] Run walk-forward split (train/validate/test)
- [ ] Evaluate results by year and by session
- [ ] Stress test around high-volatility events
- [ ] Perform parameter sensitivity checks
- [ ] Promote only stable parameter regions

## Phase 6: Live Rollout
- [ ] Paper/sim execution bridge to Tradovate
- [ ] Reconciliation checks (signal vs fill vs position)
- [ ] Alerts/logging/health monitoring
- [ ] Controlled live size ramp-up
- [ ] Incident rollback procedure

## Current status
- [x] Data pipeline (download, curation, validation)
- [x] Multi-timeframe feature generation (`3m`, `15m`, `1h`)
- [x] Choose v1 symbol (recommended: `MNQ.c.0`)
- [x] Freeze market structure logic using `15m` and `1h`
- [x] Freeze entry logic using `3m`
- [x] Freeze exit logic (stop, target, time-based exit)
- [x] Define risk limits (max trades/day, max concurrent positions)
- [x] Define allowed trading session windows (RTH/ETH rules)
- [x] Write strategy config in `config/strategy_v1.yaml`
- [ ] Strategy definition v1 (review and lock with your approval)
