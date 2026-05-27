"""
Portfolio Agent.

size_intent(signal, equity, config, now) → PortfolioIntent | None

Sizing rules:
  risk_amount   = equity × risk_pct
  quantity      = risk_amount / stop_distance   (in base currency)
  quantity      floored to venue qty_precision  (never rounds up)
  notional      = quantity × entry_price
  leverage      = notional / equity  (capped at max_leverage by scaling qty down)

Rejected when:
  - stop_distance is zero
  - quantity rounds down to zero
  - notional < min_notional_usdt
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.contracts.trading import OrderEntry, OrderPlan, PortfolioIntent, TargetLevel


class PortfolioConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    risk_pct: Decimal = Decimal("0.01")          # 1% of equity per trade
    max_leverage: Decimal = Decimal("10")
    min_notional_usdt: Decimal = Decimal("10")
    qty_precision: int = 3                        # decimal places, e.g. 3 → 0.001 BTC
    price_precision: int = 2
    taker_fee_bps: Decimal = Decimal("5.5")
    slippage_bps: Decimal = Decimal("5")
    max_hold_minutes: int = 480                   # default 8 h


def _floor_qty(raw: float, precision: int) -> Decimal:
    factor = 10 ** precision
    return Decimal(str(math.floor(raw * factor) / factor))


def size_intent(
    signal: SignalCandidate,
    equity: Decimal,
    config: PortfolioConfig,
    now: datetime,
) -> Optional[PortfolioIntent]:
    entry = float(signal.entry_reference)
    stop  = float(signal.invalidation_price)
    stop_distance = abs(entry - stop)

    if stop_distance == 0:
        return None

    risk_amount = float(equity) * float(config.risk_pct)
    qty_raw = risk_amount / stop_distance

    # Cap by leverage before flooring
    max_qty_by_leverage = float(equity) * float(config.max_leverage) / entry
    qty_capped = min(qty_raw, max_qty_by_leverage)

    quantity = _floor_qty(qty_capped, config.qty_precision)
    if quantity <= 0:
        return None

    notional = quantity * Decimal(f"{entry:.{config.price_precision}f}")

    if notional < config.min_notional_usdt:
        return None

    leverage = (notional / equity).quantize(Decimal("0.01"))
    actual_risk = (quantity * Decimal(f"{stop_distance:.{config.price_precision}f}")).quantize(Decimal("0.01"))

    if actual_risk <= Decimal("0"):
        return None

    target_plan = _build_target_plan(signal.target_prices)

    entry_price_d = Decimal(f"{entry:.{config.price_precision}f}")

    return PortfolioIntent(
        signal_id=signal.signal_id,
        venue=signal.venue,
        symbol=signal.symbol,
        side=signal.side,
        entry_type="limit",
        entry_price=entry_price_d,
        stop_price=signal.invalidation_price,
        target_plan=target_plan,
        risk_amount=actual_risk.quantize(Decimal("0.01")),
        quantity=quantity,
        notional=notional.quantize(Decimal("0.01")),
        leverage=leverage,
        max_slippage_bps=config.slippage_bps,
        time_in_force="GTC",
        max_hold_minutes=config.max_hold_minutes,
        created_at=now,
    )


def _build_target_plan(target_prices: list[Decimal]) -> list[TargetLevel]:
    if not target_prices:
        return []
    frac = Decimal("1") / Decimal(str(len(target_prices)))
    return [TargetLevel(price=p, quantity_fraction=frac) for p in target_prices]


def build_order_plan(intent: PortfolioIntent, now: datetime) -> OrderPlan:
    """Convert an approved PortfolioIntent into an OrderPlan ready for execution."""
    is_long = intent.side == "long"
    entry_side = "buy" if is_long else "sell"
    exit_side  = "sell" if is_long else "buy"

    entry_order = OrderEntry(
        order_type=intent.entry_type,
        side=entry_side,
        quantity=intent.quantity,
        price=intent.entry_price,
        time_in_force=intent.time_in_force,
    )
    stop_order = OrderEntry(
        order_type="stop_market",
        side=exit_side,
        quantity=intent.quantity,
        trigger_price=intent.stop_price,
        reduce_only=True,
    )
    tp_orders = [
        OrderEntry(
            order_type="limit",
            side=exit_side,
            quantity=(intent.quantity * level.quantity_fraction).quantize(
                Decimal("0.001")
            ),
            price=level.price,
            reduce_only=True,
        )
        for level in intent.target_plan
    ]
    return OrderPlan(
        approved_intent_id=intent.intent_id,
        entry_order=entry_order,
        stop_order=stop_order,
        take_profit_orders=tp_orders,
        created_at=now,
    )
