"""
Tests for live execution path: paper.live_execution module + runtime._live_tick.

Uses httpx.MockTransport to fake Bybit V5 responses. No real network.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable

import httpx
import pytest

from finding_alpha.contracts.trading import PortfolioIntent
from finding_alpha.execution.bybit_client import (
    BybitClient,
    BybitClientConfig,
    TESTNET_URL,
)
from finding_alpha.execution.execution_agent import (
    LEG_ENTRY,
    LEG_STOP,
    ExecutionAgent,
)
from finding_alpha.execution.order_state import OrderState
from finding_alpha.matrix.event_log import MatrixEventLog
from finding_alpha.paper.live_execution import (
    CLOSE_REASON_STOP,
    CLOSE_REASON_TARGET,
    CLOSE_REASON_TIMEOUT,
    PaperContext,
    build_plan_from_intent,
    make_live_plan_ref,
    parse_live_plan_ref,
    rebuild_stop_only_plan,
    target_breached,
    timeout_breached,
)
from finding_alpha.paper.runtime import (
    PaperRuntimeConfig,
    _live_tick,
    _submit_live_intent,
)
from finding_alpha.paper.state import PaperState


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ok(result: dict) -> httpx.Response:
    return httpx.Response(200, json={"retCode": 0, "retMsg": "OK", "result": result})


def _intent(side: str = "short", now: datetime | None = None) -> PortfolioIntent:
    now = now or datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    return PortfolioIntent(
        signal_id="sig-1",
        venue="bybit",
        symbol="BTCUSDT",
        side=side,
        entry_type="limit",
        entry_price=Decimal("60000"),
        stop_price=Decimal("60500") if side == "short" else Decimal("59500"),
        risk_amount=Decimal("25"),
        quantity=Decimal("0.001"),
        notional=Decimal("60"),
        leverage=Decimal("1"),
        max_slippage_bps=Decimal("10"),
        time_in_force="GTC",
        max_hold_minutes=60,
        created_at=now,
    )


def _agent(handler: Callable[[httpx.Request], httpx.Response]) -> ExecutionAgent:
    cfg = BybitClientConfig(api_key="k", api_secret="s", base_url=TESTNET_URL)
    transport = httpx.MockTransport(handler)
    http = httpx.Client(base_url=TESTNET_URL, transport=transport)
    return ExecutionAgent(BybitClient(cfg, http=http))


def _ctx(
    entry_filled: bool = False,
    close_requested: bool = False,
    side: str = "short",
    now: datetime | None = None,
) -> PaperContext:
    now = now or datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    return PaperContext(
        signal_id="sig-1",
        strategy_id="prev_day_breakdown_v1",
        strategy_version="1.0",
        feature_version="f-1",
        intent_id="intent-1",
        side=side,
        entry_price=Decimal("60000"),
        stop_price=Decimal("60500") if side == "short" else Decimal("59500"),
        target_price=Decimal("58000") if side == "short" else Decimal("62000"),
        quantity=Decimal("0.001"),
        notional=Decimal("60"),
        risk_amount=Decimal("25"),
        max_exit_ts=now + timedelta(hours=1),
        entry_submitted_at=now,
        entry_filled_at=now if entry_filled else None,
        close_requested_at=now if close_requested else None,
    )


def _cfg(tmp_path) -> PaperRuntimeConfig:
    return PaperRuntimeConfig(
        symbol="BTCUSDT",
        timeframe="1h",
        venue="bybit",
        execution_mode="live",
        paper_dir=tmp_path,
    )


# ── build_plan_from_intent ────────────────────────────────────────────────────


def test_build_plan_from_intent_short_maps_sell_entry_buy_stop():
    intent = _intent(side="short")
    plan = build_plan_from_intent(intent, intent.created_at)
    assert plan.entry_order.side == "sell"
    assert plan.entry_order.order_type == "limit"
    assert plan.stop_order.side == "buy"
    assert plan.stop_order.order_type == "stop_market"
    assert plan.stop_order.reduce_only is True
    assert plan.stop_order.trigger_price == intent.stop_price


def test_build_plan_from_intent_long_maps_buy_entry_sell_stop():
    intent = _intent(side="long")
    plan = build_plan_from_intent(intent, intent.created_at)
    assert plan.entry_order.side == "buy"
    assert plan.stop_order.side == "sell"


# ── Serialization round-trip ──────────────────────────────────────────────────


def test_live_plan_ref_roundtrip_preserves_all_fields():
    intent = _intent(side="short")
    plan = build_plan_from_intent(intent, intent.created_at)
    # Build a PlanState by submitting through a mocked agent
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/v5/order/create":
            return _ok({"orderId": "v-entry", "orderLinkId": ""})
        raise AssertionError(req.url.path)
    agent = _agent(handler)
    plan_state = agent.submit_plan(plan, intent)

    ctx = _ctx(entry_filled=True, close_requested=True)
    ctx.close_reason = CLOSE_REASON_TARGET
    ctx.close_link_id = f"{plan_state.plan_id[:24]}-close"

    ref = make_live_plan_ref(plan_state, ctx)
    # Must be JSON serializable (state.py round-trips via json.dumps)
    json_str = json.dumps(ref)
    ref2 = json.loads(json_str)

    plan_state2, ctx2 = parse_live_plan_ref(ref2)
    assert plan_state2.plan_id == plan_state.plan_id
    assert plan_state2.legs[LEG_ENTRY].state == plan_state.legs[LEG_ENTRY].state
    assert plan_state2.legs[LEG_ENTRY].link_id == plan_state.legs[LEG_ENTRY].link_id
    assert ctx2.signal_id == ctx.signal_id
    assert ctx2.entry_price == ctx.entry_price
    assert ctx2.entry_filled_at == ctx.entry_filled_at
    assert ctx2.close_reason == CLOSE_REASON_TARGET


# ── rebuild_stop_only_plan ────────────────────────────────────────────────────


def test_rebuild_stop_only_plan_preserves_plan_id_and_stop():
    intent = _intent(side="short")
    plan = build_plan_from_intent(intent, intent.created_at)
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/v5/order/create":
            return _ok({"orderId": "v-entry", "orderLinkId": ""})
        raise AssertionError(req.url.path)
    agent = _agent(handler)
    plan_state = agent.submit_plan(plan, intent)

    ctx = _ctx(entry_filled=True)
    rebuilt = rebuild_stop_only_plan(plan_state, ctx)
    assert rebuilt.order_plan_id == plan_state.plan_id
    assert rebuilt.stop_order.side == "buy"
    assert rebuilt.stop_order.trigger_price == ctx.stop_price
    assert rebuilt.stop_order.reduce_only is True


# ── target_breached / timeout_breached ────────────────────────────────────────


def test_target_breached_short_returns_true_when_mark_below_target():
    ctx = _ctx(entry_filled=True)
    assert target_breached(plan_state=None, ctx=ctx, mark_price=Decimal("57999")) is True


def test_target_breached_short_returns_false_when_mark_above_target():
    ctx = _ctx(entry_filled=True)
    assert target_breached(plan_state=None, ctx=ctx, mark_price=Decimal("58001")) is False


def test_target_breached_returns_false_when_entry_not_filled():
    ctx = _ctx(entry_filled=False)
    assert target_breached(plan_state=None, ctx=ctx, mark_price=Decimal("0")) is False


def test_target_breached_returns_false_when_close_already_requested():
    ctx = _ctx(entry_filled=True, close_requested=True)
    assert target_breached(plan_state=None, ctx=ctx, mark_price=Decimal("0")) is False


def test_timeout_breached_returns_true_after_max_exit_ts():
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    ctx = _ctx(entry_filled=True, now=now)
    assert timeout_breached(ctx, now + timedelta(hours=2)) is True


def test_timeout_breached_returns_false_before_max_exit_ts():
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    ctx = _ctx(entry_filled=True, now=now)
    assert timeout_breached(ctx, now + timedelta(minutes=30)) is False


# ── _live_tick integration ────────────────────────────────────────────────────


def _build_ticking_state(handler, tmp_path):
    """Submit an entry via mocked agent, build the resulting state."""
    intent = _intent(side="short")
    plan = build_plan_from_intent(intent, intent.created_at)

    agent = _agent(handler)
    plan_state = agent.submit_plan(plan, intent)

    ctx = PaperContext(
        signal_id=intent.signal_id,
        strategy_id="prev_day_breakdown_v1",
        strategy_version="1.0",
        feature_version="f-1",
        intent_id=intent.intent_id,
        side=intent.side,
        entry_price=intent.entry_price,
        stop_price=intent.stop_price,
        target_price=Decimal("58000"),
        quantity=intent.quantity,
        notional=intent.notional,
        risk_amount=intent.risk_amount,
        max_exit_ts=intent.created_at + timedelta(hours=1),
        entry_submitted_at=intent.created_at,
    )
    state = PaperState()
    state.live_plan_ref = make_live_plan_ref(plan_state, ctx)
    matrix = MatrixEventLog(log_path=tmp_path / "matrix.jsonl")
    cfg = _cfg(tmp_path)
    return state, matrix, cfg, agent, plan_state, ctx


def test_live_tick_noop_when_no_ref(tmp_path):
    def handler(req):
        raise AssertionError(f"unexpected call: {req.url.path}")
    agent = _agent(handler)
    state = PaperState()
    matrix = MatrixEventLog(log_path=tmp_path / "matrix.jsonl")
    cfg = _cfg(tmp_path)
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    result = _live_tick(state, matrix, cfg, agent, now)
    assert result is None
    assert state.live_plan_ref is None


def test_live_tick_detects_entry_fill_and_submits_stop(tmp_path):
    """Entry transitions New → Filled; tick should stamp fill, submit stop."""
    create_calls: list[dict] = []

    def handler(req):
        path = req.url.path
        if path == "/v5/order/create":
            body = json.loads(req.content.decode())
            create_calls.append(body)
            return _ok({"orderId": f"v-{body['orderLinkId']}", "orderLinkId": body["orderLinkId"]})
        if path == "/v5/order/realtime":
            link_id = req.url.params.get("orderLinkId", "")
            # Entry → Filled; stop → New (would be checked after stop submitted)
            if "entry" in link_id:
                return _ok({"list": [{
                    "orderId": "v-entry",
                    "orderStatus": "Filled",
                    "avgPrice": "60000",
                    "cumExecQty": "0.001",
                    "cumExecFee": "0.012",
                    "updatedTime": "1748793600000",
                }]})
            if "stop" in link_id:
                return _ok({"list": [{
                    "orderId": "v-stop",
                    "orderStatus": "Untriggered",
                }]})
            return _ok({"list": []})
        if path == "/v5/position/list":
            return _ok({"list": [{
                "symbol": "BTCUSDT",
                "side": "Sell",
                "size": "0.001",
                "markPrice": "59950",
            }]})
        raise AssertionError(f"unexpected path: {path}")

    state, matrix, cfg, agent, _ps, _ctx = _build_ticking_state(handler, tmp_path)
    now = datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc)
    trade = _live_tick(state, matrix, cfg, agent, now)

    assert trade is None
    # One entry submit (during _build_ticking_state setup) + one stop submit during tick
    stop_creates = [c for c in create_calls if "stop" in c.get("orderLinkId", "")]
    assert len(stop_creates) == 1
    # live_plan_ref preserved + entry_filled_at stamped
    _, ctx2 = parse_live_plan_ref(state.live_plan_ref)
    assert ctx2.entry_filled_at is not None


def test_live_tick_submits_runtime_close_on_target_breach(tmp_path):
    """Position is open, entry filled, mark price below target → close."""
    create_calls: list[dict] = []
    cancel_calls: list[dict] = []

    def handler(req):
        path = req.url.path
        if path == "/v5/order/create":
            body = json.loads(req.content.decode())
            create_calls.append(body)
            return _ok({"orderId": f"v-{body['orderLinkId']}", "orderLinkId": body["orderLinkId"]})
        if path == "/v5/order/cancel":
            cancel_calls.append(json.loads(req.content.decode()))
            return _ok({"orderId": "cancelled"})
        if path == "/v5/order/realtime":
            link_id = req.url.params.get("orderLinkId", "")
            if "entry" in link_id:
                return _ok({"list": [{"orderId": "v-entry", "orderStatus": "Filled"}]})
            if "stop" in link_id:
                return _ok({"list": [{"orderId": "v-stop", "orderStatus": "Untriggered"}]})
            return _ok({"list": []})
        if path == "/v5/position/list":
            return _ok({"list": [{
                "symbol": "BTCUSDT",
                "side": "Sell",
                "size": "0.001",
                "markPrice": "57500",  # below target=58000 → breach
            }]})
        raise AssertionError(f"unexpected: {path}")

    state, matrix, cfg, agent, _, _ = _build_ticking_state(handler, tmp_path)
    # Pre-populate: pretend entry already filled, stop already exists, no close yet
    plan_state, ctx = parse_live_plan_ref(state.live_plan_ref)
    plan_state.legs[LEG_ENTRY].state = OrderState.FILLED
    ctx.entry_filled_at = datetime(2026, 6, 1, 12, 30, tzinfo=timezone.utc)
    # Manually add a stop leg so we don't re-submit one this tick
    from finding_alpha.execution.execution_agent import LegState
    plan_state.legs[LEG_STOP] = LegState(
        link_id=f"{plan_state.plan_id[:30]}-stop"[:36],
        state=OrderState.OPEN,
        venue_order_id="v-stop",
        side="Buy",
        order_type="Market",
        qty="0.001",
        trigger_price="60500",
        reduce_only=True,
    )
    state.live_plan_ref = make_live_plan_ref(plan_state, ctx)

    now = datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc)
    trade = _live_tick(state, matrix, cfg, agent, now)

    assert trade is None  # position still open per mock
    # Stop should be cancelled, close market order submitted
    assert len(cancel_calls) == 1
    close_creates = [c for c in create_calls if "close" in c.get("orderLinkId", "")]
    assert len(close_creates) == 1
    assert close_creates[0]["orderType"] == "Market"
    # close_reason captured
    _, ctx2 = parse_live_plan_ref(state.live_plan_ref)
    assert ctx2.close_reason == CLOSE_REASON_TARGET
    assert ctx2.close_requested_at is not None


def test_live_tick_returns_paper_trade_when_position_closes(tmp_path):
    """Stop fills, position size = 0 → PaperTrade reconstructed and returned."""
    def handler(req):
        path = req.url.path
        if path == "/v5/order/realtime":
            link_id = req.url.params.get("orderLinkId", "")
            if "entry" in link_id:
                return _ok({"list": [{
                    "orderId": "v-entry",
                    "orderStatus": "Filled",
                    "avgPrice": "60000",
                    "cumExecQty": "0.001",
                    "cumExecFee": "0.012",
                    "updatedTime": "1748793600000",
                }]})
            if "stop" in link_id:
                return _ok({"list": [{
                    "orderId": "v-stop",
                    "orderStatus": "Filled",
                    "avgPrice": "60500",
                    "cumExecQty": "0.001",
                    "cumExecFee": "0.012",
                    "updatedTime": "1748797200000",
                }]})
            return _ok({"list": []})
        if path == "/v5/position/list":
            return _ok({"list": []})  # flat
        if path == "/v5/order/create":
            body = json.loads(req.content.decode())
            return _ok({"orderId": f"v-{body['orderLinkId']}", "orderLinkId": body["orderLinkId"]})
        raise AssertionError(f"unexpected: {path}")

    state, matrix, cfg, agent, _, _ = _build_ticking_state(handler, tmp_path)
    # Pre-populate: entry filled, stop exists and will be reported Filled
    plan_state, ctx = parse_live_plan_ref(state.live_plan_ref)
    plan_state.legs[LEG_ENTRY].state = OrderState.FILLED
    ctx.entry_filled_at = datetime(2026, 6, 1, 12, 30, tzinfo=timezone.utc)
    from finding_alpha.execution.execution_agent import LegState
    plan_state.legs[LEG_STOP] = LegState(
        link_id=f"{plan_state.plan_id[:30]}-stop"[:36],
        state=OrderState.OPEN,
        venue_order_id="v-stop",
        side="Buy",
        order_type="Market",
        qty="0.001",
        trigger_price="60500",
        reduce_only=True,
    )
    state.live_plan_ref = make_live_plan_ref(plan_state, ctx)

    now = datetime(2026, 6, 1, 13, 30, tzinfo=timezone.utc)
    trade = _live_tick(state, matrix, cfg, agent, now)

    assert trade is not None
    assert trade.exit_reason == CLOSE_REASON_STOP
    assert trade.entry_price == Decimal("60000")
    assert trade.exit_price == Decimal("60500")
    # Short trade with exit > entry = loss; gross_pnl = (60500-60000)*0.001*(-1) = -0.50
    assert trade.gross_pnl == Decimal("-0.50")
    # net = gross - fees(0.024) = -0.524
    assert trade.net_pnl == Decimal("-0.52")
    assert state.live_plan_ref is None  # cleared after close
