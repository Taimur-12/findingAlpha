"""
Phase 8 paper runtime safety check tests.

Covers the invariants listed in STATE.md:
  - no signal from unfinished candle (bar finality)
  - no signal when candle finality cannot be proven (stale data)
  - no paper trade without stop (PaperPosition contract)
  - no duplicate open paper position (is_slot_free enforcement)
  - paper audit logging (Matrix events emitted on entry and exit)
  - PendingEntry round-trips through PaperState persistence
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from finding_alpha.contracts.market import DataQualityEvent
from finding_alpha.contracts.execution import TradeOutcome
from finding_alpha.contracts.signals import ResearchState
from finding_alpha.live.feed import is_bar_final, is_data_stale
from finding_alpha.matrix.event_log import MatrixEventLog
from finding_alpha.paper.state import (
    PaperPosition, PaperState, PaperTrade, PendingEntry,
    load_state, save_state,
)
from finding_alpha.paper.runtime import (
    PaperRuntimeConfig, _check_position_exit, _load_and_check_advisory,
    _try_fill_entry,
)
from finding_alpha.research.advisory import save_advisory

_UTC = timezone.utc


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime(2026, 5, 27, 14, 30, 0, tzinfo=_UTC)


def _make_bar(
    open_time: datetime,
    open_: float = 67000.0,
    high: float = 67500.0,
    low: float = 66500.0,
    close: float = 67000.0,
    volume: float = 1000.0,
) -> pd.Series:
    close_time = open_time + timedelta(hours=1, milliseconds=-1)
    return pd.Series({
        "open_time": pd.Timestamp(open_time),
        "close_time": pd.Timestamp(close_time),
        "open": str(open_),
        "high": str(high),
        "low": str(low),
        "close": str(close),
        "volume": str(volume),
        "quote_volume": str(open_ * volume),
    })


def _make_short_position(
    entry_price: Decimal = Decimal("67000"),
    stop_price: Decimal = Decimal("67500"),
    target_price: Decimal = Decimal("64000"),
    risk_amount: Decimal = Decimal("25"),
    quantity: Decimal = Decimal("0.001"),
    entry_ts: datetime = None,
    max_exit_ts: datetime = None,
) -> PaperPosition:
    if entry_ts is None:
        entry_ts = datetime(2026, 5, 27, 12, 0, 0, tzinfo=_UTC)
    if max_exit_ts is None:
        max_exit_ts = entry_ts + timedelta(hours=12)
    return PaperPosition(
        signal_id="sig-001",
        strategy_id="prev_day_breakdown_v1",
        intent_id="int-001",
        symbol="BTCUSDT",
        side="short",
        entry_ts=entry_ts,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        quantity=quantity,
        notional=(quantity * entry_price).quantize(Decimal("0.01")),
        risk_amount=risk_amount,
        max_exit_ts=max_exit_ts,
        feature_version="1.0",
        strategy_version="1.0",
    )


def _make_pending(
    entry_price: Decimal = Decimal("67000"),
    signal_bar_ts: datetime = None,
) -> PendingEntry:
    if signal_bar_ts is None:
        signal_bar_ts = datetime(2026, 5, 27, 12, 0, 0, tzinfo=_UTC)
    stop = entry_price + Decimal("500")
    target = entry_price - Decimal("3000")
    qty = Decimal("0.001")
    notional = (qty * entry_price).quantize(Decimal("0.01"))
    return PendingEntry(
        signal_id="sig-001",
        strategy_id="prev_day_breakdown_v1",
        intent_id="int-001",
        symbol="BTCUSDT",
        side="short",
        entry_price=entry_price,
        stop_price=stop,
        target_price=target,
        quantity=qty,
        notional=notional,
        risk_amount=Decimal("25"),
        max_hold_minutes=720,
        signal_bar_open_time=signal_bar_ts,
        feature_version="1.0",
        strategy_version="1.0",
    )


def _default_cfg(tmp_path: Path) -> PaperRuntimeConfig:
    return PaperRuntimeConfig(paper_dir=tmp_path)


# ── Bar finality tests ─────────────────────────────────────────────────────────

def test_bar_final_after_close_plus_grace():
    """A bar that closed more than 60 seconds ago is final."""
    open_time = datetime(2026, 5, 27, 13, 0, 0, tzinfo=_UTC)
    now = open_time + timedelta(hours=1, seconds=61)
    assert is_bar_final(open_time, "1h", now) is True


def test_bar_not_final_before_close():
    """A bar still in progress (close time in the future) is not final."""
    open_time = datetime(2026, 5, 27, 13, 0, 0, tzinfo=_UTC)
    now = open_time + timedelta(minutes=30)
    assert is_bar_final(open_time, "1h", now) is False


def test_bar_not_final_within_grace_period():
    """A bar that just closed (< 60s ago) is not final — grace period not elapsed."""
    open_time = datetime(2026, 5, 27, 13, 0, 0, tzinfo=_UTC)
    now = open_time + timedelta(hours=1, seconds=30)  # only 30s after close
    assert is_bar_final(open_time, "1h", now) is False


# ── Stale data tests ───────────────────────────────────────────────────────────

def test_data_stale_when_bar_missed():
    """If the most recent final bar is 2+ bar durations old, data is stale."""
    last_bar_ts = datetime(2026, 5, 27, 11, 0, 0, tzinfo=_UTC)
    now = last_bar_ts + timedelta(hours=2, seconds=1)
    assert is_data_stale(last_bar_ts, "1h", now) is True


def test_data_not_stale_when_recent():
    """If the most recent final bar is 70 minutes old (1 bar), data is fresh."""
    last_bar_ts = datetime(2026, 5, 27, 13, 0, 0, tzinfo=_UTC)
    now = last_bar_ts + timedelta(minutes=70)
    assert is_data_stale(last_bar_ts, "1h", now) is False


# ── PaperPosition invariant tests ─────────────────────────────────────────────

def test_paper_position_short_stop_must_be_above_entry():
    """Short position with stop below entry is rejected at contract level."""
    with pytest.raises(Exception):
        PaperPosition(
            signal_id="x", strategy_id="x", intent_id="x", symbol="BTCUSDT",
            side="short",
            entry_ts=datetime(2026, 5, 27, 12, 0, 0, tzinfo=_UTC),
            entry_price=Decimal("67000"),
            stop_price=Decimal("66000"),    # wrong — stop below entry for short
            target_price=Decimal("64000"),
            quantity=Decimal("0.001"),
            notional=Decimal("67.00"),
            risk_amount=Decimal("25"),
            max_exit_ts=datetime(2026, 5, 27, 23, 0, 0, tzinfo=_UTC),
            feature_version="1.0",
            strategy_version="1.0",
        )


def test_paper_position_naive_timestamps_rejected():
    """PaperPosition rejects naive (non-UTC) timestamps."""
    with pytest.raises(Exception):
        PaperPosition(
            signal_id="x", strategy_id="x", intent_id="x", symbol="BTCUSDT",
            side="short",
            entry_ts=datetime(2026, 5, 27, 12, 0, 0),   # naive — no tzinfo
            entry_price=Decimal("67000"),
            stop_price=Decimal("67500"),
            target_price=Decimal("64000"),
            quantity=Decimal("0.001"),
            notional=Decimal("67.00"),
            risk_amount=Decimal("25"),
            max_exit_ts=datetime(2026, 5, 27, 23, 0, 0, tzinfo=_UTC),
            feature_version="1.0",
            strategy_version="1.0",
        )


# ── Slot / duplicate position tests ───────────────────────────────────────────

def test_no_duplicate_position_when_position_open():
    """is_slot_free returns False when a position is already open."""
    state = PaperState()
    state.open_position = _make_short_position()
    assert state.is_slot_free() is False


def test_no_duplicate_position_when_pending_entry():
    """is_slot_free returns False when a pending entry is already set."""
    state = PaperState()
    state.pending_entry = _make_pending()
    assert state.is_slot_free() is False


def test_slot_free_when_both_clear():
    """is_slot_free returns True only when no position and no pending entry."""
    state = PaperState()
    assert state.is_slot_free() is True


# ── Trade log test ─────────────────────────────────────────────────────────────

def test_trade_logged_on_stop_hit(tmp_path):
    """
    When a short position's stop is hit, a TradeOutcome is logged to the Matrix
    and a PaperTrade is returned with exit_reason='stop_loss'.
    """
    state = PaperState()
    state.open_position = _make_short_position(
        entry_price=Decimal("67000"),
        stop_price=Decimal("67500"),
        target_price=Decimal("64000"),
    )
    matrix = MatrixEventLog()
    cfg = _default_cfg(tmp_path)
    now = _now()

    # Bar that touches the stop: high >= 67500
    bar = _make_bar(
        open_time=datetime(2026, 5, 27, 14, 0, 0, tzinfo=_UTC),
        high=67600.0,
        low=66800.0,
        close=67100.0,
    )

    trade = _check_position_exit(state, bar, matrix, cfg, now)

    assert trade is not None
    assert trade.exit_reason == "stop_loss"
    assert state.open_position is None   # position cleared

    # TradeOutcome must be in the Matrix
    outcomes = [e for e in matrix.events if isinstance(e, TradeOutcome)]
    assert len(outcomes) == 1
    assert outcomes[0].exit_reason == "stop_loss"


def test_trade_logged_on_tp_hit(tmp_path):
    """TP hit: TradeOutcome logged with exit_reason='take_profit'."""
    state = PaperState()
    state.open_position = _make_short_position(
        entry_price=Decimal("67000"),
        stop_price=Decimal("67500"),
        target_price=Decimal("64000"),
    )
    matrix = MatrixEventLog()
    cfg = _default_cfg(tmp_path)
    now = _now()

    # Bar that touches target: low <= 64000
    bar = _make_bar(
        open_time=datetime(2026, 5, 27, 14, 0, 0, tzinfo=_UTC),
        high=67200.0,
        low=63900.0,
        close=64100.0,
    )

    trade = _check_position_exit(state, bar, matrix, cfg, now)

    assert trade is not None
    assert trade.exit_reason == "take_profit"
    outcomes = [e for e in matrix.events if isinstance(e, TradeOutcome)]
    assert len(outcomes) == 1


def test_stop_wins_over_tp_same_candle(tmp_path):
    """When both stop and TP are hit on the same candle, stop wins (conservative)."""
    state = PaperState()
    state.open_position = _make_short_position(
        entry_price=Decimal("67000"),
        stop_price=Decimal("67500"),
        target_price=Decimal("64000"),
    )
    matrix = MatrixEventLog()
    cfg = _default_cfg(tmp_path)
    now = _now()

    # Bar that touches both stop (high >= 67500) and TP (low <= 64000)
    bar = _make_bar(
        open_time=datetime(2026, 5, 27, 14, 0, 0, tzinfo=_UTC),
        high=67600.0,
        low=63900.0,
        close=65000.0,
    )

    trade = _check_position_exit(state, bar, matrix, cfg, now)
    assert trade is not None
    assert trade.exit_reason == "stop_loss"


# ── Pending entry fill tests ───────────────────────────────────────────────────

def test_pending_entry_fills_when_touched(tmp_path):
    """
    A SHORT pending entry fills when bar high >= entry_price.
    State transitions from pending_entry set → open_position set.
    """
    state = PaperState()
    state.pending_entry = _make_pending(entry_price=Decimal("67000"))
    matrix = MatrixEventLog()
    cfg = _default_cfg(tmp_path)
    now = _now()

    # Bar high reaches 67000+ — should fill
    bar = _make_bar(
        open_time=datetime(2026, 5, 27, 13, 0, 0, tzinfo=_UTC),
        high=67200.0,
        low=66500.0,
        close=66700.0,
    )

    _try_fill_entry(state, bar, matrix, cfg, now)

    assert state.open_position is not None
    assert state.pending_entry is None
    assert state.open_position.entry_price == Decimal("67000")
    assert state.open_position.stop_price > state.open_position.entry_price


def test_pending_entry_canceled_when_not_touched(tmp_path):
    """
    A SHORT pending entry is canceled when bar high < entry_price.
    A DataQualityEvent is logged as the missed-fill record.
    """
    state = PaperState()
    state.pending_entry = _make_pending(entry_price=Decimal("67000"))
    matrix = MatrixEventLog()
    cfg = _default_cfg(tmp_path)
    now = _now()

    # Bar high stays below 67000 — limit never reached
    bar = _make_bar(
        open_time=datetime(2026, 5, 27, 13, 0, 0, tzinfo=_UTC),
        high=66900.0,
        low=66300.0,
        close=66500.0,
    )

    _try_fill_entry(state, bar, matrix, cfg, now)

    assert state.open_position is None
    assert state.pending_entry is None
    dq_events = [e for e in matrix.events if isinstance(e, DataQualityEvent)]
    assert len(dq_events) == 1


# ── State persistence test ─────────────────────────────────────────────────────

def test_paper_state_round_trips_through_json(tmp_path):
    """save_state / load_state must reproduce the full state including pending_entry."""
    state = PaperState(
        equity=Decimal("10123.45"),
        peak_equity=Decimal("10200.00"),
        daily_start_equity=Decimal("10000.00"),
        daily_date="2026-05-27",
        pending_entry=_make_pending(),
        last_processed_bar_ts=datetime(2026, 5, 27, 13, 0, 0, tzinfo=_UTC),
    )
    path = tmp_path / "state.json"
    save_state(state, path)

    loaded = load_state(path)
    assert loaded.equity == Decimal("10123.45")
    assert loaded.peak_equity == Decimal("10200.00")
    assert loaded.pending_entry is not None
    assert loaded.pending_entry.entry_price == Decimal("67000")
    assert loaded.last_processed_bar_ts == datetime(2026, 5, 27, 13, 0, 0, tzinfo=_UTC)
    assert loaded.open_position is None


# ── Advisory gate tests (Phase 9) ──────────────────────────────────────────────

def _cfg_with_advisory(tmp_path: Path) -> PaperRuntimeConfig:
    return PaperRuntimeConfig(
        paper_dir=tmp_path,
        advisory_path=tmp_path / "advisory.json",
        strategy_id="prev_day_breakdown_v1",
    )


def _build_advisory(
    *,
    confidence_multiplier: Decimal = Decimal("1.0"),
    trade_policy: str = "normal",
    allowed_strategies: list[str] | None = None,
) -> ResearchState:
    now = _now()
    return ResearchState(
        as_of=now,
        expires_at=now + timedelta(hours=24),
        assets=["BTC"],
        event_type="none",
        severity=Decimal("0"),
        directional_bias=Decimal("0"),
        confidence_multiplier=confidence_multiplier,
        trade_policy=trade_policy,
        model_id="claude-sonnet-4-6",
        prompt_version="1.0",
        allowed_strategies=allowed_strategies or [],
    )


def test_advisory_gate_proceeds_with_no_file(tmp_path):
    """Missing advisory file → permissive default → proceed with full risk_pct."""
    cfg = _cfg_with_advisory(tmp_path)
    matrix = MatrixEventLog()
    proceed, eff_risk = _load_and_check_advisory(cfg, matrix, _now())
    assert proceed is True
    assert eff_risk == cfg.risk_pct
    # No matrix events emitted on missing file (default state, no spam).
    assert all(getattr(e, "reason_code", "") != "ADVISORY_INVALID" for e in matrix.events)


def test_advisory_gate_blocks_on_hard_block(tmp_path):
    cfg = _cfg_with_advisory(tmp_path)
    save_advisory(_build_advisory(trade_policy="block_new_entries"), cfg.advisory_path)
    matrix = MatrixEventLog()
    proceed, _ = _load_and_check_advisory(cfg, matrix, _now())
    assert proceed is False
    block_events = [e for e in matrix.events
                    if getattr(e, "reason_code", "") == "ADVISORY_HARD_BLOCK"]
    assert len(block_events) == 1


def test_advisory_gate_blocks_when_strategy_not_allowed(tmp_path):
    cfg = _cfg_with_advisory(tmp_path)  # strategy_id = prev_day_breakdown_v1
    save_advisory(_build_advisory(allowed_strategies=["short_composite_v1"]),
                  cfg.advisory_path)
    matrix = MatrixEventLog()
    proceed, _ = _load_and_check_advisory(cfg, matrix, _now())
    assert proceed is False
    skip_events = [e for e in matrix.events
                   if getattr(e, "reason_code", "") == "ADVISORY_STRATEGY_NOT_ALLOWED"]
    assert len(skip_events) == 1


def test_advisory_gate_scales_risk_when_scalar_below_one(tmp_path):
    cfg = _cfg_with_advisory(tmp_path)
    save_advisory(_build_advisory(confidence_multiplier=Decimal("0.5")),
                  cfg.advisory_path)
    matrix = MatrixEventLog()
    proceed, eff_risk = _load_and_check_advisory(cfg, matrix, _now())
    assert proceed is True
    expected = (cfg.risk_pct * Decimal("0.5")).quantize(Decimal("0.0000001"))
    assert eff_risk == expected


def test_advisory_gate_logs_invalid_event_on_malformed_file(tmp_path):
    cfg = _cfg_with_advisory(tmp_path)
    cfg.advisory_path.write_text("{not valid json")
    matrix = MatrixEventLog()
    proceed, eff_risk = _load_and_check_advisory(cfg, matrix, _now())
    # Falls back to default → proceeds normally.
    assert proceed is True
    assert eff_risk == cfg.risk_pct
    invalid_events = [e for e in matrix.events
                      if getattr(e, "reason_code", "") == "ADVISORY_INVALID"]
    assert len(invalid_events) == 1


def test_advisory_gate_logs_invalid_event_on_expired_file(tmp_path):
    cfg = _cfg_with_advisory(tmp_path)
    # Build an advisory that expires in the past.
    past = _now() - timedelta(hours=48)
    expired = ResearchState(
        as_of=past,
        expires_at=past + timedelta(hours=1),
        assets=["BTC"], event_type="none",
        severity=Decimal("0"), directional_bias=Decimal("0"),
        confidence_multiplier=Decimal("1.0"), trade_policy="normal",
        model_id="m", prompt_version="1.0",
    )
    save_advisory(expired, cfg.advisory_path)
    matrix = MatrixEventLog()
    proceed, _ = _load_and_check_advisory(cfg, matrix, _now())
    assert proceed is True  # falls back to default
    invalid_events = [e for e in matrix.events
                      if getattr(e, "reason_code", "") == "ADVISORY_INVALID"]
    assert len(invalid_events) == 1
