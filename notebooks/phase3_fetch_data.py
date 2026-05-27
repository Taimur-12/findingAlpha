"""
Phase 3 data fetch script.

Downloads 6 months of historical data from Bybit and Binance and saves to Parquet.
Run once from the repo root:

    conda activate finding_alpha
    python notebooks/phase3_fetch_data.py

Output (gitignored):
    data/bybit/BTCUSDT/15m/candles.parquet + metadata.json
    data/bybit/BTCUSDT/1h/candles.parquet  + metadata.json
    data/bybit/BTCUSDT/funding.parquet
    data/bybit/BTCUSDT/open_interest_1h.parquet
    data/binance/BTCUSDT/15m/candles.parquet + metadata.json
    data/binance/BTCUSDT/1h/candles.parquet  + metadata.json
    data/binance/BTCUSDT/funding.parquet
    data/binance/BTCUSDT/open_interest_1h.parquet
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.data.bybit_loader import (
    fetch_candles as bybit_candles,
    fetch_funding as bybit_funding,
    fetch_open_interest as bybit_oi,
)
from finding_alpha.data.binance_loader import (
    fetch_candles as binance_candles,
    fetch_funding as binance_funding,
    fetch_open_interest as binance_oi,
)
from finding_alpha.data.normalizer import normalize_candles, normalize_funding, normalize_open_interest
from finding_alpha.data.quality import check_candles
from finding_alpha.data.storage import (
    save_candles, save_funding, save_open_interest,
)

DATA_DIR = ROOT / "data"
SYMBOL = "BTCUSDT"
END_DT = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
START_DT = END_DT - timedelta(days=180)

print(f"Period: {START_DT.date()} -> {END_DT.date()} (180 days)")
print(f"Expected: ~{180 * 96} x 15m candles, ~{180 * 24} x 1h candles")
print()


def _report(label: str, df, timeframe: str = "15m") -> None:
    r = check_candles(df, timeframe)
    gaps = r["gap_count"]
    missing = r["total_missing"]
    zero = len(r["zero_volume_times"])
    print(f"  {label}: {r['total_candles']} candles | {gaps} gaps ({missing} missing) | {zero} zero-vol")


# ═══════════════════════════════════════
# BYBIT
# ═══════════════════════════════════════

print("=== BYBIT ===")

print("Fetching 15m candles...")
df = normalize_candles(bybit_candles(SYMBOL, "15m", START_DT, END_DT))
_report("15m", df, "15m")
save_candles(df, DATA_DIR, "bybit", SYMBOL, "15m", {"quality": check_candles(df, "15m")})

print("Fetching 1h candles...")
df = normalize_candles(bybit_candles(SYMBOL, "1h", START_DT, END_DT))
_report("1h", df, "1h")
save_candles(df, DATA_DIR, "bybit", SYMBOL, "1h", {"quality": check_candles(df, "1h")})

print("Fetching funding rates...")
df_f = normalize_funding(bybit_funding(SYMBOL, START_DT, END_DT))
print(f"  funding: {len(df_f)} entries")
save_funding(df_f, DATA_DIR, "bybit", SYMBOL)

print("Fetching open interest (1h)...")
df_oi = normalize_open_interest(bybit_oi(SYMBOL, "1h", START_DT, END_DT))
print(f"  OI: {len(df_oi)} entries")
save_open_interest(df_oi, DATA_DIR, "bybit", SYMBOL, "1h")

# ═══════════════════════════════════════
# BINANCE (reference)
# ═══════════════════════════════════════

print()
print("=== BINANCE (reference) ===")

print("Fetching 15m candles...")
df = normalize_candles(binance_candles(SYMBOL, "15m", START_DT, END_DT))
_report("15m", df, "15m")
save_candles(df, DATA_DIR, "binance", SYMBOL, "15m", {"quality": check_candles(df, "15m")})

print("Fetching 1h candles...")
df = normalize_candles(binance_candles(SYMBOL, "1h", START_DT, END_DT))
_report("1h", df, "1h")
save_candles(df, DATA_DIR, "binance", SYMBOL, "1h", {"quality": check_candles(df, "1h")})

print("Fetching funding rates...")
df_f = normalize_funding(binance_funding(SYMBOL, START_DT, END_DT))
print(f"  funding: {len(df_f)} entries")
save_funding(df_f, DATA_DIR, "binance", SYMBOL)

print("Fetching open interest (1h)...")
# Note: Binance OI history retention is limited (~30 days for short periods)
df_oi = normalize_open_interest(binance_oi(SYMBOL, "1h", START_DT, END_DT))
print(f"  OI: {len(df_oi)} entries (Binance OI retention may be <30 days)")
save_open_interest(df_oi, DATA_DIR, "binance", SYMBOL, "1h")

print()
print("Phase 3 data fetch complete.")
print(f"Files saved to: {DATA_DIR}")
