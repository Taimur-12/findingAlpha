"""
Feature and regime contracts.
FeatureSnapshot: all computed indicators at a decision timestamp.
RegimeState: current market regime classification.
Both are immutable and versioned.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _new_id() -> str:
    return str(uuid4())


class FeatureSnapshot(BaseModel):
    """
    All deterministic features computed at a single decision timestamp.
    A feature that cannot be computed honestly is None, never guessed.
    Every snapshot carries a feature_version so backtests are reproducible.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    snapshot_id: str = Field(default_factory=_new_id)
    venue: str
    symbol: str
    timeframe: str
    ts: datetime                          # timestamp of the final candle close
    feature_version: str                  # e.g. "1.0" — bump when formula changes

    # ── Price features ────────────────────────────────────────────────────────
    close: Optional[Decimal] = None
    ema_20: Optional[Decimal] = None
    ema_50: Optional[Decimal] = None
    ema_200: Optional[Decimal] = None
    ema_200_slope: Optional[Decimal] = None

    # ── Momentum features ─────────────────────────────────────────────────────
    rsi_6: Optional[Decimal] = None
    rsi_14: Optional[Decimal] = None
    rsi_24: Optional[Decimal] = None
    macd_line: Optional[Decimal] = None
    macd_signal: Optional[Decimal] = None
    macd_histogram: Optional[Decimal] = None
    macd_histogram_slope: Optional[Decimal] = None

    # ── Volatility features ───────────────────────────────────────────────────
    atr_14: Optional[Decimal] = None
    atr_percentile: Optional[Decimal] = None       # 0-100, rank over rolling 90d
    bb_upper: Optional[Decimal] = None
    bb_middle: Optional[Decimal] = None
    bb_lower: Optional[Decimal] = None
    bb_percent_b: Optional[Decimal] = None
    bb_bandwidth: Optional[Decimal] = None
    bb_bandwidth_percentile: Optional[Decimal] = None

    # ── Trend features ────────────────────────────────────────────────────────
    adx_14: Optional[Decimal] = None
    supertrend_direction: Optional[Literal["up", "down"]] = None

    # ── Structure features ────────────────────────────────────────────────────
    session_vwap: Optional[Decimal] = None
    session_high: Optional[Decimal] = None
    session_low: Optional[Decimal] = None
    prev_day_high: Optional[Decimal] = None
    prev_day_low: Optional[Decimal] = None
    prev_week_high: Optional[Decimal] = None
    prev_week_low: Optional[Decimal] = None

    # ── Order-flow features ───────────────────────────────────────────────────
    volume_z_score: Optional[Decimal] = None
    cvd: Optional[Decimal] = None                  # cumulative volume delta
    taker_buy_imbalance: Optional[Decimal] = None  # fallback when CVD unavailable
    spread_bps: Optional[Decimal] = None

    # ── Derivatives positioning features ─────────────────────────────────────
    funding_rate: Optional[Decimal] = None
    funding_z_score: Optional[Decimal] = None
    oi_value: Optional[Decimal] = None
    oi_delta: Optional[Decimal] = None
    oi_z_score: Optional[Decimal] = None

    # ── Cross-asset features ──────────────────────────────────────────────────
    btc_correlation_30: Optional[Decimal] = None   # rolling 30-period correlation

    # ── Data quality flags ────────────────────────────────────────────────────
    funding_stale: bool = False
    oi_stale: bool = False
    reference_venue_missing: bool = False

    @model_validator(mode="after")
    def ts_must_be_utc(self) -> FeatureSnapshot:
        if self.ts.tzinfo is None:
            raise ValueError("ts must be timezone-aware (UTC)")
        return self


class RegimeState(BaseModel):
    """
    Market regime classification for a symbol/timeframe.
    A strong higher-timeframe regime can block lower-timeframe signals.
    Unknown regime means reduced confidence, not aggressive trading.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    state_id: str = Field(default_factory=_new_id)
    venue: str
    symbol: str
    timeframe: str
    classified_at: datetime
    regime_version: str                   # bump when classification rules change

    regime: Literal[
        "trend_up",
        "trend_down",
        "range",
        "breakout_pending",
        "high_volatility",
        "crisis",
        "unknown",
    ]
    confidence: Decimal                   # 0.0 to 1.0
    evidence: dict[str, str] = Field(default_factory=dict)  # key -> reason
    blocked_strategies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_confidence(self) -> RegimeState:
        if not (Decimal("0") <= self.confidence <= Decimal("1")):
            raise ValueError("confidence must be between 0 and 1")
        if self.classified_at.tzinfo is None:
            raise ValueError("classified_at must be timezone-aware (UTC)")
        return self
