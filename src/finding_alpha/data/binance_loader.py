"""
Binance USD-M Futures REST API historical data loader.

Fetches: OHLCV candles, funding rate history, open interest history.
Used as reference data alongside Bybit primary venue.
All timestamps returned as UTC. All numeric values as strings (Decimal-safe).
"""

import time
import httpx
import pandas as pd
from datetime import datetime

BINANCE_FAPI_BASE = "https://fapi.binance.com"

_INTERVAL_MAP = {"15m": "15m", "1h": "1h"}
_MS_PER_INTERVAL = {"15m": 15 * 60 * 1000, "1h": 60 * 60 * 1000}
_OI_PERIOD_MAP = {"15m": "15m", "1h": "1h"}

_CANDLE_COLUMNS = ["venue", "symbol", "timeframe", "open_time", "close_time",
                   "open", "high", "low", "close", "volume", "quote_volume", "is_final"]
_FUNDING_COLUMNS = ["venue", "symbol", "funding_time", "funding_rate"]
_OI_COLUMNS = ["venue", "symbol", "timeframe", "ts", "open_interest"]


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def fetch_candles(symbol: str, timeframe: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """Fetch OHLCV candles from Binance USD-M futures.

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
    current_start = start_ms

    with httpx.Client(timeout=30) as client:
        while current_start < end_ms:
            resp = client.get(
                f"{BINANCE_FAPI_BASE}/fapi/v1/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current_start,
                    "endTime": end_ms,
                    "limit": 1500,
                },
            )
            resp.raise_for_status()
            page = resp.json()
            if not page:
                break

            rows.extend(page)

            newest_ts = int(page[-1][0])
            if newest_ts >= end_ms or len(page) < 1500:
                break
            current_start = newest_ts + interval_ms
            time.sleep(0.12)

    if not rows:
        return pd.DataFrame(columns=_CANDLE_COLUMNS)

    # Binance kline columns: [open_time, open, high, low, close, volume, close_time,
    #                          quote_vol, trades, taker_buy_base, taker_buy_quote, ignore]
    df = pd.DataFrame(rows, columns=[
        "open_time_ms", "open", "high", "low", "close", "volume",
        "close_time_ms", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    df["open_time"] = pd.to_datetime(df["open_time_ms"].astype(int), unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time_ms"].astype(int), unit="ms", utc=True)
    df = (
        df[["open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"]]
        .drop_duplicates(subset=["open_time"])
        .sort_values("open_time")
        .reset_index(drop=True)
    )
    start_ts = pd.Timestamp(start_dt)
    end_ts = pd.Timestamp(end_dt)
    df = df[(df["open_time"] >= start_ts) & (df["open_time"] <= end_ts)].reset_index(drop=True)
    df["venue"] = "binance"
    df["symbol"] = symbol
    df["timeframe"] = timeframe
    df["is_final"] = True
    return df[_CANDLE_COLUMNS]


def fetch_funding(symbol: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """Fetch funding rate history from Binance USD-M futures (every 8h).

    Returns DataFrame with columns: venue, symbol, funding_time, funding_rate (str).
    """
    start_ms = _ms(start_dt)
    end_ms = _ms(end_dt)
    rows: list = []
    current_start = start_ms

    with httpx.Client(timeout=30) as client:
        while current_start < end_ms:
            resp = client.get(
                f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate",
                params={
                    "symbol": symbol,
                    "startTime": current_start,
                    "endTime": end_ms,
                    "limit": 1000,
                },
            )
            resp.raise_for_status()
            page = resp.json()
            if not page:
                break

            rows.extend(page)

            newest_ts = int(page[-1]["fundingTime"])
            if newest_ts >= end_ms or len(page) < 1000:
                break
            current_start = newest_ts + 1
            time.sleep(0.12)

    if not rows:
        return pd.DataFrame(columns=_FUNDING_COLUMNS)

    df = pd.DataFrame(rows)
    df["funding_time"] = pd.to_datetime(df["fundingTime"].astype(int), unit="ms", utc=True)
    df = df.rename(columns={"fundingRate": "funding_rate"})
    df = (
        df[["funding_time", "funding_rate"]]
        .drop_duplicates(subset=["funding_time"])
        .sort_values("funding_time")
        .reset_index(drop=True)
    )
    df["venue"] = "binance"
    df["symbol"] = symbol
    return df[_FUNDING_COLUMNS]


def fetch_open_interest(symbol: str, timeframe: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """Fetch open interest history from Binance USD-M futures.

    Binance's openInterestHist endpoint does not accept startTime — only endTime works.
    We paginate backwards using endTime, stopping when we pass start_dt.
    Returns DataFrame with columns: venue, symbol, timeframe, ts, open_interest (str).
    """
    period = _OI_PERIOD_MAP.get(timeframe, "1h")
    start_ms = _ms(start_dt)
    end_ms = _ms(end_dt)
    rows: list = []
    current_end = end_ms

    with httpx.Client(timeout=60) as client:
        while current_end > start_ms:
            resp = client.get(
                f"{BINANCE_FAPI_BASE}/futures/data/openInterestHist",
                params={
                    "symbol": symbol,
                    "period": period,
                    "endTime": current_end,
                    "limit": 500,
                },
            )
            resp.raise_for_status()
            page = resp.json()
            if not page:
                break

            rows.extend(page)

            # Response is ascending (oldest first); page[0] is the oldest entry
            oldest_ts = int(page[0]["timestamp"])
            if oldest_ts <= start_ms or len(page) < 500:
                break
            current_end = oldest_ts - 1
            time.sleep(0.12)

    if not rows:
        return pd.DataFrame(columns=_OI_COLUMNS)

    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms", utc=True)
    # Binance USD-M OI uses "sumOpenInterest" (not "openInterest")
    df = df.rename(columns={"sumOpenInterest": "open_interest"})
    df = (
        df[["ts", "open_interest"]]
        .drop_duplicates(subset=["ts"])
        .sort_values("ts")
        .reset_index(drop=True)
    )
    df["venue"] = "binance"
    df["symbol"] = symbol
    df["timeframe"] = timeframe
    return df[_OI_COLUMNS]
