"""
Tests for the Bybit V5 REST client (Phase 10 — Private API + Testnet).

All HTTP traffic is intercepted via httpx.MockTransport so no real network
calls are made. The mock handler inspects the request and returns canned
responses matching Bybit V5 envelope shape: {"retCode": 0, "result": {...}}.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Callable

import httpx
import pytest

from finding_alpha.execution.bybit_client import (
    BybitAPIError,
    BybitClient,
    BybitClientConfig,
    MAINNET_URL,
    TESTNET_URL,
    _build_query_string,
    _sign,
)
from finding_alpha.execution.order_state import (
    InvalidTransitionError,
    OrderEvent,
    OrderState,
    TERMINAL_STATES,
    is_terminal,
    transition,
    valid_events,
)


def _make_client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str = "test-key",
    api_secret: str = "test-secret",
    base_url: str = TESTNET_URL,
) -> BybitClient:
    cfg = BybitClientConfig(api_key=api_key, api_secret=api_secret, base_url=base_url)
    transport = httpx.MockTransport(handler)
    http = httpx.Client(base_url=base_url, transport=transport)
    return BybitClient(cfg, http=http)


def _ok(result: dict) -> httpx.Response:
    return httpx.Response(200, json={"retCode": 0, "retMsg": "OK", "result": result})


def _err(ret_code: int, ret_msg: str) -> httpx.Response:
    return httpx.Response(200, json={"retCode": ret_code, "retMsg": ret_msg, "result": {}})


# ── Config from env ───────────────────────────────────────────────────────────

def test_config_from_env_testnet():
    env = {
        "BYBIT_LIVE_MODE": "testnet",
        "BYBIT_TESTNET_API_KEY": "tk",
        "BYBIT_TESTNET_API_SECRET": "ts",
    }
    cfg = BybitClientConfig.from_env(env)
    assert cfg.api_key == "tk"
    assert cfg.api_secret == "ts"
    assert cfg.base_url == TESTNET_URL


def test_config_from_env_mainnet():
    env = {
        "BYBIT_LIVE_MODE": "mainnet",
        "BYBIT_LIVE_API_KEY": "mk",
        "BYBIT_LIVE_API_SECRET": "ms",
    }
    cfg = BybitClientConfig.from_env(env)
    assert cfg.base_url == MAINNET_URL


def test_config_from_env_missing_keys_raises():
    env = {"BYBIT_LIVE_MODE": "testnet"}
    with pytest.raises(RuntimeError, match="Missing Bybit credentials"):
        BybitClientConfig.from_env(env)


def test_config_from_env_unknown_mode_raises():
    env = {"BYBIT_LIVE_MODE": "demo"}
    with pytest.raises(ValueError, match="Unknown BYBIT_LIVE_MODE"):
        BybitClientConfig.from_env(env)


# ── Signing + query helpers ───────────────────────────────────────────────────

def test_sign_matches_hmac_sha256():
    expected = hmac.new(b"my-secret", b"payload-string", hashlib.sha256).hexdigest()
    assert _sign("my-secret", "payload-string") == expected


def test_build_query_string_sorts_alphabetically():
    assert _build_query_string({"symbol": "BTCUSDT", "category": "linear"}) == \
        "category=linear&symbol=BTCUSDT"


def test_build_query_string_skips_none_values():
    assert _build_query_string({"a": 1, "b": None, "c": 2}) == "a=1&c=2"


# ── Order endpoints ───────────────────────────────────────────────────────────

def test_create_order_market_sends_required_fields():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v5/order/create"
        captured["body"] = json.loads(req.content)
        captured["headers"] = dict(req.headers)
        return _ok({"orderId": "ord-1", "orderLinkId": "link-1"})

    with _make_client(handler) as c:
        result = c.create_order(
            symbol="BTCUSDT", side="Sell", order_type="Market",
            qty="0.001", order_link_id="link-1",
        )
    assert result["orderId"] == "ord-1"
    body = captured["body"]
    assert body["category"] == "linear"
    assert body["symbol"] == "BTCUSDT"
    assert body["side"] == "Sell"
    assert body["orderType"] == "Market"
    assert body["qty"] == "0.001"
    assert body["orderLinkId"] == "link-1"
    assert body["reduceOnly"] is False
    # Auth headers present (httpx normalizes header names to lowercase)
    assert "x-bapi-api-key" in captured["headers"]
    assert "x-bapi-sign" in captured["headers"]
    assert len(captured["headers"]["x-bapi-sign"]) == 64  # SHA-256 hex


def test_create_order_limit_includes_price_and_link_id():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(req.content)
        return _ok({"orderId": "ord-2"})

    with _make_client(handler) as c:
        c.create_order(
            symbol="BTCUSDT", side="Buy", order_type="Limit",
            qty="0.002", price="65000.0", order_link_id="abc",
        )
    body = captured["body"]
    assert body["price"] == "65000.0"
    assert body["orderType"] == "Limit"
    assert body["orderLinkId"] == "abc"


def test_cancel_order_by_id():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v5/order/cancel"
        captured["body"] = json.loads(req.content)
        return _ok({"orderId": "ord-3"})

    with _make_client(handler) as c:
        c.cancel_order(symbol="BTCUSDT", order_id="ord-3")
    assert captured["body"]["orderId"] == "ord-3"
    assert captured["body"]["symbol"] == "BTCUSDT"


def test_cancel_order_requires_id_or_link():
    with _make_client(lambda r: _ok({})) as c:
        with pytest.raises(ValueError, match="Provide order_id or order_link_id"):
            c.cancel_order(symbol="BTCUSDT")


def test_query_order_passes_params():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v5/order/realtime"
        captured["query"] = dict(req.url.params)
        return _ok({"list": [{"orderId": "ord-x"}]})

    with _make_client(handler) as c:
        result = c.query_order(symbol="BTCUSDT", order_id="ord-x")
    assert captured["query"]["symbol"] == "BTCUSDT"
    assert captured["query"]["orderId"] == "ord-x"
    assert result["list"][0]["orderId"] == "ord-x"


def test_query_positions_optional_symbol():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v5/position/list"
        captured["query"] = dict(req.url.params)
        return _ok({"list": []})

    with _make_client(handler) as c:
        c.query_positions()
    assert captured["query"]["settleCoin"] == "USDT"
    assert "symbol" not in captured["query"]


def test_query_wallet_balance():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v5/account/wallet-balance"
        captured["query"] = dict(req.url.params)
        return _ok({"list": [{"totalEquity": "10000"}]})

    with _make_client(handler) as c:
        result = c.query_wallet_balance()
    assert captured["query"]["accountType"] == "UNIFIED"
    assert result["list"][0]["totalEquity"] == "10000"


# ── Error handling ────────────────────────────────────────────────────────────

def test_bybit_api_error_raised_on_non_zero_ret_code():
    def handler(req: httpx.Request) -> httpx.Response:
        return _err(110007, "insufficient balance")

    with _make_client(handler) as c:
        with pytest.raises(BybitAPIError) as exc_info:
            c.create_order(symbol="BTCUSDT", side="Sell", order_type="Market", qty="0.001")
    assert exc_info.value.ret_code == 110007
    assert "insufficient balance" in str(exc_info.value)


def test_http_error_propagates():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "internal error"})

    with _make_client(handler) as c:
        with pytest.raises(httpx.HTTPStatusError):
            c.query_positions()


# ── Order state machine ──────────────────────────────────────────────────────

_HAPPY_PATH_LIMIT = [
    (OrderState.PLANNED, OrderEvent.SUBMIT, OrderState.SUBMITTED),
    (OrderState.SUBMITTED, OrderEvent.ACK, OrderState.ACKNOWLEDGED),
    (OrderState.ACKNOWLEDGED, OrderEvent.OPEN_IN_BOOK, OrderState.OPEN),
    (OrderState.OPEN, OrderEvent.FULL_FILL, OrderState.FILLED),
]

_HAPPY_PATH_MARKET = [
    (OrderState.PLANNED, OrderEvent.SUBMIT, OrderState.SUBMITTED),
    (OrderState.SUBMITTED, OrderEvent.ACK, OrderState.ACKNOWLEDGED),
    (OrderState.ACKNOWLEDGED, OrderEvent.FULL_FILL, OrderState.FILLED),
]

_CANCEL_PATH = [
    (OrderState.OPEN, OrderEvent.CANCEL_REQUEST, OrderState.CANCEL_REQUESTED),
    (OrderState.CANCEL_REQUESTED, OrderEvent.CANCEL_CONFIRMED, OrderState.CANCELED),
]

_RACE_PATH = [
    (OrderState.OPEN, OrderEvent.CANCEL_REQUEST, OrderState.CANCEL_REQUESTED),
    (OrderState.CANCEL_REQUESTED, OrderEvent.FULL_FILL, OrderState.FILLED),
]

_FAILURE_PATHS = [
    (OrderState.SUBMITTED, OrderEvent.REJECT, OrderState.REJECTED),
    (OrderState.SUBMITTED, OrderEvent.TIMEOUT, OrderState.RECONCILIATION_REQUIRED),
    (OrderState.ACKNOWLEDGED, OrderEvent.REJECT, OrderState.REJECTED),
    (OrderState.OPEN, OrderEvent.EXPIRE, OrderState.EXPIRED),
    (OrderState.PARTIALLY_FILLED, OrderEvent.FULL_FILL, OrderState.FILLED),
    (OrderState.PARTIALLY_FILLED, OrderEvent.CANCEL_REQUEST, OrderState.CANCEL_REQUESTED),
    (OrderState.CANCEL_REQUESTED, OrderEvent.CANCEL_FAILED, OrderState.RECONCILIATION_REQUIRED),
]


@pytest.mark.parametrize("from_state,event,expected", _HAPPY_PATH_LIMIT)
def test_happy_path_limit_order(from_state, event, expected):
    assert transition(from_state, event) == expected


@pytest.mark.parametrize("from_state,event,expected", _HAPPY_PATH_MARKET)
def test_happy_path_market_order(from_state, event, expected):
    assert transition(from_state, event) == expected


@pytest.mark.parametrize("from_state,event,expected", _CANCEL_PATH)
def test_cancel_path(from_state, event, expected):
    assert transition(from_state, event) == expected


@pytest.mark.parametrize("from_state,event,expected", _RACE_PATH)
def test_cancel_race_with_fill(from_state, event, expected):
    """Cancel request raced by a fill — order ends up FILLED, not CANCELED."""
    assert transition(from_state, event) == expected


@pytest.mark.parametrize("from_state,event,expected", _FAILURE_PATHS)
def test_failure_paths(from_state, event, expected):
    assert transition(from_state, event) == expected


@pytest.mark.parametrize("terminal", list(TERMINAL_STATES))
def test_terminal_states_have_no_outgoing_transitions(terminal):
    assert is_terminal(terminal)
    assert valid_events(terminal) == frozenset()


def test_non_terminal_states_have_outgoing_transitions():
    non_terminal = [s for s in OrderState if s not in TERMINAL_STATES]
    for s in non_terminal:
        assert not is_terminal(s)
        assert len(valid_events(s)) > 0


def test_invalid_transition_raises():
    with pytest.raises(InvalidTransitionError) as exc_info:
        transition(OrderState.PLANNED, OrderEvent.FULL_FILL)
    assert exc_info.value.from_state == OrderState.PLANNED
    assert exc_info.value.event == OrderEvent.FULL_FILL


def test_invalid_transition_from_terminal_state_raises():
    with pytest.raises(InvalidTransitionError):
        transition(OrderState.FILLED, OrderEvent.CANCEL_REQUEST)


def test_valid_events_for_open_state():
    expected = {
        OrderEvent.FULL_FILL,
        OrderEvent.PARTIAL_FILL,
        OrderEvent.CANCEL_REQUEST,
        OrderEvent.EXPIRE,
    }
    assert valid_events(OrderState.OPEN) == frozenset(expected)


# ── Execution agent ───────────────────────────────────────────────────────────

from datetime import datetime, timezone
from decimal import Decimal

from finding_alpha.contracts.trading import OrderEntry, OrderPlan, PortfolioIntent
from finding_alpha.execution.execution_agent import (
    LEG_ENTRY,
    LEG_STOP,
    ExecutionAgent,
    PlanState,
    _link_id,
    _trigger_direction_for_stop,
)


def _intent(symbol: str = "BTCUSDT", side: str = "short") -> PortfolioIntent:
    return PortfolioIntent(
        signal_id="sig-1",
        venue="bybit",
        symbol=symbol,
        side=side,
        entry_type="limit",
        entry_price=Decimal("60000"),
        stop_price=Decimal("60500"),
        risk_amount=Decimal("50"),
        quantity=Decimal("0.01"),
        notional=Decimal("600"),
        leverage=Decimal("5"),
        max_slippage_bps=Decimal("10"),
        time_in_force="GTC",
        max_hold_minutes=240,
        created_at=datetime.now(timezone.utc),
    )


def _plan(intent: PortfolioIntent) -> OrderPlan:
    entry = OrderEntry(
        order_type="limit",
        side="sell" if intent.side == "short" else "buy",
        quantity=intent.quantity,
        price=intent.entry_price,
    )
    stop = OrderEntry(
        order_type="stop_market",
        side="buy" if intent.side == "short" else "sell",
        quantity=intent.quantity,
        trigger_price=intent.stop_price,
        reduce_only=True,
    )
    return OrderPlan(
        approved_intent_id=intent.intent_id,
        entry_order=entry,
        stop_order=stop,
        created_at=datetime.now(timezone.utc),
    )


def _agent(handler: Callable[[httpx.Request], httpx.Response]) -> ExecutionAgent:
    return ExecutionAgent(_make_client(handler))


def test_link_id_short_plan_id():
    assert _link_id("abc123", "entry") == "abc123-entry"


def test_link_id_truncates_long_plan_id():
    plan = "a" * 50
    result = _link_id(plan, "entry")
    assert len(result) <= 36
    assert result.endswith("-entry")


def test_trigger_direction_short_stop_is_buy_rise():
    assert _trigger_direction_for_stop("Buy") == 1


def test_trigger_direction_long_stop_is_sell_fall():
    assert _trigger_direction_for_stop("Sell") == 2


def test_submit_plan_acks_entry_leg():
    intent = _intent()
    plan = _plan(intent)

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content.decode())
        return _ok({"orderId": "venue-123", "orderLinkId": captured["body"]["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)

    assert captured["path"] == "/v5/order/create"
    assert captured["body"]["symbol"] == "BTCUSDT"
    assert captured["body"]["side"] == "Sell"
    assert captured["body"]["orderType"] == "Limit"
    assert captured["body"]["orderLinkId"] == state.entry.link_id
    assert state.entry.state == OrderState.ACKNOWLEDGED
    assert state.entry.venue_order_id == "venue-123"


def test_submit_plan_rejection_marks_entry_rejected():
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        return _err(110007, "Insufficient balance")

    agent = _agent(handler)
    with pytest.raises(BybitAPIError):
        agent.submit_plan(plan, intent)


def test_submit_stop_after_entry_fills():
    intent = _intent()
    plan = _plan(intent)
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        calls.append(body)
        return _ok({"orderId": f"venue-{len(calls)}", "orderLinkId": body["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.apply_bybit_status(state, LEG_ENTRY, "Filled")
    assert state.entry.state == OrderState.FILLED

    state = agent.submit_stop(state, plan)
    assert len(calls) == 2
    stop_body = calls[1]
    assert stop_body["side"] == "Buy"
    assert stop_body["reduceOnly"] is True
    assert stop_body["triggerPrice"] == "60500"
    assert stop_body["triggerDirection"] == 1   # short stop triggers on rise
    assert state.stop is not None
    assert state.stop.state == OrderState.ACKNOWLEDGED


def test_submit_stop_is_idempotent_no_double_submission():
    intent = _intent()
    plan = _plan(intent)
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        calls.append(body)
        return _ok({"orderId": f"venue-{len(calls)}", "orderLinkId": body["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.submit_stop(state, plan)
    state = agent.submit_stop(state, plan)
    assert len(calls) == 2   # entry + stop, not entry + stop + stop


def test_apply_bybit_status_unknown_forces_reconciliation():
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.apply_bybit_status(state, LEG_ENTRY, "SomeNewStatus")
    assert state.entry.state == OrderState.RECONCILIATION_REQUIRED


def test_apply_bybit_status_invalid_transition_forces_reconciliation():
    """ACK→PARTIAL_FILL is valid; FILLED→PARTIAL_FILL is not — and terminal
    states are early-exited, so the path here is via OPEN→REJECT (no such
    transition exists in the machine)."""
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.apply_bybit_status(state, LEG_ENTRY, "New")
    assert state.entry.state == OrderState.OPEN
    # OPEN + Rejected has no transition in the machine → forced reconciliation
    state = agent.apply_bybit_status(state, LEG_ENTRY, "Rejected")
    assert state.entry.state == OrderState.RECONCILIATION_REQUIRED


def test_apply_bybit_status_on_terminal_state_is_noop():
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.apply_bybit_status(state, LEG_ENTRY, "Filled")
    assert state.entry.state == OrderState.FILLED
    state = agent.apply_bybit_status(state, LEG_ENTRY, "New")
    assert state.entry.state == OrderState.FILLED   # unchanged


def test_apply_bybit_status_unknown_leg_raises():
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    with pytest.raises(KeyError):
        agent.apply_bybit_status(state, "bogus", "Filled")


def test_cancel_leg_transitions_to_canceled_on_success():
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        if request.url.path == "/v5/order/create":
            return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})
        return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.apply_bybit_status(state, LEG_ENTRY, "New")
    state = agent.cancel_leg(state, LEG_ENTRY)
    assert state.entry.state == OrderState.CANCEL_REQUESTED
    state = agent.apply_bybit_status(state, LEG_ENTRY, "Cancelled")
    assert state.entry.state == OrderState.CANCELED


def test_cancel_leg_api_error_marks_reconciliation():
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        if request.url.path == "/v5/order/create":
            return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})
        return _err(110001, "Order does not exist")

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.apply_bybit_status(state, LEG_ENTRY, "New")
    with pytest.raises(BybitAPIError):
        agent.cancel_leg(state, LEG_ENTRY)
    assert state.entry.state == OrderState.RECONCILIATION_REQUIRED


def test_cancel_leg_on_terminal_is_noop():
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.apply_bybit_status(state, LEG_ENTRY, "Filled")
    state = agent.cancel_leg(state, LEG_ENTRY)
    assert state.entry.state == OrderState.FILLED


def test_reconcile_leg_filled_forces_state():
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v5/order/create":
            body = json.loads(request.content.decode())
            return _ok({"orderId": "v-99", "orderLinkId": body["orderLinkId"]})
        # Query endpoint
        return _ok({"list": [{"orderId": "v-99", "orderStatus": "Filled"}]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state.entry.state = OrderState.RECONCILIATION_REQUIRED   # simulate desync
    state = agent.reconcile_leg(state, LEG_ENTRY)
    assert state.entry.state == OrderState.FILLED
    assert state.entry.venue_order_id == "v-99"


def test_reconcile_leg_missing_at_exchange_marks_rejected():
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v5/order/create":
            body = json.loads(request.content.decode())
            return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})
        return _ok({"list": []})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.reconcile_leg(state, LEG_ENTRY)
    assert state.entry.state == OrderState.REJECTED


def test_cancel_race_full_fill_after_cancel_request():
    """Bybit fills the order between our cancel request and confirmation.
    State machine: CANCEL_REQUESTED + FULL_FILL → FILLED."""
    intent = _intent()
    plan = _plan(intent)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        return _ok({"orderId": "v-1", "orderLinkId": body["orderLinkId"]})

    agent = _agent(handler)
    state = agent.submit_plan(plan, intent)
    state = agent.apply_bybit_status(state, LEG_ENTRY, "New")
    state = agent.cancel_leg(state, LEG_ENTRY)
    assert state.entry.state == OrderState.CANCEL_REQUESTED
    state = agent.apply_bybit_status(state, LEG_ENTRY, "Filled")
    assert state.entry.state == OrderState.FILLED
