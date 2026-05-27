"""
Order-flow and derivatives positioning features.

All functions operate on float-dtype pd.Series.
NaN returned for warmup periods. Never forward-filled.
"""

import numpy as np
import pandas as pd


def volume_zscore(volume: pd.Series, period: int = 20) -> pd.Series:
    """Z-score of volume relative to rolling mean/std."""
    mean = volume.rolling(period, min_periods=period).mean()
    std = volume.rolling(period, min_periods=period).std(ddof=0)
    return ((volume - mean) / std.replace(0.0, np.nan)).rename("volume_z_score")


def funding_zscore(funding_rate: pd.Series, period: int = 20) -> pd.Series:
    """Z-score of funding rate relative to rolling mean/std."""
    mean = funding_rate.rolling(period, min_periods=period).mean()
    std = funding_rate.rolling(period, min_periods=period).std(ddof=0)
    return ((funding_rate - mean) / std.replace(0.0, np.nan)).rename("funding_z_score")


def oi_delta(oi: pd.Series) -> pd.Series:
    """Percent change in open interest per bar."""
    return oi.pct_change().rename("oi_delta")


def oi_zscore(oi: pd.Series, period: int = 20) -> pd.Series:
    """Z-score of OI percent change relative to rolling mean/std."""
    delta = oi.pct_change()
    mean = delta.rolling(period, min_periods=period).mean()
    std = delta.rolling(period, min_periods=period).std(ddof=0)
    return ((delta - mean) / std.replace(0.0, np.nan)).rename("oi_z_score")


def merge_funding(candles: pd.DataFrame, funding: pd.DataFrame) -> pd.DataFrame:
    """
    Asof-merge funding rates onto candle timestamps.

    The most recent funding record at or before each candle's open_time is used.
    Staleness: if the nearest funding record is >9h old, funding_stale is set True.
    """
    if funding.empty:
        candles = candles.copy()
        candles["funding_rate"] = np.nan
        candles["funding_stale"] = True
        return candles

    f = funding[["funding_time", "funding_rate"]].copy()
    f["funding_rate"] = f["funding_rate"].astype(float)
    f = f.sort_values("funding_time").rename(columns={"funding_time": "open_time"})

    merged = pd.merge_asof(
        candles.sort_values("open_time"),
        f,
        on="open_time",
        direction="backward",
    )
    # Mark stale if the matched funding record is >9h old
    matched_age = (merged["open_time"] - merged["open_time"].shift()).abs()
    # Simple heuristic: if the last funding update is more than 9 hours before the candle
    funding_ts = f["open_time"]
    merged = merged.sort_values("open_time").reset_index(drop=True)
    merged["funding_stale"] = False

    # Recompute staleness: find the funding_time for each merged row
    idx = pd.merge_asof(
        merged[["open_time"]],
        f.rename(columns={"open_time": "funding_time"}),
        left_on="open_time",
        right_on="funding_time",
        direction="backward",
    )
    if "funding_time" in idx.columns:
        stale_mask = (merged["open_time"] - idx["funding_time"]).abs() > pd.Timedelta(hours=9)
        merged["funding_stale"] = stale_mask.fillna(True)

    return merged


def merge_oi(candles: pd.DataFrame, oi: pd.DataFrame) -> pd.DataFrame:
    """
    Asof-merge open interest onto candle timestamps.

    The most recent OI record at or before each candle's open_time is used.
    Staleness: if the nearest OI record is >2h old, oi_stale is set True.
    """
    if oi.empty:
        candles = candles.copy()
        candles["oi_value"] = np.nan
        candles["oi_stale"] = True
        return candles

    o = oi[["ts", "open_interest"]].copy()
    o["open_interest"] = o["open_interest"].astype(float)
    o = o.sort_values("ts").rename(columns={"ts": "open_time", "open_interest": "oi_value"})

    merged = pd.merge_asof(
        candles.sort_values("open_time"),
        o,
        on="open_time",
        direction="backward",
    )
    merged = merged.sort_values("open_time").reset_index(drop=True)

    idx = pd.merge_asof(
        merged[["open_time"]],
        o.rename(columns={"open_time": "oi_time"})[["oi_time"]],
        left_on="open_time",
        right_on="oi_time",
        direction="backward",
    )
    if "oi_time" in idx.columns:
        stale_mask = (merged["open_time"] - idx["oi_time"]).abs() > pd.Timedelta(hours=2)
        merged["oi_stale"] = stale_mask.fillna(True)
    else:
        merged["oi_stale"] = True

    return merged
