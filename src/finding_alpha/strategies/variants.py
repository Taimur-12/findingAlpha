"""Research-only parameterized strategy variants for Phase 7B."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.strategies.fast_reject import check_features, check_rr


@dataclass(frozen=True)
class LiquiditySweepParams:
    strategy_id: str
    allowed_regimes: tuple[str, ...] = ("range", "breakout_pending")
    allowed_sessions: tuple[str, ...] = ("asia", "london", "london_ny_overlap", "ny", "wind_down")
    min_volume_z: float = 1.5
    min_wick_atr: float = 0.0
    stop_buffer_atr: float = 0.25
    target_atr: float = 2.0
    horizon_minutes: int = 240
    min_rr: float = 1.5


@dataclass(frozen=True)
class TrendPullbackParams:
    strategy_id: str
    side: str = "both"  # both, long, short
    allowed_sessions: tuple[str, ...] = ("asia", "london", "london_ny_overlap", "ny", "wind_down")
    proximity_atr: float = 1.5
    stop_atr: float = 0.5
    target_atr: float = 2.5
    min_adx: float = 20.0
    rsi_low: float = 40.0
    rsi_high: float = 60.0
    horizon_minutes: int = 360
    min_rr: float = 1.5


@dataclass(frozen=True)
class SqueezeParams:
    strategy_id: str
    allowed_regimes: tuple[str, ...] = ("breakout_pending", "range", "trend_up", "trend_down")
    allowed_sessions: tuple[str, ...] = ("asia", "london", "london_ny_overlap", "ny", "wind_down")
    max_bandwidth_pct: float = 20.0
    min_volume_z: float = 0.5
    target_atr: float = 2.0
    horizon_minutes: int = 180
    min_rr: float = 1.5


@dataclass(frozen=True)
class PrevDayBreakoutParams:
    strategy_id: str
    side: str = "both"
    allowed_regimes: tuple[str, ...] = ("trend_up", "trend_down", "breakout_pending")
    allowed_sessions: tuple[str, ...] = ("asia", "london", "london_ny_overlap", "ny", "wind_down")
    min_volume_z: float = 0.5
    stop_atr: float = 1.0
    target_atr: float = 2.0
    horizon_minutes: int = 480
    min_rr: float = 1.5


def liquidity_sweep_variant(params: LiquiditySweepParams):
    required = ("close", "prev_day_low", "prev_day_high", "atr_14", "volume_z_score")

    def find_signal(
        snapshot: FeatureSnapshot,
        regime: RegimeState,
        row: pd.Series,
        now: datetime,
    ) -> Optional[SignalCandidate]:
        if regime.regime not in params.allowed_regimes:
            return None
        if _session_name(now) not in params.allowed_sessions:
            return None
        rejected, _ = check_features(snapshot, required)
        if rejected:
            return None

        close = float(snapshot.close)
        atr = float(snapshot.atr_14)
        vol_z = float(snapshot.volume_z_score)
        pdl = float(snapshot.prev_day_low)
        pdh = float(snapshot.prev_day_high)
        high = float(row["high"])
        low = float(row["low"])

        if atr <= 0 or vol_z < params.min_volume_z:
            return None

        long_depth = (pdl - low) / atr
        short_depth = (high - pdh) / atr
        long_setup = low < pdl and close > pdl and long_depth >= params.min_wick_atr
        short_setup = high > pdh and close < pdh and short_depth >= params.min_wick_atr
        if long_setup and short_setup:
            return None

        if long_setup:
            stop = low - params.stop_buffer_atr * atr
            target = close + params.target_atr * atr
            rejected, _ = check_rr(close, stop, target, params.min_rr)
            if rejected:
                return None
            return _signal(
                params.strategy_id,
                snapshot,
                "long",
                now,
                close,
                stop,
                target,
                params.horizon_minutes,
                {"regime": regime.regime, "session": _session_name(now), "wick_atr": f"{long_depth:.2f}"},
            )

        if short_setup:
            stop = high + params.stop_buffer_atr * atr
            target = close - params.target_atr * atr
            rejected, _ = check_rr(close, stop, target, params.min_rr)
            if rejected:
                return None
            return _signal(
                params.strategy_id,
                snapshot,
                "short",
                now,
                close,
                stop,
                target,
                params.horizon_minutes,
                {"regime": regime.regime, "session": _session_name(now), "wick_atr": f"{short_depth:.2f}"},
            )

        return None

    return find_signal


def trend_pullback_variant(params: TrendPullbackParams):
    required = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "rsi_14", "atr_14")

    def find_signal(
        snapshot: FeatureSnapshot,
        regime: RegimeState,
        row: pd.Series,
        now: datetime,
    ) -> Optional[SignalCandidate]:
        if _session_name(now) not in params.allowed_sessions:
            return None
        rejected, _ = check_features(snapshot, required)
        if rejected:
            return None

        close = float(snapshot.close)
        e20 = float(snapshot.ema_20)
        e50 = float(snapshot.ema_50)
        e200 = float(snapshot.ema_200)
        adx = float(snapshot.adx_14)
        rsi = float(snapshot.rsi_14)
        atr = float(snapshot.atr_14)
        if atr <= 0 or adx < params.min_adx or not (params.rsi_low <= rsi <= params.rsi_high):
            return None

        if params.side in ("both", "long") and regime.regime == "trend_up":
            if e20 > e50 > e200 and e50 <= close <= e50 + params.proximity_atr * atr:
                stop = e50 - params.stop_atr * atr
                target = close + params.target_atr * atr
                rejected, _ = check_rr(close, stop, target, params.min_rr)
                if not rejected:
                    return _signal(params.strategy_id, snapshot, "long", now, close, stop, target, params.horizon_minutes, {"regime": regime.regime, "session": _session_name(now)})

        if params.side in ("both", "short") and regime.regime == "trend_down":
            if e20 < e50 < e200 and e50 - params.proximity_atr * atr <= close <= e50:
                stop = e50 + params.stop_atr * atr
                target = close - params.target_atr * atr
                rejected, _ = check_rr(close, stop, target, params.min_rr)
                if not rejected:
                    return _signal(params.strategy_id, snapshot, "short", now, close, stop, target, params.horizon_minutes, {"regime": regime.regime, "session": _session_name(now)})

        return None

    return find_signal


def squeeze_variant(params: SqueezeParams):
    required = (
        "close", "bb_upper", "bb_lower", "bb_middle",
        "bb_bandwidth_percentile", "atr_14", "volume_z_score", "supertrend_direction",
    )

    def find_signal(
        snapshot: FeatureSnapshot,
        regime: RegimeState,
        row: pd.Series,
        now: datetime,
    ) -> Optional[SignalCandidate]:
        if regime.regime not in params.allowed_regimes:
            return None
        if _session_name(now) not in params.allowed_sessions:
            return None
        rejected, _ = check_features(snapshot, required)
        if rejected:
            return None

        bw_pct = float(snapshot.bb_bandwidth_percentile)
        close = float(snapshot.close)
        upper = float(snapshot.bb_upper)
        lower = float(snapshot.bb_lower)
        middle = float(snapshot.bb_middle)
        atr = float(snapshot.atr_14)
        vol_z = float(snapshot.volume_z_score)
        if bw_pct > params.max_bandwidth_pct or atr <= 0 or vol_z < params.min_volume_z:
            return None

        if close > upper and snapshot.supertrend_direction == "up":
            stop = middle
            target = close + params.target_atr * atr
            rejected, _ = check_rr(close, stop, target, params.min_rr)
            if not rejected:
                return _signal(params.strategy_id, snapshot, "long", now, close, stop, target, params.horizon_minutes, {"regime": regime.regime, "session": _session_name(now)})

        if close < lower and snapshot.supertrend_direction == "down":
            stop = middle
            target = close - params.target_atr * atr
            rejected, _ = check_rr(close, stop, target, params.min_rr)
            if not rejected:
                return _signal(params.strategy_id, snapshot, "short", now, close, stop, target, params.horizon_minutes, {"regime": regime.regime, "session": _session_name(now)})

        return None

    return find_signal


def prev_day_breakout_variant(params: PrevDayBreakoutParams):
    required = ("close", "prev_day_high", "prev_day_low", "atr_14", "volume_z_score")

    def find_signal(
        snapshot: FeatureSnapshot,
        regime: RegimeState,
        row: pd.Series,
        now: datetime,
    ) -> Optional[SignalCandidate]:
        if regime.regime not in params.allowed_regimes:
            return None
        if _session_name(now) not in params.allowed_sessions:
            return None
        rejected, _ = check_features(snapshot, required)
        if rejected:
            return None

        close = float(snapshot.close)
        pdh = float(snapshot.prev_day_high)
        pdl = float(snapshot.prev_day_low)
        atr = float(snapshot.atr_14)
        vol_z = float(snapshot.volume_z_score)
        if atr <= 0 or vol_z < params.min_volume_z:
            return None

        if params.side in ("both", "long") and close > pdh and regime.regime in ("trend_up", "breakout_pending"):
            stop = close - params.stop_atr * atr
            target = close + params.target_atr * atr
            rejected, _ = check_rr(close, stop, target, params.min_rr)
            if not rejected:
                return _signal(params.strategy_id, snapshot, "long", now, close, stop, target, params.horizon_minutes, {"regime": regime.regime, "session": _session_name(now), "level": "prev_day_high"})

        if params.side in ("both", "short") and close < pdl and regime.regime in ("trend_down", "breakout_pending"):
            stop = close + params.stop_atr * atr
            target = close - params.target_atr * atr
            rejected, _ = check_rr(close, stop, target, params.min_rr)
            if not rejected:
                return _signal(params.strategy_id, snapshot, "short", now, close, stop, target, params.horizon_minutes, {"regime": regime.regime, "session": _session_name(now), "level": "prev_day_low"})

        return None

    return find_signal


def _signal(
    strategy_id: str,
    snapshot: FeatureSnapshot,
    side: str,
    now: datetime,
    entry: float,
    stop: float,
    target: float,
    horizon_minutes: int,
    evidence: dict[str, str],
) -> SignalCandidate:
    return SignalCandidate(
        strategy_id=strategy_id,
        venue=snapshot.venue,
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        side=side,
        created_at=now,
        expires_at=now + timedelta(minutes=horizon_minutes),
        base_confidence=Decimal("0.70"),
        expected_horizon_minutes=horizon_minutes,
        entry_reference=Decimal(f"{entry:.2f}"),
        invalidation_price=Decimal(f"{stop:.2f}"),
        target_prices=[Decimal(f"{target:.2f}")],
        evidence=evidence,
        feature_version=snapshot.feature_version,
        strategy_version="research",
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
