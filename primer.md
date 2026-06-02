# QuantFusion: BTCUSDT Perpetuals Trading Bot

## What This Is

**QuantFusion** is an automated trading bot for BTCUSDT perpetuals on Bybit (testnet). It combines regime classification (bull/bear/chop detection) with technical signals (EMA crossovers) to generate short-term directional trades.

- **Exchange:** Bybit perpetuals (testnet)
- **Asset:** BTCUSDT
- **Venue:** Live paper trading (testnet account, real API orders)
- **Dashboard:** Streamlit UI for monitoring, switching between sim/live views, and manual trade execution

## Current Phase

**Phase 8: Live testnet trading with dashboard UI**

- **Active strategy:** 15m EMA scalp (`ema_scalp_15m_v1`)
- **Frozen strategies:** 1h daily breakdown, 1h composite (logic built, not trading right now)
- **Status:** Live cycle button works; trades execute on Bybit testnet; state/trades logged

## High-Level Architecture

```
Signal Generation
├─ Regime classifier (LLM-driven advisory on market conditions)
├─ Candle fetcher (Bybit 1h/15m OHLCV)
├─ EMA crossover logic (fast vs slow EMAs)
└─ Risk calc (kelly, position sizing, R-multiples)
   ↓
Order Execution
├─ BybitClient (API wrapper)
├─ Entry/exit order submission
├─ Fill/stop/target polling
└─ State persistence (JSON)
   ↓
Monitoring
├─ Streamlit dashboard (tabs: overview, KPIs, trades, live control)
├─ Trade log (entry/exit prices, fees, outcomes)
└─ Matrix events (regime, signal, trade events)
```

## Key Components

### Core Libraries (`src/finding_alpha/`)
- **`execution/bybit_client.py`** — API wrapper with unwrap pattern (raises `BybitAPIError` on failure, returns inner result dict on success)
- **`paper/live_execution.py`** — live trade runner; handles entry submission, fill polling, exit condition checking
- **`paper/runtime.py`** — cycle orchestrator; fetches data, runs signal logic, logs trades
- **`advisory.py`** — LLM-based market context (calls Claude Sonnet, caches advisory for ~24h)

### Strategies (`src/finding_alpha/strategies/`)
- **`ema_scalp_15m_v1.py`** — 15m scalp (ACTIVE)
- **`prev_day_breakdown_v1.py`** — 1h daily breakdown (FROZEN)
- **`short_composite_v1.py`** — 1h composite (FROZEN)

### Dashboard (`dashboard/app.py`)
- Streamlit app at `http://localhost:8501`
- Sidebar toggle: "📊 Simulation" vs "🛰 Live testnet"
- Tabs: 0=overview, 1=live candle, 2=strategy signals, 3=regime, 4=KPIs, 5=advisory, 6=trade log, 7=live trading control

### Data Files
- **`paper/sim/`** — simulation state (historical backtest replay)
- **`paper/live/`** — live testnet state (15m, 1h strategies)
  - `state.json` — current position, pending entry, equity
  - `trades.jsonl` — all closed trades (entry/exit/fees/outcome)
  - `matrix.jsonl` — matrix events (signal, regime, trade lifecycle)
- **`advisory.json`** — current LLM advisory (expires ~24h)
- **`paper/advisory_log.jsonl`** — advisory history

## What's Been Built

| Component | Status | Notes |
|---|---|---|
| Bybit API client | ✓ Complete | Testnet-ready, handles errors, unwraps responses |
| 15m strategy logic | ✓ Complete | EMA cross, regime check, position sizing |
| 1h strategy logic | ✓ Complete | Built but not trading (frozen) |
| Live execution engine | ✓ Complete | Entry/exit order submission, fill polling, state persistence |
| Dashboard UI | ✓ Complete | Sim/live toggle, all tabs functional |
| Simulation runner | ✓ Complete | Historical backtest replay |
| Advisory runner | ✓ Complete | LLM-based market context, ~24h cache |
| Trade logging | ✓ Complete | Full trade anatomy recorded |
| Close position script | ✓ Fixed | Manual emergency position closer (market + limit+chase fallback) |

## Tech Stack

- **Language:** Python 3.10+
- **Framework:** Streamlit (dashboard)
- **Exchange:** Bybit (API v5)
- **LLM:** Claude Sonnet 4.6 (advisory)
- **Data:** Pandas (candles, funding, OI)
- **Logging:** JSONL + JSON state files

## How Live Trading Works

1. **Manual trigger:** User presses "▶ RUN LIVE CYCLE NOW" on dashboard tab 7
2. **State load:** Bot loads `paper/live/{strategy}/state.json`
3. **Poll fills/exits:** Checks if pending entry filled, if open position hit stop/target/timeout
4. **Fetch fresh data:** 1h candle + funding + OI from Bybit
5. **Run strategy:** Classify regime, check EMA signals
6. **Submit order:** If signal fires, place real testnet order
7. **Persist:** Update state.json, append trades.jsonl, log matrix.jsonl event

**Key constraint:** Bot is NOT autonomous. Every action (entry, exit, polling) requires a manual "RUN LIVE CYCLE NOW" press. Recommended cadence: every ~15 minutes at :00, :15, :30, :45 UTC.

## Operational Files

- **`notebooks/runners/close_position.py`** — Emergency position closer (market → limit+chase fallback)
- **`notebooks/runners/phase7b_fetch_extended_bybit.py`** — Fetch candle data from Bybit
- **`notebooks/runners/phase8_simulation_runner.py`** — Run historical simulation
- **`notebooks/runners/phase9_advisory_runner.py`** — Refresh LLM advisory
- **`.env`** (gitignored) — `BYBIT_TESTNET_API_KEY`, `BYBIT_TESTNET_API_SECRET`

## Common Workflows

| Goal | Command | Notes |
|---|---|---|
| Start dashboard | `.venv/bin/streamlit run dashboard/app.py` | Opens at localhost:8501 |
| Run live cycle | Press "▶ RUN LIVE CYCLE NOW" in dashboard | Only way to trade live |
| Refresh sim data | See `docs/current/dashboard_operations.md` § 4 | Takes ~30 sec |
| Refresh advisory | `python notebooks/runners/phase9_advisory_runner.py` | Every ~24h or before demo |
| Close position manually | `python notebooks/runners/close_position.py` | Market first, limit+chase fallback |
| Wipe live state | `rm -rf paper/live/` | Resets to $10k starting equity |

## Project Roadmap (Future)

- Fix 1m ghost halt (strategy-aware ghost detection)
- Unfreeze 1h strategies (tune parameters)
- Add autonomous mode (remove manual RUN button requirement)
- Add real live account support (currently testnet only)
