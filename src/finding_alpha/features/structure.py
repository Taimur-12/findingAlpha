"""
Market structure features: session levels and prior period ranges.

Session boundary is 00:00 UTC (daily reset).
Week boundary is Monday 00:00 UTC.
All functions take a candle DataFrame with an 'open_time' column (UTC-aware).
"""

import pandas as pd


def session_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Daily VWAP, resetting at 00:00 UTC.
    Uses typical price = (high + low + close) / 3.
    """
    d = df.copy()
    d["_date"] = d["open_time"].dt.normalize()
    d["_tp"] = (d["high"] + d["low"] + d["close"]) / 3
    d["_tp_vol"] = d["_tp"] * d["volume"]
    d["_cum_tp_vol"] = d.groupby("_date")["_tp_vol"].cumsum()
    d["_cum_vol"] = d.groupby("_date")["volume"].cumsum()
    vwap = d["_cum_tp_vol"] / d["_cum_vol"].replace(0.0, float("nan"))
    return vwap.rename("session_vwap")


def session_high_low(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling session high and low (resets at 00:00 UTC each day)."""
    d = df.copy()
    d["_date"] = d["open_time"].dt.normalize()
    s_high = d.groupby("_date")["high"].cummax().rename("session_high")
    s_low = d.groupby("_date")["low"].cummin().rename("session_low")
    return pd.DataFrame({"session_high": s_high, "session_low": s_low})


def prev_day_high_low(df: pd.DataFrame) -> pd.DataFrame:
    """Previous complete day's high and low (00:00 UTC boundary)."""
    d = df.copy()
    d["_date"] = d["open_time"].dt.normalize()
    daily = (
        d.groupby("_date")
        .agg(prev_day_high=("high", "max"), prev_day_low=("low", "min"))
        .shift(1)         # shift by 1 day so each day sees the PREVIOUS day's range
    )
    return d.merge(daily, left_on="_date", right_index=True, how="left")[
        ["prev_day_high", "prev_day_low"]
    ].reset_index(drop=True)


def prev_week_high_low(df: pd.DataFrame) -> pd.DataFrame:
    """Previous complete ISO week's high and low (Mon 00:00 UTC boundary)."""
    d = df.copy()
    iso = d["open_time"].dt.isocalendar()
    d["_year"] = iso["year"].values
    d["_week"] = iso["week"].values
    weekly = (
        d.groupby(["_year", "_week"])
        .agg(prev_week_high=("high", "max"), prev_week_low=("low", "min"))
        .shift(1)         # shift by 1 week
    )
    merged = d.merge(weekly, left_on=["_year", "_week"], right_index=True, how="left")
    return merged[["prev_week_high", "prev_week_low"]].reset_index(drop=True)
