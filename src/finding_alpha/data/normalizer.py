"""
Schema normalizer for candle, funding, and open interest DataFrames.

Both Bybit and Binance loaders already produce matching column names.
This module enforces consistent dtypes and column order before Parquet storage.
"""

import pandas as pd

CANDLE_COLUMNS = [
    "venue", "symbol", "timeframe",
    "open_time", "close_time",
    "open", "high", "low", "close",
    "volume", "quote_volume",
    "is_final",
]
FUNDING_COLUMNS = ["venue", "symbol", "funding_time", "funding_rate"]
OI_COLUMNS = ["venue", "symbol", "timeframe", "ts", "open_interest"]

_PRICE_COLS = ["open", "high", "low", "close", "volume", "quote_volume"]


def normalize_candles(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce schema, sort, and deduplicate a candle DataFrame."""
    if df.empty:
        return df
    df = df.copy()
    for col in _PRICE_COLS:
        df[col] = df[col].astype(str)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], utc=True)
    df["is_final"] = df["is_final"].astype(bool)
    df = (
        df.drop_duplicates(subset=["open_time"])
        .sort_values("open_time")
        .reset_index(drop=True)
    )
    return df[CANDLE_COLUMNS]


def normalize_funding(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce schema, sort, and deduplicate a funding rate DataFrame."""
    if df.empty:
        return df
    df = df.copy()
    df["funding_rate"] = df["funding_rate"].astype(str)
    df["funding_time"] = pd.to_datetime(df["funding_time"], utc=True)
    df = (
        df.drop_duplicates(subset=["funding_time"])
        .sort_values("funding_time")
        .reset_index(drop=True)
    )
    return df[FUNDING_COLUMNS]


def normalize_open_interest(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce schema, sort, and deduplicate an open interest DataFrame."""
    if df.empty:
        return df
    df = df.copy()
    df["open_interest"] = df["open_interest"].astype(str)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    extra = [c for c in df.columns if c not in OI_COLUMNS]
    df = (
        df.drop_duplicates(subset=["ts"])
        .sort_values("ts")
        .reset_index(drop=True)
    )
    return df[OI_COLUMNS + extra]
