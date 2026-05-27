import sys
sys.path.insert(0, "src")
import pandas as pd
from pathlib import Path

DATA = Path("data")
checks = [
    ("bybit",   "BTCUSDT", "15m", "candles"),
    ("bybit",   "BTCUSDT", "1h",  "candles"),
    ("binance", "BTCUSDT", "15m", "candles"),
    ("binance", "BTCUSDT", "1h",  "candles"),
]
for venue, sym, tf, kind in checks:
    df = pd.read_parquet(DATA / venue / sym / tf / f"{kind}.parquet")
    print(f"{venue}/{sym}/{tf}: {len(df)} rows | {df['open_time'].min()} -> {df['open_time'].max()}")

for venue, sym in [("bybit", "BTCUSDT"), ("binance", "BTCUSDT")]:
    df = pd.read_parquet(DATA / venue / sym / "funding.parquet")
    print(f"{venue}/{sym}/funding: {len(df)} rows")
    df = pd.read_parquet(DATA / venue / sym / "open_interest_1h.parquet")
    print(f"{venue}/{sym}/OI_1h:   {len(df)} rows | {df['ts'].min()} -> {df['ts'].max()}")
