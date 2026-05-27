"""
Parquet persistence for historical data.

Directory layout:
    data/{venue}/{symbol}/{timeframe}/candles.parquet
    data/{venue}/{symbol}/{timeframe}/metadata.json
    data/{venue}/{symbol}/funding.parquet
    data/{venue}/{symbol}/open_interest_{timeframe}.parquet
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _write_meta(path: Path, meta: dict) -> None:
    path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")


def save_candles(
    df: pd.DataFrame,
    base_dir: Path,
    venue: str,
    symbol: str,
    timeframe: str,
    metadata: dict | None = None,
) -> Path:
    """Write candle DataFrame to Parquet and a sidecar metadata.json."""
    out_dir = base_dir / venue / symbol / timeframe
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / "candles.parquet"
    df.to_parquet(parquet_path, index=False)
    meta = {
        "venue": venue,
        "symbol": symbol,
        "timeframe": timeframe,
        "total_candles": len(df),
        "start": df["open_time"].min().isoformat() if not df.empty else None,
        "end": df["open_time"].max().isoformat() if not df.empty else None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        **(metadata or {}),
    }
    _write_meta(out_dir / "metadata.json", meta)
    return parquet_path


def load_candles(base_dir: Path, venue: str, symbol: str, timeframe: str) -> pd.DataFrame:
    path = base_dir / venue / symbol / timeframe / "candles.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No candle data at {path}")
    return pd.read_parquet(path)


def load_candles_metadata(base_dir: Path, venue: str, symbol: str, timeframe: str) -> dict:
    path = base_dir / venue / symbol / timeframe / "metadata.json"
    if not path.exists():
        raise FileNotFoundError(f"No metadata at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_funding(
    df: pd.DataFrame,
    base_dir: Path,
    venue: str,
    symbol: str,
) -> Path:
    out_dir = base_dir / venue / symbol
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "funding.parquet"
    df.to_parquet(path, index=False)
    return path


def load_funding(base_dir: Path, venue: str, symbol: str) -> pd.DataFrame:
    path = base_dir / venue / symbol / "funding.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No funding data at {path}")
    return pd.read_parquet(path)


def save_open_interest(
    df: pd.DataFrame,
    base_dir: Path,
    venue: str,
    symbol: str,
    timeframe: str,
) -> Path:
    out_dir = base_dir / venue / symbol
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"open_interest_{timeframe}.parquet"
    df.to_parquet(path, index=False)
    return path


def load_open_interest(base_dir: Path, venue: str, symbol: str, timeframe: str) -> pd.DataFrame:
    path = base_dir / venue / symbol / f"open_interest_{timeframe}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No OI data at {path}")
    return pd.read_parquet(path)
