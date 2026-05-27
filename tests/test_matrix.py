"""
Matrix event log tests.
Core invariant: replaying the same log always produces the same final state.
"""

import pytest
import tempfile
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from pathlib import Path

from finding_alpha.contracts import CandleEvent, SignalCandidate, RiskDecision, reason_codes
from finding_alpha.matrix import MatrixEventLog, replay


def utc_now():
    return datetime.now(timezone.utc)


def make_candle(symbol="BTCUSDT", timeframe="15m", close=75000.0) -> CandleEvent:
    now = utc_now()
    return CandleEvent(
        venue="bybit", symbol=symbol, timeframe=timeframe,
        open_time=now, close_time=now,
        open=Decimal(str(close - 100)),
        high=Decimal(str(close + 200)),
        low=Decimal(str(close - 200)),
        close=Decimal(str(close)),
        volume=Decimal("12.345"),
        quote_volume=Decimal("926000"),
        is_final=True,
    )


def make_signal(entry=75000.0, stop=74500.0) -> SignalCandidate:
    now = utc_now()
    return SignalCandidate(
        strategy_id="liquidity_sweep_v1",
        venue="bybit", symbol="BTCUSDT", timeframe="15m",
        side="long", created_at=now, expires_at=now + timedelta(minutes=60),
        base_confidence=Decimal("0.72"), expected_horizon_minutes=60,
        entry_reference=Decimal(str(entry)),
        invalidation_price=Decimal(str(stop)),
        feature_version="1.0", strategy_version="1.0",
    )


# ── Basic append and projection ───────────────────────────────────────────────

def test_append_and_retrieve_candle():
    log = MatrixEventLog()
    candle = make_candle()
    log.append(candle)

    retrieved = log.latest_candle("bybit", "BTCUSDT", "15m")
    assert retrieved is not None
    assert retrieved.close == candle.close
    assert log.event_count() == 1


def test_latest_candle_updates_on_new_append():
    log = MatrixEventLog()
    log.append(make_candle(close=75000.0))
    log.append(make_candle(close=75500.0))

    latest = log.latest_candle("bybit", "BTCUSDT", "15m")
    assert latest.close == Decimal("75500.0")


def test_open_signals_tracked():
    log = MatrixEventLog()
    signal = make_signal()
    log.append(signal)

    assert len(log.open_signals()) == 1
    assert log.open_signals()[0].signal_id == signal.signal_id


# ── Deterministic replay ──────────────────────────────────────────────────────

def test_deterministic_replay():
    """
    Core invariant: replaying the same log file twice gives identical state.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "test_events.jsonl"

        # Build the log
        log1 = MatrixEventLog(log_path=log_path)
        log1.append(make_candle(close=75000.0))
        log1.append(make_candle(close=75300.0))
        log1.append(make_signal(entry=75300.0, stop=74800.0))

        # Replay it
        log2 = replay(log_path)

        assert log2.event_count() == log1.event_count()
        assert log2.latest_candle("bybit", "BTCUSDT", "15m").close == \
               log1.latest_candle("bybit", "BTCUSDT", "15m").close
        assert len(log2.open_signals()) == len(log1.open_signals())


def test_replay_twice_gives_identical_state():
    """Replay the same file twice — both replays must agree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "events.jsonl"

        log = MatrixEventLog(log_path=log_path)
        for price in [74000.0, 74500.0, 75000.0, 75500.0]:
            log.append(make_candle(close=price))
        log.append(make_signal(entry=75500.0, stop=75000.0))

        replay_a = replay(log_path)
        replay_b = replay(log_path)

        assert replay_a.event_count() == replay_b.event_count()
        candle_a = replay_a.latest_candle("bybit", "BTCUSDT", "15m")
        candle_b = replay_b.latest_candle("bybit", "BTCUSDT", "15m")
        assert candle_a.close == candle_b.close
        assert candle_a.event_id == candle_b.event_id


# ── Immutability of returned events ──────────────────────────────────────────

def test_events_list_is_a_copy():
    """log.events returns a copy — mutating it does not affect the log."""
    log = MatrixEventLog()
    log.append(make_candle())

    events_copy = log.events
    events_copy.clear()

    assert log.event_count() == 1  # original unaffected
