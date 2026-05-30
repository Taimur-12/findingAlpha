# Finding Alpha Phased Build Plan

Last reviewed: 2026-05-29 (accelerated build path added)

This file converts `FINDING_ALPHA_SOURCE_OF_TRUTH.md` and `agentic_quant_trading_project_deep_dive.md` into phase-by-phase build instructions. It is not a calendar timeline. Use it to create a timeline only after the phase gates are understood.

The rule for every phase is simple:

```text
Do not move forward because code exists.
Move forward only when the exit gate is proven with evidence.
```

## 0. Build Doctrine

### 0.1 System Shape

Finding Alpha is built as a Python trading engine, not as a notebook project.

Use:

- Python package for production logic.
- Jupyter notebooks only for research, plots, data inspection, and experiment review.
- Parquet files for early historical datasets.
- In-process event bus for the first working system.
- Postgres later for durable decisions, orders, and trade logs.
- Redis later only when separate services need shared hot state.
- No Databricks in v1.

### 0.2 Non-Negotiable Constraints

- Hot path is deterministic.
- LLMs are cold-path research tools only.
- Backtest, paper, and live use the same contracts.
- Exchange is source of truth for live orders, fills, balances, and positions.
- Venue eligibility is checked before any live execution.
- Bybit is the first technical execution target only if the account/product/jurisdiction is allowed.
- MEXC is not first live execution venue.
- Binance and OKX are reference data venues first.
- No 5m live trading in v1.
- No DCA in v1.
- No RL in live.
- No ML optimizer changes live risk or parameters.
- No strategy moves forward without walk-forward, sensitivity, paper, and operational evidence.

### 0.3 High-Level Phase Flow

```text
Phase 0: Scope and venue eligibility gate
Phase 1: Architecture spike
Phase 2: Contracts and Matrix event log
Phase 3: Historical data foundation
Phase 4: Feature and regime engine
Phase 5: Strategy research and fast rejection
Phase 6: Portfolio, risk, and execution simulation
Phase 7: Authoritative event-driven validation
Phase 8: Live-data paper runtime
Phase 9: Research Agent shadow mode
Phase 10: Exchange private API and testnet execution
Phase 11: Micro-live trading
Phase 12: Live v1
Phase 13: Controlled expansion
Phase 14: Advanced research backlog
```

### 0.4 Accelerated Build Path (added 2026-05-29)

The original phase plan is a wall-clock-gated rollout: build phase N, observe for weeks, then build phase N+1. That cadence makes sense for an institutional team. For a solo build, it makes sense to **split each gate into two parts**:

1. **Code-correctness work** — anything that can be validated by historical replay, unit tests, or testnet round-trips. Build this immediately, in one pass.
2. **Wall-clock validation** — anything that physically requires real elapsed time (multi-week stability, real-money fill quality, funding accumulation). Run this in the background after the code is complete.

Under the accelerated path the **gates do not disappear** — they are reordered. No real capital is deployed until the original Phase 11/12 evidence has accumulated. What changes is that *the code for Phases 9–11 is written before the Phase 8 multi-week observation finishes*, validated by:

- Historical replay through the existing simulation runner (`notebooks/phase8_simulation_runner.py`)
- Bybit testnet (free API, real exchange behavior, no real capital)
- Unit and integration tests against fixed datasets

**What is built immediately (accelerated):**

- Phase 9 — LLM advisory layer, validated by replaying historical bars with advisories injected
- Phase 10 — Bybit private API + testnet integration, validated by end-to-end testnet round-trip
- Phase 11 — micro-live code path, env-flag gated, hard-capped position size; **no capital flows yet**

**What still requires wall-clock time (run in background, not blocking):**

- Phase 8 multi-week unattended paper observation (already running via cron)
- Phase 11 micro-live capital deployment — only after the rest of the accelerated build is reviewed and the original Phase 11 pre-flight checks pass
- Phase 12 live v1 — same gate as before, unchanged

**Doctrine for the accelerated path:**

- No new strategies during the build. Frozen: `prev_day_breakdown_v1`, `short_composite_v1`.
- No risk-policy changes during the build. The Risk Agent remains the final veto.
- LLM advisory is upside-only. Default `risk_scalar=1.0` when advisory missing. LLM cannot raise risk above strategy/portfolio config; it can only reduce or block.
- Bybit testnet keys are kept in `.env` (gitignored). Live keys are not added until micro-live capital deployment is explicitly approved.
- The original exit gates for Phase 11 and Phase 12 still apply. The accelerated path only changes *when the code is written*, not *when capital is risked*.

## Phase 0: Scope And Venue Eligibility Gate

### Objective

Freeze the first build target and prevent the project from drifting into a giant platform before the core engine is validated.

### Build Target

Version 1 trades:

- BTCUSDT first.
- ETHUSDT second only after BTC path works.
- 15m and 1h only.
- One strategy selected after validation.
- One position max in micro-live.
- Two positions max in live v1.
- Bybit linear USDT perpetuals only if venue eligibility passes.
- Binance USD-M and OKX public data for reference only.
- MEXC public data only, no first live execution.

### Required Work

1. Confirm venue/product eligibility.
   - Confirm whether the account jurisdiction is allowed to trade the exact derivative product.
   - Confirm whether API trading is allowed for that account type.
   - Confirm whether testnet/demo is available for the exact product type.
   - If the jurisdiction is prohibited, live execution on that venue is blocked.

2. Freeze v1 scope.
   - Symbols: BTCUSDT, then ETHUSDT.
   - Timeframes: 15m and 1h.
   - Strategies to research: liquidity sweep reversal, short/long squeeze, trend pullback.
   - Blocked: 5m scalping, DCA, multi-exchange execution, autonomous LLM trading, RL, market making.

3. Choose the first data priority.
   - Execution/reference venue: Bybit if eligible.
   - Reference venue 1: Binance USD-M futures.
   - Reference venue 2: OKX public derivatives data if accessible.
   - Optional reference: MEXC public contract data.

4. Define success evidence for the whole project.
   - Positive expectancy after fees, slippage, and funding.
   - Bounded drawdown.
   - Parameter robustness.
   - Paper-trading operational correctness.
   - Micro-live order safety.

### Deliverables

- `v1_scope_decision.md`
- `venue_eligibility_decision.md`
- `blocked_features.md`
- first venue/symbol/timeframe decision record

### Exit Gate

Move to Phase 1 only when:

- The first technical venue is identified.
- Jurisdiction/product eligibility is documented.
- The first symbol/timeframe set is frozen.
- The no-build-yet list is accepted.

### Do Not Move Forward If

- Live venue eligibility is unclear.
- You are still debating 5m scalping for v1.
- You want DCA in v1.
- You want multiple live venues before one venue works.

## Phase 1: Architecture Spike

### Objective

Answer the highest-risk architecture questions before building the full system:

- Can NautilusTrader be the authoritative event/live substrate?
- If not, what must the custom simulator support?
- Can Bybit order semantics be represented safely?
- Can historical data be imported cleanly?

### Required Work

1. NautilusTrader spike.
   - Install and run a minimal backtest or example.
   - Check whether Bybit integration supports the needed product category.
   - Check whether Binance/OKX data can be used as reference inputs.
   - Check whether custom risk checks can be inserted cleanly.
   - Check whether strategy boundaries can wrap Finding Alpha contracts.

2. Custom simulator feasibility spike.
   - Write a tiny event replay loop.
   - Replay one BTCUSDT 15m candle file.
   - Emit a dummy signal.
   - Produce a dummy portfolio intent.
   - Simulate one limit entry, one stop, one take profit.

3. Bybit API semantics spike.
   - Fetch instruments and precision.
   - Fetch BTCUSDT klines.
   - Subscribe to a public kline WebSocket.
   - Confirm candle finality field behavior.
   - In testnet/demo only, test:
     - limit order acknowledgement
     - market order behavior
     - post-only behavior
     - reduce-only behavior
     - stop order behavior
     - cancel behavior
     - partial-fill behavior if possible
     - order query and position query reconciliation

4. Historical data import spike.
   - Import a small BTCUSDT sample.
   - Save to Parquet.
   - Replay it deterministically.
   - Confirm timestamp, timezone, interval, and candle close conventions.

### Key Technical Checks

- Bybit order acknowledgement is not a fill.
- Market orders may execute with exchange-side slippage protections; do not assume full fill at last price.
- Post-only orders can cancel if they would cross the book.
- TP/SL behavior must be tested for the exact product category.
- Strategy code cannot depend on notebook state.

### Deliverables

- `architecture_spike_report.md`
- `nautilus_vs_custom_decision.md`
- `bybit_order_semantics_report.md`
- `historical_data_import_sample.parquet`
- minimal replay script or notebook used only for inspection

### Exit Gate

Move to Phase 2 only when:

- You have chosen NautilusTrader or a custom event simulator.
- You know how order acknowledgement, fills, stops, and reconciliation will be represented.
- You can replay one historical sample deterministically.
- You can fetch and normalize one live public data stream.

### Do Not Move Forward If

- The simulator decision is still vague.
- Stop-order behavior is not understood.
- Historical candle timestamps are not understood.
- You cannot reconcile testnet orders against exchange state.

## Phase 2: Canonical Contracts And Matrix

### Objective

Build the domain language of the system. Every later phase depends on these contracts.

### Required Work

1. Implement canonical event models.
   - `MarketEvent`
   - `CandleEvent`
   - `DataQualityEvent`
   - `FeatureSnapshot`
   - `RegimeState`
   - `SignalCandidate`
   - `ResearchState`
   - `PortfolioIntent`
   - `RiskDecision`
   - `OrderPlan`
   - `ExecutionReport`
   - `TradeOutcome`

2. Enforce precision rules.
   - Use `Decimal` for money, prices, quantities, fees, risk, and PnL.
   - Use UTC timestamps.
   - Store exchange timestamp and received timestamp where available.
   - Include venue, symbol, product type, and data source in every market event.

3. Build Matrix v1.
   - Append-only event log.
   - In-memory projections.
   - Deterministic replay.
   - Latest-state snapshot.
   - Versioned configs.

4. Build serialization.
   - JSON lines or Parquet for early event storage.
   - Schema version in every event.
   - Deserialization tests.

5. Define reason codes.
   - Risk rejections.
   - Data quality blocks.
   - Strategy rejects.
   - Execution errors.
   - Reconciliation states.

### Required Tests

- Serialize/deserialize every contract.
- Replay the same event log twice and get identical final Matrix state.
- Reject invalid events:
  - missing symbol
  - missing timestamp
  - non-final candle used for strategy
  - signal without invalidation price
  - portfolio intent without stop
  - risk decision without reason code when rejected

### Deliverables

- domain model package
- event log writer/reader
- Matrix projection module
- deterministic replay test
- reason-code registry

### Exit Gate

Move to Phase 3 only when:

- All core events exist and validate.
- Replay is deterministic.
- Every event has schema versioning.
- Invalid trading states are rejected at the contract layer.

### Do Not Move Forward If

- Any module passes arbitrary dictionaries instead of typed contracts.
- Money values use float.
- Events can be mutated after append.
- Strategy agents can read non-final candles.

## Phase 3: Historical Data Foundation

### Objective

Create the trusted historical data layer used by research and event-driven validation.

### Required Work

1. Build Bybit historical loader.
   - Instruments metadata.
   - 15m BTCUSDT candles.
   - 1h BTCUSDT candles.
   - Then ETHUSDT.
   - Funding history if available through API.
   - Open interest history if available through API.
   - Mark/index prices if needed.

2. Build Binance reference loader.
   - USD-M futures klines.
   - Funding history.
   - Open interest snapshots/history where available.
   - Mark/index price data where available.

3. Build optional OKX reference loader.
   - Public candles.
   - Funding.
   - Open interest.
   - Mark/index data.

4. Add data normalization.
   - Symbol normalization.
   - Venue normalization.
   - Timeframe normalization.
   - Timestamp alignment.
   - Candle close time convention.
   - Volume unit convention.

5. Add data quality reports.
   - Missing candles.
   - Duplicate candles.
   - Out-of-order timestamps.
   - Zero-volume anomalies.
   - Funding/OI gaps.
   - Venue mismatch checks.

6. Store early datasets.
   - Parquet by venue/symbol/timeframe/date range.
   - Metadata file describing collection time and API source.

### Required Checks

- Candle counts match expected interval counts after accounting for gaps.
- No duplicate `(venue, symbol, timeframe, open_time)` rows.
- Candle open/close convention is documented.
- Funding timestamps are aligned to actual funding times.
- OI values are not forward-filled silently.
- Data unavailable from one venue is marked missing, not guessed.

### Deliverables

- data loader modules
- Parquet historical datasets
- data quality reports
- source metadata
- replay-ready historical event stream

### Exit Gate

Move to Phase 4 only when:

- BTCUSDT 15m and 1h historical data replays cleanly.
- Binance reference data is available for the same periods or missingness is documented.
- Data quality report is acceptable.
- The Feature Agent can trust the candle finality and timestamp convention.

### Do Not Move Forward If

- There are unexplained historical gaps.
- Funding/OI data is stale or mixed with candle timestamps incorrectly.
- Venue symbols or contract types are ambiguous.
- You cannot reproduce the dataset from source metadata.

## Phase 4: Feature And Regime Engine

### Objective

Build deterministic, versioned features and market regime classification.

### Required Work

1. Implement indicator features.
   - RSI 6, 14, 24 using Wilder smoothing.
   - MACD 12/26/9 with histogram and histogram slope.
   - EMA 20, 50, 200 and EMA 200 slope.
   - Bollinger bands, percent B, bandwidth, bandwidth percentile.
   - ATR 14 and ATR percentile.
   - ADX 14.
   - Supertrend.
   - Session VWAP.

2. Implement order-flow and derivatives features.
   - Volume z-score.
   - Taker-buy imbalance where available.
   - CVD when trade aggressor side is available.
   - Funding rate and funding z-score.
   - OI delta and OI z-score.
   - Rolling and EWMA correlation to BTC.
   - Spread bps where bid/ask data exists.

3. Implement structure features.
   - Swing highs/lows.
   - Previous day high/low.
   - Previous week high/low.
   - Session high/low.
   - Support/resistance zones.
   - Equal highs/lows.
   - Sweep/reclaim markers.

4. Implement Regime Agent.
   - `trend_up`
   - `trend_down`
   - `range`
   - `breakout_pending`
   - `high_volatility`
   - `crisis` or `risk_blocked`

5. Version all feature logic.
   - `feature_version`
   - `regime_version`
   - formula notes
   - warmup periods

### Required Tests

- Indicator unit tests against known calculations.
- Warmup periods excluded.
- No feature uses future candle information.
- Feature snapshot generated only after final candle.
- Missing source data marks feature missing.
- Regime classification is deterministic for the same snapshot.

### Deliverables

- Feature Agent
- Regime Agent
- feature snapshot datasets
- feature validation report
- formula/version documentation

### Exit Gate

Move to Phase 5 only when:

- Features compute deterministically from historical replay.
- Critical indicators match expected formulas.
- Regime classification is stable and explainable.
- Feature missingness is explicit.
- No lookahead is found in feature generation.

### Do Not Move Forward If

- Indicators are copied from charts without formula ownership.
- Any strategy requires features that are not validated.
- Missing funding/OI is silently treated as neutral.
- Regime classification changes randomly between runs.

## Phase 5: Strategy Research And Fast Rejection

### Objective

Test strategy ideas separately and cheaply before building full execution realism around them.

### Strategy Modules

Research these separately:

1. Liquidity sweep reversal.
2. Short/long squeeze.
3. Trend pullback.

Do not combine them yet.

### Required Work

1. Define each strategy contract.
   - required features
   - entry condition
   - invalidation logic
   - target logic
   - allowed regimes
   - blocked regimes
   - max hold assumption
   - expected timeframe

2. Build vectorized or semi-vectorized research tests.
   - Use pandas/NumPy/Polars.
   - Use notebooks only for inspection and plots.
   - Strategy logic itself lives in Python modules.

3. Run fast parameter grids.
   - RSI thresholds.
   - ATR stop multipliers.
   - volume z-score thresholds.
   - funding z-score thresholds.
   - ADX thresholds.
   - sweep reclaim rules.
   - max hold times.
   - target R multiples.

4. Run first-pass cost model.
   - maker/taker fees.
   - conservative slippage.
   - funding cost.
   - missed limit fills.

5. Reject weak ideas early.
   - If edge only exists before fees, reject.
   - If edge only exists on one parameter spike, reject.
   - If edge only exists in one historical event, reject.
   - If trade count is too low for the intended frequency, reject or reclassify as low-frequency.

### Required Metrics

For each strategy separately:

- gross return
- net return
- expectancy
- average R
- median R
- win rate
- profit factor
- drawdown
- trade count
- fee share of gross profit
- slippage share of gross profit
- performance by session
- performance by regime
- performance by symbol
- parameter sensitivity

### Deliverables

- one research report per strategy
- parameter grid results
- first-pass sensitivity charts/tables
- rejected-strategy notes
- candidate-strategy shortlist

### Exit Gate

Move to Phase 6 only when:

- At least one strategy shows positive first-pass net expectancy.
- Strategy rules are explicit enough to convert into event-driven simulation.
- Parameter sensitivity shows a plausible plateau.
- No obvious lookahead exists.

### Do Not Move Forward If

- Strategies are still merged into one vague confidence score.
- A strategy has no explicit invalidation price.
- A strategy only works before transaction costs.
- A strategy cannot explain why it should work.

## Phase 6: Portfolio, Risk, And Execution Simulation

### Objective

Build the deterministic agents that turn signals into safe trade intents and simulated execution.

### Required Work

1. Build Portfolio Agent.
   - Calculate risk amount.
   - Calculate stop distance.
   - Calculate quantity.
   - Calculate notional.
   - Calculate leverage.
   - Round to venue precision.
   - Reject if minimum notional breaks risk.
   - Define max hold time.
   - Define target plan.

2. Build Risk Agent.
   - Data freshness checks.
   - Feature validity checks.
   - Daily loss stop.
   - Max drawdown stop.
   - Max open positions.
   - Portfolio heat.
   - Correlation exposure.
   - Spread cap.
   - Expected net R after fees/slippage/funding.
   - Event window block.
   - Structural crisis block.
   - Reason codes for all rejections.

3. Build Coordinator.
   - Batch simultaneous signals.
   - Select between correlated BTC/ETH signals.
   - Attach cached ResearchState.
   - Apply session thresholds.
   - Prevent multiple strategies from opening conflicting trades.

4. Build Execution Simulator.
   - Market order fills.
   - Limit order fills.
   - Post-only assumptions.
   - Stop order triggers.
   - Take-profit handling.
   - Partial fill handling.
   - Fees.
   - Funding.
   - Slippage.
   - Rejected order simulation.

5. Build Analytics Agent v1.
   - Closed trade log.
   - Open risk log.
   - Signal log.
   - No-trade/rejection log.
   - Strategy metrics.
   - Operational metrics.

### Required Failure Tests

- Signal without stop is rejected.
- Position size above risk is rejected.
- Rounded quantity does not exceed risk.
- Correlated same-direction BTC/ETH signal is blocked or reduced.
- Data stale blocks entry.
- Missing funding/OI blocks strategies that require it.
- Stop order simulation triggers correctly.
- Partial fills do not create incorrect PnL.
- Daily loss stop blocks new trades.
- Drawdown stop blocks new trades.
- No unprotected simulated position exists.

### Deliverables

- Portfolio Agent
- Risk Agent
- Coordinator
- Execution Simulator
- Analytics Agent v1
- failure-mode test suite

### Exit Gate

Move to Phase 7 only when:

- Signals can become intents, decisions, orders, fills, and outcomes through deterministic contracts.
- Risk Agent can reject and explain every blocked trade.
- Execution Simulator models fees, slippage, stops, partial fills, and funding.
- Failure tests pass.

### Do Not Move Forward If

- Risk checks are only after execution.
- Rejections do not have reason codes.
- Execution simulation assumes every limit touch fills.
- Funding is ignored for held perp positions.
- Partial fills break state.

## Phase 7: Authoritative Event-Driven Validation

### Objective

Validate candidate strategies using the same event-driven contracts that paper/live will use.

### Required Work

1. Convert candidate strategies from Phase 5 into event-driven strategy agents.

2. Run event-driven backtests.
   - BTCUSDT 15m.
   - BTCUSDT 1h.
   - ETHUSDT only after BTC works.
   - By session.
   - By regime.
   - By market period.

3. Run walk-forward validation.
   - Train: 90 days.
   - Validate: 30 days.
   - Test: 30 days.
   - Roll forward: 30 days.
   - Freeze parameters before test window.

4. Run parameter sensitivity.
   - Ensure plateau, not spike.
   - Check chosen parameters are not at grid edges.
   - Check trade count.

5. Run stress tests.
   - Higher slippage.
   - Higher taker fee.
   - Missed limit fills.
   - Wider spread.
   - Stale reference data.
   - Sudden volatility shock.
   - Correlated asset move.

6. Run ablation tests.
   - Without funding.
   - Without OI.
   - Without CVD/taker imbalance.
   - Without regime filter.
   - Without session filter.
   - Without ResearchState.

### Required Promotion Metrics

For a strategy to move to paper:

- Out-of-sample profit factor >= 1.25.
- Positive expectancy after fees, slippage, and funding.
- Drawdown within planned limits.
- At least 300 historical qualifying trades, unless explicitly marked low-frequency.
- Parameter plateau confirmed.
- No major lookahead violations.
- No single month or event accounts for most returns.
- Operational simulator passes stop, partial-fill, and circuit-breaker tests.

### Deliverables

- authoritative backtest report
- walk-forward report
- parameter sensitivity report
- stress test report
- ablation report
- strategy promotion decision

### Exit Gate

Move to Phase 8 only when:

- Exactly one strategy is selected for first paper trading.
- The selected strategy passes all promotion metrics.
- The strategy has a fixed version and fixed parameters.
- The paper-trading risk policy is defined.

### Do Not Move Forward If

- You want to paper trade multiple unvalidated strategies at once.
- Strategy parameters are still changing daily.
- Backtest fill assumptions are optimistic.
- Results are not broken down by session and regime.

## Phase 8: Live-Data Paper Runtime

### Objective

Run the selected strategy against live market data without capital and prove the system behaves correctly in real time.

### Required Work

1. Build live public data runtime.
   - Bybit live stream if eligible/available.
   - Binance reference stream.
   - Optional OKX reference stream.
   - Stale data detection.
   - Reconnect logic.
   - REST backfill after reconnect.

2. Run deterministic feature engine live.
   - Generate final-candle snapshots.
   - Generate regime states.
   - Validate feature timestamps.

3. Run selected strategy live.
   - Emit paper `SignalCandidate`.
   - Coordinator arbitrates.
   - Portfolio Agent sizes.
   - Risk Agent approves/rejects.
   - Execution Simulator creates paper fills.

4. Record everything.
   - Market events.
   - Feature snapshots.
   - Signals.
   - Rejections.
   - Paper orders.
   - Paper fills.
   - Paper trade outcomes.
   - Operational incidents.

5. Build basic monitoring.
   - Current runtime status.
   - Last market event time.
   - Data stale flags.
   - Current open paper position.
   - Paper PnL.
   - Last risk rejection.
   - Last error.

No full dashboard is required yet. A CLI report or simple local report is enough.

### Required Paper Checks

- No non-final candle signals.
- No duplicate signal execution.
- No unprotected paper position.
- No state drift after reconnect.
- Stale data blocks entries.
- Reference venue missingness is handled.
- Risk Agent blocks as expected.
- Paper fills are not more optimistic than backtest model.

### Deliverables

- live paper runtime
- paper trade log
- operational incident log
- paper performance report
- fill-assumption comparison report

### Exit Gate

Move to Phase 9 and Phase 10 only when:

- Paper runtime is stable.
- Selected strategy has positive paper expectancy or enough evidence to continue.
- No unresolved state bugs exist.
- No unprotected paper position occurred.
- Data reconnects are handled safely.

### Do Not Move Forward If

- The system cannot run unattended in paper mode.
- Reconnect breaks state.
- You need manual fixes to keep paper trading running.
- Paper trades are not reproducible from logs.

## Phase 9: Research Agent Shadow Mode

### Objective

Build the LLM Research Agent without allowing it to control live trading.

### Required Work

1. Build news/macro ingestion.
   - Crypto news feeds.
   - Exchange status notices.
   - Macro calendar events.
   - Official regulatory/exchange sources where available.

2. Build ResearchState output.
   - `as_of`
   - `expires_at`
   - assets
   - event type
   - severity
   - directional bias
   - confidence multiplier
   - trade policy
   - reason codes
   - sources
   - model and prompt version

3. Add deterministic validator.
   - Reject malformed output.
   - Reject stale output.
   - Clamp multiplier.
   - Require sources.
   - Apply hard-block keyword rules for structural exchange/stablecoin risk.

4. Run in shadow mode.
   - Attach ResearchState to every paper signal.
   - Record what it would have done.
   - Do not let it alter paper or live decisions yet.

5. Evaluate value.
   - blocked-trade expectancy
   - boosted-trade expectancy
   - false-block rate
   - missed-crisis rate
   - stale-news incidents
   - source-quality issues

### Deliverables

- Research Agent
- ResearchState validator
- shadow-mode dataset
- Research Agent evaluation report

### Exit Gate

Research Agent may influence paper decisions only when:

- It improves drawdown or expectancy in shadow mode.
- It does not overblock profitable trades.
- It has low stale-news failure rate.
- It is source-linked and reproducible.

Research Agent may influence live decisions only after:

- It has already proven value in paper.
- Risk Agent still has final veto.
- It can only raise thresholds, reduce size, or block new entries.

### Do Not Move Forward If

- LLM output is free-form prose.
- Source links are missing.
- The LLM suggests trade sizes or orders.
- Research Agent changes live config.
- Shadow-mode evidence is not measured.

## Phase 10: Private API And Testnet Execution

### Objective

Prove private exchange execution mechanics before risking capital.

### Required Work

1. Build Execution Agent against testnet/demo.
   - Submit limit orders.
   - Submit market orders.
   - Submit reduce-only orders.
   - Submit stop orders.
   - Cancel orders.
   - Query orders.
   - Query positions.
   - Query balances.
   - Reconcile local and exchange state.

2. Implement idempotency.
   - Deterministic client order IDs.
   - Retry logic checks existing order before re-submit.
   - Duplicate submit prevention.

3. Implement order state machine.
   - planned
   - submitted
   - acknowledged
   - open
   - partially_filled
   - filled
   - cancel_requested
   - canceled
   - rejected
   - expired
   - reconciliation_required

4. Implement protective stop workflow.
   - Entry plan includes stop before submission.
   - Stop is placed according to tested venue mechanics.
   - If stop cannot be confirmed, emergency policy triggers.

5. Test failure cases.
   - API timeout after submit.
   - Duplicate order retry.
   - Stop rejection.
   - Partial fill.
   - Cancel failure.
   - WebSocket disconnect after fill.
   - REST query failure.
   - Local/exchange mismatch.

### Deliverables

- private Bybit adapter in testnet/demo
- order state machine
- reconciliation loop
- execution failure test report
- emergency policy report

### Exit Gate

Move to Phase 11 only when:

- Testnet/demo execution is stable.
- Stop behavior is understood.
- Reconciliation works.
- Duplicate orders are prevented.
- Failure cases have deterministic handling.
- Venue eligibility for live product is confirmed.

### Do Not Move Forward If

- You cannot prove stop placement.
- Order acknowledgement is treated as fill.
- Duplicate retry can create duplicate exposure.
- Local state can disagree with exchange state without halting.

## Phase 11: Micro-Live Trading

### Objective

Validate real exchange behavior with tiny capital and minimal system complexity.

### Rules

- One venue.
- One symbol.
- One strategy.
- One position max.
- 15m or 1h only.
- No DCA.
- No 5m.
- Research Agent cannot control live unless separately approved.
- Risk per trade: 0.10 to 0.25 percent.
- Daily loss stop: 0.75 to 1.00 percent.
- Halt on unresolved reconciliation mismatch.

### Required Work

1. Run live pre-flight check.
   - venue eligibility confirmed
   - account mode confirmed
   - isolated margin confirmed
   - product category confirmed
   - precision metadata loaded
   - data feeds fresh
   - reference data fresh
   - Risk Agent active
   - emergency halt available

2. Execute only approved live trades.
   - SignalCandidate.
   - PortfolioIntent.
   - RiskDecision approve.
   - OrderPlan.
   - ExecutionReport.
   - Stop confirmation.
   - Reconciliation.

3. Compare live vs expected.
   - expected entry price vs actual fill
   - expected fee vs actual fee
   - expected slippage vs actual slippage
   - stop placement latency
   - missed fill rate
   - cancel latency
   - data latency

4. Record live incidents.
   - rejected orders
   - precision errors
   - delayed stops
   - reconnects
   - reconciliation drift
   - manual interventions

### Deliverables

- micro-live trade log
- live execution quality report
- live slippage report
- live reconciliation report
- incident review

### Exit Gate

Move to Phase 12 only when:

- At least 50 micro-live trades are completed, or a lower-frequency strategy has a documented equivalent observation period.
- No order precision errors remain.
- No stop placement failures occurred.
- No unresolved reconciliation mismatch occurred.
- Live slippage fits paper/backtest assumptions.
- No daily loss stop breach occurred from software fault.
- No manual emergency was caused by preventable software error.

### Do Not Move Forward If

- Any position was unprotected.
- Stop behavior surprised you.
- Live fills are materially worse than backtest/paper assumptions.
- You manually rescued trades because the system state was wrong.

## Phase 11.5: Data Infrastructure Upgrade

### Objective

Replace the current JSONL + Parquet sprawl with a single queryable analytical store so that every type of data the system touches can be inspected, joined, and reasoned about with SQL. This is the project's "Palantir-equivalent step" at retail scale — without buying Palantir.

### Why now

Phase 8 paper observation and Phase 11 micro-live both produce structured event logs. By the time micro-live has ~50 trades, JSONL scans become painful for analytical questions like "win rate by regime by month by funding bucket." DuckDB on top of Parquet solves this without ops cost.

### Required Work

1. Migrate live event log to a structured store.
   - Continue writing JSONL append-only for hot-path determinism.
   - Add a periodic compaction job that rolls JSONL into Parquet per day/strategy.
   - Expose all Parquet files as DuckDB views.

2. Build the eight-table analytical schema.
   - `trades` — every closed trade across backtest + paper + live + walk-forward, enriched with regime, microstructure z-scores, news tags, macro tags at entry, outcome R, exit reason, fee, slippage, funding cost.
   - `advisories` — every LLM advisory ever generated, with prompt_version, model_id, raw response, downstream gate decisions.
   - `matrix_events` — full compacted event log, queryable by event type and time.
   - `walk_forward` — every window result from every backtest grid.
   - `snapshots` — hourly market snapshot (regime, full feature set, microstructure z-scores) even when no trade fires.
   - `counterfactuals` — every gated signal: what was the signal, what would have happened if it executed.
   - `slippage` — per-order: expected fill vs actual fill, latency, fee, slippage in bps.
   - `versions` — model and prompt version registry with hashes.

3. Add counterfactual logging at every gate.
   - Risk Agent rejection → log signal + would-have-happened path.
   - LLM advisory block → log signal + would-have-happened path.
   - Regime filter rejection → log signal + would-have-happened path.

4. Add SQL views and analytical notebooks.
   - View: `v_trade_performance_by_regime`
   - View: `v_strategy_decay` (rolling expectancy with anomaly flags)
   - View: `v_advisory_value` (advisory blocks correlated with would-have-been outcomes)
   - Notebook: `notebooks/research/duckdb_workbench.ipynb` for ad-hoc queries.

### Deliverables

- `data/duckdb/analytics.db` — single source of truth for analysis
- Compaction job (cron, daily)
- Counterfactual logging wired into all three gates
- Eight Parquet tables + their DuckDB view definitions
- Research workbench notebook

### Exit Gate

Move to Phase 12.5 only when:

- All historical paper trades are queryable in DuckDB.
- Counterfactual log has at least 4 weeks of accumulated gate decisions.
- At least three analytical questions can be answered via SQL in under 30 seconds each.

### Do Not Move Forward If

- The compaction job loses or duplicates events.
- DuckDB views diverge from the underlying JSONL.
- Counterfactual log cannot be replayed deterministically.

## Phase 12: Live v1

### Objective

Run controlled production trading with the smallest validated scope.

### Allowed

- One validated strategy.
- BTCUSDT first.
- ETHUSDT only after correlation/risk policy is proven.
- 15m and 1h only.
- Risk per trade around 0.25 percent.
- Daily loss stop around 1.5 percent.
- Two positions max only after one-position live is stable.
- Research Agent may only reduce risk/block entries if separately validated.

### Still Blocked

- 5m live scalping.
- DCA.
- Multi-exchange execution.
- Autonomous ML parameter changes.
- RL.
- Market making.
- Arbitrage.
- Unvalidated strategies.

### Required Work

1. Run daily operational review.
   - data incidents
   - order incidents
   - risk decisions
   - open positions
   - PnL
   - drawdown
   - rejected trades
   - state reconciliation

2. Run weekly strategy review.
   - expectancy
   - profit factor
   - drawdown
   - MFE/MAE
   - slippage
   - fee share
   - performance by session
   - performance by regime
   - comparison to backtest/paper

3. Freeze production parameters.
   - No live parameter changes without a new backtest and paper validation.

4. Maintain incident rules.
   - Any unresolved reconciliation error halts new entries.
   - Any stop failure halts live trading.
   - Any venue/product eligibility concern halts live trading.
   - Any strategy decay alert pauses scale-up.

### Deliverables

- live v1 operating report
- weekly strategy health reports
- production parameter register
- incident log
- scale decision notes

### Exit Gate

Move to Phase 13 only when:

- Live v1 has positive expectancy over a meaningful sample.
- Operational incidents are rare and handled automatically.
- Live slippage remains within assumptions.
- Drawdown remains within risk policy.
- Strategy behavior matches backtest/paper expectations.

### Do Not Move Forward If

- Profit comes from one lucky outlier.
- Strategy quality differs sharply from paper.
- You are tempted to increase risk to recover losses.
- Operational incidents are still common.

## Phase 12.5: Cold-Path ML

### Objective

Add ML where it earns its place — research, analysis, decision support — without putting it in the hot path. Hot path stays fully deterministic.

### Why now

By Phase 12 there should be 100+ live trades and 1000+ paper trades enriched in DuckDB. That's the minimum sample to start training useful supervised models on trade outcomes.

### Required Work

1. Train trade outcome classifier.
   - Input: feature snapshot at entry.
   - Output: predicted R-multiple distribution.
   - Model: LightGBM or XGBoost (not neural nets — sample too small).
   - Use: flag signals firing in rare feature configurations for manual review. Does not block.

2. Build strategy decay detector.
   - Rolling expectancy time-series with anomaly detection.
   - Triggers manual review when expectancy drifts beyond historical band.
   - Does not auto-pause strategies; alerts only.

3. Build ML regime classifier as a second opinion.
   - Compare its output to the rules-based classifier each bar.
   - Disagreements logged for review.
   - The rules-based classifier remains authoritative for the hot path.

4. Add SHAP-based feature importance reports.
   - Monthly report on which features predict trade outcomes.
   - Guides where to look for new strategies (Phase 13+).

### Hot-path constraints

- ML output NEVER directly drives a trade decision.
- ML output NEVER overrides the Risk Agent.
- ML output NEVER changes stop or target placement.
- All hot-path logic stays in `src/finding_alpha/strategies/` and `src/finding_alpha/risk/`.

### Deliverables

- `src/finding_alpha/ml/outcome_classifier.py`
- `src/finding_alpha/ml/decay_detector.py`
- `src/finding_alpha/ml/regime_ml.py`
- Monthly feature importance report (auto-generated)
- Validation: hot-path tests pass unchanged; ML modules have their own test suite.

### Exit Gate

Move to Phase 13 only when:

- All ML modules have ≥80% test coverage.
- Outcome classifier has out-of-sample R² > 0 on held-out trades.
- ML output appears in research notebooks but never in live decisions.

### Do Not Move Forward If

- Any ML output influences a hot-path decision.
- Model retraining is not reproducible.
- Out-of-sample performance is worse than the deterministic baseline.

## Phase 13: Controlled Expansion

### Objective

Expand only after the core system proves it can survive real trading.

### Expansion Order

1. Add ETHUSDT.
   - Re-run backtest.
   - Re-run paper.
   - Test correlation rules.
   - Micro-live separately.

2. Add second validated strategy.
   - Must pass all research, event-driven, paper, and micro-live gates.
   - Must not conflict with existing strategy.
   - Coordinator must arbitrate between strategies.

3. Add better storage.
   - Postgres for durable decisions, orders, trades, configs.
   - Redis only if live services are split.
   - TimescaleDB/ClickHouse only if market data volume justifies it.

4. Add simple dashboard.
   - current state
   - open risk
   - PnL
   - last decisions
   - data health
   - order health
   - risk state

5. Consider Research Agent active risk modifier.
   - Only after shadow/paper evidence.
   - Only risk-reducing actions first.

6. Consider 5m paper research.
   - Only after live fill/slippage data is strong.
   - Requires tick/order-book data.
   - Requires realistic queue/slippage model.
   - Requires separate paper and micro-live gates.

### Deliverables

- expansion proposal
- backtest/paper/micro-live evidence for each expansion
- updated risk policy
- updated Coordinator rules
- dashboard if justified

### Exit Gate

Move beyond Phase 13 only when:

- Expanded system improves robustness or capacity without breaking risk discipline.
- Each added symbol/strategy has independent evidence.
- Complexity does not reduce observability.

### Do Not Move Forward If

- Expansion is motivated by boredom or impatience.
- You have not saturated the current validated setup.
- New features make failures harder to diagnose.

## Phase 13.5: Cold-Path LLM Agents

### Objective

Expand the LLM beyond the daily risk advisor (Phase 9) into a multi-agent research assistant. All agents are cold-path. None can place orders, change parameters, or override risk.

### Why now

By Phase 13 there is enough live data and enough strategy/instrument breadth that periodic LLM analysis can identify patterns a human reviewer would miss in raw logs. The daily advisor (Phase 9) has been running long enough to know its quirks.

### Required Work

1. Trade post-mortem agent.
   - Cadence: weekly.
   - Input: last 7 days of trades + matrix events + advisory log.
   - Output: structured analysis JSON — what worked, what didn't, any patterns flagged for review.
   - Writes to `data/memory/post_mortem/YYYY-MM-DD.json`.

2. Strategy hypothesis agent.
   - Cadence: quarterly.
   - Input: enriched trade ledger + feature snapshots + walk-forward results.
   - Output: list of feature combinations the LLM thinks may have predictive power.
   - Human reviews; promising hypotheses go through full deterministic backtest validation.

3. Document tagger.
   - Cadence: on news feed item arrival.
   - Input: news article URL or exchange announcement.
   - Output: structured tag (category, severity, affected instruments, time window).
   - Powers Phase 11+ news integration described in `phase9_llm_advisory_final_vision.md`.

4. Wire agents into the audit log.
   - Every agent run logs prompt, model_id, input hash, output, latency, cost.
   - Reviewable in DuckDB via the `advisories` table extended with `agent_type`.

### Hot-path constraints

- No LLM agent has order-placement authority.
- No LLM agent can change strategy parameters.
- No LLM agent can override Risk Agent.
- All agent outputs are written to disk; the hot path reads only the daily advisor's JSON (still bounded).

### Deliverables

- `src/finding_alpha/research/post_mortem.py`
- `src/finding_alpha/research/hypothesis.py`
- `src/finding_alpha/research/document_tagger.py`
- Weekly post-mortem report
- Quarterly hypothesis report
- News tag archive populated from real feed

### Exit Gate

Move to Phase 14 only when:

- All agents have been running for at least one full quarter.
- At least one strategy hypothesis has been validated through deterministic backtest.
- Cost per agent run is bounded and documented.

### Do Not Move Forward If

- Any agent has been given execution authority.
- Agent outputs are unreviewed.
- Cost grows unbounded.

## Phase 14: Advanced Research Backlog

### Objective

Keep advanced ideas out of v1 while preserving a path to evaluate them later.

### Allowed Only After Live v1 Stability

1. 5m scalping.
   - Requires tick/order-book data.
   - Requires measured live slippage.
   - Requires strict fee edge.
   - Requires separate event simulation and paper gate.

2. DCA.
   - Requires explicit total-risk cap across all layers.
   - Requires layer-by-layer independent signal validation.
   - Requires tail-risk stress testing.
   - Should not be enabled until the single-entry system is mature.

3. Multi-exchange execution.
   - Requires each venue to pass private API tests.
   - Requires venue eligibility.
   - Requires per-venue precision/order semantics.
   - Requires cross-venue position reconciliation.

4. ML ranking model.
   - Use only after large signal/trade dataset.
   - Train offline.
   - Validate out-of-sample.
   - Shadow mode before influence.
   - Advisory only at first.

5. Research Lab Agent.
   - Can propose experiments.
   - Cannot change live parameters.
   - Cannot trade.

6. On-chain and social signals.
   - Use as context first.
   - Require timestamped availability.
   - Require evidence that they improve outcomes.

7. Market making or arbitrage.
   - Treat as separate business lines.
   - Do not bolt onto the directional strategy engine casually.

### Exit Gate

An advanced feature moves into the main build only when:

- It has a hypothesis.
- It has historical data.
- It has a deterministic contract.
- It can be backtested without lookahead.
- It passes paper.
- It does not weaken risk controls.

## Final Phase Checklist

Use this before declaring any phase complete:

- Are all deliverables present?
- Are all tests passing?
- Is there written evidence for the exit gate?
- Are unresolved risks documented?
- Did anything violate the source-of-truth constraints?
- Can the phase output be reproduced from logs/data?
- Did this phase add only the complexity required for the next phase?
- Is the next phase blocked by any unclear assumption?

If any answer is weak, do not advance.

## Source Links Checked

- [NautilusTrader documentation](https://nautilustrader.io/docs/latest/)
- [NautilusTrader integrations](https://nautilustrader.io/docs/nightly/integrations/)
- [Bybit V5 create order](https://bybit-exchange.github.io/docs/v5/order/create-order)
- [Bybit V5 REST kline](https://bybit-exchange.github.io/docs/v5/market/kline)
- [Bybit V5 WebSocket kline](https://bybit-exchange.github.io/docs/v5/websocket/public/kline)
- [Bybit service restricted countries](https://www.bybit.com/en/help-center/article/Service-Restricted-Countries?category=8c8de4a417efb42713)
- [Binance USD-M futures klines](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data)
- [Binance USD-M futures open interest](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest)
- [Binance USD-M futures funding history](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)
- [Binance USD-M futures kline WebSocket](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Kline-Candlestick-Streams)
- [OKX API v5 documentation](https://www.okx.com/docs-v5/en)
- [OKX US risk and compliance disclosures](https://www.okx.com/en-us/help/us-risk-and-compliance-disclosures)
- [MEXC contract API](https://mexcdevelop.github.io/apidocs/contract_v1_en/)
- [MEXC restricted countries notice](https://www.mexc.com/learn/article/mexc-restricted-countries-complete-list-of-prohibited-limited-regions/1?handleDefaultLocale=keep)
- [Freqtrade documentation](https://www.freqtrade.io/en/stable/)
- [FreqAI documentation](https://www.freqtrade.io/en/stable/freqai/)
