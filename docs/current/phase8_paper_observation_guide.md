# Phase 8 — Paper Trading Observation Guide

**Phase start:** 2026-05-28  
**Original "hard minimum":** ~2026-07-23 (8 weeks)  
**Status (2026-05-29):** RUNTIME COMPLETE. Sim-validated. Observation now runs **in the background** while the accelerated build progresses through Phases 9–11. The wall-clock observation period is no longer a hard block on downstream code work — it remains a hard block on **deploying live capital**.

---

## Accelerated Build Note (2026-05-29)

The original guide framed Phase 8 as a 6–8 week blocking gate before Phase 9 could begin. Under the accelerated build path (see `FINDING_ALPHA_PHASED_BUILD_PLAN.md` section 0.4), this changes:

- The runtime is already complete and was validated against 8 weeks of historical data on 2026-05-29 — no crashes, no unprotected positions, no circuit breaker trips, sane exit distribution.
- The cron-based paper observation continues uninterrupted in the background.
- Phases 9, 10, and 11 are built in parallel against the same data and against Bybit testnet.
- **Real capital deployment (Phase 11 micro-live, Phase 12 live v1) is still blocked** until the original observation evidence has accumulated AND the accelerated build code is reviewed.

The observation guide below still describes what to watch for. Read it as "what the background observation is doing," not "what must finish before any other code can be written."

---

## What Phase 8 Is

Phase 8 is a live-data observation period. The goal is **not** to build new code — the runtime is already complete. The goal is to watch both strategies behave on live Bybit data and confirm they behave consistently with their backtests.

No private API keys are needed. Both runners use only Bybit's public REST API.

---

## What Was Built (already complete entering Phase 8)

| Module | File | Purpose |
|---|---|---|
| Live feed | `src/finding_alpha/live/feed.py` | Fetch candles, funding, OI from Bybit REST; bar finality and stale checks |
| Paper state | `src/finding_alpha/paper/state.py` | PaperState, PaperPosition, PendingEntry, PaperTrade, JSON persistence |
| Paper runtime | `src/finding_alpha/paper/runtime.py` | `process_final_bar()`, `run_once()`, `run_loop()` |
| Runner (strategy 1) | `notebooks/phase8_paper_runner.py` | Runs `prev_day_breakdown_v1` in `paper/` dir |
| Runner (strategy 2) | `notebooks/phase8_short_composite_runner.py` | Runs `short_composite_v1` in `paper/composite/` dir |
| Safety tests | `tests/test_paper.py` | 16 tests covering bar finality, stale data, position invariants, trade logging |

---

## The Two Strategies Under Observation

### Strategy 1 — `prev_day_breakdown_v1`

| Metric | Backtest Value |
|---|---|
| Trades | 95 (2yr data) |
| Win rate | 31.6% |
| Expectancy | +0.420R |
| Profit factor | 1.441 |
| Net PnL | +$1,015 |

**Signal logic:** Close below previous day's low, volume z-score ≥ 2.0, regime `trend_down` or `breakout_pending`, Asia / London / overlap sessions only (NY solo blocked).  
**Stop:** entry + 0.75 × ATR14  
**Target:** entry − 4.5 × ATR14  
**Max hold:** 12h  
**Risk per trade:** 0.25% of paper equity

**Paper files:** `paper/state.json`, `paper/trades.jsonl`, `paper/matrix.jsonl`

---

### Strategy 2 — `short_composite_v1`

| Metric | Backtest Value |
|---|---|
| Trades | 233 (3yr data, scored from 2024) |
| Win rate | 36.9% |
| Expectancy | +0.235R |
| Profit factor | 1.301 |
| Net PnL | +$1,398 |
| Walk-forward | 16/33 windows profitable |

**Signal 1 (priority):** Close < prev_day_low, vol_z ≥ 1.0, regime `trend_down` / `breakout_pending`.  
**Signal 2:** Bar opens above EMA20, closes below it; regime `trend_down`; ADX ≥ 20; EMA stack (EMA20 < EMA50 < EMA200).  
**Stop:** S1 = entry + 0.75 ATR | S2 = EMA50 + 0.5 ATR  
**Target:** entry − 4.5 × ATR14 (both signals)

**Paper files:** `paper/composite/state.json`, `paper/composite/trades.jsonl`, `paper/composite/matrix.jsonl`

---

## How the Runtime Works (one `--once` call)

```
1. fetch_recent_candles()    — last 305 bars from Bybit public REST
2. filter to final bars      — is_bar_final(): open_time + 1h + 60s grace
3. determine new bars        — bars newer than last_processed_bar_ts
4. fetch funding + OI        — last 14 days each
5. for each new bar (oldest → newest):
     a. try fill pending entry  — 1-bar window; fills if price touches entry
     b. check open position     — stop / TP / max_hold_time exit
     c. [latest bar only] run pipeline:
           build_feature_df() → FeatureSnapshot
           classify_regime() → RegimeState
           find_signal() → SignalCandidate (or None)
           size_intent() → PortfolioIntent
           risk_evaluate() → RiskDecision
           if approved: set PendingEntry (fills next bar)
6. save_state() + append trades.jsonl
```

**Catch-up mode:** If the runner was offline for multiple hours, steps (a) and (b) run on every missed bar, but new signals are only attempted on the latest bar. This prevents stale-signal entries.

---

## How to Run

### Activate environment

```bash
source .venv/bin/activate
```

### Process new bars (run this hourly)

```bash
python notebooks/phase8_paper_runner.py --once
python notebooks/phase8_short_composite_runner.py --once
```

### Check status without processing

```bash
python notebooks/phase8_paper_runner.py --status
python notebooks/phase8_short_composite_runner.py --status
```

### Continuous polling (keeps terminal open)

```bash
python notebooks/phase8_paper_runner.py --poll 60
python notebooks/phase8_short_composite_runner.py --poll 60
```

### Automate with cron (recommended for unattended operation)

```bash
crontab -e
```

Add:
```
5 * * * * cd "/Users/taimurjahanzaib/Desktop/AI QUANT FIRM" && .venv/bin/python notebooks/phase8_paper_runner.py --once >> /tmp/paper_breakdown.log 2>&1
6 * * * * cd "/Users/taimurjahanzaib/Desktop/AI QUANT FIRM" && .venv/bin/python notebooks/phase8_short_composite_runner.py --once >> /tmp/paper_composite.log 2>&1
```

### Reset state (start from scratch)

```bash
rm paper/state.json paper/matrix.jsonl
rm paper/composite/state.json paper/composite/matrix.jsonl
# trades.jsonl files will also exist after first trades; delete if resetting fully
```

---

## Simulating Phase 8 on Historical Data

Instead of waiting 6–8 weeks in real time, you can replay the last 8 weeks of historical Bybit data through the **exact same paper runtime code**. This is not cheating — the strategies were validated on this data already. The purpose of simulation is to:

1. Confirm the paper runtime code (pending entry fills, stop/TP logic, state persistence) behaves identically to the backtester
2. Generate a full `trades.jsonl` so you can inspect signal frequency, exit distribution, and equity curve
3. Check that the runtime does not crash, produce unprotected positions, or diverge from expected behavior

Run the simulation with:

```bash
python notebooks/phase8_simulation_runner.py --weeks 8
```

This replays the last 8 weeks of historical data (from `data/bybit/BTCUSDT/1h/candles.parquet`) through both strategies. Results are written to `paper/sim/` and `paper/sim/composite/` so they do not overwrite your live paper state.

After simulation, check both `--status` outputs (the script prints them) and compare:

| Metric | Expected range (from backtest) |
|---|---|
| Trades in 8 weeks | prev_day: 3–10 | composite: 8–18 |
| Expectancy | Should be near backtest value (within noise for small N) |
| No unprotected positions | Every PaperTrade must have entry_price, stop_price, exit_price |
| No crashes | Script must exit cleanly with status=ok |

If simulation passes, the runtime infrastructure is sound and you can confidently run live paper trading.

---

## Phase 8 Gate — All must pass before advancing to Phase 9

| Criterion | How to verify |
|---|---|
| 6–8 weeks minimum elapsed | Check `paper/state.json` last_processed_bar_ts vs start date 2026-05-28 |
| Positive or non-broken expectancy | `--status` on both runners; trades.jsonl shows expectancy ≥ −0.2R |
| Runtime runs unattended | Cron logs show no errors over multiple weeks |
| No unprotected paper position | Every entry in trades.jsonl has a non-null exit_reason; matrix.jsonl has no open positions without stop |
| Behavior matches backtest | Signal frequency, win rate, exit distribution within plausible range of backtest |

### What "positive or non-broken" means

With low trade counts (20–40 trades in 8 weeks), statistical noise is high. You are NOT trying to match the exact backtest P&L. You are looking for red flags:

- Expectancy < −1.0R over 10+ trades → something is structurally wrong
- 0 trades in 8 weeks → strategy is broken or signals are always blocked
- Circuit breaker triggered → drawdown exceeded 10% (serious problem)
- Runtime crashes every day → infrastructure problem (must fix before Phase 9)

Expect roughly:
- `prev_day_breakdown_v1`: 1–2 trades per 2 weeks (very low frequency)
- `short_composite_v1`: 2–4 trades per 2 weeks

---

## What to Watch For

### Good signs
- Signals firing at expected frequency
- Exit distribution consistent with backtest (mostly stop_loss exits, occasional take_profit)
- Win rate near 30–37% (small N, so ±15pp is acceptable noise)
- Runtime recovers cleanly from network errors (returns to `status: ok` next run)

### Warning signs
- Circuit breaker trips (equity fell 10%)
- 0 signals over 4+ weeks (check regime distribution; possible regime-filter over-blocking)
- Pending entries consistently miss (price never touches entry after signal → fill assumption wrong)
- Matrix log shows repeated `DATA_STALE` events (feed reliability issue)

### Fatal signs (stop, investigate before proceeding)
- Unprotected position in state.json (stop_price missing)
- Equity jumping up/down without corresponding trade in trades.jsonl (PnL accounting bug)
- Runtime writing duplicate trades for the same signal_id

---

## Files Written During Observation

| File | Contents |
|---|---|
| `paper/state.json` | Current equity, open position, pending entry, last bar processed |
| `paper/trades.jsonl` | Append-only; one JSON line per closed trade with entry/exit/PnL/R |
| `paper/matrix.jsonl` | Full event audit log: every CandleEvent, FeatureSnapshot, RegimeState, Signal, RiskDecision, TradeOutcome |
| `paper/composite/state.json` | Same as above, for short_composite_v1 |
| `paper/composite/trades.jsonl` | Closed trades for short_composite_v1 |
| `paper/composite/matrix.jsonl` | Full event log for short_composite_v1 |

---

## After Phase 8 Gate Passes → Phase 9

Phase 9 is the Research Agent shadow mode — the LLM advisory layer runs alongside the paper runtime and produces a bounded advisory JSON (strategy_allowlist, risk_scalar, hard_block) that the runtime consults before taking signals.

Design document: `docs/current/phase9_llm_advisory_layer_design.md`

Phase 9 is fully blocked until Phase 8 gate passes. Do not begin Phase 9 work until:
- Both runners have operated without errors for 6+ weeks
- At least one of the strategies has produced ≥ 5 paper trades
- Expectancy is not deeply negative (> −1.0R average)
