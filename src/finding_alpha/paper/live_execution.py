"""
Live execution wiring for the paper runtime.

Bridges Phase 8 paper pipeline to Phase 10 ExecutionAgent. When the runtime
config has execution_mode='live', signals that pass the risk gate are
submitted to Bybit instead of being simulated. The runtime polls exchange
truth every bar and reconstructs PaperTrade records when positions close.

Exchange-managed:
  - Entry (limit order with deterministic orderLinkId)
  - Stop (stop_market reduce-only, submitted after entry fills)

Runtime-managed (no native Bybit support for arbitrary-minute expiry):
  - Take-profit at target_price — cancel stop + submit reduce-only market close
  - Max-hold timeout at max_exit_ts — cancel stop + submit reduce-only market close

The runtime persists an opaque live_plan_ref dict on PaperState. This module
owns its schema and provides serialize/deserialize. The dict has the shape:

    {
      "schema_version": "1.0",
      "plan_state": {...},        # PlanState (execution_agent dataclass) as dict
      "paper_context": {...},     # PaperContext (this module) as dict
    }
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from finding_alpha.contracts.trading import (
    OrderEntry,
    OrderPlan,
    PortfolioIntent,
)
from finding_alpha.execution.bybit_client import BybitClient
from finding_alpha.execution.execution_agent import (
    LEG_ENTRY,
    LEG_STOP,
    ExecutionAgent,
    LegState,
    PlanState,
)
from finding_alpha.execution.order_state import OrderState, is_terminal

LIVE_PLAN_REF_SCHEMA = "1.0"

CLOSE_REASON_TARGET = "take_profit"
CLOSE_REASON_TIMEOUT = "max_hold_time"
CLOSE_REASON_STOP = "stop_loss"
CLOSE_REASON_UNKNOWN = "unknown_close"

MAX_LINK_ID_LEN = 36


# ── Paper-side context persisted alongside PlanState ─────────────────────────


@dataclass
class PaperContext:
    """Paper-side context needed to reconstruct a PaperTrade when the plan
    closes. Mutated as the plan progresses: stamp entry_filled_at when fill
    detected, stamp close_requested_at when runtime initiates exit."""

    signal_id: str
    strategy_id: str
    strategy_version: str
    feature_version: str
    intent_id: str
    side: str                       # "long" / "short" (paper-side, matches PaperTrade)
    entry_price: Decimal            # limit price submitted to exchange
    stop_price: Decimal
    target_price: Decimal
    quantity: Decimal
    notional: Decimal
    risk_amount: Decimal
    max_exit_ts: datetime
    entry_submitted_at: datetime
    entry_filled_at: Optional[datetime] = None
    close_requested_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    close_link_id: Optional[str] = None


# ── Plan construction ────────────────────────────────────────────────────────


def build_plan_from_intent(intent: PortfolioIntent, now: datetime) -> OrderPlan:
    """Translate an approved PortfolioIntent into an OrderPlan ready for the
    ExecutionAgent. Short intents map to a sell entry + buy stop; long intents
    map to the opposite."""
    entry_side = "sell" if intent.side == "short" else "buy"
    stop_side = "buy" if intent.side == "short" else "sell"

    entry = OrderEntry(
        order_type=intent.entry_type,
        side=entry_side,
        quantity=intent.quantity,
        price=intent.entry_price,
        time_in_force=intent.time_in_force,
        reduce_only=False,
    )
    stop = OrderEntry(
        order_type="stop_market",
        side=stop_side,
        quantity=intent.quantity,
        trigger_price=intent.stop_price,
        reduce_only=True,
    )
    return OrderPlan(
        approved_intent_id=intent.intent_id,
        entry_order=entry,
        stop_order=stop,
        created_at=now,
    )


# ── Serialization ────────────────────────────────────────────────────────────


def _serialize_leg(leg: LegState) -> dict:
    return {
        "link_id": leg.link_id,
        "state": leg.state.value,
        "venue_order_id": leg.venue_order_id,
        "side": leg.side,
        "order_type": leg.order_type,
        "qty": leg.qty,
        "price": leg.price,
        "trigger_price": leg.trigger_price,
        "reduce_only": leg.reduce_only,
    }


def _deserialize_leg(d: dict) -> LegState:
    return LegState(
        link_id=d["link_id"],
        state=OrderState(d["state"]),
        venue_order_id=d.get("venue_order_id"),
        side=d.get("side", ""),
        order_type=d.get("order_type", ""),
        qty=d.get("qty", ""),
        price=d.get("price"),
        trigger_price=d.get("trigger_price"),
        reduce_only=d.get("reduce_only", False),
    )


def _serialize_plan_state(plan_state: PlanState) -> dict:
    return {
        "plan_id": plan_state.plan_id,
        "intent_id": plan_state.intent_id,
        "symbol": plan_state.symbol,
        "side": plan_state.side,
        "legs": {name: _serialize_leg(leg) for name, leg in plan_state.legs.items()},
    }


def _deserialize_plan_state(d: dict) -> PlanState:
    state = PlanState(
        plan_id=d["plan_id"],
        intent_id=d["intent_id"],
        symbol=d["symbol"],
        side=d["side"],
    )
    state.legs = {name: _deserialize_leg(leg_d) for name, leg_d in d["legs"].items()}
    return state


def _serialize_paper_context(ctx: PaperContext) -> dict:
    def _dec(v: Optional[Decimal]) -> Optional[str]:
        return str(v) if v is not None else None

    def _ts(v: Optional[datetime]) -> Optional[str]:
        return v.isoformat() if v is not None else None

    return {
        "signal_id": ctx.signal_id,
        "strategy_id": ctx.strategy_id,
        "strategy_version": ctx.strategy_version,
        "feature_version": ctx.feature_version,
        "intent_id": ctx.intent_id,
        "side": ctx.side,
        "entry_price": _dec(ctx.entry_price),
        "stop_price": _dec(ctx.stop_price),
        "target_price": _dec(ctx.target_price),
        "quantity": _dec(ctx.quantity),
        "notional": _dec(ctx.notional),
        "risk_amount": _dec(ctx.risk_amount),
        "max_exit_ts": _ts(ctx.max_exit_ts),
        "entry_submitted_at": _ts(ctx.entry_submitted_at),
        "entry_filled_at": _ts(ctx.entry_filled_at),
        "close_requested_at": _ts(ctx.close_requested_at),
        "close_reason": ctx.close_reason,
        "close_link_id": ctx.close_link_id,
    }


def _deserialize_paper_context(d: dict) -> PaperContext:
    def _dec(key: str) -> Optional[Decimal]:
        v = d.get(key)
        return Decimal(v) if v is not None else None

    def _ts(key: str) -> Optional[datetime]:
        v = d.get(key)
        if v is None:
            return None
        dt = datetime.fromisoformat(v)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    return PaperContext(
        signal_id=d["signal_id"],
        strategy_id=d["strategy_id"],
        strategy_version=d["strategy_version"],
        feature_version=d["feature_version"],
        intent_id=d["intent_id"],
        side=d["side"],
        entry_price=_dec("entry_price"),
        stop_price=_dec("stop_price"),
        target_price=_dec("target_price"),
        quantity=_dec("quantity"),
        notional=_dec("notional"),
        risk_amount=_dec("risk_amount"),
        max_exit_ts=_ts("max_exit_ts"),
        entry_submitted_at=_ts("entry_submitted_at"),
        entry_filled_at=_ts("entry_filled_at"),
        close_requested_at=_ts("close_requested_at"),
        close_reason=d.get("close_reason"),
        close_link_id=d.get("close_link_id"),
    )


def make_live_plan_ref(plan_state: PlanState, ctx: PaperContext) -> dict:
    return {
        "schema_version": LIVE_PLAN_REF_SCHEMA,
        "plan_state": _serialize_plan_state(plan_state),
        "paper_context": _serialize_paper_context(ctx),
    }


def parse_live_plan_ref(ref: dict) -> tuple[PlanState, PaperContext]:
    plan_state = _deserialize_plan_state(ref["plan_state"])
    ctx = _deserialize_paper_context(ref["paper_context"])
    return plan_state, ctx


# ── Active operations ────────────────────────────────────────────────────────


def submit_entry_live(
    agent: ExecutionAgent,
    plan: OrderPlan,
    intent: PortfolioIntent,
) -> PlanState:
    return agent.submit_plan(plan, intent)


def poll_live_legs(agent: ExecutionAgent, plan_state: PlanState) -> PlanState:
    """Reconcile every non-terminal leg against exchange truth."""
    for leg_name in list(plan_state.legs.keys()):
        leg = plan_state.legs[leg_name]
        if not is_terminal(leg.state):
            agent.reconcile_leg(plan_state, leg_name)
    return plan_state


def entry_just_filled(plan_state: PlanState, ctx: PaperContext) -> bool:
    """Entry leg is filled or partially filled, and we haven't yet stamped
    the fill time. Used to trigger one-shot post-fill actions."""
    entry = plan_state.legs.get(LEG_ENTRY)
    if entry is None:
        return False
    is_filled = entry.state in (OrderState.FILLED, OrderState.PARTIALLY_FILLED)
    return is_filled and ctx.entry_filled_at is None


def stop_needs_submission(plan_state: PlanState) -> bool:
    """Entry filled and no stop leg in plan yet."""
    entry = plan_state.legs.get(LEG_ENTRY)
    if entry is None:
        return False
    if entry.state not in (OrderState.FILLED, OrderState.PARTIALLY_FILLED):
        return False
    return LEG_STOP not in plan_state.legs


def submit_stop_live(
    agent: ExecutionAgent,
    plan_state: PlanState,
    plan: OrderPlan,
) -> PlanState:
    return agent.submit_stop(plan_state, plan)


def target_breached(
    plan_state: PlanState,
    ctx: PaperContext,
    mark_price: Decimal,
) -> bool:
    if ctx.close_requested_at is not None:
        return False
    if ctx.entry_filled_at is None:
        return False
    if ctx.side == "short":
        return mark_price <= ctx.target_price
    return mark_price >= ctx.target_price


def timeout_breached(ctx: PaperContext, now: datetime) -> bool:
    if ctx.close_requested_at is not None:
        return False
    if ctx.entry_filled_at is None:
        return False
    return now >= ctx.max_exit_ts


def _make_close_link_id(plan_id: str) -> str:
    base = f"{plan_id}-close"
    if len(base) <= MAX_LINK_ID_LEN:
        return base
    keep = MAX_LINK_ID_LEN - len("-close")
    return f"{plan_id[:keep]}-close"


def submit_runtime_close(
    agent: ExecutionAgent,
    plan_state: PlanState,
    ctx: PaperContext,
    reason: str,
    now: datetime,
) -> None:
    """Cancel the exchange stop (best-effort), then submit a reduce-only
    market order to close the position. Mutates ctx with close metadata.

    Race window: the stop may trigger between our cancel and the close. The
    reduce_only=True flag on both prevents overfill — Bybit will reject the
    close as zero-size if the stop already cleared the position.
    """
    stop = plan_state.legs.get(LEG_STOP)
    if stop is not None and not is_terminal(stop.state):
        try:
            agent.cancel_leg(plan_state, LEG_STOP)
        except Exception:
            pass

    close_side = "Buy" if ctx.side == "short" else "Sell"
    close_link_id = _make_close_link_id(plan_state.plan_id)

    agent._client.create_order(  # noqa: SLF001 — see module-level comment
        symbol=plan_state.symbol,
        side=close_side,
        order_type="Market",
        qty=str(ctx.quantity),
        order_link_id=close_link_id,
        reduce_only=True,
    )
    ctx.close_requested_at = now
    ctx.close_reason = reason
    ctx.close_link_id = close_link_id


# ── Close detection + trade reconstruction ───────────────────────────────────


def query_position_state(
    client: BybitClient,
    symbol: str,
) -> tuple[Decimal, Optional[str], Optional[Decimal]]:
    """Return (size, side, mark_price). Mark price is None when flat."""
    result = client.query_positions(symbol=symbol)
    rows = result.get("list", []) or []
    for row in rows:
        if row.get("symbol") != symbol:
            continue
        try:
            size = Decimal(row.get("size", "0") or "0")
        except Exception:
            size = Decimal("0")
        if size > 0:
            return size, row.get("side"), _maybe_decimal(row.get("markPrice"))
    return Decimal("0"), None, None


def rebuild_stop_only_plan(plan_state: PlanState, ctx: PaperContext) -> OrderPlan:
    """Reconstruct an OrderPlan sufficient for agent.submit_stop after a
    restart. submit_stop reads only plan.order_plan_id and plan.stop_order;
    the entry_order field is a required-but-unused placeholder."""
    stop_side = "buy" if ctx.side == "short" else "sell"
    entry_side = "sell" if ctx.side == "short" else "buy"

    entry_placeholder = OrderEntry(
        order_type="limit",
        side=entry_side,
        quantity=ctx.quantity,
        price=ctx.entry_price,
    )
    stop = OrderEntry(
        order_type="stop_market",
        side=stop_side,
        quantity=ctx.quantity,
        trigger_price=ctx.stop_price,
        reduce_only=True,
    )
    return OrderPlan(
        order_plan_id=plan_state.plan_id,
        approved_intent_id=ctx.intent_id,
        entry_order=entry_placeholder,
        stop_order=stop,
        created_at=ctx.entry_submitted_at,
    )


def trade_is_closed(ctx: PaperContext, position_size: Decimal) -> bool:
    """A plan whose entry filled and whose exchange position is now zero."""
    return ctx.entry_filled_at is not None and position_size == Decimal("0")


def determine_exit_reason(plan_state: PlanState, ctx: PaperContext) -> str:
    if ctx.close_reason is not None:
        return ctx.close_reason
    stop = plan_state.legs.get(LEG_STOP)
    if stop is not None and stop.state == OrderState.FILLED:
        return CLOSE_REASON_STOP
    return CLOSE_REASON_UNKNOWN


def fetch_entry_fill_details(
    client: BybitClient,
    plan_state: PlanState,
) -> tuple[Optional[Decimal], Optional[Decimal], Optional[datetime], Optional[Decimal]]:
    """Return (avg_price, cum_qty, fill_ts, cum_fee) for the entry leg."""
    entry = plan_state.legs.get(LEG_ENTRY)
    if entry is None:
        return None, None, None, None
    return _query_fill_details(client, plan_state.symbol, entry.link_id)


def fetch_exit_fill_details(
    client: BybitClient,
    plan_state: PlanState,
    ctx: PaperContext,
) -> tuple[Optional[Decimal], Optional[datetime], Optional[Decimal]]:
    """Return (avg_price, fill_ts, cum_fee) for whichever leg actually closed
    the position. Prefers the runtime close leg (if present and filled),
    otherwise falls back to the stop leg."""
    candidates: list[str] = []
    if ctx.close_link_id:
        candidates.append(ctx.close_link_id)
    stop = plan_state.legs.get(LEG_STOP)
    if stop is not None:
        candidates.append(stop.link_id)

    for link_id in candidates:
        price, _qty, fill_ts, fee = _query_fill_details(client, plan_state.symbol, link_id)
        if price is not None:
            return price, fill_ts, fee
    return None, None, None


def _query_fill_details(
    client: BybitClient,
    symbol: str,
    link_id: str,
) -> tuple[Optional[Decimal], Optional[Decimal], Optional[datetime], Optional[Decimal]]:
    result = client.query_order(symbol=symbol, order_link_id=link_id)
    rows = result.get("list", []) or []
    if not rows:
        return None, None, None, None
    row = rows[0]
    if row.get("orderStatus") not in ("Filled", "PartiallyFilled"):
        return None, None, None, None

    avg_price = _maybe_decimal(row.get("avgPrice") or row.get("price"))
    cum_qty = _maybe_decimal(row.get("cumExecQty"))
    cum_fee = _maybe_decimal(row.get("cumExecFee"))
    fill_ts = _maybe_ms_to_datetime(row.get("updatedTime") or row.get("createdTime"))
    return avg_price, cum_qty, fill_ts, cum_fee


def _maybe_decimal(v) -> Optional[Decimal]:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def _maybe_ms_to_datetime(v) -> Optional[datetime]:
    if v is None:
        return None
    try:
        ms = int(v)
    except Exception:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
