"""
Data quality checks for historical candle DataFrames.

Detects: timestamp gaps, duplicate rows, zero-volume candles.
Returns a plain dict so it can be serialised to the Parquet metadata JSON.
"""

import pandas as pd
from typing import Any

_MS_PER_INTERVAL: dict[str, int] = {
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
}


def check_candles(df: pd.DataFrame, timeframe: str) -> dict[str, Any]:
    """Return a quality report for a normalised candle DataFrame.

    Report keys:
        total_candles       int
        gap_count           int
        total_missing       int   — sum of expected candles inside all gaps
        gaps                list  — [{from, to, missing_candles}]
        duplicate_times     list  — ISO strings of duplicated open_time values
        zero_volume_times   list  — ISO strings of open_time where volume == 0
    """
    if df.empty:
        return {
            "total_candles": 0,
            "gap_count": 0,
            "total_missing": 0,
            "gaps": [],
            "duplicate_times": [],
            "zero_volume_times": [],
        }

    if timeframe not in _MS_PER_INTERVAL:
        raise ValueError(f"Unsupported timeframe {timeframe!r}. Use: {list(_MS_PER_INTERVAL)}")

    interval_ms = _MS_PER_INTERVAL[timeframe]
    expected_delta = pd.Timedelta(milliseconds=interval_ms)

    times = pd.to_datetime(df["open_time"], utc=True).sort_values().reset_index(drop=True)

    gaps = []
    for i in range(1, len(times)):
        delta = times[i] - times[i - 1]
        if delta > expected_delta * 1.5:
            missing = round(delta / expected_delta) - 1
            gaps.append({
                "from": times[i - 1].isoformat(),
                "to": times[i].isoformat(),
                "missing_candles": missing,
            })

    dup_times = (
        df[df.duplicated(subset=["open_time"], keep=False)]["open_time"]
        .drop_duplicates()
        .apply(lambda t: pd.Timestamp(t).isoformat())
        .tolist()
    )

    volume_numeric = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    zero_vol_times = (
        df[volume_numeric == 0.0]["open_time"]
        .apply(lambda t: pd.Timestamp(t).isoformat())
        .tolist()
    )

    return {
        "total_candles": len(df),
        "gap_count": len(gaps),
        "total_missing": sum(g["missing_candles"] for g in gaps),
        "gaps": gaps,
        "duplicate_times": dup_times,
        "zero_volume_times": zero_vol_times,
    }
