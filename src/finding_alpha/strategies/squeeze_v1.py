"""
BB Squeeze Breakout — v1.

Setup: Bollinger Band bandwidth percentile ≤ 20 (compression), then price
closes outside the bands in the direction of the supertrend.

Entry:  close of the breakout bar.
Stop:   bb_middle (middle band invalidates the breakout premise).
Target: entry ± 2.0×ATR.
Min R:R: 1.5.

Blocked regimes: crisis, high_volatility.
Works in range and breakout_pending; exits early if trend_up / trend_down
takes over (regime check at signal time only).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from .fast_reject import check_regime, check_features, check_rr

STRATEGY_ID = "squeeze_v1"
STRATEGY_VERSION = "1.0"

_BLOCKED = frozenset({"crisis", "high_volatility"})
_REQUIRED = (
    "close", "bb_upper", "bb_lower", "bb_middle",
    "bb_bandwidth_percentile", "atr_14", "volume_z_score", "supertrend_direction",
)

_SQUEEZE_THRESHOLD  = 20.0   # bb_bandwidth_percentile
_MIN_VOLUME_ZSCORE  = 0.5
_TARGET_ATR_MULT    = 2.0
_HORIZON_MINUTES    = 180    # 3 h


def find_signal(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    now: datetime,
) -> Optional[SignalCandidate]:
    rejected, _ = check_regime(regime, _BLOCKED)
    if rejected:
        return None

    rejected, _ = check_features(snapshot, _REQUIRED)
    if rejected:
        return None

    bw_pct = float(snapshot.bb_bandwidth_percentile)
    if bw_pct > _SQUEEZE_THRESHOLD:
        return None

    close     = float(snapshot.close)
    bb_upper  = float(snapshot.bb_upper)
    bb_lower  = float(snapshot.bb_lower)
    bb_middle = float(snapshot.bb_middle)
    atr       = float(snapshot.atr_14)
    vol_z     = float(snapshot.volume_z_score)
    supertrend = snapshot.supertrend_direction

    if atr <= 0 or vol_z < _MIN_VOLUME_ZSCORE:
        return None

    long_setup  = close > bb_upper and supertrend == "up"
    short_setup = close < bb_lower and supertrend == "down"

    if long_setup and short_setup:
        return None

    if long_setup:
        stop   = bb_middle
        target = close + _TARGET_ATR_MULT * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None
        return SignalCandidate(
            strategy_id=STRATEGY_ID,
            venue=snapshot.venue,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            side="long",
            created_at=now,
            expires_at=now + timedelta(minutes=_HORIZON_MINUTES),
            base_confidence=Decimal("0.60"),
            expected_horizon_minutes=_HORIZON_MINUTES,
            entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"),
            target_prices=[Decimal(f"{target:.2f}")],
            evidence={
                "bb_bandwidth_percentile": f"{bw_pct:.1f}",
                "bb_upper": f"{bb_upper:.2f}",
                "volume_z_score": f"{vol_z:.2f}",
                "atr_14": f"{atr:.2f}",
                "regime": regime.regime,
            },
            feature_version=snapshot.feature_version,
            strategy_version=STRATEGY_VERSION,
        )

    if short_setup:
        stop   = bb_middle
        target = close - _TARGET_ATR_MULT * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None
        return SignalCandidate(
            strategy_id=STRATEGY_ID,
            venue=snapshot.venue,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            side="short",
            created_at=now,
            expires_at=now + timedelta(minutes=_HORIZON_MINUTES),
            base_confidence=Decimal("0.60"),
            expected_horizon_minutes=_HORIZON_MINUTES,
            entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"),
            target_prices=[Decimal(f"{target:.2f}")],
            evidence={
                "bb_bandwidth_percentile": f"{bw_pct:.1f}",
                "bb_lower": f"{bb_lower:.2f}",
                "volume_z_score": f"{vol_z:.2f}",
                "atr_14": f"{atr:.2f}",
                "regime": regime.regime,
            },
            feature_version=snapshot.feature_version,
            strategy_version=STRATEGY_VERSION,
        )

    return None
