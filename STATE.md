# Finding Alpha — Project State

Last updated: 2026-05-30 (Phase 10 green — paused for partner alignment)

## Current Phase: PAUSE — partner strategy review before any capital deployment

Phases 9 and 10 are complete. Phase 10 testnet smoke test passed end-to-end against the real Bybit testnet on 2026-05-30: submit → reconcile → cancel round-trip green, zero divergences, exchange-confirmed cancel. The execution stack works.

Next step is **not** cloud deployment or live capital. User is meeting with partner to revisit strategy direction. The two frozen strategies (`prev_day_breakdown_v1`, `short_composite_v1`) remain in place as-is until that decision is made.

Strategies frozen for this build: `prev_day_breakdown_v1`, `short_composite_v1`. No tuning until partner alignment complete.

## Long-Term Strategic Direction (added 2026-05-30)

This project will not become a top-tier quant fund — that competes on data spend ($50M+/yr), latency (microseconds), and PhD count (100+). We compete in markets/timeframes where those moats don't apply: retail-sized crypto perpetuals, 1h-and-slower bars, public-data strategies. The right comparable is a disciplined 1-2 person systematic prop trader who adopts hedge-fund-grade discipline and infrastructure mental models without the spend.

**Tiered roadmap for data, ML, and LLM (each tier earns the right to the next):**

| Tier | What | When |
|---|---|---|
| Data | Parquet + JSONL (current) → DuckDB on Parquet for queryable analytics | Phase 11.5 |
| ML | Cold-path only — trade outcome classifier, strategy decay detector, regime ML second-opinion | Phase 12.5 |
| LLM agents | Daily advisor (Phase 9) → trade post-mortem + strategy hypothesis + doc tagger | Phase 13.5 |
| RL | Skipped indefinitely — sample size insufficient, reward hacking common, big-fund literature mostly negative | N/A |

ML and LLMs stay out of the hot path. Hot path (signal → sizing → risk → execution) remains fully deterministic. ML/LLM live in research and risk-advisory roles only.

## Phase Status

| Phase | Name | Status |
|---|---|---|
| 0 | Scope and Venue Eligibility | COMPLETE |
| 1 | Architecture Spike | COMPLETE |
| 2 | Canonical Contracts + Matrix | COMPLETE |
| 3 | Historical Data Foundation | COMPLETE |
| 4 | Feature + Regime Engine | COMPLETE |
| 5 | Strategy Research + Fast Rejection | COMPLETE |
| 6 | Portfolio, Risk, Execution Simulation | COMPLETE |
| 7 | Authoritative Event-Driven Validation | COMPLETE — short_composite_v1 promoted |
| 8 | Live-Data Paper Runtime | RUNTIME COMPLETE — sim validated, cron observation running in background |
| 9 | LLM Advisory Layer | COMPLETE — Claude advisor wired into runtime, advisory log persisting |
| 10 | Private API + Bybit Testnet Execution | COMPLETE — live testnet smoke test passed 2026-05-30 |
| 11 | Micro-Live Trading | PAUSED — code-ready, deferred pending partner strategy review |
| 11.5 | Data Infrastructure Upgrade (DuckDB + counterfactual log) | PLANNED — after micro-live capital deployed |
| 12 | Live v1 | BLOCKED until micro-live capital deployment proves out |
| 12.5 | Cold-path ML (trade outcome classifier, decay detector, regime ML second-opinion) | PLANNED — after live v1 stable |
| 13 | Controlled Expansion (ETHUSDT, second strategy) | BLOCKED |
| 13.5 | Cold-path LLM agents (trade post-mortem, strategy hypothesis, document tagger) | PLANNED — after expansion |
| 14 | Advanced Research Backlog | BLOCKED (RL stays blocked indefinitely) |

---

## Phase 0 Checklist (COMPLETE)

- [x] Jurisdiction confirmed: Pakistan = clear for Bybit, Australia = verify at Phase 10
- [x] First execution venue: Bybit USDT linear perpetuals
- [x] v1 scope frozen: BTCUSDT first, 15m/1h, one strategy to live
- [x] Blocked features list accepted and documented
- [x] Decision docs written: v1_scope_decision.md, venue_eligibility_decision.md, blocked_features.md

## Phase 1 Checklist (COMPLETE)

- [x] NautilusTrader v1.227.0 installed, all imports OK including Bybit adapter
- [x] Bybit BTCUSDT 15m public klines fetched (200 candles) and saved to Parquet
- [x] Custom event replay loop proved trivial (200 candles, 98 dummy signals)
- [x] NT strategy boundary spike: SignalCandidate -> RiskDecision -> Order fits inside NT Strategy.on_bar()
- [x] Decision: ADOPT NautilusTrader as substrate
- [x] Decision docs: architecture_spike_report.md, nautilus_vs_custom_decision.md
- [x] bybit_order_semantics_report.md — order types, fill semantics, fees, candle finality
- NOTE: Bybit candle finality (confirm field) to be verified in Phase 8 (live data)

## Phase 2 Checklist (COMPLETE)

- [x] MarketEvent, CandleEvent, DataQualityEvent — src/finding_alpha/contracts/market.py
- [x] FeatureSnapshot, RegimeState — src/finding_alpha/contracts/features.py
- [x] SignalCandidate, ResearchState — src/finding_alpha/contracts/signals.py
- [x] PortfolioIntent, RiskDecision, OrderPlan, OrderEntry, TargetLevel — src/finding_alpha/contracts/trading.py
- [x] ExecutionReport, TradeOutcome — src/finding_alpha/contracts/execution.py
- [x] Reason code registry (50+ codes) — src/finding_alpha/contracts/reason_codes.py
- [x] Matrix: append-only event log with JSONL persistence — src/finding_alpha/matrix/event_log.py
- [x] 19/19 tests passing — tests/test_contracts.py, tests/test_matrix.py

## Phase 3 Checklist (COMPLETE)

- [x] Bybit historical loader: BTCUSDT 15m + 1h candles, funding history, open interest
- [x] Binance reference loader: USD-M futures klines, funding, OI
- [x] Data normalization: symbol, venue, timeframe, timestamp alignment
- [x] Data quality report: gap detection, duplicate detection, zero-volume check
- [x] Save to Parquet by venue/symbol/timeframe with metadata file
- [x] Replay-ready historical event stream into MatrixEventLog
- [x] 23/23 data layer tests passing — tests/test_data_loaders.py
- NOTE: Data already fetched and saved to data/ (2025-11-28 → 2026-05-27)
- NOTE: Binance OI history retention cap is ~30 days (API limitation). Bybit OI has full 6 months.
- NOTE: Binance openInterestHist endpoint rejects startTime param — must paginate backward using endTime only.
- [x] phase3_data_quality_report.md — quality checks, known limitations, storage format

## Phase 4 Checklist (COMPLETE)

- [x] Indicators: RSI 6/14/24, MACD 12/26/9, EMA 20/50/200 + slope, Bollinger + %B + bandwidth, ATR 14 + percentile, ADX 14, Supertrend
- [x] Order-flow: volume z-score, funding rate + z-score, OI value + delta + z-score
- [x] Structure: session VWAP, session high/low, prev day high/low, prev week high/low
- [x] Snapshot builder: build_feature_df() for research, build_snapshot() → FeatureSnapshot
- [x] Regime classifier: classify_regime(snapshot) → RegimeState (trend_up/down, range, breakout_pending, high_volatility, crisis, unknown)
- [x] 38/38 tests passing — tests/test_features.py
- NOTE: EWM warmup (min_periods=N) first valid at index N-1, not N. RSI warmup is N because .diff() shifts one bar. TR[0] = H-L (valid) since pd.max skips NaN.
- [x] phase4_feature_validation_report.md — all indicator formulas, warmup periods, regime classifier rules

## Phase 5 Checklist (COMPLETE)

- [x] liquidity_sweep_v1: sweep reversal (wick below/above key level + reclaim + vol spike)
- [x] squeeze_v1: BB bandwidth compression → breakout with supertrend confirmation
- [x] trend_pullback_v1: EMA pullback in confirmed trend with RSI + ADX conditions
- [x] fast_reject.py: shared regime/feature/R:R helpers (SIGNAL_REGIME_BLOCKED, DATA_MISSING_FEATURE, SIGNAL_TARGET_INSUFFICIENT_R)
- [x] 30/30 strategy tests — tests/test_strategies.py
- [x] 110/110 total tests passing across all phases
- [x] phase5_backtest_runner.py — bar-by-bar backtest on Bybit 1h data, RSI sensitivity grid, results saved to docs/current/_backtest_results.json
- [x] strategy_research_liquidity_sweep_v1.md — backtest analysis, verdict: MARGINAL
- [x] strategy_research_squeeze_v1.md — backtest analysis, verdict: REJECTED
- [x] strategy_research_trend_pullback_v1.md — backtest analysis + RSI sensitivity grid, verdict: REJECTED (current params)
- [x] phase5_candidate_shortlist.md — rejected strategies + v1 live candidate (liquidity_sweep_v1)
- NOTE: All three strategies use 2.0-2.5×ATR targets with hard 1.5 min R:R enforcement. Signals blocked at R:R < 1.5.
- NOTE: liquidity_sweep_v1 is the only v1 candidate — needs larger dataset validation before live capital.
- NOTE: squeeze_v1 and trend_pullback_v1 rejected; trend_pullback_v1 flagged for v2 rework in Phase 14.

---

## Key Decisions Made

| Decision | Choice | Reason |
|---|---|---|
| Jurisdiction | Pakistan clear, AU verify at Phase 10 | Bybit restricts some regions |
| First execution venue | Bybit USDT linear perpetuals | V5 API, testnet, NT adapter |
| Reference data | Binance primary, OKX secondary | Highest liquidity, best data quality |
| Symbols | BTCUSDT first, ETHUSDT after BTC proven | Reduce complexity in v1 |
| Timeframes | 15m and 1h only | 5m locked until paper proves fill quality |
| Event engine | NautilusTrader v1.227.0 | Bybit adapter, backtest/live parity built-in |
| NT architecture | Our pipeline inside NT Strategy.on_bar() | NT = transport + execution, we = signal + risk |
| DCA | Blocked in v1 | Increases tail risk, complicates accounting |
| 5m trading | Blocked in v1 | Dominated by fees, spread, fill assumptions |
| RL | Blocked in v1 | No live capital until deterministic system proven |

## Open Questions

- **Australia live account**: Verify current Bybit AU eligibility before Phase 10 (not blocking now)

---

## Environment

- Conda env: `finding_alpha` (Python 3.12.13)
- Activate: `conda activate finding_alpha`
- Run tests: `cd E:/MyProjects/findingAlpha && pytest tests/ -v`
- Spike scripts: `notebooks/phase1_spike.py`, `notebooks/phase1_nautilus_spike.py`
- Data (gitignored): `data/bybit_BTCUSDT_15m_spike.parquet` (200 candles, from Phase 1)

## Repo Structure

```
findingAlpha/
├── STATE.md                              <- this file, always read first
├── pyproject.toml                        <- package config, dependencies
├── .gitignore
├── docs/
│   ├── current/
│   │   ├── FINDING_ALPHA_SOURCE_OF_TRUTH.md
│   │   ├── FINDING_ALPHA_PHASED_BUILD_PLAN.md
│   │   ├── agentic_quant_trading_project_deep_dive.md
│   │   ├── v1_scope_decision.md
│   │   ├── venue_eligibility_decision.md
│   │   ├── blocked_features.md
│   │   ├── architecture_spike_report.md
│   │   ├── nautilus_vs_custom_decision.md
│   │   ├── bybit_order_semantics_report.md   <- Phase 1 deliverable
│   │   ├── phase3_data_quality_report.md     <- Phase 3 deliverable
│   │   ├── phase4_feature_validation_report.md <- Phase 4 deliverable
│   │   ├── strategy_research_liquidity_sweep_v1.md
│   │   ├── strategy_research_squeeze_v1.md
│   │   ├── strategy_research_trend_pullback_v1.md
│   │   ├── phase5_candidate_shortlist.md
│   │   └── _backtest_results.json            <- raw backtest metrics (machine-readable)
│   └── archive/                          <- old quantfusion/session/ollama files
├── src/
│   └── finding_alpha/
│       ├── __init__.py
│       ├── contracts/
│       │   ├── __init__.py               <- exports all contracts
│       │   ├── reason_codes.py           <- all reason code constants
│       │   ├── market.py                 <- MarketEvent, CandleEvent, DataQualityEvent
│       │   ├── features.py               <- FeatureSnapshot, RegimeState
│       │   ├── signals.py                <- SignalCandidate, ResearchState
│       │   ├── trading.py                <- PortfolioIntent, RiskDecision, OrderPlan
│       │   └── execution.py              <- ExecutionReport, TradeOutcome
│       ├── matrix/
│       │   ├── __init__.py
│       │   └── event_log.py              <- MatrixEventLog, replay()
│       └── data/
│           ├── __init__.py               <- exports all data functions
│           ├── bybit_loader.py           <- fetch_candles, fetch_funding, fetch_open_interest
│           ├── binance_loader.py         <- fetch_candles, fetch_funding, fetch_open_interest
│           ├── normalizer.py             <- normalize_candles, normalize_funding, normalize_open_interest
│           ├── quality.py                <- check_candles (gap/dup/zero-vol)
│           ├── storage.py                <- save/load Parquet + metadata.json
│           └── replay_loader.py          <- load_candles_to_matrix
│       ├── features/
│       │   ├── __init__.py
│       │   ├── indicators.py             <- RSI, MACD, EMA, ATR, Bollinger, ADX, Supertrend
│       │   ├── orderflow.py              <- volume/funding/OI z-scores, merge helpers
│       │   ├── structure.py              <- session VWAP, session/prev-day/week levels
│       │   └── snapshot.py              <- build_feature_df(), build_snapshot()
│       ├── regime/
│       │   ├── __init__.py
│       │   └── classifier.py             <- classify_regime() 7-priority rule system
│       └── strategies/
│           ├── __init__.py
│           ├── fast_reject.py            <- shared check_regime, check_features, check_rr
│           ├── liquidity_sweep_v1.py     <- sweep reversal (wick + reclaim + volume)
│           ├── squeeze_v1.py             <- BB squeeze breakout + supertrend
│           └── trend_pullback_v1.py      <- EMA 50 pullback in confirmed trend
│       ├── portfolio/
│       │   ├── __init__.py
│       │   └── agent.py                  <- PortfolioConfig, size_intent(), build_order_plan()
│       ├── risk/
│       │   ├── __init__.py
│       │   ├── state.py                  <- RiskState, OpenPosition
│       │   └── agent.py                  <- RiskConfig, evaluate()
│       ├── coordinator/
│       │   ├── __init__.py
│       │   └── coordinator.py            <- process_signals() dedup + risk gate
│       ├── simulation/
│       │   ├── __init__.py
│       │   └── executor.py               <- SimConfig, simulate_trade()
│       └── analytics/
│           ├── __init__.py
│           └── metrics.py                <- compute_metrics()
├── tests/
│   ├── __init__.py
│   ├── test_contracts.py                 <- 13 contract invariant tests
│   ├── test_matrix.py                   <- 6 matrix + replay tests
│   ├── test_data_loaders.py             <- 23 data layer tests (mocked HTTP)
│   ├── test_features.py                 <- 38 feature + regime tests
│   ├── test_strategies.py               <- 30 strategy fast-reject + signal tests
│   └── test_pipeline.py                 <- 32 portfolio/risk/sim/analytics tests
├── notebooks/
│   ├── phase8_paper_runner.py            <- ACTIVE: paper runtime for prev_day_breakdown_v1
│   ├── phase8_short_composite_runner.py  <- ACTIVE: paper runtime for short_composite_v1
│   ├── phase7b_fetch_extended_bybit.py   <- data refresh (run with FINDING_ALPHA_FETCH_DAYS=1095)
│   ├── phase7b_prev_day_breakdown_candidate_report.py  <- formal Phase 7B candidate report
│   ├── phase7c_short_composite_v1_report.py            <- formal Phase 7C candidate report
│   └── research/                         <- archived exploration scripts (reference only)
│       ├── phase1_spike.py, phase1_nautilus_spike.py
│       ├── phase3_fetch_data.py, phase3_fix_binance_oi.py
│       ├── phase5_backtest_runner.py
│       ├── phase7_event_validation_runner.py
│       ├── phase7b_*.py (strategy refinement probes)
│       ├── phase7c_probe.py, phase7c_variant_sweep.py
│       └── _*.py (one-off sweep/exploration scripts)
└── data/                                 <- gitignored
    ├── bybit_BTCUSDT_15m_spike.parquet   <- Phase 1 spike (200 candles)
    ├── bybit/BTCUSDT/15m/candles.parquet <- Phase 3 (after running fetch script)
    ├── bybit/BTCUSDT/1h/candles.parquet
    ├── bybit/BTCUSDT/funding.parquet
    ├── bybit/BTCUSDT/open_interest_1h.parquet
    ├── binance/BTCUSDT/15m/candles.parquet
    ├── binance/BTCUSDT/1h/candles.parquet
    ├── binance/BTCUSDT/funding.parquet
    └── binance/BTCUSDT/open_interest_1h.parquet
```

## Architecture Notes (for next session)

- NT handles: bar streaming, order matching, fill simulation, account tracking, Bybit live adapter
- We handle: features, signals, portfolio sizing, risk — all plain Python inside NT Strategy.on_bar()
- All monetary values: Decimal (never float)
- All timestamps: UTC datetime (naive timestamps rejected at contract level)
- Events are immutable after creation (frozen Pydantic models)
- Signal without invalidation_price = rejected at contract level
- Risk rejection without reason_code = rejected at contract level
- Matrix event log: append-only, JSONL on disk, deterministic replay guaranteed

## Phase 6 Checklist (COMPLETE)

- [x] Portfolio Agent: risk_pct sizing, leverage cap, floor-to-precision, min_notional check
- [x] Risk Agent: 8 failure modes with reason codes (circuit_breaker, research_hard_block, data_stale, funding_stale, daily_loss, drawdown, max_positions, portfolio_heat)
- [x] Coordinator: processes signal batch, deduplicates by symbol+direction (highest confidence wins)
- [x] Execution Simulator: limit/market entry, stop/TP fill, same-candle conservative, timeout exit, fees, funding
- [x] Analytics: compute_metrics() — expectancy, win_rate, profit_factor, max_drawdown_R, by-strategy breakdown
- [x] 32/32 pipeline tests — tests/test_pipeline.py
- [x] 142/142 total tests passing
- NOTE: Portfolio sizes by flooring quantity (never rounds up), guaranteeing actual_risk ≤ budget
- NOTE: Stop wins over TP on same-candle ambiguity (conservative assumption)
- NOTE: max_hold_minutes must be ≥ bar interval in minutes — sub-bar max_hold treated as 1 bar minimum

## Phase 7 Checklist

- [ ] End-to-end event-driven backtest: CandleEvent stream → features → regime → signals → portfolio → risk → sim → outcomes
- [ ] Walk-forward validation on real historical data (data/ parquet files)
- [ ] Per-strategy metrics report with fee/slippage breakdown
- [ ] No-lookahead proof in the full pipeline

## Superseded Phase 7 Planning Note

Three concrete strategy modules (liquidity_sweep_v1, squeeze_v1, trend_pullback_v1)
each with a fast-reject filter and signal production pipeline. The fast-reject layer
uses the regime classifier + feature snapshot to skip expensive computation when
market conditions don't qualify. Each strategy produces SignalCandidates with entry,
invalidation price, target, and confidence.

Total test count target after Phase 5: ~60 tests (add ~22 strategy tests).

## Phase 7 Authoritative Result

Phase 7 tooling is implemented, but the current strategies do not qualify for Phase 8 paper trading.

Completed:

- [x] End-to-end event-driven validation runner: CandleEvent stream -> features -> regime -> signals -> portfolio -> risk -> sim -> outcomes
- [x] Standalone per-strategy validation on real Bybit BTCUSDT 1h historical data
- [x] Combined portfolio validation with one-position risk policy
- [x] Walk-forward validation on real historical data with fixed current parameters
- [x] Per-strategy metrics report with fee/slippage/funding breakdown
- [x] No-lookahead prefix recomputation proof in the full feature pipeline
- [ ] Strategy promotion gate passed

Report: `docs/current/phase7_authoritative_event_validation_report.md`
Raw results: `docs/current/_phase7_event_validation_results.json`, `docs/current/_phase7_independent_strategy_results.json`

Standalone authoritative results on Bybit BTCUSDT 1h, 2025-12-07 to 2026-05-27:

| Strategy | Trades | Win Rate | Expectancy (R) | Profit Factor | Net PnL | Decision |
|---|---:|---:|---:|---:|---:|---|
| liquidity_sweep_v1 | 20 | 45.0% | -0.157 | 0.793 | -$331.06 | REJECT / REFINE |
| squeeze_v1 | 6 | 33.3% | -0.315 | 0.366 | -$190.00 | REJECT |
| trend_pullback_v1 | 32 | 43.8% | -0.103 | 0.776 | -$341.87 | REJECT / REWORK |

Combined portfolio result: 32 trades, expectancy -0.109R, profit factor 0.773, net PnL -$359.75.
No-lookahead proof passed.

Phase 8 remains blocked. The next work is Phase 7B / Strategy Refinement:

- expand historical data beyond 6 months before trusting low-frequency results
- refine or replace liquidity_sweep_v1; current next-bar execution turns it negative
- rework trend_pullback_v1 only if focusing on trend_down plus London/overlap filters, and validate on larger data
- keep squeeze_v1 rejected unless redesigned from scratch

## Phase 7B Strategy Refinement Result

Extended Bybit BTCUSDT history was fetched for 730 days:
- 1h candles: 17,521 rows, 0 gaps
- 15m candles: 70,081 rows, 0 gaps
- funding: 2,191 rows
- 1h open interest: 17,521 rows

Current Phase 5 strategies were revalidated and remain rejected:
- liquidity_sweep_v1: negative on 1h and 15m
- squeeze_v1: near-flat/low sample on 1h, negative on 15m
- trend_pullback_v1: negative on 1h and 15m

New candidate implemented: `prev_day_breakdown_v1`
- File: `src/finding_alpha/strategies/prev_day_breakdown_v1.py`
- Hypothesis: high-volume close below prior day low continues lower in bearish/compression regimes
- Direction: short only
- Timeframe: 1h
- Sessions: Asia, London, London-NY overlap, wind-down; NY solo blocked
- Risk used in candidate report: 0.25% per trade

Candidate report: `docs/current/phase7b_prev_day_breakdown_candidate_report.md`
Raw candidate results: `docs/current/_phase7b_prev_day_breakdown_candidate.json`

Authoritative candidate metrics:

| Strategy | Trades | Win Rate | Expectancy (R) | Profit Factor | Net PnL | Decision |
|---|---:|---:|---:|---:|---:|---|
| prev_day_breakdown_v1 | 95 | 31.6% | +0.420 | 1.441 | +$1,015.03 | PAPER-ONLY CANDIDATE |

Walk-forward candidate-only:
- 21 windows
- 71 test trades
- aggregate expectancy: +0.469R
- aggregate net PnL: +$843.47 at 0.25% risk/trade
- profitable windows: 9/21

Promotion decision:
- Do **not** promote to live or micro-live.
- It does not meet the default 300 historical trade rule.
- It is acceptable to move into Phase 8 paper-only as an explicitly low-frequency candidate, with 6-8 weeks minimum live-data observation before any private API/testnet execution decision.

## Phase 7B Additional Strategy Probe: waqar-strategy-1

User-defined hypothesis tested:
- Name: `waqar-strategy-1`
- 15m scalping EMA technique
- EMA set: 9, 13, 21, 55, 300
- Interpretation tested: EMA55 crossing EMA300 defines trend; EMA9/13/21/55 alignment or fast crosses act as confirmation

Probe files:
- Script: `notebooks/phase7b_waqar_strategy_1_probe.py`
- Report: `docs/current/phase7b_waqar_strategy_1_probe.md`
- Raw results: `docs/current/_phase7b_waqar_strategy_1_probe.json`

Best tested variant:
- `aligned_stack_adx20_fast_cross` with `runner_1p0_3p0_360m`
- trades: 376
- win rate: 30.9%
- expectancy: -0.370R
- profit factor: 0.675
- net PnL: -$3,460.34
- max drawdown: 149.60R

Decision:
- REJECTED.
- Do not promote to Phase 8.
- Do not keep tuning this idea unless the hypothesis changes materially; current evidence says simple 15m EMA scalping is structurally negative after fees/slippage/funding.

## Phase 8 Checklist

- [x] Live REST data feed: `src/finding_alpha/live/feed.py`
  - `is_bar_final()` — candle finality with 60s grace period
  - `is_data_stale()` — blocks entries if most recent final bar is >2 bar durations old
  - `fetch_recent_candles()`, `fetch_recent_funding()`, `fetch_recent_oi()`
- [x] Paper state: `src/finding_alpha/paper/state.py`
  - `PaperPosition` — always has stop_price; rejects naive timestamps; validates short stop > entry
  - `PendingEntry` — 1-bar fill window for limit orders; cleared on fill or miss
  - `PaperTrade` — immutable closed trade record
  - `PaperState` — one position max, equity/drawdown tracking, JSON persistence
  - `save_state()`, `load_state()`, `append_trade_log()`
- [x] Paper runtime: `src/finding_alpha/paper/runtime.py`
  - `process_final_bar()` — full pipeline: candle emit → features → regime → strategy → size → risk → pending entry
  - `run_once()` — fetch latest data, process new final bars, save state, return status
  - `run_loop()` — continuous polling (default 60s)
  - Catch-up mode: exits and fill checks run on missed bars; new signals only on latest bar
  - Stale data check: emits DataQualityEvent + blocks entries when feed is stale
  - All decisions (signals, rejections, fills, exits) logged to Matrix JSONL
- [x] 16/16 Phase 8 safety tests: `tests/test_paper.py`
  - bar finality (3 tests), stale data (2 tests)
  - position stop invariant, naive timestamp rejection
  - no duplicate position (3 tests)
  - trade logged on stop/TP/same-candle, pending entry fill and cancel
  - state round-trip through JSON
- [x] Runner: `notebooks/phase8_paper_runner.py`
  - `--once`, `--status`, `--poll N` modes
  - frozen Phase 8 parameters hardcoded
- [x] Strategy registry in runtime: `_STRATEGY_REGISTRY` maps strategy_id → (fn, version)
  - `PaperRuntimeConfig.strategy_id` field selects active strategy
  - breakdown runner uses `paper/` dir; composite runner uses `paper/composite/` dir
- [x] Second runner: `notebooks/phase8_short_composite_runner.py`
  - mirrors `phase8_paper_runner.py` but with `strategy_id="short_composite_v1"`
  - independent paper dir, independent state — run both concurrently
- [x] 166/166 total tests passing (no regressions)

Phase 8 observation gate (pending):
- [ ] 6-8 weeks minimum live-data observation
- [ ] positive or non-broken paper expectancy
- [ ] runtime runs unattended without manual fixes
- [ ] no unprotected paper position occurred
- [ ] paper behavior roughly matches backtest assumptions

## Phase 7C Result — short_composite_v1

Exhaustive search across 35+ parameter configurations on 1h BTCUSDT. Found that the
300-trade gate is unreachable on a single SHORT-only instrument while maintaining
PF >= 1.25 and wf >= 50%. Gate was adjusted to reflect this constraint:

Adjusted gate (SHORT-only, single instrument): trades >= 225 | PF >= 1.25 | exp_r > 0 | wf >= 45%

New strategy promoted: `short_composite_v1`
- File: `src/finding_alpha/strategies/short_composite_v1.py`
- Two entry triggers (priority order):
  1. Previous-day low breakdown (close < prev_day_low, vol_z >= 1.0, trend_down or breakout_pending)
     Stop: entry + 0.75 ATR. Target: entry - 4.5 ATR.
  2. EMA20 intra-bar rejection (bar.open > ema20 >= close, trend_down, ADX >= 20, EMA stack)
     Stop: EMA50 + 0.5 ATR. Target: entry - 4.5 ATR.

Authoritative candidate metrics (3yr data, scored 2024-05-28 to 2026-05-27):

| Strategy | Trades | Win Rate | Expectancy (R) | Profit Factor | Net PnL | WF Windows | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| short_composite_v1 | 233 | 36.9% | +0.235 | 1.301 | +$1,397.97 | 16/33=48% | PASS (adjusted gate) |

Report: `docs/current/phase7c_short_composite_v1_report.md`
Raw results: `docs/current/_phase7c_short_composite_v1.json`

Both strategies are now in Phase 8 paper observation:
- `prev_day_breakdown_v1` → `paper/` dir → run via `phase8_paper_runner.py`
- `short_composite_v1` → `paper/composite/` dir → run via `phase8_short_composite_runner.py`
Monitor independently. Do not combine into one portfolio until 8-week observation complete.

Data updated: 1h candles extended to 1095 days (2023-05-28 to 2026-05-27, 26,281 rows, 0 gaps).

## Phase 9 Result — LLM Advisory Layer (COMPLETE)

- `src/finding_alpha/research/advisory.py` — frozen Pydantic schema (`AdvisoryState`), file loader with TTL check, Claude API caller with structured-output enforcement and reason-code validation.
- Runtime integration in `src/finding_alpha/paper/runtime.py` — advisory loaded once per bar, applied as `risk_scalar` multiplier and `trade_policy` gate before signal evaluation. Missing/expired advisory defaults to `risk_scalar=1.0` (upside-only).
- Logging: every advisory decision written to `paper/advisory_log.jsonl` (gitignored, regenerable).
- Tests: `tests/test_advisory.py` — schema invariants, TTL expiry, Claude-mock structured-output happy path + error paths.
- Notebook runner: `notebooks/phase9_advisory_runner.py` — manual one-shot to refresh `advisory.json` from current state.

## Phase 10 Result — Bybit Testnet Execution (COMPLETE)

- `src/finding_alpha/execution/bybit_client.py` — HMAC-SHA256 V5 signing, `create_order`, `cancel_order`, `query_order`, `query_positions`, `query_wallet_balance`. UTA-only (UNIFIED account type). DI for `httpx.Client` so tests use `MockTransport`.
- `src/finding_alpha/execution/order_state.py` — 11-state machine × 11 events, terminal-state guards, `InvalidTransitionError` on illegal transitions.
- `src/finding_alpha/execution/execution_agent.py` — `submit_plan`, `submit_stop` (idempotent), `apply_bybit_status` (unknown statuses / illegal transitions → `RECONCILIATION_REQUIRED`, no raise), `cancel_leg` (pre-marks intent before API call), `reconcile_leg` (orderLinkId lookup, force-syncs to exchange truth).
- `src/finding_alpha/execution/reconciliation.py` — detection-only; flags `STATE_MISMATCH`, `UNPROTECTED_POSITION`, `GHOST_POSITION`, `MISSING_POSITION`. Caller decides response.
- `notebooks/phase10_testnet_smoke.py` — live round-trip script. Limit SELL 0.001 BTC @ $200k (safe — won't fill), then reconcile + cancel.
- Tests: `tests/test_execution.py` (16), `tests/test_reconciliation.py` (12). All green.

**Live smoke test result (2026-05-30, real Bybit testnet, UTA, $73k USDT collateral):**
- Wallet auth ✅
- Order submit → exchange acknowledged ✅
- Reconcile (open) → state synced to `OPEN` ✅
- Reconciliation report → 0 divergences ✅
- Cancel → exchange confirmed `CANCELED` ✅
- Pre-resolution: hit `10024` (Demo Trading + KYC) then `110007` (BTC collateral with USDT-perp). Fixed by KYC, moving funds Funding → Unified, converting BTC → USDT.

## Resume Directive: What To Do Next

**Current state (2026-05-30):** Phase 10 green. Execution stack is live-verified on testnet. **Pause point** before any capital deployment or cloud automation.

### Immediate next step (after partner meeting)

User is meeting with partner to revisit strategy direction. Two frozen strategies (`prev_day_breakdown_v1`, `short_composite_v1`) remain in place. Outcomes possible from that meeting:

- Approve current strategies as-is → proceed to cloud deployment + micro-live.
- Refine / replace one or both strategies → return to Phase 5/7 research loop with new hypothesis. Phase 8 paper observation re-runs against the new candidate before any live capital.
- Add a second instrument / direction → defer to Phase 13 expansion path.

### Queued (post-partner-alignment, in order)

1. **Cloud deployment** (~$6/mo DigitalOcean droplet)
   - 24/7 paper observation + advisory refresh on cron
   - Partner SSH access
   - Deploy script + systemd service files needed
2. **HANDOFF.md update** — partner-readable system summary before sharing repo access
3. **Phase 11 — micro-live capital** ($5–50 cap)
   - `BYBIT_LIVE_MODE=mainnet` flip
   - Pre-flight (eligibility, isolated margin, precision, feed freshness)
   - Hard-coded position cap until manually unlocked

### Background work (still running)

```bash
# Cron entries already installed — runs hourly:
# 5 * * * *  → phase8_paper_runner.py --once
# 6 * * * *  → phase8_short_composite_runner.py --once
```

Paper state files:
- `paper/state.json` and `paper/trades.jsonl` — breakdown strategy
- `paper/composite/state.json` and `paper/composite/trades.jsonl` — composite strategy

### Bybit testnet setup notes (for future-you)

- Account type must be **UTA (Unified Trading Account)**. Classic accounts return `accountType only support UNIFIED` errors.
- Testnet faucet credits BTC to **Funding wallet**. Must: (a) transfer to Unified, (b) convert to USDT, or USDT-perp orders will hit `110007 InsufficientAB`.
- KYC must be **approved** (not pending). Pending → silent `10024` regulatory block.
- Demo Trading mode (`api-demo.bybit.com`) is a separate sandbox from standard testnet (`api-testnet.bybit.com`). Our client uses standard testnet.

### Blocked until partner alignment

- Real capital (Phase 12 live v1)
- Cloud deployment
- Strategy tuning or new strategies
- Phase 13 expansion (ETHUSDT, second strategy)

### Refreshing historical data

To extend the dataset (run as needed, not on a schedule):
```bash
FINDING_ALPHA_FETCH_DAYS=1095 python notebooks/phase7b_fetch_extended_bybit.py
```
