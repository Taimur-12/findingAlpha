"""
Execution Simulator.

simulate_trade(intent, future_candles, config, ...) → TradeOutcome | None

Simulates what happens to a trade after entry on historical OHLCV data.
Returns None if the entry order never fills (limit price never touched).

Fill rules:
  Entry limit (long):  fills at intent.entry_price when candle low ≤ entry_price.
  Entry market (long): fills at first candle open × (1 + slippage).
  Stop (long):         triggers when candle low ≤ stop_price; fills at stop - slippage.
  TP   (long):         triggers when candle high ≥ tp_price; fills at tp_price.
  Short: mirrors long with high/low swapped.
  Same-candle stop + TP: stop wins (conservative).
  Timeout: exits at candle close with taker fee.

Fees:
  Entry limit  → maker_fee_bps
  Entry market → taker_fee_bps
  Stop         → taker_fee_bps (market fill)
  TP           → maker_fee_bps (limit fill)
  Timeout exit → taker_fee_bps

Funding: if future_candles has a 'funding_rate' column, applies
  funding_cost += funding_rate × notional_at_entry
  every 8-hour period (480 min) the trade is held.
  Each bar that has a non-NaN funding_rate triggers the charge once.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from finding_alpha.contracts.execution import TradeOutcome
from finding_alpha.contracts.trading import PortfolioIntent

_BPS = Decimal("0.0001")


class SimConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    taker_fee_bps: Decimal = Decimal("5.5")
    maker_fee_bps: Decimal = Decimal("2.0")
    stop_slippage_bps: Decimal = Decimal("10")   # extra slippage on stop fills


def simulate_trade(
    intent: PortfolioIntent,
    future_candles: pd.DataFrame,
    config: SimConfig,
    strategy_id: str,
    strategy_version: str,
    feature_version: str,
    timeframe: str,
    entry_ts: datetime,
) -> Optional[TradeOutcome]:
    """
    Simulate a single trade. future_candles must be sorted ascending by open_time
    and must contain float columns: open, high, low, close.
    The first row is the bar immediately after signal generation.
    """
    if future_candles.empty:
        return None

    is_long   = intent.side == "long"
    entry_lim = float(intent.entry_price)
    stop_px   = float(intent.stop_price)
    tp_px     = float(intent.target_plan[0].price) if intent.target_plan else None
    qty       = float(intent.quantity)
    notional  = float(intent.notional)
    max_bars  = intent.max_hold_minutes // _bar_minutes(future_candles)

    candles = future_candles.head(max_bars).reset_index(drop=True)

    # ── Simulate entry ────────────────────────────────────────────────────────
    entry_fill_price: Optional[float] = None
    entry_bar_idx: int = -1
    entry_fee_bps: Decimal

    if intent.entry_type == "market":
        row0 = candles.iloc[0]
        slippage_mult = 1 + float(config.taker_fee_bps * _BPS) if is_long else 1 - float(config.taker_fee_bps * _BPS)
        # slippage on market order uses stop_slippage_bps (market fill assumption)
        slip = float(intent.max_slippage_bps * _BPS)
        entry_fill_price = float(row0["open"]) * (1 + slip if is_long else 1 - slip)
        entry_bar_idx = 0
        entry_fee_bps = config.taker_fee_bps
    else:
        # Limit order: scan for price touch
        for idx, row in candles.iterrows():
            touched = row["low"] <= entry_lim if is_long else row["high"] >= entry_lim
            if touched:
                entry_fill_price = entry_lim
                entry_bar_idx = int(idx)
                entry_fee_bps = config.maker_fee_bps
                break

    if entry_fill_price is None:
        return None  # limit never filled

    entry_fill_d  = Decimal(f"{entry_fill_price:.2f}")
    entry_fee     = Decimal(f"{notional:.2f}") * entry_fee_bps * _BPS
    actual_entry_ts = _bar_ts(candles, entry_bar_idx, entry_ts)

    # ── Simulate exit ─────────────────────────────────────────────────────────
    post_entry = candles.iloc[entry_bar_idx + 1 :].reset_index(drop=True)
    funding_cost = _compute_funding(candles.iloc[:entry_bar_idx + 1], notional)

    exit_price_f: Optional[float] = None
    exit_reason:  Optional[str]   = None
    exit_fee_bps: Decimal
    exit_bar_idx: int = -1

    for idx, row in post_entry.iterrows():
        high = float(row["high"])
        low  = float(row["low"])

        stop_hit = low <= stop_px if is_long else high >= stop_px
        tp_hit   = (high >= tp_px if is_long else low <= tp_px) if tp_px is not None else False

        # Same candle: conservative — stop wins
        if stop_hit and tp_hit:
            stop_hit, tp_hit = True, False

        if stop_hit:
            slip = float(config.stop_slippage_bps * _BPS)
            exit_price_f = stop_px * (1 - slip) if is_long else stop_px * (1 + slip)
            exit_reason  = "stop_loss"
            exit_fee_bps = config.taker_fee_bps
            exit_bar_idx = int(idx)
            break

        if tp_hit:
            exit_price_f = tp_px
            exit_reason  = "take_profit"
            exit_fee_bps = config.maker_fee_bps
            exit_bar_idx = int(idx)
            break

        # Accumulate funding as we hold
        funding_cost += _row_funding(row, notional)

    if exit_price_f is None:
        # Max hold time reached — exit at last close with taker fee
        last = post_entry.iloc[-1] if not post_entry.empty else candles.iloc[-1]
        exit_price_f = float(last["close"])
        exit_reason  = "max_hold_time"
        exit_fee_bps = config.taker_fee_bps
        exit_bar_idx = len(post_entry) - 1

    exit_fill_d = Decimal(f"{exit_price_f:.2f}")
    exit_notional = Decimal(f"{exit_price_f * qty:.2f}")
    exit_fee = exit_notional * exit_fee_bps * _BPS

    side_sign = Decimal("1") if is_long else Decimal("-1")
    gross_pnl = (exit_fill_d - entry_fill_d) * Decimal(f"{qty:.{8}f}") * side_sign
    total_fees = (entry_fee + exit_fee).quantize(Decimal("0.01"))
    net_pnl    = (gross_pnl - total_fees - funding_cost).quantize(Decimal("0.01"))

    exit_ts = _bar_ts(
        post_entry if not post_entry.empty else candles,
        exit_bar_idx,
        actual_entry_ts,
        fallback_offset_minutes=intent.max_hold_minutes,
    )
    # Guarantee exit_ts > entry_ts (contract requirement)
    if exit_ts <= actual_entry_ts:
        exit_ts = actual_entry_ts + timedelta(minutes=1)

    return TradeOutcome(
        signal_id=intent.signal_id,
        intent_id=intent.intent_id,
        venue=intent.venue,
        symbol=intent.symbol,
        timeframe=timeframe,
        side=intent.side,
        entry_ts=actual_entry_ts,
        exit_ts=exit_ts,
        entry_price=entry_fill_d,
        exit_price=exit_fill_d,
        quantity=Decimal(f"{qty:.8f}"),
        gross_pnl=gross_pnl.quantize(Decimal("0.01")),
        total_fees=total_fees,
        funding_cost=funding_cost.quantize(Decimal("0.01")),
        net_pnl=net_pnl,
        initial_risk_amount=intent.risk_amount,
        exit_reason=exit_reason,
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        feature_version=feature_version,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _bar_minutes(candles: pd.DataFrame) -> int:
    if len(candles) < 2:
        return 60
    try:
        t0 = pd.Timestamp(candles.iloc[0]["open_time"])
        t1 = pd.Timestamp(candles.iloc[1]["open_time"])
        minutes = int((t1 - t0).total_seconds() / 60)
        return max(1, minutes)
    except Exception:
        return 60


def _bar_ts(candles: pd.DataFrame, idx: int, base_ts: datetime, fallback_offset_minutes: int = 0) -> datetime:
    try:
        row = candles.iloc[idx]
        ts = pd.Timestamp(row["open_time"])
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return ts.to_pydatetime()
    except Exception:
        return base_ts + timedelta(minutes=fallback_offset_minutes)


def _compute_funding(candles: pd.DataFrame, notional: float) -> Decimal:
    if "funding_rate" not in candles.columns:
        return Decimal("0")
    total = Decimal("0")
    for _, row in candles.iterrows():
        total += _row_funding(row, notional)
    return total


def _row_funding(row: pd.Series, notional: float) -> Decimal:
    if "funding_rate" not in row.index:
        return Decimal("0")
    rate = row["funding_rate"]
    if rate is None or (isinstance(rate, float) and np.isnan(rate)):
        return Decimal("0")
    return Decimal(f"{float(rate) * notional:.4f}")
