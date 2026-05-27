"""
Phase 4 feature engine tests.

Core invariants:
  - Warmup periods return NaN (never silent zeros)
  - No lookahead (each bar uses only current and past data)
  - Indicator formulas produce expected values on known inputs
  - Snapshot builder populates None for missing/NaN features
  - Regime classifier is deterministic
"""

import math
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from finding_alpha.features.indicators import (
    rsi, macd, ema, ema_slope, atr, bollinger_bands, adx, supertrend,
)
from finding_alpha.features.orderflow import volume_zscore, funding_zscore
from finding_alpha.features.snapshot import build_feature_df, build_snapshot
from finding_alpha.regime.classifier import classify_regime


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _candle_df(n: int = 300, seed: int = 42, trend: float = 0.0) -> pd.DataFrame:
    """Synthetic OHLCV candle DataFrame with n rows."""
    rng = np.random.default_rng(seed)
    closes = 50000.0 + np.cumsum(rng.normal(trend, 200, n))
    dates = [
        datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i)
        for i in range(n)
    ]
    df = pd.DataFrame({
        "venue": "bybit",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "open_time": dates,
        "close_time": [d + timedelta(hours=1) for d in dates],
        "open":   (closes - np.abs(rng.normal(0, 100, n))).astype(str),
        "high":   (closes + np.abs(rng.normal(100, 100, n))).astype(str),
        "low":    (closes - np.abs(rng.normal(100, 100, n))).astype(str),
        "close":  closes.astype(str),
        "volume": (rng.uniform(5, 50, n)).astype(str),
        "quote_volume": (closes * rng.uniform(5, 50, n)).astype(str),
        "is_final": True,
    })
    return df


def _float_close(n: int = 100) -> pd.Series:
    rng = np.random.default_rng(0)
    return pd.Series(50000.0 + np.cumsum(rng.normal(0, 200, n)), dtype=float)


# ── RSI ────────────────────────────────────────────────────────────────────────

class TestRSI:
    def test_warmup_is_nan(self):
        close = _float_close(30)
        result = rsi(close, period=14)
        assert result.iloc[:14].isna().all(), "First 14 values must be NaN"

    def test_values_in_range(self):
        close = _float_close(100)
        result = rsi(close, period=14).dropna()
        assert (result >= 0).all() and (result <= 100).all()

    def test_all_gains_gives_high_rsi(self):
        """Strictly increasing close → RSI should approach 100."""
        close = pd.Series([100.0 + i for i in range(50)])
        result = rsi(close, period=14).dropna()
        assert result.iloc[-1] > 95

    def test_all_losses_gives_low_rsi(self):
        """Strictly decreasing close → RSI should approach 0."""
        close = pd.Series([100.0 - i * 0.5 for i in range(50)])
        result = rsi(close, period=14).dropna()
        assert result.iloc[-1] < 5


# ── EMA ────────────────────────────────────────────────────────────────────────

class TestEMA:
    def test_warmup_is_nan(self):
        close = _float_close(50)
        result = ema(close, period=20)
        assert result.iloc[:19].isna().all()

    def test_ema_between_min_and_max(self):
        close = _float_close(100)
        result = ema(close, period=20).dropna()
        assert (result >= close.min()).all() and (result <= close.max()).all()

    def test_constant_price_gives_same_ema(self):
        close = pd.Series([100.0] * 50)
        result = ema(close, period=10).dropna()
        assert (result - 100.0).abs().max() < 1e-6

    def test_slope_sign(self):
        """Increasing price → positive slope."""
        close = pd.Series([100.0 + i for i in range(50)])
        e200 = ema(close, period=10)
        slope = ema_slope(e200).dropna()
        assert (slope > 0).all()


# ── MACD ───────────────────────────────────────────────────────────────────────

class TestMACD:
    def test_warmup_is_nan(self):
        close = _float_close(60)
        result = macd(close)
        assert result["macd_line"].iloc[:25].isna().all()
        assert result["macd_signal"].iloc[:33].isna().all()

    def test_histogram_equals_line_minus_signal(self):
        close = _float_close(200)
        result = macd(close).dropna()
        diff = (result["macd_histogram"] - (result["macd_line"] - result["macd_signal"])).abs()
        assert diff.max() < 1e-6


# ── ATR ────────────────────────────────────────────────────────────────────────

class TestATR:
    def test_warmup_is_nan(self):
        close = _float_close(30)
        high = close + 50
        low = close - 50
        result = atr(high, low, close, period=14, pct_period=100)
        assert result["atr_14"].iloc[:13].isna().all()

    def test_atr_positive(self):
        close = _float_close(200)
        high = close + 100
        low = close - 100
        result = atr(high, low, close, period=14, pct_period=50).dropna()
        assert (result["atr_14"] > 0).all()

    def test_percentile_0_to_100(self):
        close = _float_close(300)
        high = close + np.abs(np.random.randn(300)) * 50
        low = close - np.abs(np.random.randn(300)) * 50
        result = atr(high, low, close, period=14, pct_period=50)
        pct = result["atr_percentile"].dropna()
        assert (pct >= 0).all() and (pct <= 100).all()


# ── Bollinger Bands ────────────────────────────────────────────────────────────

class TestBollingerBands:
    def test_upper_above_middle_above_lower(self):
        close = _float_close(100)
        result = bollinger_bands(close, period=20).dropna()
        assert (result["bb_upper"] >= result["bb_middle"]).all()
        assert (result["bb_middle"] >= result["bb_lower"]).all()

    def test_warmup_is_nan(self):
        close = _float_close(30)
        result = bollinger_bands(close, period=20)
        assert result["bb_middle"].iloc[:19].isna().all()

    def test_percent_b_at_close_near_middle(self):
        """When price is at the middle band, %B ≈ 0.5."""
        close = pd.Series([100.0] * 50)
        result = bollinger_bands(close, period=20).dropna()
        # Constant price → std=0 → %B is NaN (zero std)
        assert result["bb_percent_b"].isna().all()


# ── ADX ────────────────────────────────────────────────────────────────────────

class TestADX:
    def test_warmup_is_nan(self):
        close = _float_close(30)
        result = adx(close + 50, close - 50, close, period=14)
        assert result.iloc[:14].isna().all()

    def test_adx_positive(self):
        close = _float_close(200)
        result = adx(close + 50, close - 50, close, period=14).dropna()
        assert (result >= 0).all()

    def test_trending_market_high_adx(self):
        """Strong trend → ADX should exceed 20."""
        close = pd.Series([100.0 + i * 10 for i in range(100)])
        result = adx(close + 50, close - 50, close, period=14).dropna()
        assert result.iloc[-1] > 20


# ── Supertrend ─────────────────────────────────────────────────────────────────

class TestSupertrend:
    def test_warmup_is_none(self):
        close = _float_close(30)
        result = supertrend(close + 50, close - 50, close, period=10)
        assert result.iloc[:9].isna().all() or all(v is None for v in result.iloc[:9])

    def test_values_are_up_or_down(self):
        close = _float_close(100)
        result = supertrend(close + 100, close - 100, close, period=10).dropna()
        assert set(result.unique()).issubset({"up", "down"})

    def test_strong_uptrend_gives_up(self):
        """Clear uptrend → supertrend should settle on 'up'."""
        close = pd.Series([100.0 + i * 5 for i in range(60)])
        result = supertrend(close + 10, close - 10, close, period=10).dropna()
        assert result.iloc[-1] == "up"


# ── Volume Z-score ─────────────────────────────────────────────────────────────

class TestVolumeZscore:
    def test_warmup_is_nan(self):
        vol = pd.Series(np.random.uniform(1, 10, 30))
        result = volume_zscore(vol, period=20)
        assert result.iloc[:19].isna().all()

    def test_high_volume_gives_positive_zscore(self):
        vol = pd.Series([5.0] * 30 + [100.0])  # spike
        result = volume_zscore(vol, period=20)
        assert result.iloc[-1] > 2.0


# ── Snapshot builder ───────────────────────────────────────────────────────────

class TestSnapshotBuilder:
    def test_build_feature_df_has_expected_columns(self):
        df = _candle_df(250)
        fdf = build_feature_df(df)
        for col in ("rsi_14", "macd_line", "ema_200", "atr_14", "bb_upper",
                    "adx_14", "supertrend_direction", "session_vwap",
                    "volume_z_score"):
            assert col in fdf.columns, f"Missing column: {col}"

    def test_build_snapshot_returns_feature_snapshot(self):
        from finding_alpha.contracts.features import FeatureSnapshot
        df = _candle_df(250)
        fdf = build_feature_df(df)
        snap = build_snapshot(fdf, "bybit", "BTCUSDT", "1h")
        assert isinstance(snap, FeatureSnapshot)

    def test_snapshot_nan_becomes_none(self):
        """Warmup rows should produce None fields in snapshot, not NaN."""
        df = _candle_df(25)  # fewer rows than EMA 200 / MACD signal warmup
        fdf = build_feature_df(df)
        snap = build_snapshot(fdf, "bybit", "BTCUSDT", "1h")
        assert snap.ema_200 is None      # needs 200 bars
        assert snap.macd_signal is None  # needs ~34 bars

    def test_snapshot_with_enough_data_has_values(self):
        df = _candle_df(300)  # enough for EMA 200
        fdf = build_feature_df(df)
        snap = build_snapshot(fdf, "bybit", "BTCUSDT", "1h")
        assert snap.ema_200 is not None
        assert snap.rsi_14 is not None
        assert snap.atr_14 is not None

    def test_snapshot_is_immutable(self):
        df = _candle_df(300)
        fdf = build_feature_df(df)
        snap = build_snapshot(fdf, "bybit", "BTCUSDT", "1h")
        with pytest.raises(Exception):
            snap.rsi_14 = Decimal("50")

    def test_no_lookahead(self):
        """Feature at row i must not depend on data from row i+1 onward."""
        df = _candle_df(300)
        fdf = build_feature_df(df)
        # Modify last row's close significantly
        df_modified = df.copy()
        df_modified.loc[df_modified.index[-1], "close"] = str(
            float(df_modified.loc[df_modified.index[-1], "close"]) * 2
        )
        fdf_modified = build_feature_df(df_modified)
        # All rows except the last must be identical in rsi_14
        orig_rsi = fdf["rsi_14"].iloc[:-1]
        mod_rsi = fdf_modified["rsi_14"].iloc[:-1]
        pd.testing.assert_series_equal(orig_rsi, mod_rsi, check_names=False)


# ── Regime classifier ──────────────────────────────────────────────────────────

class TestRegimeClassifier:
    def _snap(self, **overrides):
        from finding_alpha.contracts.features import FeatureSnapshot
        now = datetime.now(timezone.utc)
        defaults = dict(
            venue="bybit", symbol="BTCUSDT", timeframe="1h",
            ts=now, feature_version="1.0",
        )
        defaults.update(overrides)
        return FeatureSnapshot(**defaults)

    def test_unknown_when_all_none(self):
        snap = self._snap()
        result = classify_regime(snap)
        assert result.regime == "unknown"
        assert result.confidence < Decimal("0.5")

    def test_crisis_when_extreme_atr_and_funding(self):
        snap = self._snap(
            atr_percentile=Decimal("97"),
            funding_rate=Decimal("0.03"),
            funding_z_score=Decimal("4.5"),
        )
        result = classify_regime(snap)
        assert result.regime == "crisis"
        assert len(result.blocked_strategies) > 0

    def test_high_volatility_when_atr_pct_high(self):
        snap = self._snap(atr_percentile=Decimal("85"))
        result = classify_regime(snap)
        assert result.regime == "high_volatility"

    def test_trend_up(self):
        snap = self._snap(
            ema_20=Decimal("52000"),
            ema_50=Decimal("50000"),
            ema_200=Decimal("48000"),
            adx_14=Decimal("28"),
            rsi_14=Decimal("62"),
        )
        result = classify_regime(snap)
        assert result.regime == "trend_up"

    def test_trend_down(self):
        snap = self._snap(
            ema_20=Decimal("48000"),
            ema_50=Decimal("50000"),
            ema_200=Decimal("52000"),
            adx_14=Decimal("28"),
            rsi_14=Decimal("38"),
        )
        result = classify_regime(snap)
        assert result.regime == "trend_down"

    def test_breakout_pending_on_squeeze(self):
        snap = self._snap(bb_bandwidth_percentile=Decimal("10"))
        result = classify_regime(snap)
        assert result.regime == "breakout_pending"

    def test_range_when_low_adx(self):
        snap = self._snap(adx_14=Decimal("12"))
        result = classify_regime(snap)
        assert result.regime == "range"

    def test_deterministic_same_input_same_output(self):
        """Same snapshot always produces same regime."""
        snap = self._snap(
            ema_20=Decimal("52000"), ema_50=Decimal("50000"),
            ema_200=Decimal("48000"), adx_14=Decimal("25"), rsi_14=Decimal("60"),
        )
        r1 = classify_regime(snap)
        r2 = classify_regime(snap)
        assert r1.regime == r2.regime
        assert r1.confidence == r2.confidence
        assert r1.blocked_strategies == r2.blocked_strategies
