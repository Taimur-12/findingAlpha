"""
Liquidity Sweep Reversal — v1.

Setup: price wicks below (long) or above (short) a key structural level
(prev_day_low / prev_day_high), triggering resting stops, then reclaims that
level within the same bar on elevated volume.

Entry:  close of the sweep candle (limit at close accepted on bar completion).
Stop:   beyond the sweep extreme (wick low - 0.25×ATR for long).
Target: entry + 2.0×ATR.
Min R:R: 1.5.

Blocked regimes: crisis, high_volatility, trend_down (for longs) / trend_up (for shorts).
Long and short setups are evaluated; whichever fires first wins. If both fire on the
same bar the signal is skipped (ambiguous candle).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from .fast_reject import check_regime, check_features, check_rr

STRATEGY_ID = "liquidity_sweep_v1"
STRATEGY_VERSION = "1.0"

_BLOCKED_LONG  = frozenset({"crisis", "high_volatility", "trend_down"})
_BLOCKED_SHORT = frozenset({"crisis", "high_volatility", "trend_up"})
_REQUIRED = (
    "close", "prev_day_low", "prev_day_high", "atr_14", "volume_z_score",
)

_MIN_VOLUME_ZSCORE = 1.5
_STOP_BUFFER_ATR   = 0.25
_TARGET_ATR_MULT   = 2.0
_HORIZON_MINUTES   = 240   # 4 h — one full trading session quarter


def find_signal(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    bar_high: float,
    bar_low: float,
    now: datetime,
) -> Optional[SignalCandidate]:
    """
    Evaluate a completed bar for a liquidity sweep setup.

    bar_high / bar_low are the raw float H/L of the current candle —
    FeatureSnapshot does not carry these fields.
    """
    rejected, _ = check_features(snapshot, _REQUIRED)
    if rejected:
        return None

    close    = float(snapshot.close)
    atr      = float(snapshot.atr_14)
    vol_z    = float(snapshot.volume_z_score)
    pdl      = float(snapshot.prev_day_low)
    pdh      = float(snapshot.prev_day_high)

    if atr <= 0 or vol_z < _MIN_VOLUME_ZSCORE:
        return None

    long_setup  = bar_low < pdl and close > pdl
    short_setup = bar_high > pdh and close < pdh

    # Ambiguous / double-sweep bar → skip
    if long_setup and short_setup:
        return None

    if long_setup:
        rejected, _ = check_regime(regime, _BLOCKED_LONG)
        if rejected:
            return None
        stop   = bar_low - _STOP_BUFFER_ATR * atr
        target = close + _TARGET_ATR_MULT * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None
        confidence = Decimal("0.70") if vol_z > 2.0 else Decimal("0.65")
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
                "sweep_level": f"{pdl:.2f}",
                "bar_low": f"{bar_low:.2f}",
                "volume_z_score": f"{vol_z:.2f}",
                "atr_14": f"{atr:.2f}",
                "regime": regime.regime,
            },
            feature_version=snapshot.feature_version,
            strategy_version=STRATEGY_VERSION,
        )

    if short_setup:
        rejected, _ = check_regime(regime, _BLOCKED_SHORT)
        if rejected:
            return None
        stop   = bar_high + _STOP_BUFFER_ATR * atr
        target = close - _TARGET_ATR_MULT * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None
        confidence = Decimal("0.70") if vol_z > 2.0 else Decimal("0.65")
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
                "sweep_level": f"{pdh:.2f}",
                "bar_high": f"{bar_high:.2f}",
                "volume_z_score": f"{vol_z:.2f}",
                "atr_14": f"{atr:.2f}",
                "regime": regime.regime,
            },
            feature_version=snapshot.feature_version,
            strategy_version=STRATEGY_VERSION,
        )

    return None
