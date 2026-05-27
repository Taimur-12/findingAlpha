# Finding Alpha — Project State

Last updated: 2026-05-27

## Current Phase: Phase 7 — Authoritative Event-Driven Validation

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
| 7 | Authoritative Event-Driven Validation | IN PROGRESS |
| 8 | Live-Data Paper Runtime | BLOCKED |
| 9 | Research Agent Shadow Mode | BLOCKED |
| 10 | Private API + Testnet Execution | BLOCKED |
| 11 | Micro-Live Trading | BLOCKED |
| 12 | Live v1 | BLOCKED |
| 13 | Controlled Expansion | BLOCKED |
| 14 | Advanced Research Backlog | BLOCKED |

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
│   ├── phase1_spike.py                   <- Bybit data + NT import check
│   ├── phase1_nautilus_spike.py          <- NT backtest engine spike
│   ├── phase3_fetch_data.py             <- downloads 6-month dataset to data/
│   └── phase5_backtest_runner.py        <- bar-by-bar backtest, all 3 strategies, RSI grid
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

## What Phase 7 Will Build

Three concrete strategy modules (liquidity_sweep_v1, squeeze_v1, trend_pullback_v1)
each with a fast-reject filter and signal production pipeline. The fast-reject layer
uses the regime classifier + feature snapshot to skip expensive computation when
market conditions don't qualify. Each strategy produces SignalCandidates with entry,
invalidation price, target, and confidence.

Total test count target after Phase 5: ~60 tests (add ~22 strategy tests).
