"""
EMA Scalp 15m — v1.

SHORT-only momentum scalp on the 15-minute timeframe.

Entry: supertrend = "down" AND EMA20 < EMA50
Stop:   entry + 0.75 x ATR14
Target: entry - 1.5 x ATR14   (2:1 R/R)
Max hold: 120 minutes (8 bars)

Designed for high signal frequency — fires on any 15m bar where
short-side structure is confirmed. Used to demonstrate live pipeline activity.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.strategies.fast_reject import check_features, check_rr


STRATEGY_ID = "ema_scalp_15m_v1"
STRATEGY_VERSION = "1.2"

_REQUIRED = ("close", "ema_20", "ema_50", "atr_14", "supertrend_direction")
_HORIZON_MINUTES = 180


def find_signal(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    row: pd.Series,
    now: datetime,
) -> Optional[SignalCandidate]:
    if regime.regime == "crisis":
        return None

    rejected, _ = check_features(snapshot, _REQUIRED)
    if rejected:
        return None

    close  = float(snapshot.close)
    e20    = float(snapshot.ema_20)
    e50    = float(snapshot.ema_50)
    atr    = float(snapshot.atr_14)
    st_dir = snapshot.supertrend_direction

    if atr <= 0:
        return None

    if st_dir != "down" or e20 >= e50:
        return None

    stop   = close + 0.75 * atr
    target = close - 1.5 * atr

    rejected, _ = check_rr(close, stop, target, min_rr=1.5)
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
        base_confidence=Decimal("0.55"),
        expected_horizon_minutes=_HORIZON_MINUTES,
        entry_reference=Decimal(f"{close:.2f}"),
        invalidation_price=Decimal(f"{stop:.2f}"),
        target_prices=[Decimal(f"{target:.2f}")],
        evidence={
            "supertrend": "down",
            "ema_stack": f"20({e20:.0f})<50({e50:.0f})",
            "regime": regime.regime,
        },
        feature_version=snapshot.feature_version,
        strategy_version=STRATEGY_VERSION,
    )
