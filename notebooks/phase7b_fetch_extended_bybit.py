"""
Phase 7B extended Bybit data fetch.

Fetches a larger BTCUSDT Bybit dataset for strategy refinement evidence.
This intentionally fetches Bybit only because Phase 7 validation currently
uses Bybit execution-venue candles, funding, and OI.

Default period: 730 days ending at today's UTC midnight.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.data.bybit_loader import (
    fetch_candles,
    fetch_funding,
    fetch_open_interest,
)
from finding_alpha.data.normalizer import normalize_candles, normalize_funding, normalize_open_interest
from finding_alpha.data.quality import check_candles
from finding_alpha.data.storage import save_candles, save_funding, save_open_interest


DATA_DIR = ROOT / "data"
SYMBOL = "BTCUSDT"
DAYS = int(os.getenv("FINDING_ALPHA_FETCH_DAYS", "730"))
END_DT = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
START_DT = END_DT - timedelta(days=DAYS)


def _report(label: str, df, timeframe: str) -> None:
    quality = check_candles(df, timeframe)
    print(
        f"{label}: {quality['total_candles']:,} candles | "
        f"gaps={quality['gap_count']} | missing={quality['total_missing']} | "
        f"zero_volume={len(quality['zero_volume_times'])}"
    )


def main() -> None:
    print(f"Fetching Bybit {SYMBOL} for {DAYS} days")
    print(f"Period: {START_DT.isoformat()} -> {END_DT.isoformat()}")

    for timeframe in ("1h", "15m"):
        print(f"\nFetching {timeframe} candles...")
        candles = normalize_candles(fetch_candles(SYMBOL, timeframe, START_DT, END_DT))
        _report(timeframe, candles, timeframe)
        save_candles(
            candles,
            DATA_DIR,
            "bybit",
            SYMBOL,
            timeframe,
            {
                "period_days": DAYS,
                "quality": check_candles(candles, timeframe),
                "phase": "7B_extended_history",
            },
        )

    print("\nFetching funding...")
    funding = normalize_funding(fetch_funding(SYMBOL, START_DT, END_DT))
    print(f"funding: {len(funding):,} rows")
    save_funding(funding, DATA_DIR, "bybit", SYMBOL)

    print("\nFetching 1h open interest...")
    oi = normalize_open_interest(fetch_open_interest(SYMBOL, "1h", START_DT, END_DT))
    print(f"open_interest_1h: {len(oi):,} rows")
    save_open_interest(oi, DATA_DIR, "bybit", SYMBOL, "1h")

    print("\nExtended Bybit fetch complete.")


if __name__ == "__main__":
    main()
