"""
Rule-based market regime classifier.

classify_regime(snapshot) → RegimeState

Classification priority (highest wins):
  1. crisis          — ATR percentile ≥ 95 AND funding extreme
  2. high_volatility — ATR percentile ≥ 80
  3. trend_up        — EMA 20 > 50 > 200, ADX ≥ 20, RSI 14 > 50
  4. trend_down      — EMA 20 < 50 < 200, ADX ≥ 20, RSI 14 < 50
  5. breakout_pending— BB bandwidth percentile ≤ 15 (squeeze)
  6. range           — ADX < 20 or indeterminate trend
  7. unknown         — insufficient features
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState

_ZERO = Decimal("0")
_ONE = Decimal("1")

REGIME_VERSION = "1.0"


def _d(val) -> Optional[Decimal]:
    return val if val is not None else None


def classify_regime(
    snapshot: FeatureSnapshot,
    regime_version: str = REGIME_VERSION,
) -> RegimeState:
    """Deterministic regime classification from a FeatureSnapshot."""
    evidence: dict[str, str] = {}
    blocked: list[str] = []
    now = datetime.now(timezone.utc)

    def _missing(*fields: str) -> bool:
        return any(getattr(snapshot, f) is None for f in fields)

    # ── 1. Crisis ─────────────────────────────────────────────────────────────
    if not _missing("atr_percentile", "funding_rate", "funding_z_score"):
        atr_pct = float(snapshot.atr_percentile)
        f_zscore = float(snapshot.funding_z_score)
        if atr_pct >= 95 and abs(f_zscore) >= 3.0:
            evidence["atr_percentile"] = f"{atr_pct:.1f}"
            evidence["funding_z_score"] = f"{f_zscore:.2f}"
            blocked = ["liquidity_sweep_v1", "squeeze_v1", "trend_pullback_v1"]
            return RegimeState(
                venue=snapshot.venue, symbol=snapshot.symbol,
                timeframe=snapshot.timeframe, classified_at=now,
                regime_version=regime_version,
                regime="crisis",
                confidence=Decimal("0.90"),
                evidence=evidence, blocked_strategies=blocked,
            )

    # ── 2. High volatility ────────────────────────────────────────────────────
    if not _missing("atr_percentile"):
        atr_pct = float(snapshot.atr_percentile)
        if atr_pct >= 80:
            evidence["atr_percentile"] = f"{atr_pct:.1f}"
            return RegimeState(
                venue=snapshot.venue, symbol=snapshot.symbol,
                timeframe=snapshot.timeframe, classified_at=now,
                regime_version=regime_version,
                regime="high_volatility",
                confidence=Decimal("0.75"),
                evidence=evidence, blocked_strategies=[],
            )

    # ── 3 & 4. Trend up / Trend down ─────────────────────────────────────────
    if not _missing("ema_20", "ema_50", "ema_200", "adx_14", "rsi_14"):
        e20 = float(snapshot.ema_20)
        e50 = float(snapshot.ema_50)
        e200 = float(snapshot.ema_200)
        adx_val = float(snapshot.adx_14)
        rsi = float(snapshot.rsi_14)

        if adx_val >= 20:
            if e20 > e50 > e200 and rsi > 50:
                evidence["ema_stack"] = "20>50>200"
                evidence["adx"] = f"{adx_val:.1f}"
                evidence["rsi_14"] = f"{rsi:.1f}"
                confidence = Decimal("0.80") if adx_val >= 25 else Decimal("0.65")
                return RegimeState(
                    venue=snapshot.venue, symbol=snapshot.symbol,
                    timeframe=snapshot.timeframe, classified_at=now,
                    regime_version=regime_version,
                    regime="trend_up",
                    confidence=confidence,
                    evidence=evidence, blocked_strategies=[],
                )

            if e20 < e50 < e200 and rsi < 50:
                evidence["ema_stack"] = "20<50<200"
                evidence["adx"] = f"{adx_val:.1f}"
                evidence["rsi_14"] = f"{rsi:.1f}"
                confidence = Decimal("0.80") if adx_val >= 25 else Decimal("0.65")
                return RegimeState(
                    venue=snapshot.venue, symbol=snapshot.symbol,
                    timeframe=snapshot.timeframe, classified_at=now,
                    regime_version=regime_version,
                    regime="trend_down",
                    confidence=confidence,
                    evidence=evidence, blocked_strategies=[],
                )

    # ── 5. Breakout pending (BB squeeze) ──────────────────────────────────────
    if not _missing("bb_bandwidth_percentile"):
        bw_pct = float(snapshot.bb_bandwidth_percentile)
        if bw_pct <= 15:
            evidence["bb_bandwidth_percentile"] = f"{bw_pct:.1f}"
            return RegimeState(
                venue=snapshot.venue, symbol=snapshot.symbol,
                timeframe=snapshot.timeframe, classified_at=now,
                regime_version=regime_version,
                regime="breakout_pending",
                confidence=Decimal("0.60"),
                evidence=evidence, blocked_strategies=[],
            )

    # ── 6. Range ──────────────────────────────────────────────────────────────
    if not _missing("adx_14"):
        adx_val = float(snapshot.adx_14)
        evidence["adx"] = f"{adx_val:.1f}"
        return RegimeState(
            venue=snapshot.venue, symbol=snapshot.symbol,
            timeframe=snapshot.timeframe, classified_at=now,
            regime_version=regime_version,
            regime="range",
            confidence=Decimal("0.55") if adx_val < 20 else Decimal("0.40"),
            evidence=evidence, blocked_strategies=[],
        )

    # ── 7. Unknown ────────────────────────────────────────────────────────────
    missing_fields = [
        f for f in ("ema_20", "ema_50", "ema_200", "adx_14", "rsi_14",
                    "atr_percentile", "bb_bandwidth_percentile")
        if getattr(snapshot, f) is None
    ]
    evidence["missing"] = ",".join(missing_fields)
    return RegimeState(
        venue=snapshot.venue, symbol=snapshot.symbol,
        timeframe=snapshot.timeframe, classified_at=now,
        regime_version=regime_version,
        regime="unknown",
        confidence=Decimal("0.10"),
        evidence=evidence, blocked_strategies=[],
    )
