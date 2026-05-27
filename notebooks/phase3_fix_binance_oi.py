"""Fetch Binance OI that failed in the first run (startTime not accepted by endpoint)."""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.data.binance_loader import fetch_open_interest as binance_oi
from finding_alpha.data.normalizer import normalize_open_interest
from finding_alpha.data.storage import save_open_interest

DATA_DIR = ROOT / "data"
SYMBOL = "BTCUSDT"
END_DT = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
START_DT = END_DT - timedelta(days=180)

print("Fetching Binance open interest (1h, backward pagination)...")
df_oi = normalize_open_interest(binance_oi(SYMBOL, "1h", START_DT, END_DT))
print(f"  OI: {len(df_oi)} entries")
save_open_interest(df_oi, DATA_DIR, "binance", SYMBOL, "1h")
print("Done.")
