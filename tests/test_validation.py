"""
Phase 7 validation tests.

Covers the authoritative event runner's core invariants:
  - signal candle cannot be used for entry fill
  - open simulated positions block overlapping entries
  - no-lookahead prefix recomputation passes
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.validation import event_runner
from finding_alpha.validation.event_runner import ValidationConfig, run_event_validation, verify_no_lookahead


def _candles(n: int = 260) -> pd.DataFrame:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    closes = 100.0 + np.linspace(0, 10, n)
    rows = []
    for i, close in enumerate(closes):
        open_time = start + timedelta(hours=i)
        rows.append(
            {
                "venue": "bybit",
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "open_time": open_time,
                "close_time": open_time + timedelta(hours=1),
                "open": str(close),
                "high": str(close + 2),
                "low": str(close - 2),
                "close": str(close),
                "volume": str(100 + i % 5),
                "quote_volume": str((100 + i % 5) * close),
                "is_final": True,
            }
        )
    return pd.DataFrame(rows)


def test_verify_no_lookahead_passes_on_causal_features():
    candles = _candles()
    result = verify_no_lookahead(
        candles,
        funding=None,
        oi=None,
        config=ValidationConfig(warmup_bars=220),
        indices=[220, 240],
    )
    assert result["passed"] is True
    assert result["checked_rows"] == 2


def test_event_runner_enters_after_signal_candle(monkeypatch):
    candles = _candles(20)
    # Signal row is index 2. Entry can only fill from index 3 onward.
    candles.loc[2, ["high", "low", "close"]] = ["120", "90", "100"]
    candles.loc[3, ["high", "low", "close"]] = ["102", "99", "101"]
    candles.loc[4, ["high", "low", "close"]] = ["112", "101", "111"]

    def fake_strategy(
        snapshot: FeatureSnapshot,
        regime: RegimeState,
        row: pd.Series,
        now: datetime,
    ) -> SignalCandidate | None:
        if row.name != 2:
            return None
        return SignalCandidate(
            strategy_id="fake_v1",
            venue=snapshot.venue,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            side="long",
            created_at=now,
            expires_at=now + timedelta(hours=4),
            base_confidence=Decimal("0.9"),
            expected_horizon_minutes=240,
            entry_reference=Decimal("100"),
            invalidation_price=Decimal("95"),
            target_prices=[Decimal("110")],
            feature_version="test",
            strategy_version="test",
        )

    monkeypatch.setitem(event_runner.STRATEGIES, "fake_v1", fake_strategy)
    result = run_event_validation(
        candles,
        config=ValidationConfig(
            warmup_bars=1,
            strategy_ids=("fake_v1",),
            risk_config=RiskConfig(max_open_positions=1),
        ),
    )

    outcome = result.strategy_stats["fake_v1"].outcomes[0]
    signal_close_time = candles.loc[2, "close_time"]
    assert outcome.entry_ts >= signal_close_time
    assert outcome.entry_ts == candles.loc[3, "open_time"]


def test_event_runner_blocks_overlapping_positions(monkeypatch):
    candles = _candles(20)
    candles.loc[3:8, ["high", "low", "close"]] = ["105", "99", "101"]
    candles.loc[9, ["high", "low", "close"]] = ["112", "99", "111"]

    def repeated_strategy(
        snapshot: FeatureSnapshot,
        regime: RegimeState,
        row: pd.Series,
        now: datetime,
    ) -> SignalCandidate | None:
        if row.name not in (2, 3):
            return None
        return SignalCandidate(
            strategy_id="overlap_v1",
            venue=snapshot.venue,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            side="long",
            created_at=now,
            expires_at=now + timedelta(hours=8),
            base_confidence=Decimal("0.9"),
            expected_horizon_minutes=480,
            entry_reference=Decimal("100"),
            invalidation_price=Decimal("95"),
            target_prices=[Decimal("110")],
            feature_version="test",
            strategy_version="test",
        )

    monkeypatch.setitem(event_runner.STRATEGIES, "overlap_v1", repeated_strategy)
    result = run_event_validation(
        candles,
        config=ValidationConfig(
            warmup_bars=1,
            strategy_ids=("overlap_v1",),
            risk_config=RiskConfig(max_open_positions=1),
        ),
    )

    stat = result.strategy_stats["overlap_v1"]
    assert stat.signals_fired == 2
    assert stat.approved == 1
    assert stat.risk_rejected == 1
    assert stat.rejection_reasons["RISK_MAX_POSITIONS"] == 1
