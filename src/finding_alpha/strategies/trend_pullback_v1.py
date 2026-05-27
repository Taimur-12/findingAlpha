"""
Trend Pullback — v1.

Setup: confirmed trend (EMA 20 > 50 > 200 for long, inverted for short),
price pulls back to within 1.5×ATR of EMA 50, RSI cools to 40–60 range,
ADX ≥ 20 (trend still active).

Entry:  close of the pullback bar when all conditions align.
Stop:   EMA 50 - 0.5×ATR (long) / EMA 50 + 0.5×ATR (short).
Target: entry + 2.5×ATR.
Min R:R: 1.5.

Allowed regimes: trend_up (long only), trend_down (short only).
Blocked regimes: all others.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from .fast_reject import check_features, check_rr

STRATEGY_ID = "trend_pullback_v1"
STRATEGY_VERSION = "1.0"

_REQUIRED = (
    "close", "ema_20", "ema_50", "ema_200",
    "adx_14", "rsi_14", "atr_14",
)

_MIN_ADX              = 20.0
_RSI_LOW              = 40.0
_RSI_HIGH             = 60.0
_PROXIMITY_ATR_MULT   = 1.5   # price must be within N×ATR of EMA 50
_STOP_ATR_BUFFER      = 0.5
_TARGET_ATR_MULT      = 2.5
_HORIZON_MINUTES      = 360   # 6 h


def find_signal(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    now: datetime,
) -> Optional[SignalCandidate]:
    # Only fires in confirmed trend regimes
    if regime.regime not in ("trend_up", "trend_down"):
        return None

    rejected, _ = check_features(snapshot, _REQUIRED)
    if rejected:
        return None

    close  = float(snapshot.close)
    e20    = float(snapshot.ema_20)
    e50    = float(snapshot.ema_50)
    e200   = float(snapshot.ema_200)
    adx    = float(snapshot.adx_14)
    rsi    = float(snapshot.rsi_14)
    atr    = float(snapshot.atr_14)

    if atr <= 0 or adx < _MIN_ADX:
        return None

    if not (_RSI_LOW <= rsi <= _RSI_HIGH):
        return None

    if regime.regime == "trend_up":
        # EMA stack confirmed
        if not (e20 > e50 > e200):
            return None
        # Price pulling back toward EMA 50 but not below it
        if not (e50 <= close <= e50 + _PROXIMITY_ATR_MULT * atr):
            return None

        stop   = e50 - _STOP_ATR_BUFFER * atr
        target = close + _TARGET_ATR_MULT * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None

        confidence = Decimal("0.75") if adx >= 28 else Decimal("0.65")
        return SignalCandidate(
            strategy_id=STRATEGY_ID,
            venue=snapshot.venue,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            side="long",
            created_at=now,
            expires_at=now + timedelta(minutes=_HORIZON_MINUTES),
            base_confidence=confidence,
            expected_horizon_minutes=_HORIZON_MINUTES,
            entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"),
            target_prices=[Decimal(f"{target:.2f}")],
            evidence={
                "ema_stack": "20>50>200",
                "adx_14": f"{adx:.1f}",
                "rsi_14": f"{rsi:.1f}",
                "atr_14": f"{atr:.2f}",
                "regime": regime.regime,
            },
            feature_version=snapshot.feature_version,
            strategy_version=STRATEGY_VERSION,
        )

    if regime.regime == "trend_down":
        if not (e20 < e50 < e200):
            return None
        # Price pulling back toward EMA 50 but not above it
        if not (e50 - _PROXIMITY_ATR_MULT * atr <= close <= e50):
            return None

        stop   = e50 + _STOP_ATR_BUFFER * atr
        target = close - _TARGET_ATR_MULT * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None

        confidence = Decimal("0.75") if adx >= 28 else Decimal("0.65")
        return SignalCandidate(
            strategy_id=STRATEGY_ID,
            venue=snapshot.venue,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            side="short",
            created_at=now,
            expires_at=now + timedelta(minutes=_HORIZON_MINUTES),
            base_confidence=confidence,
            expected_horizon_minutes=_HORIZON_MINUTES,
            entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"),
            target_prices=[Decimal(f"{target:.2f}")],
            evidence={
                "ema_stack": "20<50<200",
                "adx_14": f"{adx:.1f}",
                "rsi_14": f"{rsi:.1f}",
                "atr_14": f"{atr:.2f}",
                "regime": regime.regime,
            },
            feature_version=snapshot.feature_version,
            strategy_version=STRATEGY_VERSION,
        )

    return None
