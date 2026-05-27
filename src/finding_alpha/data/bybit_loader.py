"""
Bybit REST API historical data loader.

Fetches: OHLCV candles, funding rate history, open interest history.
All timestamps returned as UTC. All numeric values as strings (Decimal-safe).
"""

import time
import httpx
import pandas as pd
from datetime import datetime

BYBIT_BASE = "https://api.bybit.com"

_INTERVAL_MAP = {"15m": "15", "1h": "60"}
_MS_PER_INTERVAL = {"15m": 15 * 60 * 1000, "1h": 60 * 60 * 1000}
_OI_INTERVAL_MAP = {"15m": "15min", "1h": "1h"}

_CANDLE_COLUMNS = ["venue", "symbol", "timeframe", "open_time", "close_time",
                   "open", "high", "low", "close", "volume", "quote_volume", "is_final"]
_FUNDING_COLUMNS = ["venue", "symbol", "funding_time", "funding_rate"]
_OI_COLUMNS = ["venue", "symbol", "timeframe", "ts", "open_interest"]


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _check(data: dict) -> None:
    if data["retCode"] != 0:
        raise RuntimeError(f"Bybit API error {data['retCode']}: {data['retMsg']}")


def fetch_candles(symbol: str, timeframe: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """Fetch OHLCV candles from Bybit linear perpetuals.

    Returns DataFrame with columns: venue, symbol, timeframe, open_time, close_time,
    open, high, low, close, volume, quote_volume (all str), is_final (bool).
    Rows are sorted ascending by open_time.
    """
    if timeframe not in _INTERVAL_MAP:
        raise ValueError(f"Unsupported timeframe {timeframe!r}. Use: {list(_INTERVAL_MAP)}")

    interval = _INTERVAL_MAP[timeframe]
    interval_ms = _MS_PER_INTERVAL[timeframe]
    start_ms = _ms(start_dt)
    end_ms = _ms(end_dt)

    rows: list = []
    current_end = end_ms

    with httpx.Client(timeout=30) as client:
        while current_end > start_ms:
            resp = client.get(
                f"{BYBIT_BASE}/v5/market/kline",
                params={
                    "category": "linear",
                    "symbol": symbol,
                    "interval": interval,
                    "start": start_ms,
                    "end": current_end,
                    "limit": 1000,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            _check(data)

            page = data["result"]["list"]
            if not page:
                break

            rows.extend(page)

            oldest_ts = int(page[-1][0])
            if oldest_ts <= start_ms:
                break
            current_end = oldest_ts - 1
            time.sleep(0.12)

    if not rows:
        return pd.DataFrame(columns=_CANDLE_COLUMNS)

    df = pd.DataFrame(
        rows,
        columns=["open_time_ms", "open", "high", "low", "close", "volume", "quote_volume"],
    )
    df["open_time_ms"] = df["open_time_ms"].astype(int)
    df["open_time"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    df["close_time"] = df["open_time"] + pd.Timedelta(milliseconds=interval_ms - 1)
    df = (
        df.drop(columns=["open_time_ms"])
        .drop_duplicates(subset=["open_time"])
        .sort_values("open_time")
        .reset_index(drop=True)
    )
    start_ts = pd.Timestamp(start_dt)
    end_ts = pd.Timestamp(end_dt)
    df = df[(df["open_time"] >= start_ts) & (df["open_time"] <= end_ts)].reset_index(drop=True)
    df["venue"] = "bybit"
    df["symbol"] = symbol
    df["timeframe"] = timeframe
    df["is_final"] = True
    return df[_CANDLE_COLUMNS]


def fetch_funding(symbol: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """Fetch funding rate history from Bybit (every 8h).

    Returns DataFrame with columns: venue, symbol, funding_time, funding_rate (str).
    """
    start_ms = _ms(start_dt)
    end_ms = _ms(end_dt)
    rows: list = []
    current_end = end_ms

    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(
                f"{BYBIT_BASE}/v5/market/funding/history",
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
            _check(data)

            page = data["result"]["list"]
            if not page:
                break

            rows.extend(page)

            oldest_ts = int(page[-1]["fundingRateTimestamp"])
            if oldest_ts <= start_ms:
                break
            current_end = oldest_ts - 1
            time.sleep(0.12)

    if not rows:
        return pd.DataFrame(columns=_FUNDING_COLUMNS)

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
    return df[_FUNDING_COLUMNS]


def fetch_open_interest(symbol: str, timeframe: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """Fetch open interest history from Bybit.

    Returns DataFrame with columns: venue, symbol, timeframe, ts, open_interest (str).
    """
    oi_interval = _OI_INTERVAL_MAP.get(timeframe, "1h")
    start_ms = _ms(start_dt)
    end_ms = _ms(end_dt)
    rows: list = []
    current_end = end_ms

    with httpx.Client(timeout=30) as client:
        while current_end > start_ms:
            resp = client.get(
                f"{BYBIT_BASE}/v5/market/open-interest",
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
            _check(data)

            page = data["result"]["list"]
            if not page:
                break

            rows.extend(page)

            oldest_ts = int(page[-1]["timestamp"])
            if oldest_ts <= start_ms:
                break
            current_end = oldest_ts - 1
            time.sleep(0.12)

    if not rows:
        return pd.DataFrame(columns=_OI_COLUMNS)

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
    return df[_OI_COLUMNS]
