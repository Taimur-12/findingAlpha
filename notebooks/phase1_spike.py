"""
Phase 1 Architecture Spike
--------------------------
1. Fetch BTCUSDT 15m klines from Bybit public API, save to Parquet
2. Test NautilusTrader can be imported and basic objects instantiated
3. Write a tiny custom event replay loop

Run with: conda activate finding_alpha && python notebooks/phase1_spike.py
"""

import httpx
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ── 1. Bybit public klines ────────────────────────────────────────────────────

def fetch_bybit_klines(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    resp = httpx.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data["retCode"] != 0:
        raise RuntimeError(f"Bybit API error: {data['retMsg']}")

    rows = data["result"]["list"]
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume", "quote_volume"
    ])
    df["open_time"] = pd.to_numeric(df["open_time"])
    df["open_time_utc"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for col in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[col] = pd.to_numeric(df[col])
    df = df.sort_values("open_time").reset_index(drop=True)
    df["venue"] = "bybit"
    df["symbol"] = symbol
    df["interval"] = interval
    return df


# ── 2. NautilusTrader import check ────────────────────────────────────────────

def test_nautilus_import() -> dict:
    results = {}
    try:
        import nautilus_trader
        results["version"] = nautilus_trader.__version__
        results["import"] = "OK"
    except Exception as e:
        results["import"] = f"FAILED: {e}"
        return results

    try:
        from nautilus_trader.model.identifiers import InstrumentId, Venue, Symbol
        InstrumentId(Symbol("BTCUSDT"), Venue("BYBIT"))
        results["identifiers"] = "OK"
    except Exception as e:
        results["identifiers"] = f"FAILED: {e}"

    try:
        from nautilus_trader.backtest.engine import BacktestEngine
        results["backtest_engine"] = "OK"
    except Exception as e:
        results["backtest_engine"] = f"FAILED: {e}"

    try:
        from nautilus_trader.adapters.bybit.factories import BybitLiveDataClientFactory
        results["bybit_adapter"] = "OK"
    except Exception as e:
        results["bybit_adapter"] = f"FAILED: {e}"

    return results


# ── 3. Tiny custom event replay loop ─────────────────────────────────────────

def custom_event_replay(df: pd.DataFrame):
    """Minimal proof that we can replay candles through a simple event loop."""
    signals = []

    for _, row in df.iterrows():
        # Dummy signal: flag if close > open (bullish candle)
        if float(row["close"]) > float(row["open"]):
            signals.append({
                "ts": row["open_time_utc"],
                "symbol": row["symbol"],
                "signal": "bullish_candle",
                "close": float(row["close"]),
            })

    return signals


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 ARCHITECTURE SPIKE")
    print("=" * 60)

    # 1. Fetch klines
    print("\n[1] Fetching Bybit BTCUSDT 15m klines...")
    try:
        df = fetch_bybit_klines("BTCUSDT", "15", limit=200)
        print(f"    Got {len(df)} candles")
        print(f"    Range: {df['open_time_utc'].iloc[0]} to {df['open_time_utc'].iloc[-1]}")
        print(f"    Latest close: {df['close'].iloc[-1]}")

        out_path = DATA_DIR / "bybit_BTCUSDT_15m_spike.parquet"
        pq.write_table(pa.Table.from_pandas(df), out_path)
        print(f"    Saved to {out_path}")
        bybit_ok = True
    except Exception as e:
        print(f"    FAILED: {e}")
        bybit_ok = False

    # 2. NautilusTrader check
    print("\n[2] Testing NautilusTrader imports...")
    nt_results = test_nautilus_import()
    for key, val in nt_results.items():
        status = "OK" if "FAILED" not in str(val) else "XX"
        print(f"    {status} {key}: {val}")

    # 3. Custom event replay
    if bybit_ok:
        print("\n[3] Custom event replay loop...")
        signals = custom_event_replay(df)
        print(f"    Replayed {len(df)} candles")
        print(f"    Dummy signals emitted: {len(signals)}")
        print(f"    Last signal: {signals[-1] if signals else 'none'}")

    print("\n" + "=" * 60)
    print("SPIKE COMPLETE — review results above")
    print("=" * 60)
