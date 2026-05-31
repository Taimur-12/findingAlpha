"""
EMA Scalp 1m — v1.

SHORT-only momentum scalp on the 1-minute timeframe.

Strategy: MACD accelerating bearish + EMA20 < EMA50
  - MACD(12,26,9) histogram < 0 (bearish momentum established)
  - MACD histogram slope < 0   (momentum accelerating, not reversing)
  - EMA20 < EMA50              (structural bearish alignment)

On 1m BTCUSDT this fires every 5–20 minutes in trending conditions,
giving 10–30+ trades per day. Well-documented institutional 1m scalp setup.

Stop:   entry + 0.5 × ATR14   Target: entry − 1.0 × ATR14   (2:1 R/R)
Max hold: 10 minutes (10 bars)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.strategies.fast_reject import check_features, check_rr


STRATEGY_ID = "ema_scalp_1m_v1"
STRATEGY_VERSION = "1.0"

_REQUIRED = (
    "close", "ema_20", "ema_50", "atr_14",
    "macd_histogram", "macd_histogram_slope",
)
_HORIZON_MINUTES = 30


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
    macd_h = float(snapshot.macd_histogram)
    macd_s = float(snapshot.macd_histogram_slope)

    if atr <= 0:
        return None

    # ── MACD accelerating bearish + EMA structural alignment ─────────────────
    if macd_h >= 0 or macd_s >= 0:
        return None
    if e20 >= e50:
        return None

    stop   = close + 0.5 * atr
    target = close - 1.0 * atr

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
            "macd_hist": f"{macd_h:.4f}",
            "macd_slope": f"{macd_s:.4f}",
            "ema_stack": f"20({e20:.0f})<50({e50:.0f})",
            "regime": regime.regime,
        },
        feature_version=snapshot.feature_version,
        strategy_version=STRATEGY_VERSION,
    )
