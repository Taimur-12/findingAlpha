"""
Tests for the reconciliation module.

Uses httpx.MockTransport to fake Bybit responses for both query_order and
query_positions. Local PlanState is built by hand to simulate various
post-restart / post-divergence scenarios.
"""

from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest

from finding_alpha.contracts.reason_codes import (
    EXEC_RECONCILIATION_MISMATCH,
    EXEC_UNPROTECTED_POSITION,
)
from finding_alpha.execution.bybit_client import (
    BybitClient,
    BybitClientConfig,
    TESTNET_URL,
)
from finding_alpha.execution.execution_agent import (
    LEG_ENTRY,
    LEG_STOP,
    ExecutionAgent,
    LegState,
    PlanState,
)
from finding_alpha.execution.order_state import OrderState
from finding_alpha.execution.reconciliation import (
    ACTION_HALT,
    ACTION_MARK_CLOSED,
    ACTION_REPLACE_STOP,
    KIND_GHOST_POSITION,
    KIND_MISSING_POSITION,
    KIND_STATE_MISMATCH,
    KIND_UNPROTECTED,
    find_unprotected,
    reconcile_plan,
)


def _agent(handler: Callable[[httpx.Request], httpx.Response]) -> ExecutionAgent:
    cfg = BybitClientConfig(api_key="k", api_secret="s", base_url=TESTNET_URL)
    transport = httpx.MockTransport(handler)
    http = httpx.Client(base_url=TESTNET_URL, transport=transport)
    return ExecutionAgent(BybitClient(cfg, http=http))


def _plan_state(
    entry_state: OrderState,
    stop_state: OrderState | None = None,
) -> PlanState:
    state = PlanState(
        plan_id="plan-1",
        intent_id="intent-1",
        symbol="BTCUSDT",
        side="short",
    )
    state.legs[LEG_ENTRY] = LegState(
        link_id="plan-1-entry",
        state=entry_state,
        venue_order_id="v-entry",
        side="Sell",
        order_type="Limit",
        qty="0.01",
        price="60000",
    )
    if stop_state is not None:
        state.legs[LEG_STOP] = LegState(
            link_id="plan-1-stop",
            state=stop_state,
            venue_order_id="v-stop",
            side="Buy",
            order_type="Market",
            qty="0.01",
            trigger_price="60500",
            reduce_only=True,
        )
    return state


def _ok(result: dict) -> httpx.Response:
    return httpx.Response(200, json={"retCode": 0, "retMsg": "OK", "result": result})


def _router(*, orders: dict[str, dict], position: dict) -> Callable:
    """Build a handler that routes query_order by orderLinkId and returns
    a canned position list for query_positions."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v5/order/realtime":
            link_id = request.url.params.get("orderLinkId", "")
            row = orders.get(link_id)
            return _ok({"list": [row]} if row else {"list": []})
        if path == "/v5/position/list":
            return _ok({"list": [position]} if position else {"list": []})
        raise AssertionError(f"unexpected path: {path}")
    return handler


# ── find_unprotected ──────────────────────────────────────────────────────────

def test_find_unprotected_entry_not_filled_returns_false():
    state = _plan_state(OrderState.OPEN)
    assert find_unprotected(state) is False


def test_find_unprotected_entry_filled_no_stop_returns_true():
    state = _plan_state(OrderState.FILLED)
    assert find_unprotected(state) is True


def test_find_unprotected_entry_filled_stop_live_returns_false():
    state = _plan_state(OrderState.FILLED, OrderState.OPEN)
    assert find_unprotected(state) is False


def test_find_unprotected_entry_filled_stop_canceled_returns_true():
    state = _plan_state(OrderState.FILLED, OrderState.CANCELED)
    assert find_unprotected(state) is True


def test_find_unprotected_partial_fill_no_stop_returns_true():
    state = _plan_state(OrderState.PARTIALLY_FILLED)
    assert find_unprotected(state) is True


# ── reconcile_plan ────────────────────────────────────────────────────────────

def test_reconcile_clean_state_no_divergences():
    state = _plan_state(OrderState.FILLED, OrderState.OPEN)
    handler = _router(
        orders={
            "plan-1-entry": {"orderId": "v-entry", "orderStatus": "Filled"},
            "plan-1-stop": {"orderId": "v-stop", "orderStatus": "New"},
        },
        position={"symbol": "BTCUSDT", "side": "Sell", "size": "0.01"},
    )
    agent = _agent(handler)
    report = reconcile_plan(agent, state)
    assert report.is_clean
    assert report.exchange_position_size.compare(0) == 1   # > 0
    assert report.exchange_position_side == "Sell"


def test_reconcile_detects_unprotected_position():
    state = _plan_state(OrderState.FILLED, OrderState.CANCELED)
    handler = _router(
        orders={
            "plan-1-entry": {"orderId": "v-entry", "orderStatus": "Filled"},
            "plan-1-stop": {"orderId": "v-stop", "orderStatus": "Cancelled"},
        },
        position={"symbol": "BTCUSDT", "side": "Sell", "size": "0.01"},
    )
    agent = _agent(handler)
    report = reconcile_plan(agent, state)
    kinds = [d.kind for d in report.divergences]
    assert KIND_UNPROTECTED in kinds
    unprotected = next(d for d in report.divergences if d.kind == KIND_UNPROTECTED)
    assert unprotected.reason_code == EXEC_UNPROTECTED_POSITION
    assert unprotected.recommended_action == ACTION_REPLACE_STOP
    assert report.has_critical


def test_reconcile_detects_ghost_position():
    """Exchange has a position but local state says entry never filled."""
    state = _plan_state(OrderState.OPEN)
    handler = _router(
        orders={
            "plan-1-entry": {"orderId": "v-entry", "orderStatus": "New"},
        },
        position={"symbol": "BTCUSDT", "side": "Sell", "size": "0.01"},
    )
    agent = _agent(handler)
    report = reconcile_plan(agent, state)
    kinds = [d.kind for d in report.divergences]
    assert KIND_GHOST_POSITION in kinds
    ghost = next(d for d in report.divergences if d.kind == KIND_GHOST_POSITION)
    assert ghost.recommended_action == ACTION_HALT
    assert report.has_critical


def test_reconcile_detects_missing_position():
    """Local says filled, exchange has no position (closed externally)."""
    state = _plan_state(OrderState.FILLED, OrderState.OPEN)
    handler = _router(
        orders={
            "plan-1-entry": {"orderId": "v-entry", "orderStatus": "Filled"},
            "plan-1-stop": {"orderId": "v-stop", "orderStatus": "New"},
        },
        position={},
    )
    agent = _agent(handler)
    report = reconcile_plan(agent, state)
    kinds = [d.kind for d in report.divergences]
    assert KIND_MISSING_POSITION in kinds
    missing = next(d for d in report.divergences if d.kind == KIND_MISSING_POSITION)
    assert missing.recommended_action == ACTION_MARK_CLOSED


def test_reconcile_records_state_mismatch_when_leg_state_changes():
    """Local entry says OPEN, exchange says Filled. reconcile_leg updates
    local state and records the change as STATE_MISMATCH."""
    state = _plan_state(OrderState.OPEN, OrderState.OPEN)
    handler = _router(
        orders={
            "plan-1-entry": {"orderId": "v-entry", "orderStatus": "Filled"},
            "plan-1-stop": {"orderId": "v-stop", "orderStatus": "New"},
        },
        position={"symbol": "BTCUSDT", "side": "Sell", "size": "0.01"},
    )
    agent = _agent(handler)
    report = reconcile_plan(agent, state)
    kinds = [d.kind for d in report.divergences]
    assert KIND_STATE_MISMATCH in kinds
    assert state.entry.state == OrderState.FILLED
    mismatch = next(d for d in report.divergences if d.kind == KIND_STATE_MISMATCH)
    assert mismatch.reason_code == EXEC_RECONCILIATION_MISMATCH
    assert "open -> filled" in mismatch.detail


def test_reconcile_no_stop_leg_position_open_is_unprotected():
    """No stop in local state at all (e.g., stop submission failed). Position
    is open. Must be flagged as unprotected."""
    state = _plan_state(OrderState.FILLED, stop_state=None)
    handler = _router(
        orders={
            "plan-1-entry": {"orderId": "v-entry", "orderStatus": "Filled"},
        },
        position={"symbol": "BTCUSDT", "side": "Sell", "size": "0.01"},
    )
    agent = _agent(handler)
    report = reconcile_plan(agent, state)
    assert any(d.kind == KIND_UNPROTECTED for d in report.divergences)


def test_reconcile_flat_position_with_canceled_entry_clean():
    """Entry was canceled before filling, no position, no stop. Clean state."""
    state = PlanState(plan_id="plan-1", intent_id="i", symbol="BTCUSDT", side="short")
    state.legs[LEG_ENTRY] = LegState(
        link_id="plan-1-entry",
        state=OrderState.CANCELED,
        venue_order_id="v-entry",
    )
    handler = _router(
        orders={
            "plan-1-entry": {"orderId": "v-entry", "orderStatus": "Cancelled"},
        },
        position={},
    )
    agent = _agent(handler)
    report = reconcile_plan(agent, state)
    assert report.is_clean
