"""
Previous Day Breakdown Continuation - v1.

Setup: BTC closes below the prior day low during a bearish or compression regime
on elevated volume. The strategy trades continuation, not reversal.

Entry: next candle can fill a limit at the breakdown candle close.
Stop:  entry + 0.75 ATR.
Target: entry - 4.5 ATR.
Horizon: 12 hours.

Allowed sessions exclude NY solo because Phase 7B evidence showed that slice was
consistently adverse for the related breakout family.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.strategies.fast_reject import check_features, check_rr


STRATEGY_ID = "prev_day_breakdown_v1"
STRATEGY_VERSION = "1.0"

_REQUIRED = ("close", "prev_day_low", "atr_14", "volume_z_score")
_ALLOWED_REGIMES = frozenset({"trend_down", "breakout_pending"})
_ALLOWED_SESSIONS = frozenset({"asia", "london", "london_ny_overlap", "wind_down"})
_MIN_VOLUME_Z = 2.0
_STOP_ATR = 0.75
_TARGET_ATR = 4.5
_HORIZON_MINUTES = 720


def find_signal(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    now: datetime,
) -> Optional[SignalCandidate]:
    if regime.regime not in _ALLOWED_REGIMES:
        return None
    session = _session_name(now)
    if session not in _ALLOWED_SESSIONS:
        return None

    rejected, _ = check_features(snapshot, _REQUIRED)
    if rejected:
        return None

    close = float(snapshot.close)
    prev_day_low = float(snapshot.prev_day_low)
    atr = float(snapshot.atr_14)
    volume_z = float(snapshot.volume_z_score)

    if atr <= 0 or volume_z < _MIN_VOLUME_Z:
        return None
    if close >= prev_day_low:
        return None

    stop = close + _STOP_ATR * atr
    target = close - _TARGET_ATR * atr
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
        base_confidence=Decimal("0.70"),
        expected_horizon_minutes=_HORIZON_MINUTES,
        entry_reference=snapshot.close,
        invalidation_price=Decimal(f"{stop:.2f}"),
        target_prices=[Decimal(f"{target:.2f}")],
        evidence={
            "breakdown_level": f"{prev_day_low:.2f}",
            "volume_z_score": f"{volume_z:.2f}",
            "atr_14": f"{atr:.2f}",
            "regime": regime.regime,
            "session": session,
        },
        feature_version=snapshot.feature_version,
        strategy_version=STRATEGY_VERSION,
    )


def _session_name(ts: datetime) -> str:
    hour = ts.hour
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 13:
        return "london"
    if 13 <= hour < 17:
        return "london_ny_overlap"
    if 17 <= hour < 22:
        return "ny"
    return "wind_down"
