"""
Order state machine for the execution agent.

Eleven states cover the lifecycle of an order from local intent to terminal
outcome. Transitions are explicit; unlisted (state, event) pairs raise
InvalidTransitionError so silent state corruption is impossible.

Terminal states (FILLED, CANCELED, REJECTED, EXPIRED, RECONCILIATION_REQUIRED)
have no outgoing transitions. RECONCILIATION_REQUIRED is the explicit "we lost
track — reconcile against the exchange before acting" state used when an
acknowledgement times out or a cancel request fails.
"""

from __future__ import annotations

from enum import Enum


class OrderState(Enum):
    PLANNED = "planned"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class OrderEvent(Enum):
    SUBMIT = "submit"
    ACK = "ack"
    OPEN_IN_BOOK = "open_in_book"
    PARTIAL_FILL = "partial_fill"
    FULL_FILL = "full_fill"
    REJECT = "reject"
    CANCEL_REQUEST = "cancel_request"
    CANCEL_CONFIRMED = "cancel_confirmed"
    EXPIRE = "expire"
    TIMEOUT = "timeout"
    CANCEL_FAILED = "cancel_failed"


TERMINAL_STATES: frozenset[OrderState] = frozenset({
    OrderState.FILLED,
    OrderState.CANCELED,
    OrderState.REJECTED,
    OrderState.EXPIRED,
    OrderState.RECONCILIATION_REQUIRED,
})


_TRANSITIONS: dict[tuple[OrderState, OrderEvent], OrderState] = {
    (OrderState.PLANNED, OrderEvent.SUBMIT): OrderState.SUBMITTED,

    (OrderState.SUBMITTED, OrderEvent.ACK): OrderState.ACKNOWLEDGED,
    (OrderState.SUBMITTED, OrderEvent.REJECT): OrderState.REJECTED,
    (OrderState.SUBMITTED, OrderEvent.TIMEOUT): OrderState.RECONCILIATION_REQUIRED,

    (OrderState.ACKNOWLEDGED, OrderEvent.OPEN_IN_BOOK): OrderState.OPEN,
    (OrderState.ACKNOWLEDGED, OrderEvent.FULL_FILL): OrderState.FILLED,
    (OrderState.ACKNOWLEDGED, OrderEvent.PARTIAL_FILL): OrderState.PARTIALLY_FILLED,
    (OrderState.ACKNOWLEDGED, OrderEvent.REJECT): OrderState.REJECTED,

    (OrderState.OPEN, OrderEvent.FULL_FILL): OrderState.FILLED,
    (OrderState.OPEN, OrderEvent.PARTIAL_FILL): OrderState.PARTIALLY_FILLED,
    (OrderState.OPEN, OrderEvent.CANCEL_REQUEST): OrderState.CANCEL_REQUESTED,
    (OrderState.OPEN, OrderEvent.EXPIRE): OrderState.EXPIRED,

    (OrderState.PARTIALLY_FILLED, OrderEvent.FULL_FILL): OrderState.FILLED,
    (OrderState.PARTIALLY_FILLED, OrderEvent.CANCEL_REQUEST): OrderState.CANCEL_REQUESTED,
    (OrderState.PARTIALLY_FILLED, OrderEvent.EXPIRE): OrderState.EXPIRED,

    # Race condition: cancel sent, but order filled before cancel took effect.
    (OrderState.CANCEL_REQUESTED, OrderEvent.CANCEL_CONFIRMED): OrderState.CANCELED,
    (OrderState.CANCEL_REQUESTED, OrderEvent.FULL_FILL): OrderState.FILLED,
    (OrderState.CANCEL_REQUESTED, OrderEvent.CANCEL_FAILED): OrderState.RECONCILIATION_REQUIRED,
}


class InvalidTransitionError(Exception):
    def __init__(self, from_state: OrderState, event: OrderEvent) -> None:
        super().__init__(
            f"Invalid transition: state={from_state.value} event={event.value}"
        )
        self.from_state = from_state
        self.event = event


def transition(from_state: OrderState, event: OrderEvent) -> OrderState:
    key = (from_state, event)
    if key not in _TRANSITIONS:
        raise InvalidTransitionError(from_state, event)
    return _TRANSITIONS[key]


def is_terminal(state: OrderState) -> bool:
    return state in TERMINAL_STATES


def valid_events(from_state: OrderState) -> frozenset[OrderEvent]:
    return frozenset(event for (s, event) in _TRANSITIONS.keys() if s == from_state)
