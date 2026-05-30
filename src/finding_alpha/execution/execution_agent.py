"""
Execution agent.

Sits between an approved OrderPlan and the Bybit private API. Job:
  1. Submit the entry leg with a deterministic orderLinkId (idempotency key).
  2. Track each leg through the order_state machine.
  3. Submit the protective stop after entry is confirmed (no unprotected
     exposure — strategies in scope are short-only futures).
  4. Map Bybit orderStatus values back to local OrderEvents so polling /
     websocket updates drive the state machine consistently.
  5. Reconcile by querying orderLinkId when local state diverges.

The agent is synchronous and stateless across calls — callers hold the
PlanState dict between invocations. Logging and persistence happen in the
caller; this file only mutates state and talks to Bybit.

Take-profit legs are not implemented: the two production strategies exit
on stop or max_hold_time, so TP plumbing would be dead code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from finding_alpha.contracts.trading import OrderPlan, PortfolioIntent
from finding_alpha.execution.bybit_client import BybitAPIError, BybitClient
from finding_alpha.execution.order_state import (
    InvalidTransitionError,
    OrderEvent,
    OrderState,
    is_terminal,
    transition,
)

LEG_ENTRY = "entry"
LEG_STOP = "stop"

MAX_LINK_ID_LEN = 36  # Bybit constraint

# Bybit orderStatus → our OrderEvent. Anything outside this table forces a
# reconciliation rather than blindly stepping the state machine.
_BYBIT_STATUS_TO_EVENT: dict[str, OrderEvent] = {
    "New": OrderEvent.OPEN_IN_BOOK,
    "PartiallyFilled": OrderEvent.PARTIAL_FILL,
    "Filled": OrderEvent.FULL_FILL,
    "Cancelled": OrderEvent.CANCEL_CONFIRMED,
    "Rejected": OrderEvent.REJECT,
    "Untriggered": OrderEvent.OPEN_IN_BOOK,
    "Triggered": OrderEvent.OPEN_IN_BOOK,
    "Deactivated": OrderEvent.CANCEL_CONFIRMED,
}

# For reconcile(): we override local state with exchange truth directly,
# bypassing the step-by-step transition graph. Used when local state is
# already RECONCILIATION_REQUIRED or otherwise out of sync.
_BYBIT_STATUS_TO_STATE: dict[str, OrderState] = {
    "New": OrderState.OPEN,
    "Untriggered": OrderState.OPEN,
    "Triggered": OrderState.OPEN,
    "PartiallyFilled": OrderState.PARTIALLY_FILLED,
    "Filled": OrderState.FILLED,
    "Cancelled": OrderState.CANCELED,
    "Rejected": OrderState.REJECTED,
    "Deactivated": OrderState.CANCELED,
}


@dataclass
class LegState:
    link_id: str
    state: OrderState
    venue_order_id: Optional[str] = None
    side: str = ""           # Bybit side string: "Buy" / "Sell"
    order_type: str = ""     # Bybit type string: "Market" / "Limit"
    qty: str = ""
    price: Optional[str] = None
    trigger_price: Optional[str] = None
    reduce_only: bool = False


@dataclass
class PlanState:
    plan_id: str
    intent_id: str
    symbol: str
    side: str                # "long" / "short" — semantic side of the trade
    legs: dict[str, LegState] = field(default_factory=dict)

    @property
    def entry(self) -> LegState:
        return self.legs[LEG_ENTRY]

    @property
    def stop(self) -> Optional[LegState]:
        return self.legs.get(LEG_STOP)


def _link_id(plan_id: str, leg: str) -> str:
    """Deterministic Bybit orderLinkId. Same plan_id + leg = same id forever.

    This is the idempotency key. If a submit times out, we can query by
    this id and discover whether the order made it before resubmitting.
    """
    candidate = f"{plan_id}-{leg}"
    if len(candidate) <= MAX_LINK_ID_LEN:
        return candidate
    keep = MAX_LINK_ID_LEN - len(leg) - 1
    return f"{plan_id[:keep]}-{leg}"


def _bybit_side(entry_side: str) -> str:
    if entry_side == "buy":
        return "Buy"
    if entry_side == "sell":
        return "Sell"
    raise ValueError(f"unknown side: {entry_side}")


def _bybit_order_type(order_type: str) -> str:
    if order_type == "market":
        return "Market"
    if order_type in ("limit", "post_only_limit"):
        return "Limit"
    if order_type == "stop_market":
        return "Market"
    if order_type == "stop_limit":
        return "Limit"
    raise ValueError(f"unknown order_type: {order_type}")


def _trigger_direction_for_stop(stop_side: str) -> int:
    # Bybit triggerDirection: 1 = trigger when price rises through trigger,
    # 2 = trigger when price falls through trigger. A short position's stop
    # is a Buy order triggered on a rise; a long position's stop is a Sell
    # triggered on a fall.
    return 1 if stop_side == "Buy" else 2


class ExecutionAgent:
    def __init__(self, client: BybitClient) -> None:
        self._client = client

    # ── Entry leg ─────────────────────────────────────────────────────────────

    def submit_plan(self, plan: OrderPlan, intent: PortfolioIntent) -> PlanState:
        """Submit the entry leg of an OrderPlan.

        Returns a PlanState with the entry leg either ACKNOWLEDGED (Bybit
        accepted the order) or REJECTED (Bybit refused it). Caller drives
        subsequent transitions via apply_bybit_status() or reconcile_leg().
        """
        state = PlanState(
            plan_id=plan.order_plan_id,
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            side=intent.side,
        )
        entry = plan.entry_order
        leg = LegState(
            link_id=_link_id(plan.order_plan_id, LEG_ENTRY),
            state=OrderState.PLANNED,
            side=_bybit_side(entry.side),
            order_type=_bybit_order_type(entry.order_type),
            qty=str(entry.quantity),
            price=str(entry.price) if entry.price is not None else None,
            reduce_only=entry.reduce_only,
        )
        state.legs[LEG_ENTRY] = leg

        leg.state = transition(leg.state, OrderEvent.SUBMIT)
        try:
            response = self._client.create_order(
                symbol=intent.symbol,
                side=leg.side,
                order_type=leg.order_type,
                qty=leg.qty,
                price=leg.price,
                order_link_id=leg.link_id,
                time_in_force=entry.time_in_force,
                reduce_only=leg.reduce_only,
            )
        except BybitAPIError:
            leg.state = transition(leg.state, OrderEvent.REJECT)
            raise
        leg.venue_order_id = response.get("orderId", "") or None
        leg.state = transition(leg.state, OrderEvent.ACK)
        return state

    # ── Stop leg ──────────────────────────────────────────────────────────────

    def submit_stop(self, state: PlanState, plan: OrderPlan) -> PlanState:
        """Submit the protective stop. Safe to call multiple times — a no-op
        once a non-terminal stop leg already exists in state."""
        existing = state.legs.get(LEG_STOP)
        if existing is not None and not is_terminal(existing.state):
            return state

        stop = plan.stop_order
        leg = LegState(
            link_id=_link_id(plan.order_plan_id, LEG_STOP),
            state=OrderState.PLANNED,
            side=_bybit_side(stop.side),
            order_type=_bybit_order_type(stop.order_type),
            qty=str(stop.quantity),
            price=str(stop.price) if stop.price is not None else None,
            trigger_price=str(stop.trigger_price) if stop.trigger_price is not None else None,
            reduce_only=True,
        )
        state.legs[LEG_STOP] = leg

        leg.state = transition(leg.state, OrderEvent.SUBMIT)
        try:
            response = self._client.create_order(
                symbol=state.symbol,
                side=leg.side,
                order_type=leg.order_type,
                qty=leg.qty,
                price=leg.price,
                order_link_id=leg.link_id,
                time_in_force=stop.time_in_force,
                reduce_only=True,
                trigger_price=leg.trigger_price,
                trigger_direction=_trigger_direction_for_stop(leg.side),
            )
        except BybitAPIError:
            leg.state = transition(leg.state, OrderEvent.REJECT)
            raise
        leg.venue_order_id = response.get("orderId", "") or None
        leg.state = transition(leg.state, OrderEvent.ACK)
        return state

    # ── Status updates from Bybit ─────────────────────────────────────────────

    def apply_bybit_status(self, state: PlanState, leg_name: str, bybit_status: str) -> PlanState:
        """Translate a Bybit orderStatus into a state machine transition.

        Unknown statuses, or transitions the machine refuses, push the leg
        into RECONCILIATION_REQUIRED rather than raising — the caller can
        then trigger reconcile_leg() to ask the exchange for ground truth.
        """
        leg = state.legs.get(leg_name)
        if leg is None:
            raise KeyError(f"unknown leg: {leg_name}")
        if is_terminal(leg.state):
            return state

        event = _BYBIT_STATUS_TO_EVENT.get(bybit_status)
        if event is None:
            leg.state = OrderState.RECONCILIATION_REQUIRED
            return state
        try:
            leg.state = transition(leg.state, event)
        except InvalidTransitionError:
            leg.state = OrderState.RECONCILIATION_REQUIRED
        return state

    # ── Cancel ────────────────────────────────────────────────────────────────

    def cancel_leg(self, state: PlanState, leg_name: str) -> PlanState:
        """Request cancellation of a leg. Local state moves to CANCEL_REQUESTED
        before the API call so a crash mid-call still records intent."""
        leg = state.legs.get(leg_name)
        if leg is None:
            raise KeyError(f"unknown leg: {leg_name}")
        if is_terminal(leg.state):
            return state

        leg.state = transition(leg.state, OrderEvent.CANCEL_REQUEST)
        try:
            self._client.cancel_order(
                symbol=state.symbol,
                order_link_id=leg.link_id,
            )
        except BybitAPIError:
            leg.state = transition(leg.state, OrderEvent.CANCEL_FAILED)
            raise
        return state

    # ── Reconcile (ground-truth recovery) ─────────────────────────────────────

    def reconcile_leg(self, state: PlanState, leg_name: str) -> PlanState:
        """Query Bybit by orderLinkId and force local state to match exchange
        truth. Used when state is RECONCILIATION_REQUIRED or after a restart."""
        leg = state.legs.get(leg_name)
        if leg is None:
            raise KeyError(f"unknown leg: {leg_name}")

        result = self._client.query_order(
            symbol=state.symbol,
            order_link_id=leg.link_id,
        )
        rows = result.get("list", []) or []
        if not rows:
            # Exchange has no record — the order never made it.
            leg.state = OrderState.REJECTED
            return state
        row = rows[0]
        bybit_status = row.get("orderStatus", "")
        forced = _BYBIT_STATUS_TO_STATE.get(bybit_status)
        if forced is not None:
            leg.state = forced
            venue_id = row.get("orderId")
            if venue_id:
                leg.venue_order_id = venue_id
        return state
