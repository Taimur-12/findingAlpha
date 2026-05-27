"""
Short Composite — v1.

SHORT-only strategy that combines two complementary entry triggers:

  1. EMA20 intra-bar rejection  (trend_down, confirmed EMA stack)
     Bar opens above EMA20, closes at or below EMA20. Price rejected at
     the 20-period moving average during a bearish trend. High-quality
     trigger — win rate ~48%, profit factor ~1.53 in isolation.
     Stop: EMA50 + 0.5 ATR.  Target: entry − 4.5 ATR.

  2. Previous-day low breakdown  (trend_down OR breakout_pending)
     Close breaks below the prior day's low with above-average volume
     (volume Z-score ≥ 1.0). Continuation of established bearish
     momentum. Inherits the breakdown family's structural edge.
     Stop: entry + 0.75 ATR.  Target: entry − 4.5 ATR.

Signal priority: breakdown fires if conditions for both are met on the
same bar (stronger signal). EMA rejection fires next.

Adjusted Phase 7C gate (one instrument, SHORT-only):
  - Trades ≥ 225
  - Profit factor ≥ 1.25
  - Expectancy R > 0
  - Walk-forward profitable windows ≥ 45 %
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.strategies.fast_reject import check_features, check_rr


STRATEGY_ID = "short_composite_v1"
STRATEGY_VERSION = "1.0"

_REQUIRED = (
    "close", "ema_20", "ema_50", "ema_200",
    "adx_14", "atr_14", "prev_day_low", "volume_z_score",
)
_HORIZON_MINUTES = 720  # 12 h


def find_signal(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    row: pd.Series,
    now: datetime,
) -> Optional[SignalCandidate]:
    if regime.regime not in ("trend_down", "breakout_pending"):
        return None

    rejected, _ = check_features(snapshot, _REQUIRED)
    if rejected:
        return None

    close   = float(snapshot.close)
    e20     = float(snapshot.ema_20)
    e50     = float(snapshot.ema_50)
    e200    = float(snapshot.ema_200)
    adx     = float(snapshot.adx_14)
    atr     = float(snapshot.atr_14)
    pdl     = float(snapshot.prev_day_low)
    vz      = float(snapshot.volume_z_score)
    bar_open = float(row["open"])

    if atr <= 0:
        return None

    # ── Signal 1: Previous-day low breakdown (priority) ───────────────────────
    if vz >= 1.0 and close < pdl:
        stop   = close + 0.75 * atr
        target = close - 4.5 * atr
        rejected, _ = check_rr(close, stop, target)
        if not rejected:
            return _make_signal(snapshot, stop, target, now, "breakdown")

    # ── Signal 2: EMA20 intra-bar rejection ───────────────────────────────────
    if (regime.regime == "trend_down"
            and adx >= 20
            and e20 < e50 < e200
            and bar_open > e20 >= close):
        stop   = e50 + 0.5 * atr
        target = close - 4.5 * atr
        rejected, _ = check_rr(close, stop, target)
        if not rejected:
            return _make_signal(snapshot, stop, target, now, "ema_rejection")

    return None


def _make_signal(
    snapshot: FeatureSnapshot,
    stop: float,
    target: float,
    now: datetime,
    trigger: str,
) -> SignalCandidate:
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
        evidence={"trigger": trigger},
        feature_version=snapshot.feature_version,
        strategy_version=STRATEGY_VERSION,
    )
