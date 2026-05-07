from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .strategies import get_strategy


@dataclass
class Position:
    side: str
    entry_time: pd.Timestamp
    entry_price: float
    stop_price: float
    target_price: float
    qty: int
    bars_held: int = 0
    moved_to_breakeven: bool = False


def _load_tf(features_dir: Path, timeframe: str, symbol_prefix: str) -> pd.DataFrame:
    candidates = sorted((features_dir / timeframe).glob(f"{symbol_prefix}*_{timeframe}.parquet"))
    if not candidates:
        raise FileNotFoundError(f"No feature file found for {symbol_prefix} in {timeframe}")
    df = pd.read_parquet(candidates[0]).copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"Expected DatetimeIndex in {candidates[0]}")
    df = df.sort_index()
    df["ts"] = df.index
    return df


def _session_allowed(ts: pd.Timestamp, sessions: dict[str, Any]) -> bool:
    allowed = sessions.get("allowed_utc", [])
    if not allowed:
        return True
    hhmm = ts.strftime("%H:%M")
    for w in allowed:
        if w["start"] <= hhmm <= w["end"]:
            return True
    return False


def _slippage_ticks(ts: pd.Timestamp, cfg: dict[str, Any]) -> int:
    # Basic session split: treat configured session windows as RTH and rest as ETH.
    if _session_allowed(ts, cfg["sessions"]):
        return int(cfg["costs"]["slippage_ticks"]["rth"])
    return int(cfg["costs"]["slippage_ticks"]["eth"])


def _to_usd(ticks: float, tick_value: float, qty: int) -> float:
    return ticks * tick_value * qty


def run_backtest(strategy_cfg: dict[str, Any], features_dir: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    features_root = Path(features_dir)
    symbol_prefix = strategy_cfg["market"]["symbol"].replace(".", "_")

    strategy = get_strategy(strategy_cfg)

    entry_tf = strategy_cfg["market"]["entry_timeframe"]
    tf_15 = "15min"
    tf_1h = "1h"

    entry = _load_tf(features_root, entry_tf, symbol_prefix)
    s15 = _load_tf(features_root, tf_15, symbol_prefix)
    s1h = _load_tf(features_root, tf_1h, symbol_prefix)

    # As-of joins prevent lookahead by joining only the latest completed HTF bar.
    df = pd.merge_asof(
        entry.reset_index(drop=True).sort_values("ts"),
        s15.reset_index(drop=True).sort_values("ts")[["ts", "position_in_20_range"]].rename(
            columns={"position_in_20_range": "s15_pos20"}
        ),
        on="ts",
        direction="backward",
    )
    df = pd.merge_asof(
        df.sort_values("ts"),
        s1h[["ts", "close", "close_sma_50", "momentum_20"]]
        .rename(
            columns={
                "close": "h1_close",
                "close_sma_50": "h1_close_sma_50",
                "momentum_20": "h1_momentum_20",
            }
        )
        .reset_index(drop=True)
        .sort_values("ts"),
        on="ts",
        direction="backward",
    )

    tick_size = float(strategy_cfg["risk_management"]["tick_size"])
    tick_value = 5.0  # MNQ per-tick USD value for 1 contract
    qty = int(strategy_cfg["position_sizing"]["contracts"])
    stop_ticks = int(strategy_cfg["risk_management"]["stop_loss"]["ticks"])
    target_ticks = int(strategy_cfg["risk_management"]["take_profit"]["ticks"])
    be_enabled = bool(strategy_cfg["risk_management"]["breakeven"]["enabled"])
    be_trigger = int(strategy_cfg["risk_management"]["breakeven"]["trigger_ticks"])
    max_bars = int(strategy_cfg["risk_management"]["time_stop"]["bars_on_entry_tf"])
    max_trades_per_day = int(strategy_cfg["position_sizing"]["max_trades_per_day"])
    cooldown_bars = int(strategy_cfg["position_sizing"]["cooldown_bars_after_exit"])

    commission_per_side = float(strategy_cfg["costs"]["commission_per_side_per_contract_usd"])
    fees_round_turn = float(strategy_cfg["costs"]["fees_per_round_turn_per_contract_usd"])
    daily_loss_limit = strategy_cfg["apex_constraints"].get("daily_loss_limit_usd")

    trades: list[dict[str, Any]] = []
    pos: Position | None = None
    cooldown = 0
    day_trade_count: dict[str, int] = {}
    day_realized: dict[str, float] = {}

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        ts = pd.Timestamp(row["ts"])
        day_key = ts.strftime("%Y-%m-%d")

        day_trade_count.setdefault(day_key, 0)
        day_realized.setdefault(day_key, 0.0)

        if cooldown > 0:
            cooldown -= 1

        # Manage existing position first.
        if pos is not None:
            pos.bars_held += 1
            exit_reason = None
            exit_price = None

            if pos.side == "long":
                if be_enabled and (row["high"] - pos.entry_price) / tick_size >= be_trigger and not pos.moved_to_breakeven:
                    pos.stop_price = pos.entry_price
                    pos.moved_to_breakeven = True
                if row["low"] <= pos.stop_price:
                    exit_reason = "stop"
                    exit_price = pos.stop_price
                elif row["high"] >= pos.target_price:
                    exit_reason = "target"
                    exit_price = pos.target_price
            else:
                if be_enabled and (pos.entry_price - row["low"]) / tick_size >= be_trigger and not pos.moved_to_breakeven:
                    pos.stop_price = pos.entry_price
                    pos.moved_to_breakeven = True
                if row["high"] >= pos.stop_price:
                    exit_reason = "stop"
                    exit_price = pos.stop_price
                elif row["low"] <= pos.target_price:
                    exit_reason = "target"
                    exit_price = pos.target_price

            if exit_reason is None and pos.bars_held >= max_bars:
                exit_reason = "time_stop"
                exit_price = float(row["close"])

            if exit_reason is not None and exit_price is not None:
                slip = _slippage_ticks(ts, strategy_cfg) * tick_size
                if pos.side == "long":
                    exit_fill = exit_price - slip
                    pnl_ticks = (exit_fill - pos.entry_price) / tick_size
                else:
                    exit_fill = exit_price + slip
                    pnl_ticks = (pos.entry_price - exit_fill) / tick_size

                gross = _to_usd(pnl_ticks, tick_value, pos.qty)
                costs = (2 * commission_per_side * pos.qty) + (fees_round_turn * pos.qty)
                net = gross - costs
                day_realized[day_key] += net

                trades.append(
                    {
                        "entry_time": pos.entry_time,
                        "exit_time": ts,
                        "side": pos.side,
                        "entry_price": pos.entry_price,
                        "exit_price": exit_fill,
                        "qty": pos.qty,
                        "bars_held": pos.bars_held,
                        "exit_reason": exit_reason,
                        "pnl_ticks": pnl_ticks,
                        "gross_pnl_usd": gross,
                        "costs_usd": costs,
                        "net_pnl_usd": net,
                    }
                )
                pos = None
                cooldown = cooldown_bars

        # Entry conditions.
        if pos is not None or cooldown > 0:
            continue
        if not _session_allowed(ts, strategy_cfg["sessions"]):
            continue
        if day_trade_count[day_key] >= max_trades_per_day:
            continue
        if daily_loss_limit is not None and day_realized[day_key] <= -abs(float(daily_loss_limit)):
            continue

        slip = _slippage_ticks(ts, strategy_cfg) * tick_size
        if strategy.should_enter_long(row, prev):
            entry_fill = float(row["close"] + slip)
            pos = Position(
                side="long",
                entry_time=ts,
                entry_price=entry_fill,
                stop_price=entry_fill - (stop_ticks * tick_size),
                target_price=entry_fill + (target_ticks * tick_size),
                qty=qty,
            )
            day_trade_count[day_key] += 1
        elif strategy.should_enter_short(row, prev):
            entry_fill = float(row["close"] - slip)
            pos = Position(
                side="short",
                entry_time=ts,
                entry_price=entry_fill,
                stop_price=entry_fill + (stop_ticks * tick_size),
                target_price=entry_fill - (target_ticks * tick_size),
                qty=qty,
            )
            day_trade_count[day_key] += 1

    trades_df = pd.DataFrame(trades)
    summary = {
        "trades": int(len(trades_df)),
        "wins": int((trades_df["net_pnl_usd"] > 0).sum()) if len(trades_df) else 0,
        "losses": int((trades_df["net_pnl_usd"] <= 0).sum()) if len(trades_df) else 0,
        "win_rate": float((trades_df["net_pnl_usd"] > 0).mean()) if len(trades_df) else 0.0,
        "net_pnl_usd": float(trades_df["net_pnl_usd"].sum()) if len(trades_df) else 0.0,
        "avg_pnl_usd": float(trades_df["net_pnl_usd"].mean()) if len(trades_df) else 0.0,
        "avg_win_usd": float(trades_df.loc[trades_df["net_pnl_usd"] > 0, "net_pnl_usd"].mean())
        if len(trades_df) and (trades_df["net_pnl_usd"] > 0).any()
        else 0.0,
        "avg_loss_usd": float(trades_df.loc[trades_df["net_pnl_usd"] <= 0, "net_pnl_usd"].mean())
        if len(trades_df) and (trades_df["net_pnl_usd"] <= 0).any()
        else 0.0,
        "profit_factor": float(
            trades_df.loc[trades_df["net_pnl_usd"] > 0, "net_pnl_usd"].sum()
            / abs(trades_df.loc[trades_df["net_pnl_usd"] <= 0, "net_pnl_usd"].sum())
        )
        if len(trades_df) and (trades_df["net_pnl_usd"] <= 0).any()
        else 0.0,
    }
    return trades_df, summary

