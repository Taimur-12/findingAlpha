# Finding Alpha Source Of Truth

Last reviewed: 2026-05-10

This is the build plan to follow. It replaces the earlier loose "AI quant firm" framing with a deterministic trading system that has narrow, controlled LLM modules. The goal is not to make the system sound intelligent. The goal is to make every trade reproducible, auditable, risk-limited, and testable in backtest, paper, and live modes.

No trading system can be 100 percent foolproof. The architecture below is designed so a wrong signal, failed API call, stale data feed, bad LLM output, or software crash cannot silently turn into uncontrolled risk.

## 1. Critical Audit Of The Previous Deep Dive

The file `agentic_quant_trading_project_deep_dive.md` had the right direction, but it was not strict enough to build from directly.

### 1.1 Problems To Fix

1. It reviewed too many projects without forcing a final build path.
   - Good research documents compare options.
   - Build documents must choose.

2. It treated "NautilusTrader vs custom simulator" as open-ended.
   - This is too important to leave vague.
   - The plan below makes this a short architecture spike with hard decision criteria.

3. It still allowed too much infrastructure too early.
   - Redis Streams, TimescaleDB, ClickHouse, Postgres, ChromaDB, FastAPI, Next.js, and multiple engines are too much for the first working system.
   - The first version should be a deterministic Python package with an event log, an in-process event bus, and one authoritative simulator.

4. It did not sharply enough separate research tools from trading runtime.
   - Qlib, RD-Agent, FinRL, TradingAgents, FinGPT, and FinRobot are research or analysis references.
   - They should not be in the hot execution path.

5. It was not strict enough about MEXC.
   - Current MEXC contract docs are useful for market data, but order endpoint reliability and account/API eligibility must be verified before live execution.
   - MEXC must not be the first live venue.

6. It did not clearly state that Bybit should be the first technical execution venue after jurisdiction eligibility passes.
   - Bybit V5 docs, testnet/demo support, and better ecosystem support make it the safer first technical target.
   - Binance and OKX should be data-confirmation venues first.

7. It did not fully define the "Matrix."
   - Matrix is not a magic ontology.
   - Matrix means append-only event log plus deterministic state projections.

8. It allowed 5-minute scalping too early.
   - 5m signals are dominated by fees, spread, queue position, latency, and false fill assumptions.
   - 5m is locked until paper trading proves fill quality.

9. It did not reject DCA strongly enough.
   - DCA increases tail risk and makes risk accounting harder.
   - No DCA in v1 live.

10. It did not make LLM backtesting reproducible enough.
   - Historical LLM classifications can leak future knowledge.
   - Any LLM result used in backtests must be timestamped, cached, source-linked, and frozen.

11. It did not fully specify exchange order-state safety.
   - Bybit order acknowledgement is not a fill.
   - Live state must come from execution reports, order queries, and position reconciliation.
   - The exchange is source of truth.

12. It did not define promotion gates tightly enough.
   - A strategy should not move from research to paper or from paper to live because it "looks good."
   - It must pass sample size, slippage, drawdown, and robustness gates.

13. It did not prevent strategy mixing.
   - Liquidity sweeps, short squeezes, trend pullbacks, and RSI mean reversion are different strategies.
   - They must be tested separately before any combined portfolio logic.

14. It mentioned daily return targets too casually.
   - Daily target is not an edge.
   - The real requirements are positive expectancy, bounded drawdown, robust parameters, and operational correctness.

15. It underweighted operational failure modes.
   - Feed stale, exchange rejects, stop not confirmed, reconciliation mismatch, DB unavailable, LLM stale, duplicate order, and partial fill all need explicit policies.

## 2. Final Architecture Doctrine

### 2.1 Non-Negotiable Decisions

1. The hot path is deterministic.
   - Data, features, signals, sizing, risk, order creation, reconciliation, and exits are deterministic code.

2. LLMs are not traders.
   - They classify news, macro context, event risk, and post-trade explanations.
   - They do not size, place, cancel, amend, or approve orders.

3. Backtesting is a runtime mode, not a separate tool.
   - The same contracts run in research, event backtest, paper, and live.

4. The exchange is source of truth.
   - Local state is a projection.
   - Orders, fills, balances, and positions must reconcile with the exchange.

5. Venue eligibility is a hard gate before live trading.
   - Bybit linear USDT perpetuals are the first technical execution target only if your account jurisdiction is allowed to use them.
   - If you are in an excluded jurisdiction, live derivatives trading on that venue is blocked regardless of technical readiness.
   - MEXC is data/reference only until proven safe for private trading and jurisdictionally allowed.
   - Binance and OKX are reference data venues first.

6. No 5m live trading until 15m/1h paper trading proves execution quality.

7. No DCA in live v1.
   - One entry, one protective stop, defined targets, defined max hold.

8. No RL in live.
   - Reinforcement learning may be explored later for offline allocation experiments only.

9. No ML optimizer controls production risk.
   - Any ML model is advisory until it has out-of-sample and shadow-mode evidence.

10. No strategy is promoted without walk-forward results, parameter sensitivity, paper-trading results, and operational pass criteria.

### 2.2 What "Agent" Means

An agent is a bounded engine with:

- owned state
- allowed inputs
- required outputs
- invariants
- failure behavior
- tests

Most agents are deterministic. "Agent" does not mean LLM.

### 2.3 What "Matrix" Means

Matrix is:

```text
append-only event log
  + deterministic projections
  + latest-state cache
  + versioned configuration
  + audit trail
```

Matrix is not:

- a reasoning brain
- a vector database
- a chat memory
- a place where agents write arbitrary JSON and hope it works

## 3. Version 1 Scope

### 3.1 In Scope For v1

- Bybit USDT perpetual data and paper/live execution only if venue eligibility passes.
- Binance USD-M futures data confirmation.
- OKX public futures data confirmation if easy to ingest.
- BTCUSDT and ETHUSDT initially.
- 15m and 1h timeframes initially.
- Deterministic feature engine.
- Three strategy modules in backtest:
  - liquidity sweep reversal
  - short/long squeeze
  - trend pullback
- Only the best validated module moves to paper trading.
- Event-driven simulator.
- Research Agent in shadow mode only.
- Risk Agent with hard veto.
- Exchange-side protective stops for every live position.
- Full event log for signals, risk decisions, orders, fills, and outcomes.

### 3.2 Out Of Scope For v1

- 5m live scalping.
- DCA / averaging down.
- Multi-exchange live execution.
- Autonomous LLM trade approval.
- RL.
- Auto parameter changes in production.
- Market making.
- Arbitrage.
- Options.
- On-chain whale strategy as a live signal.
- Full dashboard before the engine is validated.

## 4. System Topology

```text
Historical replay / live market data
        |
        v
Data Agent
        |
        v
Feature Agent
        |
        v
Regime Agent
        |
        v
Strategy Agents
        |
        v
Coordinator
        |
        v
Portfolio Agent
        |
        v
Risk Agent
        |
        v
Execution Agent / Execution Simulator
        |
        v
Exchange / Simulated Exchange

Side path:
News and macro feeds -> Research Agent -> cached ResearchState -> Coordinator/Risk context

Audit path:
Every event -> Matrix event log -> Analytics Agent -> reports and validation metrics
```

## 5. Canonical Contracts

All prices, sizes, fees, balances, and PnL use `Decimal`. All timestamps are UTC. Every event must carry both `exchange_ts` where available and `received_ts` in live mode.

### 5.1 MarketEvent

Represents raw normalized exchange data.

Required fields:

- `event_id`
- `venue`
- `symbol`
- `event_type`: `trade`, `book`, `kline`, `funding`, `open_interest`, `mark_price`, `index_price`
- `exchange_ts`
- `received_ts`
- `payload`
- `source_sequence` if available

Invariant:

- Events are immutable after written.

Failure behavior:

- If sequence gap or stale feed is detected, Data Agent emits `DataQualityEvent`.

### 5.2 CandleEvent

Represents a confirmed candle.

Required fields:

- `venue`
- `symbol`
- `timeframe`
- `open_time`
- `close_time`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume`
- `taker_buy_volume` if available
- `is_final`

Invariant:

- Strategy agents can only trade on final candles.

### 5.3 FeatureSnapshot

Represents deterministic features at a decision timestamp.

Required feature groups:

- price features
- volatility features
- momentum features
- trend features
- structure features
- order-flow features
- derivatives positioning features
- data quality flags

Minimum features:

- RSI 6, RSI 14, RSI 24
- MACD line, signal, histogram, histogram slope
- EMA 20, 50, 200, EMA 200 slope
- Bollinger middle, upper, lower, percent B, bandwidth percentile
- ATR 14, ATR percentile
- ADX 14
- Supertrend direction
- session VWAP
- volume z-score
- CVD or taker-buy imbalance
- funding rate and funding z-score
- OI delta and OI z-score
- rolling correlation to BTC
- spread bps

Invariant:

- Each snapshot includes a `feature_version`.

### 5.4 RegimeState

Required fields:

- `symbol`
- `timeframe`
- `regime`: `trend_up`, `trend_down`, `range`, `breakout_pending`, `high_volatility`, `crisis`
- `confidence`
- `evidence`
- `blocked_strategies`

Invariant:

- A strong higher-timeframe regime can block lower-timeframe counter-trend signals.

### 5.5 SignalCandidate

Required fields:

- `signal_id`
- `strategy_id`
- `symbol`
- `timeframe`
- `side`: `long` or `short`
- `created_at`
- `expires_at`
- `base_confidence`
- `expected_horizon_minutes`
- `entry_reference`
- `invalidation_price`
- `target_prices`
- `evidence`
- `feature_version`
- `strategy_version`

Invariant:

- A signal without invalidation price is invalid.

### 5.6 ResearchState

Research Agent output. It is optional context, not a trade command.

Required fields:

- `as_of`
- `expires_at`
- `assets`
- `event_type`: `none`, `macro`, `geopolitical`, `regulatory`, `exchange_risk`, `stablecoin_risk`, `protocol_risk`, `market_structure`, `unknown`
- `severity`: 0 to 1
- `directional_bias`: -1 to 1
- `confidence_multiplier`: 0 to 1.15
- `trade_policy`: `normal`, `raise_thresholds`, `reduce_size`, `block_new_entries`, `close_risk_positions`
- `reason_codes`
- `sources`
- `model_id`
- `prompt_version`

Invariant:

- Expired research state is ignored or treated as stale risk, never silently reused.

### 5.7 PortfolioIntent

Portfolio Agent output before risk approval.

Required fields:

- `intent_id`
- `signal_id`
- `symbol`
- `side`
- `entry_type`
- `entry_price`
- `stop_price`
- `target_plan`
- `risk_amount`
- `quantity`
- `notional`
- `leverage`
- `max_slippage_bps`
- `time_in_force`
- `max_hold_minutes`

Invariant:

- Total risk is known before execution.

### 5.8 RiskDecision

Risk Agent output.

Required fields:

- `decision_id`
- `intent_id`
- `decision`: `approve`, `reject`, `mutate`, `halt`
- `reason_codes`
- `approved_intent`
- `risk_snapshot`
- `risk_policy_version`

Invariant:

- Execution Agent only acts on approved decisions.

### 5.9 OrderPlan

Execution Agent input after risk approval.

Required fields:

- `order_plan_id`
- `approved_intent_id`
- `entry_order`
- `stop_order`
- `take_profit_orders`
- `cancel_rules`
- `emergency_exit_rules`

Invariant:

- Live long/short exposure is not allowed without a protective stop confirmed or immediately placed according to exchange mechanics.

### 5.10 ExecutionReport

Required fields:

- `order_id`
- `client_order_id`
- `venue_order_id`
- `status`
- `filled_quantity`
- `remaining_quantity`
- `avg_fill_price`
- `fee`
- `liquidity_flag`: `maker`, `taker`, `unknown`
- `exchange_ts`
- `received_ts`
- `raw_response_ref`

Invariant:

- Local order state changes only through execution reports or reconciliation.

## 6. Agent Specifications

### 6.1 Data Agent

Type: deterministic

Owns:

- exchange public data connections
- raw event normalization
- candle building
- data quality events
- historical backfill

Must ingest:

- Bybit klines, trades, order book, mark price, funding, open interest
- Binance klines, trades or aggregated trade data, order book, funding, open interest
- OKX public candles/funding/OI if used
- MEXC public contract data only after endpoint checks

Core algorithms:

- REST backfill after reconnect.
- Local candle builder from trades where needed.
- Sequence gap detection where exchange provides sequence IDs.
- Stale feed detection by event type.
- Duplicate event suppression.
- Symbol normalization.
- Precision metadata load on startup.

Failure behavior:

- Stale primary feed: block new entries for affected symbol.
- Missing reference venue data: lower signal confidence or block cross-exchange strategies.
- Backfill gap: mark feature snapshots invalid until repaired.

### 6.2 Feature Agent

Type: deterministic

Owns:

- all indicator calculations
- feature versioning
- feature validation against reference values

Core algorithms:

- RSI using Wilder smoothing.
- MACD using EMA 12/26/9.
- ATR using true range and Wilder smoothing.
- ADX using +DM, -DM, +DI, -DI, DX.
- Bollinger percent B and bandwidth percentile.
- Supertrend from ATR bands.
- CVD from trade aggressor side where available.
- Taker-buy imbalance from candle taker-buy volume where trade-level CVD is unavailable.
- Rolling and EWMA correlations.
- Funding/OI z-scores using rolling windows.

Invariant:

- A feature that cannot be computed honestly is missing, not guessed.

### 6.3 Regime Agent

Type: deterministic

Owns:

- market state classification
- higher-timeframe override
- strategy availability flags

Regime rules:

```text
trend_up:
  price > EMA200
  EMA200 slope positive
  Supertrend green
  ADX > 25
  swing structure HH/HL

trend_down:
  price < EMA200
  EMA200 slope negative
  Supertrend red
  ADX > 25
  swing structure LH/LL

range:
  EMA200 flat
  ADX < 20
  frequent mean crosses
  Bollinger bandwidth not expanding

breakout_pending:
  Bollinger bandwidth percentile < 15
  ATR percentile < 20
  range compression for N candles

high_volatility:
  ATR percentile > 90
  spread wider than normal
  market-wide correlation rising
```

Failure behavior:

- Unknown regime means reduced confidence, not aggressive trading.

### 6.4 Strategy Agents

Type: deterministic

Each strategy emits `SignalCandidate`. A strategy does not size trades or call APIs.

#### Strategy 1: Liquidity Sweep Reversal

Purpose:

- Capture stop-hunt reversals around meaningful levels.

Inputs:

- session high/low
- previous day/week high/low
- support/resistance zones
- candle wick and close behavior
- volume z-score
- CVD or taker-buy imbalance
- funding/OI context
- regime

Long candidate:

```text
price trades below a validated support or session low
candle closes back above that level
volume_z >= threshold
sell pressure weakens or CVD diverges
target is next liquidity pool above
regime does not show strong trend_down without capitulation evidence
```

Short candidate mirrors the long logic above resistance.

Reject if:

- close does not reclaim the swept level
- spread is abnormal
- target does not provide enough net R after fees/slippage
- active structural crypto risk

#### Strategy 2: Short/Long Squeeze

Purpose:

- Trade crowded perp positioning when forced covering can drive a sharp move.

Long candidate:

```text
funding_z is strongly negative
OI is elevated or recently expanded
price is at structural support
RSI is oversold
MACD bearish momentum is decelerating
volume indicates capitulation or absorption
```

Short candidate:

```text
funding_z is strongly positive
OI is elevated or recently expanded
price is at structural resistance
RSI is overbought
MACD bullish momentum is decelerating
volume indicates exhaustion or absorption
```

Reject if:

- OI is rising aggressively in the direction against the trade with no exhaustion.
- news indicates structural crypto damage.

#### Strategy 3: Trend Pullback

Purpose:

- Avoid forcing mean reversion during real trends.

Long candidate:

```text
higher timeframe trend_up
price pulls back to EMA20/EMA50/VWAP/Supertrend zone
RSI resets to 40-55, not panic oversold
MACD resumes upward momentum
volume confirms bounce
```

Short candidate mirrors the setup in a downtrend.

Reject if:

- ADX is weak and range regime dominates.
- pullback becomes a structure break.

### 6.5 Coordinator

Type: deterministic

Owns:

- simultaneous signal arbitration
- correlation-aware candidate selection
- attaching cached ResearchState
- session threshold application

Rules:

- Batch signals by decision timestamp.
- Risk sees the batch before any order is approved.
- If BTC and ETH generate same-direction correlated signals, choose one unless risk budget explicitly allows both.
- Prefer the signal with:
  - higher net expected R
  - cleaner invalidation level
  - better data quality
  - better liquidity
  - stronger higher-timeframe alignment
- Do not merge strategies into one confidence score until each strategy has standalone evidence.

### 6.6 Portfolio Agent

Type: deterministic

Owns:

- position sizing
- stop/target plan
- max hold time
- leverage calculation

Formula:

```text
risk_amount = equity * risk_fraction
stop_distance = abs(entry_price - stop_price)
quantity = risk_amount / stop_distance
notional = quantity * entry_price
leverage = notional / margin_allocated
```

Rules:

- Leverage is derived from stop distance and notional. It is not a confidence knob.
- Quantity and price are rounded to exchange rules before risk approval.
- If rounded quantity changes risk materially, recalculate.
- If minimum notional forces risk above limit, reject.
- No DCA in v1 live.

Initial live risk policy:

| Mode | Risk per trade | Daily loss stop | Max open positions | Notes |
|---|---:|---:|---:|---|
| Research backtest | variable | variable | variable | experiment only |
| Paper | selected policy | selected policy | 1-3 | prove mechanics |
| Micro-live | 0.10-0.25 percent | 0.75-1.00 percent | 1 | execution validation |
| Live v1 after proof | 0.25 percent | 1.50 percent | 2 | no DCA, no 5m |

### 6.7 Risk Agent

Type: deterministic

Owns:

- veto authority
- risk policy
- circuit breakers
- portfolio heat
- data quality enforcement
- live exposure controls

Pre-trade checks:

- data is fresh
- research state is not a hard-block event
- no active circuit breaker
- daily PnL within limit
- drawdown within limit
- max open positions not exceeded
- portfolio heat within limit
- correlation exposure acceptable
- expected net R after fees, slippage, and funding is acceptable
- stop price is valid
- leverage within cap
- spread within cap
- event window rules pass
- exchange is healthy

Live risk checks:

- open position has confirmed protective stop
- stop distance still matches policy
- position size matches expected size
- account equity drift is acceptable
- exchange reconciliation matches local projection

Circuit breakers:

| Trigger | v1 action |
|---|---|
| data stale for traded symbol | block new entries |
| stop order not confirmed after entry | emergency close or immediate manual halt policy |
| reconciliation mismatch | block new entries until resolved |
| 2 consecutive losses in micro-live | pause and review |
| daily loss stop hit | block new entries for the day |
| drawdown from live peak > 3 percent in v1 | halt live trading |
| structural exchange/stablecoin risk | block new entries |
| private API errors on order path | block new entries and reconcile |

### 6.8 Execution Agent

Type: deterministic

Owns:

- private exchange API calls
- order state machine
- idempotency
- protective stops
- reconciliation
- emergency exits

Bybit-specific rules:

- Order acknowledgement is not fill confirmation.
- `orderLinkId` or equivalent client ID must be used for idempotency where supported.
- Market orders can behave as IOC-style slippage-protected orders; do not assume guaranteed full fill.
- Post-only orders may cancel if they would execute immediately.
- TP/SL semantics must be tested on the exact product category before live use.

Order state machine:

```text
planned
submitted
acknowledged
open
partially_filled
filled
cancel_requested
canceled
rejected
expired
reconciliation_required
```

Execution policy:

- Prefer limit or post-only limit entries where strategy allows.
- Emergency exits may use market orders.
- Every entry must define stop handling before submit.
- If bracket/OCO behavior is not reliable for the product, the system must simulate bracket management while still placing exchange-side protective stops.
- Every live request/response is stored by reference in the event log.

### 6.9 Research Agent

Type: non-deterministic, cold path

Owns:

- news classification
- macro/event severity
- event type classification
- confidence multiplier proposal
- source-linked summaries

Allowed influence:

- raise thresholds
- reduce size
- block new entries during structural events
- add context to reports

Not allowed:

- direct trade approval
- position sizing
- order placement
- changing production parameters
- overriding Risk Agent

Shadow mode requirement:

- Minimum 4-8 weeks in paper mode before it can affect live decisions.
- For every signal, record what Research Agent would have done and compare outcome.

### 6.10 Analytics Agent

Type: deterministic, with optional offline analysis

Owns:

- trade log
- signal log
- no-trade log
- MFE/MAE analysis
- expectancy
- drawdown
- parameter sensitivity
- walk-forward reports
- strategy decay detection

Core outputs:

- strategy-level performance
- symbol-level performance
- session-level performance
- timeframe-level performance
- feature contribution
- signal rejection reasons
- operational errors

## 7. API And Data Source Plan

### 7.0 Venue Eligibility Gate

Before any live exchange integration, confirm the chosen venue legally and operationally supports your jurisdiction, account type, and product.

Current review notes:

- Bybit lists the United States among excluded jurisdictions in its service restriction notice.
- MEXC lists the United States and several other regions among prohibited jurisdictions in its restricted-country notice.
- OKX US disclosures state that OKX US offers US users spot/buy/sell/convert style services, while global OKX products are not available to US users.

Hard rule:

```text
If the account jurisdiction is not allowed for the exact product, live trading is blocked.
Use backtest and paper trading only until a compliant venue is selected.
```

This gate is not optional. A system that can trade technically but violates venue restrictions is not production-ready.

### 7.1 First Technical Execution Venue: Bybit

Use Bybit first if venue eligibility passes because:

- V5 API is well documented.
- Official Python client exists.
- Testnet/demo workflow exists.
- Ecosystem support is stronger than MEXC.
- NautilusTrader has Bybit integration support.

Use initially after eligibility passes:

- USDT linear perpetuals.
- One-way mode unless a verified reason exists for hedge mode.
- Isolated margin.
- BTCUSDT first, ETHUSDT second.

Verify before any live order:

- instrument precision
- minimum order size
- stop order behavior
- reduce-only behavior
- TP/SL behavior
- partial-fill behavior
- cancel behavior
- reconciliation endpoints
- rate limit behavior

### 7.2 MEXC Role

MEXC is not first live execution venue.

Use MEXC only for:

- public market data comparison
- future execution research
- possible backup venue after private endpoint tests

Reason:

- Current contract docs are useful but private order-path maturity must be verified.
- The system cannot depend on uncertain private-order behavior in v1.

### 7.3 Binance Role

Use Binance USD-M futures as high-quality reference data:

- klines
- trades or aggregate trades
- order book
- funding
- open interest
- mark/index price

Purpose:

- confirm volume
- confirm trend
- confirm derivatives positioning
- detect whether a Bybit/MEXC signal is venue-specific noise

### 7.4 OKX Role

Use OKX public data as secondary confirmation:

- funding
- open interest
- mark/index price
- candles
- liquidation/public derivatives data if available

Use the correct regional API domain for the account and jurisdiction.

### 7.5 Data Quality Gates

Every signal requires:

- execution venue data fresh
- reference venue data fresh unless strategy does not require cross-exchange confirmation
- candle finality confirmed
- no recent sequence gap unresolved
- spread below threshold
- funding/OI not stale if used as evidence
- feature snapshot valid

If a feature is missing:

- either block strategies needing it
- or mark confidence lower through explicit rule

Never silently substitute zero.

## 8. Backtesting Source Of Truth

### 8.1 Three Backtest Levels

#### Level 1: Vectorized Research

Purpose:

- fast idea rejection
- parameter sweeps
- sensitivity surfaces

Allowed tools:

- pandas
- NumPy
- Polars
- vectorbt if helpful

Not authoritative for live.

#### Level 2: Event-Driven Simulator

Purpose:

- authoritative strategy validation
- exact agent contract replay
- fill model
- fees
- funding
- stops
- risk gates
- portfolio constraints

This is the backtest that decides paper-trading promotion.

#### Level 3: Paper Trading

Purpose:

- prove live data, order simulation, reconciliation, logging, and alerts.
- Research Agent shadow-mode evaluation.

Paper trading is not optional.

### 8.2 NautilusTrader Decision Gate

Run a short integration spike before building the authoritative simulator.

Adopt NautilusTrader if:

- Bybit adapter supports the required instrument type.
- Backtest and live paths can use the same strategy boundary.
- Required order semantics can be represented cleanly.
- Custom Finding Alpha risk checks can be inserted without fighting the engine.
- Historical data import is manageable.

Build custom event simulator if:

- MEXC execution becomes mandatory.
- Bybit order semantics cannot be represented safely.
- Finding Alpha risk model becomes harder inside Nautilus than outside.
- Integration complexity delays basic backtesting.

Even if NautilusTrader is not adopted, copy its principle: same event model for backtest and live.

### 8.3 Event-Driven Backtest Loop

```python
for event in replay:
    matrix.append(event)
    data_quality = data_agent.project(event)
    features = feature_agent.update(event, matrix)
    regime = regime_agent.classify(features, matrix)
    candidates = strategy_bus.evaluate(features, regime, matrix)
    batch = coordinator.arbitrate(candidates, matrix.research_state, matrix)
    intents = portfolio_agent.size(batch, matrix.account)
    decisions = risk_agent.evaluate(intents, matrix)
    reports = execution_simulator.apply(decisions, event, matrix)
    analytics_agent.record(event, features, candidates, decisions, reports)
```

### 8.4 Fill Model Requirements

Market order fill:

- If L2 book is available, consume book depth.
- If only OHLCV is available, use pessimistic slippage.
- Include taker fee.

Limit order fill:

- If price only touches limit, assume no fill unless queue model justifies it.
- If price trades through limit by at least one tick, allow fill.
- Include maker fee only if the order truly rests.
- Partial fills if modeled size exceeds available depth.

Stop order:

- Model trigger price.
- Model resulting order type.
- Include slippage beyond stop during gaps or fast candles.

Funding:

- If position is open at funding timestamp, apply funding payment using notional and rate.

Spread:

- Entry must include bid/ask where available.
- Candle close alone is not enough for scalping validation.

### 8.5 No-Lookahead Rules

- Signal generated on candle close can only enter on next candle or later.
- A candle's high/low cannot be used to decide an entry at that candle's close.
- Funding/OI values are only available after their actual timestamp.
- News is only available after publish time and simulated ingest delay.
- Indicator warmup periods must be excluded from performance.

### 8.6 Walk-Forward Validation

Use rolling windows:

```text
train: 90 days
validate: 30 days
test: 30 days
roll forward: 30 days
```

For each window:

1. choose parameters using train/validate only
2. freeze parameters
3. run test
4. aggregate test results

Reject any strategy that only works in one market regime.

### 8.7 Parameter Sensitivity

Every candidate strategy must show a plateau, not a spike.

Test ranges:

- RSI threshold
- ATR stop multiplier
- volume z-score
- funding z-score
- ADX threshold
- session threshold
- max hold time
- stop buffer
- take-profit R multiple

Reject if:

- best result is at the edge of the grid
- trade count is too small
- performance collapses with small parameter changes
- gross edge disappears after fees/slippage/funding
- one outlier event creates most profit

### 8.8 Required Metrics

Report by strategy, symbol, timeframe, and session:

- net PnL
- net expectancy per trade
- average R
- median R
- win rate
- profit factor
- max drawdown
- Calmar ratio
- Sharpe and Sortino
- MFE/MAE
- average hold time
- time in market
- fee share of gross profit
- slippage share of gross profit
- funding contribution
- worst day
- worst streak
- number of trades
- rejected signal count

### 8.9 Promotion Gate: Research To Paper

Minimum requirements:

- event-driven out-of-sample profit factor >= 1.25
- positive expectancy after fees, slippage, and funding
- max drawdown within planned limits
- at least 300 qualifying historical trades for the strategy, or a documented reason for lower frequency
- parameter plateau confirmed
- no major lookahead violations
- no single month or single event accounts for most returns
- operational simulator passes stop, fill, partial-fill, and circuit-breaker tests

### 8.10 Promotion Gate: Paper To Micro-Live

Minimum requirements:

- at least 150 paper trades, or 6-8 weeks if strategy is lower frequency
- fee-adjusted expectancy positive
- slippage and missed-fill assumptions measured
- no unprotected simulated position
- no duplicate orders
- no unresolved reconciliation errors
- Research Agent remains shadow-only unless separately validated
- one strategy selected for live
- one symbol selected for live

### 8.11 Promotion Gate: Micro-Live To Live v1

Minimum requirements:

- at least 50 micro-live trades
- no order precision errors
- no stop placement failures
- no unresolved exchange reconciliation mismatch
- live slippage within backtest/paper bounds
- no breach of daily loss stop
- no manual emergency caused by software bug

## 9. LLM Research Agent Rules

### 9.1 Inputs

Allowed inputs:

- timestamped news articles
- macro calendar events
- exchange status notices
- official regulatory/exchange posts
- your historical event examples
- current market context summary produced by deterministic code

Not allowed:

- raw private account state unless needed for report generation
- direct exchange credentials
- free-form control of trading config

### 9.2 Output Schema

The LLM must output structured data only:

```json
{
  "as_of": "UTC timestamp",
  "expires_at": "UTC timestamp",
  "assets": ["BTC", "ETH"],
  "event_type": "macro",
  "severity": 0.0,
  "directional_bias": 0.0,
  "confidence_multiplier": 1.0,
  "trade_policy": "normal",
  "reason_codes": [],
  "sources": [],
  "one_sentence_summary": ""
}
```

Validation:

- malformed output is ignored
- stale output is ignored
- missing sources lowers trust or rejects output
- multiplier is clamped
- structural risk keywords go through deterministic hard-block rules

### 9.3 Shadow Evaluation

For every signal in paper mode:

- record ResearchState
- record what action it would have recommended
- record actual trade outcome
- calculate blocked-trade expectancy
- calculate boosted-trade expectancy
- calculate false-block rate
- calculate missed-crisis rate

Research Agent becomes active only if it improves drawdown or expectancy without overblocking.

## 10. Build Sequence

### Phase A: Architecture Spike

Goal:

- decide NautilusTrader vs custom event simulator
- verify Bybit order semantics in testnet/demo
- verify historical data import path

Deliverables:

- one BTCUSDT data replay
- one dummy signal
- one paper order path
- one stop order test
- one reconciliation loop
- decision note: Nautilus adopted or custom simulator selected

Exit gate:

- no uncertainty about the authoritative simulator path.

### Phase B: Domain Contracts And Matrix

Goal:

- implement contracts and append-only event log.

Deliverables:

- all canonical contract models
- event serializer/deserializer
- deterministic replay test
- in-memory Matrix projection
- persisted event log

Exit gate:

- replaying the same events produces the same final state.

### Phase C: Historical Data And Features

Goal:

- build trusted market dataset and feature engine.

Deliverables:

- Bybit BTCUSDT/ETHUSDT 15m/1h candles
- Binance reference candles/funding/OI
- feature snapshots
- feature validation against independent reference calculations

Exit gate:

- indicators match expected formulas and candle finality is correct.

### Phase D: Strategy Research

Goal:

- test each strategy separately.

Deliverables:

- liquidity sweep strategy backtest
- squeeze strategy backtest
- trend pullback strategy backtest
- parameter sensitivity report
- walk-forward report

Exit gate:

- only validated strategies proceed.

### Phase E: Event Simulator And Risk

Goal:

- authoritative backtest with order/risk realism.

Deliverables:

- fee model
- funding model
- slippage model
- limit/market/stop fill model
- Risk Agent active
- portfolio constraints
- circuit breakers

Exit gate:

- research-to-paper promotion gate is met.

### Phase F: Paper Trading

Goal:

- prove real-time operation without capital.

Deliverables:

- live Bybit data
- reference Binance data
- simulated order lifecycle
- Research Agent shadow mode
- operational metrics
- paper-trading report

Exit gate:

- paper-to-micro-live gate is met.

### Phase G: Micro-Live

Goal:

- validate real exchange execution with tiny risk.

Rules:

- one symbol
- one strategy
- one position max
- no DCA
- no 5m
- Research Agent cannot affect live orders unless separately approved after shadow mode

Exit gate:

- micro-live-to-live-v1 gate is met.

### Phase H: Live v1

Goal:

- controlled production trading.

Allowed:

- second symbol if correlation/risk policy permits
- second validated strategy if paper and micro-live gates pass
- small risk increase within policy

Still blocked:

- DCA
- 5m scalping
- autonomous ML parameter changes
- multi-exchange execution

## 11. Explicit Do-Not-Build-Yet List

Do not build these before Phase F:

- full dashboard
- mobile app
- multi-agent LLM debate system
- RL policy
- on-chain whale model
- social sentiment model
- multi-exchange execution
- DCA layer manager
- 5m scalping
- auto parameter optimizer
- strategy marketplace
- market-making bot

These distract from the core proof: can the deterministic engine produce positive expectancy after realistic costs while maintaining correct execution and risk state?

## 12. Double-Pass Checklist

### Pass 1: Architecture Soundness

- Is every hot-path decision deterministic?
- Can the same agent contracts run in backtest, paper, and live?
- Is there exactly one source of truth for orders and positions?
- Can every signal be traced to feature versions and data timestamps?
- Can every risk rejection be explained by reason codes?
- Can Research Agent failure degrade safely?
- Can data staleness block entries automatically?
- Can the system run one strategy without the rest of the architecture?
- Are strategy modules isolated enough to test separately?
- Is live execution limited to Bybit until another venue is proven?

### Pass 2: Failure Mode Soundness

- What happens if the entry order partially fills?
- What happens if the stop order is rejected?
- What happens if the WebSocket disconnects after entry?
- What happens if REST order query fails?
- What happens if local state disagrees with exchange state?
- What happens if funding/OI data is stale?
- What happens if Binance confirms nothing but Bybit shows a signal?
- What happens if spread triples?
- What happens if Research Agent reports stale crisis news?
- What happens if two correlated signals arrive simultaneously?
- What happens if a strategy performs well before fees but fails after fees?
- What happens if backtest fills are too optimistic?

If any answer is "we will handle it later," the system is not ready for live capital.

## 13. Final Build Order Summary

Follow this exact order:

1. Bybit execution and data semantics spike.
2. Decide NautilusTrader vs custom simulator.
3. Implement canonical contracts.
4. Implement Matrix event log and deterministic replay.
5. Build Bybit/Binance historical data loader.
6. Build Feature Agent.
7. Build Regime Agent.
8. Build one strategy at a time.
9. Run vectorized research only for fast rejection.
10. Run event-driven backtest for real validation.
11. Implement Risk Agent fully before paper trading.
12. Paper trade one validated strategy.
13. Run Research Agent in shadow mode.
14. Micro-live one symbol, one strategy, one position.
15. Scale only after live operational correctness and positive expectancy are proven.

## 14. Sources Used For Current Review

Architecture and trading engines:

- [NautilusTrader documentation](https://nautilustrader.io/docs/latest/)
- [NautilusTrader integrations](https://nautilustrader.io/docs/nightly/integrations/)
- [QuantConnect Algorithm Framework](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview)
- [Freqtrade documentation](https://www.freqtrade.io/en/stable/)
- [FreqAI documentation](https://www.freqtrade.io/en/stable/freqai/)
- [Hummingbot documentation](https://hummingbot.org/)
- [TradingAgents GitHub](https://github.com/TauricResearch/TradingAgents)
- [FinRL GitHub](https://github.com/AI4Finance-Foundation/FinRL)
- [FinRL-X GitHub](https://github.com/AI4Finance-Foundation/FinRL-Trading)
- [Microsoft Qlib GitHub](https://github.com/microsoft/qlib)
- [Microsoft RD-Agent GitHub](https://github.com/microsoft/RD-Agent)
- [OpenAlice GitHub](https://github.com/TraderAlice/OpenAlice)

Exchange/API references:

- [Bybit V5 REST kline](https://bybit-exchange.github.io/docs/v5/market/kline)
- [Bybit V5 WebSocket kline](https://bybit-exchange.github.io/docs/v5/websocket/public/kline)
- [Bybit V5 create order](https://bybit-exchange.github.io/docs/v5/order/create-order)
- [Bybit V5 open interest](https://bybit-exchange.github.io/docs/v5/market/open-interest)
- [MEXC contract API](https://mexcdevelop.github.io/apidocs/contract_v1_en/)
- [MEXC API overview](https://www.mexc.com/mexc-api)
- [MEXC restricted countries notice](https://www.mexc.com/learn/article/mexc-restricted-countries-complete-list-of-prohibited-limited-regions/1?handleDefaultLocale=keep)
- [Binance USD-M futures klines](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data)
- [Binance USD-M futures open interest](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest)
- [Binance USD-M futures funding history](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)
- [Binance USD-M futures kline WebSocket](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Kline-Candlestick-Streams)
- [OKX API v5 documentation](https://www.okx.com/docs-v5/en)
- [Bybit service restricted countries](https://www.bybit.com/en/help-center/article/Service-Restricted-Countries?category=8c8de4a417efb42713)
- [OKX US risk and compliance disclosures](https://www.okx.com/en-us/help/us-risk-and-compliance-disclosures)
