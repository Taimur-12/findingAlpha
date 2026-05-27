# Architecture Spike Report

Date: 2026-05-27
Status: PARTIAL — Bybit data and NT import confirmed, deeper NT strategy spike pending

## What Was Tested

### 1. Bybit Public API

- Endpoint: `GET /v5/market/kline` (linear, BTCUSDT, 15m)
- Result: 200 candles returned cleanly
- Timestamp format: Unix ms, converts correctly to UTC
- Candle fields: open_time, open, high, low, close, volume, quote_volume
- Saved to Parquet without issues
- No auth required for public klines

**Confirmed**: Bybit public data is accessible and well-structured.

### 2. NautilusTrader v1.227.0

All imports successful on Python 3.12 / Windows:

- `nautilus_trader` base import: OK
- `InstrumentId`, `Venue`, `Symbol` identifiers: OK
- `BacktestEngine`: OK
- `BybitLiveDataClientFactory` adapter: OK

**Confirmed**: NautilusTrader installs cleanly and the Bybit adapter exists.

### 3. Custom Event Replay Loop

- 200 candles replayed through a simple for-loop
- Dummy signal emitted per candle
- Clean, understandable, zero friction

**Confirmed**: A custom simulator is trivial to write at this scale.

## Next Spike Required Before Decision

The critical remaining question is whether NautilusTrader's strategy/risk boundary supports our contracts cleanly:

- Can a `SignalCandidate` be emitted from a NT Strategy class?
- Can a custom Risk Agent be inserted between strategy output and execution?
- Can the same strategy code run in backtest and live mode identically?
- What is the NT learning curve cost vs. a custom 300-line event loop?

## Preliminary Assessment

| Factor | NautilusTrader | Custom Simulator |
|---|---|---|
| Bybit adapter | Exists | Must build |
| Backtest/live parity | Built-in design | Must enforce ourselves |
| Custom risk insertion | Unknown — needs spike | Full control |
| Learning curve | High | Low |
| Order semantics | Well modeled | Must model ourselves |
| Time to first working backtest | Slower | Faster |
| Long-term production value | Higher if it fits | Lower ceiling |

## Decision: Not Yet Made

Run the NT strategy boundary spike before deciding. See `nautilus_vs_custom_decision.md` for the final call.
