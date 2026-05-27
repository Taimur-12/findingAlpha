"""
Contract tests.
Each test proves a specific invariant from the source of truth.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from finding_alpha.contracts import (
    CandleEvent, DataQualityEvent, FeatureSnapshot,
    RegimeState, SignalCandidate, ResearchState,
    PortfolioIntent, RiskDecision, OrderPlan, OrderEntry,
    ExecutionReport, TradeOutcome, reason_codes,
)


def utc_now():
    return datetime.now(timezone.utc)


# ── CandleEvent ────────────────────────────────────────────────────────────────

def test_candle_valid():
    c = CandleEvent(
        venue="bybit", symbol="BTCUSDT", timeframe="15m",
        open_time=utc_now(), close_time=utc_now(),
        open=Decimal("75000"), high=Decimal("75500"),
        low=Decimal("74800"), close=Decimal("75200"),
        volume=Decimal("12.345"), quote_volume=Decimal("926000"),
        is_final=True,
    )
    assert c.is_final is True
    assert c.high >= c.low


def test_candle_rejects_invalid_ohlcv():
    with pytest.raises(Exception):
        CandleEvent(
            venue="bybit", symbol="BTCUSDT", timeframe="15m",
            open_time=utc_now(), close_time=utc_now(),
            open=Decimal("75000"), high=Decimal("74000"),  # high < low
            low=Decimal("74800"), close=Decimal("75200"),
            volume=Decimal("12.345"), quote_volume=Decimal("926000"),
        )


def test_candle_rejects_naive_timestamp():
    with pytest.raises(Exception):
        CandleEvent(
            venue="bybit", symbol="BTCUSDT", timeframe="15m",
            open_time=datetime(2026, 1, 1),  # no timezone
            close_time=datetime(2026, 1, 1),
            open=Decimal("75000"), high=Decimal("75500"),
            low=Decimal("74800"), close=Decimal("75200"),
            volume=Decimal("12.345"), quote_volume=Decimal("926000"),
        )


# ── SignalCandidate ────────────────────────────────────────────────────────────

def test_signal_valid_long():
    now = utc_now()
    s = SignalCandidate(
        strategy_id="liquidity_sweep_v1",
        venue="bybit", symbol="BTCUSDT", timeframe="15m",
        side="long",
        created_at=now,
        expires_at=now + timedelta(minutes=60),
        base_confidence=Decimal("0.72"),
        expected_horizon_minutes=60,
        entry_reference=Decimal("75000"),
        invalidation_price=Decimal("74500"),    # below entry — valid long
        target_prices=[Decimal("75800"), Decimal("76200")],
        evidence={"sweep": "session_low_reclaimed", "volume": "z_score_2.1"},
        feature_version="1.0",
        strategy_version="1.0",
    )
    assert s.side == "long"
    assert s.invalidation_price < s.entry_reference


def test_signal_rejects_missing_invalidation_long():
    """Core invariant: long stop must be below entry."""
    now = utc_now()
    with pytest.raises(Exception):
        SignalCandidate(
            strategy_id="liquidity_sweep_v1",
            venue="bybit", symbol="BTCUSDT", timeframe="15m",
            side="long",
            created_at=now,
            expires_at=now + timedelta(minutes=60),
            base_confidence=Decimal("0.72"),
            expected_horizon_minutes=60,
            entry_reference=Decimal("75000"),
            invalidation_price=Decimal("75500"),  # ABOVE entry — invalid
            feature_version="1.0",
            strategy_version="1.0",
        )


def test_signal_rejects_missing_invalidation_short():
    """Core invariant: short stop must be above entry."""
    now = utc_now()
    with pytest.raises(Exception):
        SignalCandidate(
            strategy_id="squeeze_v1",
            venue="bybit", symbol="BTCUSDT", timeframe="15m",
            side="short",
            created_at=now,
            expires_at=now + timedelta(minutes=60),
            base_confidence=Decimal("0.65"),
            expected_horizon_minutes=60,
            entry_reference=Decimal("75000"),
            invalidation_price=Decimal("74500"),  # BELOW entry for short — invalid
            feature_version="1.0",
            strategy_version="1.0",
        )


# ── RiskDecision ──────────────────────────────────────────────────────────────

def test_risk_reject_requires_reason_code():
    """A rejection without a reason code is invalid."""
    with pytest.raises(Exception):
        RiskDecision(
            intent_id="some-intent-id",
            decision="reject",
            reason_codes=[],          # empty — should fail
            approved_intent=None,
            risk_policy_version="1.0",
            decided_at=utc_now(),
        )


def test_risk_reject_with_reason_code():
    d = RiskDecision(
        intent_id="some-intent-id",
        decision="reject",
        reason_codes=[reason_codes.RISK_DAILY_LOSS_STOP],
        approved_intent=None,
        risk_policy_version="1.0",
        decided_at=utc_now(),
    )
    assert not d.is_approved
    assert d.reason_codes[0] == reason_codes.RISK_DAILY_LOSS_STOP


def test_risk_approve_requires_intent():
    """An approval without an approved_intent is invalid."""
    with pytest.raises(Exception):
        RiskDecision(
            intent_id="some-intent-id",
            decision="approve",
            reason_codes=[],
            approved_intent=None,     # missing — should fail
            risk_policy_version="1.0",
            decided_at=utc_now(),
        )


# ── ResearchState ─────────────────────────────────────────────────────────────

def test_research_multiplier_is_clamped():
    """Multiplier above 1.15 gets clamped down to 1.15."""
    now = utc_now()
    r = ResearchState(
        as_of=now,
        expires_at=now + timedelta(minutes=15),
        assets=["BTC"],
        event_type="none",
        severity=Decimal("0"),
        directional_bias=Decimal("0"),
        confidence_multiplier=Decimal("2.0"),  # way too high
        trade_policy="normal",
        model_id="claude-sonnet-4-6",
        prompt_version="1.0",
    )
    assert r.confidence_multiplier == Decimal("1.15")


def test_research_hard_block_detection():
    now = utc_now()
    r = ResearchState(
        as_of=now,
        expires_at=now + timedelta(minutes=15),
        assets=["BTC", "ETH"],
        event_type="exchange_risk",
        severity=Decimal("1.0"),
        directional_bias=Decimal("-0.9"),
        confidence_multiplier=Decimal("0"),
        trade_policy="block_new_entries",
        reason_codes=[reason_codes.RESEARCH_EXCHANGE_INSOLVENCY],
        sources=["https://example.com/news"],
        model_id="claude-sonnet-4-6",
        prompt_version="1.0",
    )
    assert r.is_hard_block is True


# ── ExecutionReport ───────────────────────────────────────────────────────────

def test_execution_report_valid():
    r = ExecutionReport(
        order_id="ord-001",
        client_order_id="strategy-signal-entry",
        venue_order_id="bybit-12345",
        status="filled",
        filled_quantity=Decimal("0.001"),
        remaining_quantity=Decimal("0"),
        avg_fill_price=Decimal("75100"),
        fee=Decimal("0.04"),
        liquidity_flag="taker",
        exchange_ts=utc_now(),
        received_ts=utc_now(),
    )
    assert r.is_terminal is True


# ── Immutability ──────────────────────────────────────────────────────────────

def test_contracts_are_immutable():
    """All contracts are frozen — no field can be changed after creation."""
    now = utc_now()
    s = SignalCandidate(
        strategy_id="test", venue="bybit", symbol="BTCUSDT", timeframe="15m",
        side="long", created_at=now, expires_at=now + timedelta(minutes=30),
        base_confidence=Decimal("0.7"), expected_horizon_minutes=30,
        entry_reference=Decimal("75000"), invalidation_price=Decimal("74500"),
        feature_version="1.0", strategy_version="1.0",
    )
    with pytest.raises(Exception):
        s.side = "short"  # frozen — must raise
