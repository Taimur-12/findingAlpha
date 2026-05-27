"""
Phase 5 strategy tests.

Core invariants:
  - Fast reject fires for blocked regimes and missing features
  - No signal when entry conditions are not met
  - Signal is produced when all conditions align
  - Produced signals are valid SignalCandidates (invalidation/entry relationship)
  - Signal confidence and R:R are within expected bounds
  - Immutability: signals cannot be mutated
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.strategies.liquidity_sweep_v1 import find_signal as sweep_signal
from finding_alpha.strategies.squeeze_v1 import find_signal as squeeze_signal
from finding_alpha.strategies.trend_pullback_v1 import find_signal as pullback_signal


# ── Helpers ────────────────────────────────────────────────────────────────────

_NOW = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)


def _regime(regime: str, confidence: str = "0.70") -> RegimeState:
    return RegimeState(
        venue="bybit", symbol="BTCUSDT", timeframe="1h",
        classified_at=_NOW, regime_version="1.0",
        regime=regime,
        confidence=Decimal(confidence),
        evidence={}, blocked_strategies=[],
    )


def _snap(**overrides) -> FeatureSnapshot:
    defaults = dict(
        venue="bybit", symbol="BTCUSDT", timeframe="1h",
        ts=_NOW, feature_version="1.0",
    )
    defaults.update(overrides)
    return FeatureSnapshot(**defaults)


def _full_sweep_snap(close=50000.0, pdl=49500.0, pdh=51000.0, atr=500.0, vol_z=2.0):
    return _snap(
        close=Decimal(f"{close:.2f}"),
        prev_day_low=Decimal(f"{pdl:.2f}"),
        prev_day_high=Decimal(f"{pdh:.2f}"),
        atr_14=Decimal(f"{atr:.2f}"),
        volume_z_score=Decimal(f"{vol_z:.2f}"),
    )


def _full_squeeze_snap(
    close=50500.0, bb_upper=50400.0, bb_lower=49600.0, bb_middle=50000.0,
    bb_bw_pct=12.0, atr=500.0, vol_z=1.0, supertrend="up",
):
    return _snap(
        close=Decimal(f"{close:.2f}"),
        bb_upper=Decimal(f"{bb_upper:.2f}"),
        bb_lower=Decimal(f"{bb_lower:.2f}"),
        bb_middle=Decimal(f"{bb_middle:.2f}"),
        bb_bandwidth_percentile=Decimal(f"{bb_bw_pct:.1f}"),
        atr_14=Decimal(f"{atr:.2f}"),
        volume_z_score=Decimal(f"{vol_z:.2f}"),
        supertrend_direction=supertrend,
    )


def _full_pullback_snap(
    close=50200.0, e20=51000.0, e50=50000.0, e200=48000.0,
    adx=25.0, rsi=50.0, atr=300.0,
):
    return _snap(
        close=Decimal(f"{close:.2f}"),
        ema_20=Decimal(f"{e20:.2f}"),
        ema_50=Decimal(f"{e50:.2f}"),
        ema_200=Decimal(f"{e200:.2f}"),
        adx_14=Decimal(f"{adx:.1f}"),
        rsi_14=Decimal(f"{rsi:.1f}"),
        atr_14=Decimal(f"{atr:.2f}"),
    )


# ── liquidity_sweep_v1 ─────────────────────────────────────────────────────────

class TestLiquiditySweep:
    def test_blocked_regime_returns_none(self):
        snap = _full_sweep_snap()
        for bad in ("crisis", "high_volatility", "trend_down"):
            assert sweep_signal(snap, _regime(bad), 49000.0, 49200.0, _NOW) is None

    def test_missing_feature_returns_none(self):
        snap = _snap()  # all None
        assert sweep_signal(snap, _regime("range"), 49000.0, 49200.0, _NOW) is None

    def test_no_sweep_returns_none(self):
        """Bar low stays above prev_day_low — not a sweep."""
        snap = _full_sweep_snap(close=50000.0, pdl=49500.0)
        bar_low = 49600.0  # above pdl
        assert sweep_signal(snap, _regime("range"), 50300.0, bar_low, _NOW) is None

    def test_sweep_no_reclaim_returns_none(self):
        """Bar low goes below pdl but close stays below it — no reclaim."""
        snap = _full_sweep_snap(close=49400.0, pdl=49500.0)  # close < pdl
        bar_low = 49200.0
        assert sweep_signal(snap, _regime("range"), 50000.0, bar_low, _NOW) is None

    def test_low_volume_returns_none(self):
        snap = _full_sweep_snap(vol_z=0.5)  # below threshold
        bar_low = 49200.0  # below pdl=49500
        assert sweep_signal(snap, _regime("range"), 50000.0, bar_low, _NOW) is None

    def test_long_sweep_produces_signal(self):
        snap = _full_sweep_snap(close=49700.0, pdl=49500.0, atr=500.0, vol_z=2.5)
        bar_low = 49300.0  # below pdl
        sig = sweep_signal(snap, _regime("range"), 50000.0, bar_low, _NOW)
        assert sig is not None
        assert sig.side == "long"
        assert sig.invalidation_price < sig.entry_reference

    def test_short_sweep_produces_signal(self):
        snap = _full_sweep_snap(close=50800.0, pdh=51000.0, atr=500.0, vol_z=2.0)
        bar_high = 51300.0  # above pdh
        sig = sweep_signal(snap, _regime("range"), bar_high, 50500.0, _NOW)
        assert sig is not None
        assert sig.side == "short"
        assert sig.invalidation_price > sig.entry_reference

    def test_ambiguous_double_sweep_returns_none(self):
        """Bar sweeps both sides — signal skipped."""
        snap = _full_sweep_snap(
            close=50000.0, pdl=49500.0, pdh=50500.0, atr=300.0, vol_z=2.0
        )
        # close > pdl (reclaim) and close < pdh (reclaim) with sweeps on both sides
        sig = sweep_signal(snap, _regime("range"), 50700.0, 49200.0, _NOW)
        assert sig is None

    def test_signal_rr_at_least_1_5(self):
        snap = _full_sweep_snap(close=49700.0, pdl=49500.0, atr=500.0, vol_z=2.0)
        bar_low = 49300.0
        sig = sweep_signal(snap, _regime("range"), 50000.0, bar_low, _NOW)
        assert sig is not None
        entry = float(sig.entry_reference)
        stop  = float(sig.invalidation_price)
        tgt   = float(sig.target_prices[0])
        risk   = entry - stop
        reward = tgt - entry
        assert reward >= 1.5 * risk

    def test_signal_is_immutable(self):
        snap = _full_sweep_snap(close=49700.0, pdl=49500.0, atr=300.0, vol_z=2.0)
        sig = sweep_signal(snap, _regime("range"), 50000.0, 49300.0, _NOW)
        with pytest.raises(Exception):
            sig.side = "short"

    def test_signal_expires_after_horizon(self):
        snap = _full_sweep_snap(close=49700.0, pdl=49500.0, atr=500.0, vol_z=2.0)
        sig = sweep_signal(snap, _regime("range"), 50000.0, 49300.0, _NOW)
        assert sig is not None
        assert sig.expires_at == _NOW + timedelta(minutes=240)


# ── squeeze_v1 ─────────────────────────────────────────────────────────────────

class TestSqueeze:
    def test_blocked_regime_returns_none(self):
        snap = _full_squeeze_snap()
        for bad in ("crisis", "high_volatility"):
            assert squeeze_signal(snap, _regime(bad), _NOW) is None

    def test_missing_feature_returns_none(self):
        snap = _snap()
        assert squeeze_signal(snap, _regime("range"), _NOW) is None

    def test_not_in_squeeze_returns_none(self):
        """bw_percentile > 20 — not in squeeze."""
        snap = _full_squeeze_snap(bb_bw_pct=30.0)
        assert squeeze_signal(snap, _regime("range"), _NOW) is None

    def test_no_breakout_returns_none(self):
        """In squeeze but price not outside bands."""
        snap = _full_squeeze_snap(close=50000.0, bb_upper=50400.0, bb_lower=49600.0, bb_bw_pct=10.0)
        # close (50000) is inside bands
        assert squeeze_signal(snap, _regime("breakout_pending"), _NOW) is None

    def test_long_breakout_produces_signal(self):
        snap = _full_squeeze_snap(
            close=50500.0, bb_upper=50400.0, bb_lower=49600.0,
            bb_middle=50000.0, bb_bw_pct=10.0, atr=500.0, vol_z=1.0, supertrend="up",
        )
        sig = squeeze_signal(snap, _regime("breakout_pending"), _NOW)
        assert sig is not None
        assert sig.side == "long"
        assert sig.invalidation_price < sig.entry_reference

    def test_short_breakout_produces_signal(self):
        snap = _full_squeeze_snap(
            close=49500.0, bb_upper=50400.0, bb_lower=49600.0,
            bb_middle=50000.0, bb_bw_pct=10.0, atr=500.0, vol_z=1.0, supertrend="down",
        )
        sig = squeeze_signal(snap, _regime("breakout_pending"), _NOW)
        assert sig is not None
        assert sig.side == "short"
        assert sig.invalidation_price > sig.entry_reference

    def test_signal_rr_at_least_1_5(self):
        snap = _full_squeeze_snap(
            close=50500.0, bb_upper=50400.0, bb_middle=50000.0,
            bb_bw_pct=10.0, atr=500.0, vol_z=1.0, supertrend="up",
        )
        sig = squeeze_signal(snap, _regime("breakout_pending"), _NOW)
        assert sig is not None
        entry  = float(sig.entry_reference)
        stop   = float(sig.invalidation_price)
        target = float(sig.target_prices[0])
        risk   = abs(entry - stop)
        reward = abs(target - entry)
        assert reward >= 1.5 * risk

    def test_supertrend_mismatch_returns_none(self):
        """Price breaks above bb_upper but supertrend is 'down'."""
        snap = _full_squeeze_snap(
            close=50500.0, bb_upper=50400.0, bb_bw_pct=10.0, vol_z=1.0, supertrend="down",
        )
        assert squeeze_signal(snap, _regime("breakout_pending"), _NOW) is None


# ── trend_pullback_v1 ──────────────────────────────────────────────────────────

class TestTrendPullback:
    def test_wrong_regime_returns_none(self):
        snap = _full_pullback_snap()
        for bad in ("crisis", "high_volatility", "range", "breakout_pending", "unknown"):
            assert pullback_signal(snap, _regime(bad), _NOW) is None

    def test_missing_feature_returns_none(self):
        snap = _snap()
        assert pullback_signal(snap, _regime("trend_up"), _NOW) is None

    def test_ema_stack_broken_returns_none(self):
        """EMA stack not aligned — not a trend."""
        snap = _full_pullback_snap(e20=50000.0, e50=51000.0, e200=48000.0)  # e20 < e50
        assert pullback_signal(snap, _regime("trend_up"), _NOW) is None

    def test_price_not_near_ema50_returns_none(self):
        """Price too far above EMA 50 — not pulling back."""
        snap = _full_pullback_snap(
            close=53000.0, e20=52000.0, e50=50000.0, e200=48000.0, atr=300.0,
        )
        # 53000 - 50000 = 3000 >> 1.5 * 300 = 450
        assert pullback_signal(snap, _regime("trend_up"), _NOW) is None

    def test_rsi_out_of_pullback_range_returns_none(self):
        snap_overbought = _full_pullback_snap(rsi=72.0)
        snap_oversold   = _full_pullback_snap(rsi=28.0)
        assert pullback_signal(snap_overbought, _regime("trend_up"), _NOW) is None
        assert pullback_signal(snap_oversold,   _regime("trend_up"), _NOW) is None

    def test_low_adx_returns_none(self):
        snap = _full_pullback_snap(adx=15.0)
        assert pullback_signal(snap, _regime("trend_up"), _NOW) is None

    def test_long_pullback_produces_signal(self):
        snap = _full_pullback_snap(
            close=50200.0, e20=51000.0, e50=50000.0, e200=48000.0,
            adx=25.0, rsi=50.0, atr=300.0,
        )
        sig = pullback_signal(snap, _regime("trend_up"), _NOW)
        assert sig is not None
        assert sig.side == "long"
        assert sig.invalidation_price < sig.entry_reference

    def test_short_pullback_produces_signal(self):
        snap = _full_pullback_snap(
            close=49800.0, e20=49000.0, e50=50000.0, e200=52000.0,
            adx=25.0, rsi=50.0, atr=300.0,
        )
        sig = pullback_signal(snap, _regime("trend_down"), _NOW)
        assert sig is not None
        assert sig.side == "short"
        assert sig.invalidation_price > sig.entry_reference

    def test_high_adx_gives_higher_confidence(self):
        snap_strong = _full_pullback_snap(adx=30.0)
        snap_weak   = _full_pullback_snap(adx=22.0)
        sig_strong = pullback_signal(snap_strong, _regime("trend_up"), _NOW)
        sig_weak   = pullback_signal(snap_weak,   _regime("trend_up"), _NOW)
        assert sig_strong is not None and sig_weak is not None
        assert sig_strong.base_confidence > sig_weak.base_confidence

    def test_signal_rr_at_least_1_5(self):
        snap = _full_pullback_snap(
            close=50200.0, e20=51000.0, e50=50000.0, e200=48000.0,
            adx=25.0, rsi=50.0, atr=300.0,
        )
        sig = pullback_signal(snap, _regime("trend_up"), _NOW)
        assert sig is not None
        entry  = float(sig.entry_reference)
        stop   = float(sig.invalidation_price)
        target = float(sig.target_prices[0])
        risk   = abs(entry - stop)
        reward = abs(target - entry)
        assert reward >= 1.5 * risk

    def test_signal_is_immutable(self):
        snap = _full_pullback_snap()
        sig = pullback_signal(snap, _regime("trend_up"), _NOW)
        with pytest.raises(Exception):
            sig.side = "short"
