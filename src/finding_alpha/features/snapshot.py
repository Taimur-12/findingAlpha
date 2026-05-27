"""
Feature snapshot builder.

build_feature_df() → full historical DataFrame of all features (for research).
build_snapshot()   → FeatureSnapshot for a single row (for trading pipeline).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd

from finding_alpha.contracts.features import FeatureSnapshot
from .indicators import (
    rsi, macd, ema, ema_slope,
    atr, bollinger_bands, adx, supertrend,
)
from .orderflow import (
    volume_zscore, funding_zscore,
    oi_delta, oi_zscore,
    merge_funding, merge_oi,
)
from .structure import (
    session_vwap, session_high_low,
    prev_day_high_low, prev_week_high_low,
)

FEATURE_VERSION = "1.0"

# ATR/bandwidth percentile window: 90 trading days
_PCT_PERIOD_15M = 90 * 96   # 90 days × 96 bars/day
_PCT_PERIOD_1H  = 90 * 24   # 90 days × 24 bars/day
_PCT_PERIOD_DEFAULT = 500


def _pct_period(timeframe: str) -> int:
    return {"15m": _PCT_PERIOD_15M, "1h": _PCT_PERIOD_1H}.get(timeframe, _PCT_PERIOD_DEFAULT)


def _to_float(df: pd.DataFrame) -> pd.DataFrame:
    """Convert string OHLCV columns to float in place (copy)."""
    df = df.copy()
    for col in ("open", "high", "low", "close", "volume", "quote_volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    return df.sort_values("open_time").reset_index(drop=True)


def _d(val) -> Optional[Decimal]:
    """Float → Decimal, None on NaN/inf."""
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if np.isnan(f) or np.isinf(f):
        return None
    return Decimal(f"{f:.8f}")


def build_feature_df(
    candles: pd.DataFrame,
    funding: pd.DataFrame | None = None,
    oi: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Compute all features for the full candle history.

    Returns a DataFrame with the same row count as candles (NaN during warmup).
    Suitable for research, backtesting, and building individual snapshots.
    """
    df = _to_float(candles)
    pp = _pct_period(str(df["timeframe"].iloc[0]) if "timeframe" in df.columns else "1h")

    close = df["close"]
    high  = df["high"]
    low   = df["low"]

    # ── Merge funding and OI ──────────────────────────────────────────────────
    if funding is not None and not funding.empty:
        df = merge_funding(df, funding)
    else:
        df["funding_rate"] = np.nan
        df["funding_stale"] = True

    if oi is not None and not oi.empty:
        df = merge_oi(df, oi)
    else:
        df["oi_value"] = np.nan
        df["oi_stale"] = True

    # ── Momentum ──────────────────────────────────────────────────────────────
    df["rsi_6"]  = rsi(close, 6)
    df["rsi_14"] = rsi(close, 14)
    df["rsi_24"] = rsi(close, 24)

    macd_df = macd(close)
    df = pd.concat([df, macd_df], axis=1)

    # ── Trend ─────────────────────────────────────────────────────────────────
    df["ema_20"]  = ema(close, 20)
    df["ema_50"]  = ema(close, 50)
    df["ema_200"] = ema(close, 200)
    df["ema_200_slope"] = ema_slope(df["ema_200"])

    # ── Volatility ────────────────────────────────────────────────────────────
    atr_df = atr(high, low, close, period=14, pct_period=pp)
    df = pd.concat([df, atr_df], axis=1)

    bb_df = bollinger_bands(close, period=20, n_std=2.0, bw_pct_period=pp)
    df = pd.concat([df, bb_df], axis=1)

    # ── Directional ───────────────────────────────────────────────────────────
    df["adx_14"] = adx(high, low, close, period=14)
    df["supertrend_direction"] = supertrend(high, low, close, period=10, multiplier=3.0)

    # ── Structure ─────────────────────────────────────────────────────────────
    df["session_vwap"] = session_vwap(df).values
    sl_df = session_high_low(df)
    df["session_high"] = sl_df["session_high"].values
    df["session_low"]  = sl_df["session_low"].values
    pdhl = prev_day_high_low(df)
    df["prev_day_high"] = pdhl["prev_day_high"].values
    df["prev_day_low"]  = pdhl["prev_day_low"].values
    pwhl = prev_week_high_low(df)
    df["prev_week_high"] = pwhl["prev_week_high"].values
    df["prev_week_low"]  = pwhl["prev_week_low"].values

    # ── Order-flow ────────────────────────────────────────────────────────────
    df["volume_z_score"] = volume_zscore(df["volume"])

    # Funding z-score (only if funding data present)
    if df["funding_rate"].notna().any():
        df["funding_z_score"] = funding_zscore(df["funding_rate"].astype(float))
    else:
        df["funding_z_score"] = np.nan

    # OI delta and z-score (only if OI present)
    if "oi_value" in df.columns and df["oi_value"].notna().any():
        oi_s = df["oi_value"].astype(float)
        df["oi_delta"]  = oi_delta(oi_s)
        df["oi_z_score"] = oi_zscore(oi_s)
    else:
        df["oi_delta"]  = np.nan
        df["oi_z_score"] = np.nan

    return df


def build_snapshot(
    feature_df: pd.DataFrame,
    venue: str,
    symbol: str,
    timeframe: str,
    feature_version: str = FEATURE_VERSION,
    row_idx: int = -1,
) -> FeatureSnapshot:
    """
    Assemble a FeatureSnapshot from a single row of the feature DataFrame.

    row_idx defaults to -1 (latest). The row must correspond to a final candle.
    """
    row = feature_df.iloc[row_idx]
    ts = pd.Timestamp(row["open_time"])
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")

    return FeatureSnapshot(
        venue=venue,
        symbol=symbol,
        timeframe=timeframe,
        ts=ts.to_pydatetime(),
        feature_version=feature_version,
        # Price
        close=_d(row.get("close")),
        ema_20=_d(row.get("ema_20")),
        ema_50=_d(row.get("ema_50")),
        ema_200=_d(row.get("ema_200")),
        ema_200_slope=_d(row.get("ema_200_slope")),
        # Momentum
        rsi_6=_d(row.get("rsi_6")),
        rsi_14=_d(row.get("rsi_14")),
        rsi_24=_d(row.get("rsi_24")),
        macd_line=_d(row.get("macd_line")),
        macd_signal=_d(row.get("macd_signal")),
        macd_histogram=_d(row.get("macd_histogram")),
        macd_histogram_slope=_d(row.get("macd_histogram_slope")),
        # Volatility
        atr_14=_d(row.get("atr_14")),
        atr_percentile=_d(row.get("atr_percentile")),
        bb_upper=_d(row.get("bb_upper")),
        bb_middle=_d(row.get("bb_middle")),
        bb_lower=_d(row.get("bb_lower")),
        bb_percent_b=_d(row.get("bb_percent_b")),
        bb_bandwidth=_d(row.get("bb_bandwidth")),
        bb_bandwidth_percentile=_d(row.get("bb_bandwidth_percentile")),
        # Trend
        adx_14=_d(row.get("adx_14")),
        supertrend_direction=row.get("supertrend_direction") or None,
        # Structure
        session_vwap=_d(row.get("session_vwap")),
        session_high=_d(row.get("session_high")),
        session_low=_d(row.get("session_low")),
        prev_day_high=_d(row.get("prev_day_high")),
        prev_day_low=_d(row.get("prev_day_low")),
        prev_week_high=_d(row.get("prev_week_high")),
        prev_week_low=_d(row.get("prev_week_low")),
        # Order-flow
        volume_z_score=_d(row.get("volume_z_score")),
        funding_rate=_d(row.get("funding_rate")),
        funding_z_score=_d(row.get("funding_z_score")),
        oi_value=_d(row.get("oi_value")),
        oi_delta=_d(row.get("oi_delta")),
        oi_z_score=_d(row.get("oi_z_score")),
        # Quality flags
        funding_stale=bool(row.get("funding_stale", True)),
        oi_stale=bool(row.get("oi_stale", True)),
        reference_venue_missing=False,
    )
