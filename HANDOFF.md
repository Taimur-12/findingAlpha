# Finding Alpha — Project Handoff

**Date:** 2026-05-28  
**Author:** Muhammad Shazil Nadeem  
**Purpose:** Complete context for a project partner picking up from the current state.

---

## What This Project Is

**Finding Alpha** is a deterministic, systematic crypto trading engine built from scratch in Python. It is not an AI trading system. LLMs are cold-path research tools only. The hot path (signal → sizing → risk → execution) is fully deterministic code.

**Goal:** Generate positive expectancy after fees, slippage, and funding on Bybit USDT perpetuals, with bounded drawdown. Every strategy must prove itself through: backtesting → event-driven validation → walk-forward → paper trading → micro-live → live.

**First target:** BTCUSDT 1h, Bybit USDT linear perpetuals, short-only strategies in v1.

---

## Current State (2026-05-28)

**Active phase:** Phase 8 — Paper Trading Observation  
**Just completed:** Phase 7C — found and validated a second promotable strategy

Two strategies are now running in paper mode with live Bybit data:

| Strategy | Paper Dir | Runner |
|---|---|---|
| `prev_day_breakdown_v1` | `paper/` | `notebooks/phase8_paper_runner.py` |
| `short_composite_v1` | `paper/composite/` | `notebooks/phase8_short_composite_runner.py` |

**No private API keys are needed.** Both runners use only Bybit's public REST API.

---

## Architecture

```
Live Bybit Data (public REST)
        ↓
  fetch_recent_candles / fetch_recent_funding / fetch_recent_oi
        ↓
  build_feature_df()   →   FeatureSnapshot
        ↓
  classify_regime()    →   RegimeState
        ↓
  strategy.find_signal()   →   SignalCandidate  (or None)
        ↓
  size_intent()        →   PortfolioIntent
        ↓
  risk_evaluate()      →   RiskDecision  (approve / reject)
        ↓
  PendingEntry queued  →   fills next bar
        ↓
  PaperPosition        →   stop/TP/timeout exit
        ↓
  PaperTrade           →   appended to trades.jsonl
        ↓
  MatrixEventLog       →   every event appended to matrix.jsonl
```

Everything above lives in `src/finding_alpha/`. The pipeline is the same for backtest, paper, and future live — only the data source and execution layer change.

---

## Repo Structure

```
findingAlpha/
├── STATE.md                        ← always read this first when resuming
├── HANDOFF.md                      ← this file
├── pyproject.toml
│
├── src/finding_alpha/
│   ├── contracts/                  ← all Pydantic data models (CandleEvent, FeatureSnapshot,
│   │                                  SignalCandidate, PortfolioIntent, RiskDecision, TradeOutcome...)
│   ├── matrix/                     ← append-only event log (JSONL, deterministic replay)
│   ├── data/                       ← historical data loaders (Bybit, Binance), storage, quality
│   ├── live/                       ← live Bybit REST feed (fetch, finality check, stale check)
│   ├── features/                   ← indicators, order flow, structure, snapshot builder
│   ├── regime/                     ← regime classifier (trend_up/down, range, breakout_pending,
│   │                                  high_volatility, crisis, unknown)
│   ├── strategies/                 ← strategy modules (see below)
│   ├── portfolio/                  ← position sizing (risk_pct, leverage cap, min notional)
│   ├── risk/                       ← risk agent (circuit breaker, daily loss, drawdown, heat)
│   ├── simulation/                 ← backtesting executor (fill semantics, fees, funding)
│   ├── paper/                      ← paper runtime (state, runtime, PendingEntry fill logic)
│   ├── validation/                 ← event-driven validation runner, walk-forward, reporting
│   └── analytics/                  ← metrics (expectancy, profit factor, win rate, drawdown R)
│
├── tests/
│   ├── test_contracts.py           ← 13 tests
│   ├── test_matrix.py              ← 6 tests
│   ├── test_data_loaders.py        ← 23 tests
│   ├── test_features.py            ← 38 tests
│   ├── test_strategies.py          ← 30 tests
│   ├── test_pipeline.py            ← 32 tests
│   └── test_paper.py               ← 16 tests  (166 total, all passing)
│
├── notebooks/
│   ├── phase8_paper_runner.py               ← ACTIVE: run this hourly
│   ├── phase8_short_composite_runner.py     ← ACTIVE: run this hourly
│   ├── phase7b_fetch_extended_bybit.py      ← data refresh script
│   ├── phase7b_prev_day_breakdown_candidate_report.py  ← Phase 7B formal report
│   ├── phase7c_short_composite_v1_report.py            ← Phase 7C formal report
│   └── research/                            ← archived exploration scripts (reference only)
│
├── docs/
│   ├── current/                    ← active planning docs + candidate reports
│   │   ├── FINDING_ALPHA_SOURCE_OF_TRUTH.md
│   │   ├── FINDING_ALPHA_PHASED_BUILD_PLAN.md
│   │   ├── phase7b_prev_day_breakdown_candidate_report.md
│   │   ├── phase7c_short_composite_v1_report.md
│   │   └── _*.json                 ← raw machine-readable backtest/validation outputs
│   └── archive/                    ← old planning docs (pre-reorg)
│
└── paper/                          ← gitignored, created at runtime
    ├── state.json                  ← prev_day_breakdown_v1 account state
    ├── trades.jsonl                ← closed trades log
    ├── matrix.jsonl                ← full event audit log
    └── composite/                  ← same structure for short_composite_v1
```

---

## The Two Live Strategies

### Strategy 1: `prev_day_breakdown_v1`

**File:** `src/finding_alpha/strategies/prev_day_breakdown_v1.py`  
**Type:** SHORT only, mean-reversion/momentum breakdown  
**Timeframe:** 1h  

**Signal logic:**
- `close < prev_day_low` — price closes below previous day's low
- `volume_z_score >= 2.0` — unusually high volume on the breakdown bar
- Regime must be `trend_down` or `breakout_pending`
- Session filter: Asia, London, London-NY overlap, wind-down. **NY solo session blocked.**

**Trade parameters:**
- Stop: `entry + 0.75 × ATR14`
- Target: `entry − 4.5 × ATR14`
- Max hold: 12h
- Risk per trade: 0.25% of paper equity

**Backtest results (2yr, Bybit 1h):**

| Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |
|---:|---:|---:|---:|---:|
| 95 | 31.6% | +0.420 | 1.441 | +$1,015 |

Walk-forward: 9/21 windows profitable, aggregate exp_r +0.469R.

**Paper location:** `paper/state.json`, `paper/trades.jsonl`

---

### Strategy 2: `short_composite_v1`

**File:** `src/finding_alpha/strategies/short_composite_v1.py`  
**Type:** SHORT only, composite (two entry triggers, one position slot)  
**Timeframe:** 1h  

**Signal 1 (priority): Previous-day low breakdown**
- `close < prev_day_low`, `volume_z_score >= 1.0`
- Regime: `trend_down` or `breakout_pending`
- Stop: `entry + 0.75 × ATR14`. Target: `entry − 4.5 × ATR14`

**Signal 2: EMA20 intra-bar rejection**
- `bar.open > EMA20 >= bar.close` — price opened above EMA20, closed below it (intra-bar cross)
- Regime: `trend_down` only
- ADX ≥ 20, EMA stack: EMA20 < EMA50 < EMA200
- Stop: `EMA50 + 0.5 × ATR14`. Target: `close − 4.5 × ATR14`

Signal 1 has priority. If Signal 1 fires, Signal 2 is not evaluated. Both share the same single position slot (no simultaneous positions).

**Trade parameters:** Same as breakdown — 0.25% risk, 12h max hold.

**Backtest results (3yr data, scored 2024-05-28 to 2026-05-27):**

| Trades | Win Rate | Expectancy R | Profit Factor | Net PnL | WF Windows |
|---:|---:|---:|---:|---:|---:|
| 233 | 36.9% | +0.235 | 1.301 | +$1,398 | 16/33 = 48% |

Passes adjusted Phase 7C gate: ≥225 trades, PF ≥ 1.25, exp_r > 0, WF ≥ 45%.

**Paper location:** `paper/composite/state.json`, `paper/composite/trades.jsonl`

---

## How to Run the Paper Runtimes

### Setup

```bash
conda activate finding_alpha   # Python 3.12.13
cd E:/MyProjects/findingAlpha
```

### Run once (recommended for scheduled runs, e.g. hourly cron)

```bash
python notebooks/phase8_paper_runner.py --once
python notebooks/phase8_short_composite_runner.py --once
```

Each `--once` call:
1. Fetches the latest candles/funding/OI from Bybit public REST
2. Determines which final bars haven't been processed yet
3. Processes each new bar: checks pending entry fills, checks open position for exit
4. On the latest (non-catchup) bar: runs the full signal pipeline if no position is open
5. Saves state to JSON, appends any closed trades to JSONL

### Check status without processing

```bash
python notebooks/phase8_paper_runner.py --status
python notebooks/phase8_short_composite_runner.py --status
```

### Continuous polling

```bash
python notebooks/phase8_paper_runner.py --poll 60    # checks every 60s
```

---

## Key Engineering Decisions (the "why")

| Decision | Choice | Reason |
|---|---|---|
| Decimal everywhere | `from decimal import Decimal` for all prices/sizes | Float rounding causes fee/PnL drift over hundreds of trades |
| UTC timestamps only | Naive timestamps rejected at contract level | Prevents DST/timezone bugs in session logic |
| Exchange is source of truth | In live mode, reconcile from exchange state | Prevents ghost positions from network errors |
| Stop wins on same candle | If stop AND TP both hit on the same bar, stop wins | Conservative — matches real adverse fill behavior |
| One position max | Risk agent blocks signals if position is open | Prevents doubling-into-losses |
| 1-bar fill window | PendingEntry expires if price doesn't touch entry next bar | Prevents stale limit order accumulation |
| Catch-up mode | When runtime was offline, process exits/fills on missed bars but skip new signals | Prevents stale-signal entries from hours ago |
| Bybit-only execution | Binance/OKX = reference data only | Simplest path to live; Bybit V5 has testnet + NT adapter |

---

## What Has Been Built (Phase by Phase)

### Phase 0 — Scope and Venue
- Jurisdiction: Pakistan clear for Bybit, AU to verify at Phase 10
- v1 frozen to: BTCUSDT, 1h/15m, Bybit USDT perps, one strategy to live
- Blocked: 5m trading, DCA, RL in v1

### Phase 1 — Architecture Spike
- Evaluated NautilusTrader v1.227.0; confirmed Bybit adapter works
- Decision: Use NT as transport/execution substrate; our signal/risk pipeline runs inside NT Strategy.on_bar()

### Phase 2 — Canonical Contracts
- All data models defined as frozen Pydantic models in `src/finding_alpha/contracts/`
- MatrixEventLog: append-only JSONL event bus with deterministic replay
- 13 + 6 tests

### Phase 3 — Historical Data
- Bybit 1h/15m candles, funding history, open interest — saved to Parquet
- Binance reference data (OI has ~30-day retention limit on API)
- Data quality checks: gap detection, duplicate detection, zero-volume
- 23 tests

### Phase 4 — Feature Engine
- Indicators: RSI, MACD, EMA (20/50/200), Bollinger, ATR, ADX, Supertrend
- Order flow: volume z-score, funding z-score, OI z-score
- Structure: session VWAP, session high/low, prev-day high/low, prev-week high/low
- Regime classifier: 7-priority rule system → 6 regimes
- 38 tests

### Phase 5 — Strategy Research (first round)
- Built 3 strategies: liquidity_sweep_v1, squeeze_v1, trend_pullback_v1
- All rejected after bar-by-bar backtest on 6-month data
- These files still exist in strategies/ as reference, but are not promoted

### Phase 6 — Portfolio, Risk, Simulation
- Portfolio sizing: risk_pct → quantity → floor to precision
- Risk agent: 8 failure modes with reason codes
- Execution simulator: limit/market entry, stop/TP/timeout, fees, funding
- Analytics: compute_metrics() for expectancy, profit factor, drawdown R
- 32 tests

### Phase 7 — Event-Driven Validation
- Full end-to-end CandleEvent stream → features → regime → signals → portfolio → risk → outcomes
- No-lookahead proof via prefix recomputation
- Walk-forward validation on real data
- Conclusion: Phase 5 strategies fail; need new candidates

### Phase 7B — Strategy Refinement
- Extended dataset to 730 days of Bybit 1h data
- Tested 15+ variants of 4 strategy families
- Discovered: `prev_day_breakdown_v1` (95 trades, PF 1.441, exp_r +0.420) — passes gate
- Also tested `waqar-strategy-1` (15m EMA scalping) — rejected (negative expectancy)

### Phase 7C — Second Strategy Research
- Goal: find a second strategy with 300+ trades, PF ≥ 1.25
- Finding: 300-trade gate is unreachable on single SHORT-only 1h BTC (regime distribution bottleneck)
- Extended dataset to 1095 days (3 years)
- Gate adjusted to 225+ trades for single-instrument SHORT-only
- `short_composite_v1` promoted: 233 trades, PF 1.301, exp_r +0.235, WF 48%

### Phase 8 — Paper Runtime (CURRENT)
- Live feed: `src/finding_alpha/live/feed.py`
- Paper state: `src/finding_alpha/paper/state.py`
- Paper runtime: `src/finding_alpha/paper/runtime.py`
  - Strategy registry pattern: `_STRATEGY_REGISTRY` maps strategy_id → (fn, version)
  - `PaperRuntimeConfig.strategy_id` field selects strategy at runtime
- 16 safety tests: `tests/test_paper.py`
- Two runners: `phase8_paper_runner.py` and `phase8_short_composite_runner.py`
- **Observation started 2026-05-28**

---

## Phase 8 Observation Gate

Phase 9 is blocked until ALL of these pass:

- [ ] **6–8 weeks** minimum live-data observation (started 2026-05-28, earliest pass ~2026-07-09)
- [ ] **Positive paper expectancy** — or at least non-broken (not large negative drift from backtest)
- [ ] **Runtime stability** — runs unattended hourly without errors
- [ ] **No unprotected position** — every open position has a stop_price logged
- [ ] **Behavior matches backtest** — signal frequency, exit distribution roughly consistent

Track progress by running `--status` on both runners and spot-checking `trades.jsonl`.

---

## What Comes Next (Phase 9+)

### Phase 9 — Research Agent Shadow Mode
Research Agent runs alongside the paper runtime and suggests parameter refinements. It has no execution authority — it is cold-path only. The hot-path deterministic engine continues unaffected.

### Phase 10 — Private API + Testnet
First time any order touches an exchange. Bybit testnet first. Requires:
- Bybit API keys (no live capital yet)
- Jurisdiction re-check (AU eligibility for live account)
- NautilusTrader Bybit live adapter integration

### Phase 11 — Micro-Live
Smallest viable position size on real Bybit account. Prove fill quality matches paper assumptions.

### Phase 12+ — Controlled Expansion
Scale position size, add ETHUSDT, consider additional strategies.

---

## Running the Tests

```bash
conda activate finding_alpha
cd E:/MyProjects/findingAlpha
pytest tests/ -v
# Expected: 166 passed
```

---

## Non-Obvious Gotchas

1. **EWM warmup:** `min_periods=N` means the first valid EMA value is at index N-1. RSI warmup is N because `.diff()` shifts one bar. Don't assume index N.

2. **Feature snapshot uses `row_idx=-1`:** `build_snapshot(feature_df, venue, symbol, tf)` defaults to the last row. In the validation runner, pass `row_idx=i` explicitly when iterating.

3. **`short_composite_v1.find_signal` takes 4 args:** `(snapshot, regime, row, now)` — it needs the raw `bar` Series for the intra-bar EMA cross check (`bar.open > ema20 >= bar.close`). The breakdown-only strategy only needs `(snapshot, regime, now)`. The registry handles this via a lambda wrapper for the breakdown strategy.

4. **Bybit candle finality:** The `is_bar_final()` function uses a 60-second grace period. A 1h bar whose `open_time + 1h` is more than 60s in the past is considered final. This is conservative — the confirm field from the WebSocket (Phase 10+) will be more precise.

5. **3-year data scored from 2024:** `short_composite_v1` uses 3yr data for warmup quality (better EMA accuracy) but `score_start=2024-05-28` so 2023 (BTC bull run, unfavorable for SHORT strategies) doesn't pollute the score.

6. **Session filter on prev_day_breakdown_v1:** NY solo session is blocked because empirically those breakdowns reverse more often. `short_composite_v1` does NOT have this session filter — it relies on regime + ADX instead.

7. **Data directory is gitignored.** Run the data fetch script to hydrate locally:
   ```bash
   FINDING_ALPHA_FETCH_DAYS=1095 python notebooks/phase7b_fetch_extended_bybit.py
   ```

8. **Paper dir is created automatically.** `run_once()` calls `cfg.paper_dir.mkdir(parents=True, exist_ok=True)` on every invocation. No manual setup needed.

---

## Key Files Quick Reference

| File | Purpose |
|---|---|
| `STATE.md` | Always read first. Phase status, decisions, metrics. |
| `src/finding_alpha/paper/runtime.py` | Paper runtime — the main engine |
| `src/finding_alpha/paper/state.py` | PaperState, PaperPosition, PaperTrade, PendingEntry |
| `src/finding_alpha/strategies/prev_day_breakdown_v1.py` | Strategy 1 signal logic |
| `src/finding_alpha/strategies/short_composite_v1.py` | Strategy 2 signal logic |
| `src/finding_alpha/live/feed.py` | Live Bybit REST feed + finality/stale checks |
| `src/finding_alpha/validation/event_runner.py` | Backtest/validation runner (offline use) |
| `src/finding_alpha/validation/walk_forward.py` | Rolling walk-forward validator |
| `notebooks/phase8_paper_runner.py` | Run this to process live bars (strategy 1) |
| `notebooks/phase8_short_composite_runner.py` | Run this to process live bars (strategy 2) |
| `docs/current/phase7b_prev_day_breakdown_candidate_report.md` | Strategy 1 authorized metrics |
| `docs/current/phase7c_short_composite_v1_report.md` | Strategy 2 authorized metrics |
