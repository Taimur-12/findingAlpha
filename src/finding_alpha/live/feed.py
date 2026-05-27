"""
Live Bybit REST data feed for Phase 8 paper runtime.

REST-only polling (no WebSocket). For 1h candles, polling every 60 s is sufficient.

Candle finality rule:
  A bar with open_time T is final when now >= T + bar_duration + GRACE_SECONDS.
  GRACE_SECONDS = 60 ensures Bybit has fully closed and indexed the bar before we read it.

Stale detection:
  The feed is stale when the most recent final bar is more than
  STALE_MULTIPLIER * bar_duration old — meaning we have missed at least one close.
  All new entries are blocked until staleness resolves.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import pandas as pd

GRACE_SECONDS: int = 60
STALE_MULTIPLIER: int = 2

_INTERVAL_MAP = {"15m": "15", "1h": "60"}
_BAR_SECONDS = {"15m": 900, "1h": 3600}
_OI_INTERVAL_MAP = {"15m": "15min", "1h": "1h"}
_BASE = "https://api.bybit.com"


def bar_seconds(timeframe: str) -> int:
    if timeframe not in _BAR_SECONDS:
        raise ValueError(f"Unsupported timeframe {timeframe!r}")
    return _BAR_SECONDS[timeframe]


def is_bar_final(open_time: datetime, timeframe: str, now: datetime) -> bool:
    """
    True if the candle at open_time has fully closed and the grace period has passed.
    Accepts both UTC-aware and UTC-naive datetimes; naive datetimes are assumed UTC.
    """
    dur = bar_seconds(timeframe)
    open_utc = _ensure_utc(open_time)
    now_utc = _ensure_utc(now)
    return now_utc >= open_utc + timedelta(seconds=dur + GRACE_SECONDS)


def is_data_stale(
    last_final_open_time: datetime,
    timeframe: str,
    now: datetime,
) -> bool:
    """
    True if we have missed at least one bar close.
    When stale, the feature buffer is out of date and new entries must be blocked.
    """
    dur = bar_seconds(timeframe)
    last_utc = _ensure_utc(last_final_open_time)
    now_utc = _ensure_utc(now)
    return (now_utc - last_utc).total_seconds() > STALE_MULTIPLIER * dur


def fetch_recent_candles(
    symbol: str,
    timeframe: str,
    n: int = 300,
) -> pd.DataFrame:
    """
    Fetch the latest n candles from Bybit REST (linear perpetuals).

    All returned rows are structurally final (they come from exchange history), but
    the most recent row may still be the in-progress candle. Callers must apply
    is_bar_final() to determine which bars are truly closed before using them.

    Returns DataFrame sorted ascending by open_time with columns:
        venue, symbol, timeframe, open_time (UTC datetime), close_time,
        open, high, low, close, volume, quote_volume, is_final (always True).
    """
    interval = _INTERVAL_MAP.get(timeframe)
    if interval is None:
        raise ValueError(f"Unsupported timeframe {timeframe!r}")
    dur_ms = bar_seconds(timeframe) * 1000

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{_BASE}/v5/market/kline",
            params={
                "category": "linear",
                "symbol": symbol,
                "interval": interval,
                "limit": min(n, 1000),
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if data["retCode"] != 0:
        raise RuntimeError(f"Bybit kline error {data['retCode']}: {data['retMsg']}")

    rows = data["result"]["list"]
    if not rows:
        return pd.DataFrame(
            columns=["venue", "symbol", "timeframe", "open_time", "close_time",
                     "open", "high", "low", "close", "volume", "quote_volume", "is_final"]
        )

    df = pd.DataFrame(
        rows,
        columns=["open_time_ms", "open", "high", "low", "close", "volume", "quote_volume"],
    )
    df["open_time_ms"] = df["open_time_ms"].astype(int)
    df["open_time"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    df["close_time"] = df["open_time"] + pd.Timedelta(milliseconds=dur_ms - 1)
    df = (
        df.drop(columns=["open_time_ms"])
        .drop_duplicates(subset=["open_time"])
        .sort_values("open_time")
        .reset_index(drop=True)
    )
    df["venue"] = "bybit"
    df["symbol"] = symbol
    df["timeframe"] = timeframe
    df["is_final"] = True
    return df[["venue", "symbol", "timeframe", "open_time", "close_time",
               "open", "high", "low", "close", "volume", "quote_volume", "is_final"]]


def fetch_recent_funding(symbol: str, days: int = 14) -> pd.DataFrame:
    """
    Fetch the last `days` days of funding rate history from Bybit.

    Returns DataFrame with columns: venue, symbol, funding_time (UTC datetime), funding_rate (str).
    Returns empty DataFrame (with correct columns) on API failure rather than raising,
    so callers can mark features as funding_stale without crashing the runtime.
    """
    _cols = ["venue", "symbol", "funding_time", "funding_rate"]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = now_ms - days * 86_400 * 1000
    rows: list = []
    current_end = now_ms

    try:
        with httpx.Client(timeout=30) as client:
            while current_end > start_ms:
                resp = client.get(
                    f"{_BASE}/v5/market/funding/history",
                    params={
                        "category": "linear",
                        "symbol": symbol,
                        "startTime": start_ms,
                        "endTime": current_end,
                        "limit": 200,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if data["retCode"] != 0:
                    break
                page = data["result"]["list"]
                if not page:
                    break
                rows.extend(page)
                oldest_ts = int(page[-1]["fundingRateTimestamp"])
                if oldest_ts <= start_ms:
                    break
                current_end = oldest_ts - 1
    except Exception:
        return pd.DataFrame(columns=_cols)

    if not rows:
        return pd.DataFrame(columns=_cols)

    df = pd.DataFrame(rows)
    df["funding_time"] = pd.to_datetime(df["fundingRateTimestamp"].astype(int), unit="ms", utc=True)
    df = df.rename(columns={"fundingRate": "funding_rate"})
    df = (
        df[["funding_time", "funding_rate"]]
        .drop_duplicates(subset=["funding_time"])
        .sort_values("funding_time")
        .reset_index(drop=True)
    )
    df["venue"] = "bybit"
    df["symbol"] = symbol
    return df[_cols]


def fetch_recent_oi(symbol: str, timeframe: str = "1h", days: int = 14) -> pd.DataFrame:
    """
    Fetch the last `days` days of open interest history from Bybit.

    Returns DataFrame with columns: venue, symbol, timeframe, ts (UTC datetime), open_interest (str).
    Returns empty DataFrame on API failure so callers can mark features as oi_stale.
    """
    _cols = ["venue", "symbol", "timeframe", "ts", "open_interest"]
    oi_interval = _OI_INTERVAL_MAP.get(timeframe, "1h")
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = now_ms - days * 86_400 * 1000
    rows: list = []
    current_end = now_ms

    try:
        with httpx.Client(timeout=30) as client:
            while current_end > start_ms:
                resp = client.get(
                    f"{_BASE}/v5/market/open-interest",
                    params={
                        "category": "linear",
                        "symbol": symbol,
                        "intervalTime": oi_interval,
                        "startTime": start_ms,
                        "endTime": current_end,
                        "limit": 200,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if data["retCode"] != 0:
                    break
                page = data["result"]["list"]
                if not page:
                    break
                rows.extend(page)
                oldest_ts = int(page[-1]["timestamp"])
                if oldest_ts <= start_ms:
                    break
                current_end = oldest_ts - 1
    except Exception:
        return pd.DataFrame(columns=_cols)

    if not rows:
        return pd.DataFrame(columns=_cols)

    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms", utc=True)
    df = df.rename(columns={"openInterest": "open_interest"})
    df = (
        df[["ts", "open_interest"]]
        .drop_duplicates(subset=["ts"])
        .sort_values("ts")
        .reset_index(drop=True)
    )
    df["venue"] = "bybit"
    df["symbol"] = symbol
    df["timeframe"] = timeframe
    return df[_cols]


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
