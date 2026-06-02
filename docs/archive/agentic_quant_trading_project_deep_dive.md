# Agentic Quant Trading Project Deep Dive

Research date: 2026-05-10  
Workspace reviewed: all Markdown files, the small text file, and the standalone architecture PDF in `E:\MyProjects\findingAlpha`.

This is not financial advice. It is an engineering and system-design analysis for a systematic trading platform. Any strategy must be validated with realistic backtesting, paper trading, operational controls, and legal/compliance review before live capital.

## 1. Executive Takeaway

Your current documents describe a useful first draft, but the next architecture should not be "seven LLM employees trading autonomously." The stronger model is a deterministic trading plant with narrow LLM research modules.

The best architecture for Finding Alpha is:

1. Deterministic hot path:
   - Market data ingestion
   - Feature computation
   - Signal generation
   - Position sizing
   - Risk veto
   - Order lifecycle management
   - Backtest/live event replay

2. Non-deterministic cold path:
   - News interpretation
   - Macro/event classification
   - Strategy research notes
   - Post-trade commentary
   - Parameter-review suggestions
   - Human-facing summaries

3. Backtesting as a first-class runtime:
   - The exact same agent contracts must run in backtest, paper, and live.
   - Backtesting is not a separate notebook. It is the simulator mode of the trading system.

The strongest ideas from the projects reviewed:

| Source | What to copy | What not to copy |
|---|---|---|
| NautilusTrader | Deterministic event-driven engine, research-to-live parity, adapter model, order semantics | Full Rust-native adoption on day one may slow you down |
| QuantConnect LEAN | Clean Alpha -> Portfolio -> Risk -> Execution separation | Default portfolio framework is not ideal for tightly coupled scalping entries/exits |
| Senex Trader | Independent engines over Redis Streams, TimescaleDB, broker as source of truth, hot/cold path split | Options-specific parts do not map directly to crypto perps |
| Freqtrade/FreqAI | Practical crypto bot features, dry-run, backtest, hyperopt, live monitoring, ML retraining patterns | Single strategy class and ccxt dependence are a poor fit for your multi-agent design |
| Qlib/RD-Agent | Research workflow, factor mining, model/backtest pipeline, online/offline split | Equity-factor style research is slower frequency than your crypto microstructure plan |
| FinRL/FinRL-X | Weight-vector contract, DRL research sandbox, train-test-trade discipline | Do not let RL control live execution early |
| TradingAgents | Role decomposition, structured debate, persistent decision logs, checkpointing | Do not put LLM debates in the live trading hot path |
| FinGPT/FinRobot | Finance-specific LLM tooling, sentiment/RAG/report agents | Treat model outputs as evidence, not authority |
| Hummingbot | Exchange connectors, market-making/arbitrage patterns, WebSocket connector lessons | Market making inventory risk is a different business from directional mean reversion |
| ABIDES | Agent-based market simulation concepts, latency/message realism | Too heavy for initial crypto backtesting |
| vectorbt/backtesting.py/backtrader/Jesse | Useful research/backtest references | None alone gives your exact multi-agent, multi-venue, risk-gated runtime |

My recommendation:

- Use your own Python domain layer and deterministic agent contracts.
- Use NautilusTrader as the most serious candidate for the event-driven engine/backtest-live substrate, especially if you want research-to-live parity.
- If you do not adopt NautilusTrader, still copy its central idea: one event model for backtest, paper, and live.
- Use Redis Streams or a typed in-process event bus for agent handoff; do not use LangGraph for deterministic agents.
- Use LLMs only for Research/News, Analyst reports, and calibration suggestions. Their output should be cached, structured, confidence-scored, and always gateable by deterministic risk rules.

## 2. What Your Existing Files Already Got Right

Across the current Markdown files, the strongest parts are:

- The system is correctly framed as mostly deterministic. Only the Research Agent needs an LLM.
- Risk veto is central. Risk should be the highest authority in the machine, not a reporting agent.
- The "Matrix/Ontology" idea is good if interpreted as shared typed state and event history, not as a vague AI brain.
- Session-aware trading is useful: Asia, London, London-NY overlap, NY solo, wind-down should not share thresholds.
- Cross-exchange data is essential. MEXC-only signals are weak; Binance, Bybit, OKX, Coinglass/Coinalyze, and macro feeds give context.
- LLM news interpretation should distinguish temporary external shocks from structural crypto damage.
- You already identified a key issue: backtesting must include fees, slippage, funding, latency, no lookahead, and portfolio-level risk.

The biggest gaps:

- Backtesting is still described as a phase, not as the core runtime contract.
- "Agents" are mostly job titles, not typed processes with inputs, outputs, invariants, and failure modes.
- The strategy mixes two systems: original RSI/MACD/Bollinger mean reversion and newer liquidity/order-flow/confluence trading. These should become separate strategy modules behind a common signal contract.
- Risk settings conflict across docs: 0.25 percent per trade in the original blueprint, 1-2 percent in the later aggressive small-account framework. This must become an explicit account-tier policy, not scattered narrative.
- Some proposed daily return targets are unrealistic as system requirements. The requirement should be positive expectancy, risk-adjusted returns, and survival gates.
- The text file in the workspace contains a plaintext secret. Treat it as compromised if real.

## 3. Projects And Products Reviewed

### 3.1 NautilusTrader

Source: [NautilusTrader GitHub](https://github.com/nautechsystems/nautilus_trader), [docs](https://nautilustrader.io/docs/latest/)

What it does:

- Open-source, production-grade trading engine.
- Rust core, Python control plane.
- Event-driven architecture for research, deterministic simulation, and live trading.
- Supports multi-asset, multi-venue trading through modular adapters.
- Backtesting supports multiple venues, instruments, strategies, tick/trade/bar/order-book/custom data, and nanosecond resolution.
- Live and backtest strategy implementations are designed to be identical.
- Supports advanced order semantics: post-only, reduce-only, OCO, OTO, time-in-force, conditional triggers.
- Existing integrations include major crypto venues such as Binance, Bybit, OKX, Kraken, Coinbase, Deribit, BitMEX, dYdX, Hyperliquid, plus data providers like Tardis.

Why it matters for you:

NautilusTrader is the closest match to the core thing Finding Alpha needs: a deterministic event engine where the same strategy code can run in simulation and live. That directly addresses your uncertainty about backtesting integration.

Pipeline pattern to copy:

```text
Historical/live data events
  -> strategy receives normalized market data
  -> strategy emits order intent
  -> risk layer validates or mutates intent
  -> execution engine submits/cancels/amends orders
  -> fills/order events update portfolio state
  -> strategy sees the same event stream in backtest and live
```

Strong algorithms and design ideas:

- Deterministic event replay: every historical tick/candle/order-book event is replayed through the same strategy handlers used live.
- Normalized instrument model: each venue's raw symbols, tick sizes, quantity precision, and order rules become typed objects.
- Time model: simulated clock in backtest, real clock in live, same event ordering assumptions.
- Adapter pattern: venue-specific REST/WebSocket code is isolated from strategy/risk logic.
- Order state machine: order intents become accepted/open/partially filled/filled/canceled/rejected events.
- Research-to-live parity: avoid rewriting vectorized notebook logic into separate production code.

Pros:

- Best fit for deterministic agents.
- Strong backtest/live parity.
- Multi-venue architecture is aligned with your MEXC/Bybit/Binance/OKX data plan.
- Better foundation for serious order lifecycle modeling than a quick pandas backtest.
- Supports order-book and tick-level simulation if you later need microstructure realism.

Cons:

- Larger learning curve than a custom pandas prototype.
- Rust core can make deep customization harder for a Python-only beginner.
- Some integrations are beta; MEXC futures may still require your own adapter.
- Does not give you a ready-made LLM/ontology/dashboard stack.

How I would use it:

- Prototype deterministic agents in Python first with clean contracts.
- Evaluate NautilusTrader as the event/backtest/live substrate before writing your own execution engine.
- If adopted, wrap Finding Alpha agents as strategy/risk/execution components around Nautilus events.
- If not adopted, copy its event replay and order state concepts.

### 3.2 QuantConnect LEAN

Source: [QuantConnect Algorithm Framework docs](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview), [LEAN GitHub](https://github.com/QuantConnect/Lean)

What it does:

- Open-source algorithmic trading engine behind QuantConnect.
- Supports backtesting and live trading across many asset classes.
- Its Algorithm Framework decomposes strategies into:
  - Universe Selection
  - Alpha
  - Portfolio Construction
  - Risk Management
  - Execution
- Signals are expressed as `Insight` objects.
- Portfolio targets are adjusted by risk before execution.

Why it matters for you:

LEAN gives a clean professional mapping for agent boundaries. Your current agents are similar, but LEAN makes the interfaces stricter:

```text
Universe/Data scope -> Alpha/Signal -> Portfolio target -> Risk-adjusted target -> Execution
```

For Finding Alpha:

| LEAN concept | Finding Alpha equivalent |
|---|---|
| Universe Selection | Symbol/timeframe eligibility, exchange health, session availability |
| Alpha Model | Math/Structure/Positioning/Liquidity agents emitting signal objects |
| Insight | Typed `SignalCandidate` with direction, horizon, confidence, evidence |
| Portfolio Construction | Position Agent sizing notional, leverage, stop, target |
| Risk Management | Risk Agent veto/mutate position target |
| Execution | Execution Agent submits orders and reconciles fills |

Strong algorithms and design ideas:

- Use typed signal objects instead of passing raw dictionaries between agents.
- Separate "signal strength" from "position target."
- Let risk mutate or reject a target before it reaches execution.
- Build custom portfolio construction for "multi-bet" trading so one signal does not allocate the whole account.
- Use risk models for exits/trailing stops when exit logic is not naturally separated.

Pros:

- Mature conceptual architecture.
- Clear separation of concerns.
- Strong model for portfolio/risk/execution handoff.
- Large data and brokerage ecosystem if you later expand beyond crypto.

Cons:

- Its default framework is better for portfolio rebalancing/ranking than tightly coupled scalping.
- Live crypto futures behavior may not map to your MEXC/Bybit-specific needs without custom brokerage/data models.
- It is a broad platform, not a specialized crypto microstructure system.

How I would use it:

- Copy the module boundaries and object contracts.
- Do not blindly adopt the whole platform unless you want QuantConnect's ecosystem and constraints.
- Your custom `SignalCandidate`, `PortfolioIntent`, `RiskDecision`, `OrderIntent`, and `ExecutionReport` should look like LEAN's `Insight`, `PortfolioTarget`, risk-adjusted target, and execution events.

### 3.3 Senex Trader

Source: [Senex Trader architecture page](https://senextrader.com/)

What it does:

- Open-source quantitative options trading framework.
- Eight independent engines:
  - Market Data Pipeline
  - Rules and Analysis
  - ML Pipeline
  - Trading Engine
  - Broker Gateway
  - Notifications
  - API Gateway
  - Scheduler
- Uses Redis Streams for messaging and TimescaleDB for time-series.
- Uses Django for the API/cold path and pure asyncio/asyncpg daemons for the hot path.
- Treats the broker as source of truth.
- Emphasizes no JSON for structured data: structured data goes into typed tables.

Why it matters for you:

This is probably the most directly useful "solo-developer production architecture" found online. It matches your desired multi-agent system better than most LLM trading projects because most engines are deterministic and independently deployable.

Pipeline pattern to copy:

```text
Market Data Engine
  -> Redis Streams: candles, trades, order book, funding, OI
Rules/Analysis Engine
  -> Redis Streams: signal candidates
Trading Engine
  -> risk checks + sizing + order lifecycle
Broker/Exchange Gateway
  -> exchange source-of-truth reconciliation
Scheduler
  -> backfills, health checks, token refresh, cleanup
API Gateway
  -> dashboard and control plane
```

Strong algorithms and design ideas:

- Hot path/cold path separation:
  - Hot path: async daemons, minimal ORM overhead, low-latency event handling.
  - Cold path: dashboard/API/reporting with Django/FastAPI style ergonomics.
- Broker/exchange as source of truth:
  - Local state is a cache.
  - Positions, fills, and balances must be reconciled against the exchange.
- Independent engine deployment:
  - Data collection should not stop because a web dashboard restarts.
  - Research/LLM failure should not stop stop-loss monitoring.
- Structured observability:
  - Prometheus metrics, structured logs, health checks, circuit breakers.

Pros:

- Very aligned with your "many deterministic agents" direction.
- Redis Streams and TimescaleDB fit your Matrix/Ontology idea better than a vague vector store.
- Practical production lessons: reconciliation, rate limits, API scopes, scheduler, alerts.
- Separates ML/AI from order execution.

Cons:

- Options-focused; Greeks/IV surface parts do not transfer directly to crypto perps.
- Public release maturity needs validation before depending on it.
- Not a complete crypto futures trading stack.

How I would use it:

- Copy the engine topology.
- Use Redis Streams or a typed event bus for process separation.
- Use TimescaleDB/ClickHouse for candles, trades, features, and backtest datasets.
- Implement "exchange as source of truth" from day one.

### 3.4 Freqtrade and FreqAI

Source: [Freqtrade docs](https://www.freqtrade.io/en/stable/), [FreqAI docs](https://www.freqtrade.io/en/stable/freqai/), [Freqtrade GitHub](https://github.com/freqtrade/freqtrade)

What it does:

- Free open-source crypto trading bot in Python.
- Supports strategy development with pandas, historical data download, backtesting, plotting, hyperoptimization, dry-run, live trading, Telegram/web UI, REST API, and analysis notebooks.
- Supports major spot and futures exchanges.
- FreqAI adds model training/inference around Freqtrade strategies.
- FreqAI features include:
  - Background retraining during live deployment
  - Large feature sets
  - Backtesting with periodic retraining
  - Outlier removal
  - Data normalization
  - Data download/update automation
  - Model persistence/crash recovery
  - Consumer fleet pattern where one bot trains and others consume signals

Why it matters for you:

Freqtrade is not the final architecture I would choose, but it is valuable source-code reference for practical crypto bot concerns:

- Dry-run mode
- Backtest output
- Exchange-specific notes
- Stoploss/trailing stop rules
- Lookahead analysis
- Producer/consumer mode
- Orderflow feature work
- Hyperparameter optimization
- Telegram and web control
- Trade database and performance analysis

Strong algorithms and design ideas:

- Hyperopt:
  - Optimize buy/sell/ROI/stoploss/trailing parameters over historical windows.
  - Useful only if you use walk-forward and parameter-sensitivity checks.
- FreqAI retraining:
  - Separate model training thread from inference/trading operations.
  - Keep latest model/data in memory for low-latency inference.
  - Persist models to disk for crash recovery.
- Lookahead and recursive analysis:
  - Explicit tools to detect data leakage or indicator instability.
- Dry-run:
  - Simulated money live against real-time data before real capital.

Pros:

- Very practical crypto-bot ecosystem.
- Many exchange edge cases have been encountered by the community.
- Strong reference for CLI, config, database, dry-run, dashboard, Telegram.
- FreqAI gives useful patterns for ML retraining and model lifecycle.

Cons:

- Uses ccxt under the hood, which your session notes already flagged as risky for production order semantics and money precision.
- Strategy abstraction is not naturally multi-agent.
- The bot owns too much of the runtime; you may fight the framework.
- Portfolio-level correlated risk and multi-signal arbitration are not its central design.

How I would use it:

- Do not build Finding Alpha inside Freqtrade unless you accept its constraints.
- Read it for implementation patterns:
  - trade lifecycle
  - dry-run semantics
  - config
  - telemetry
  - exchange-specific handling
  - backtest reports
  - lookahead checks

### 3.5 Qlib

Source: [Microsoft Qlib GitHub](https://github.com/microsoft/qlib)

What it does:

- Open-source AI-oriented quantitative investment platform from Microsoft.
- Covers data processing, model training, backtesting, analysis, and online serving.
- Supports supervised learning, market dynamics modeling, and reinforcement learning.
- Has a full quant investment chain: alpha seeking, risk modeling, portfolio optimization, and order execution.
- Integrates with RD-Agent for LLM-based automated factor mining and model optimization.

Why it matters for you:

Qlib is more "quant research platform" than "crypto execution bot." Its relevance is how to structure research and evaluate models:

```text
Data provider
  -> feature/factor engineering
  -> model training
  -> signal generation
  -> portfolio construction
  -> backtest
  -> analysis
  -> online serving
```

Strong algorithms and design ideas:

- Factor pipeline:
  - Build features from raw data.
  - Train models to predict future return/risk labels.
  - Rank assets/signals.
- Rolling/online serving:
  - Research models are trained offline and served online.
  - Live code consumes model outputs, not notebooks.
- Adaptive modeling:
  - Concept drift and market dynamics are explicit research problems.
- Nested decision framework:
  - Model decisions at different granularities can be nested, which maps to your higher-timeframe override.

Pros:

- Excellent inspiration for research discipline.
- Strong ML/backtest/research workflow.
- Useful if you later build predictive feature models from your full signal log.
- RD-Agent integration is relevant to automated research.

Cons:

- Not a live crypto futures execution engine.
- Equity-style alpha factors and daily-frequency workflows do not directly solve your 5m/15m order-flow trading.
- Data model likely needs adaptation for funding, OI, liquidations, order book, sessions, and exchange state.

How I would use it:

- Copy the offline research workflow and model registry thinking.
- Use it as reference for Analytics Agent and Research Lab, not for hot-path execution.
- If you later train models, use Qlib-like datasets: features, labels, instruments, time index, train/valid/test splits.

### 3.6 RD-Agent

Source: [Microsoft RD-Agent GitHub](https://github.com/microsoft/RD-Agent), [RD-Agent Quant publication page](https://www.microsoft.com/en-us/research/publication/rd-agent-quant-a-multi-agent-framework-for-data-centric-factors-and-model-joint-optimization/)

What it does:

- Multi-agent R&D automation framework.
- In quant mode, it automates factor mining and model optimization.
- Focuses on coordinated factor-model co-optimization.
- Works with Qlib for quant research workflows.

Why it matters for you:

This is not a live trading agent. It is an offline research agent. That distinction is critical.

The right use for Finding Alpha:

```text
Offline research loop:
  propose feature/factor idea
  implement factor
  run backtest/walk-forward
  compare metrics
  keep/reject
  write experiment note

Live trading:
  only consumes approved, versioned factors/models
```

Strong algorithms and design ideas:

- Auto factor mining:
  - Generate candidate factors from price, volume, funding, OI, CVD, macro, news.
  - Evaluate them against future returns, MFE/MAE, and stop-before-target labels.
- Model optimization:
  - Iterate model architecture or hyperparameters.
  - Compare out-of-sample metrics, not just in-sample fit.
- Experiment traceability:
  - Every idea should produce code, data version, parameters, metrics, and conclusion.

Pros:

- Strong model for a non-live LLM research assistant.
- Helps avoid putting LLMs in the order path.
- Can mine new deterministic rules from your historical signal database.

Cons:

- Still needs guardrails against overfitting and data snooping.
- Factor mining can generate impressive but false patterns.
- It is not designed for per-trade execution safety.

How I would use it:

- Build a "Research Lab Agent" inspired by RD-Agent that cannot trade.
- It can propose:
  - new confluence features
  - thresholds
  - parameter ranges
  - ablation tests
  - walk-forward experiments
- It cannot change production parameters without human approval and paper validation.

### 3.7 FinRL and FinRL-X

Source: [FinRL GitHub](https://github.com/AI4Finance-Foundation/FinRL), [FinRL-X GitHub](https://github.com/AI4Finance-Foundation/FinRL-Trading)

What it does:

- FinRL is a financial reinforcement learning framework.
- Classic FinRL uses a three-layer architecture:
  - market environments
  - DRL agents
  - financial applications
- It supports DRL agents such as A2C, DDPG, PPO, SAC, and TD3.
- FinRL-X is the newer AI-native modular trading infrastructure.
- FinRL-X introduces a weight-centric interface: strategy outputs a target portfolio weight vector, then execution/risk layers act on it.
- FinRL-X positions itself as ML + DRL + LLM-ready, with professional backtesting and brokerage execution.

Why it matters for you:

The main lesson is not "use RL to trade." The useful lesson is the interface contract:

```text
strategy/data/ML logic -> target weights or trade intent -> risk overlay -> execution
```

For Finding Alpha, a crypto-perp version is:

```text
Signal agents -> PortfolioIntent:
  symbol
  side
  desired risk in R
  desired notional
  stop price
  target prices
  max leverage
  expiry

Risk Agent -> approved/rejected/mutated intent
Execution Agent -> actual orders
```

Strong algorithms and design ideas:

- RL agents:
  - A2C/PPO: policy-gradient methods for sequential decisions.
  - DDPG/TD3/SAC: continuous-action methods that can output allocation weights.
- Market environment:
  - State: features at time t.
  - Action: position/weight/order decision.
  - Reward: return adjusted by transaction cost, drawdown, risk.
- Train-test-trade pipeline:
  - Train on historical period.
  - Validate out-of-sample.
  - Paper/live trade with frozen policy.
- Weight-centric contract:
  - Decouples alpha logic from execution.

Pros:

- Good research sandbox for portfolio allocation experiments.
- Useful if you later want a model to choose between strategies or timeframes.
- Gives a clean target-weight/intent contract.

Cons:

- RL is fragile in finance.
- Reward hacking and overfitting are common.
- Historical market environments do not capture real liquidity, slippage, exchange outages, and regime shocks unless you explicitly model them.
- It is dangerous to give an RL policy direct live execution power.

How I would use it:

- Do not use RL in Phase 1-3.
- Later, maybe use RL for:
  - strategy allocation between deterministic strategies
  - session-level throttle
  - order execution timing in simulation
- Never let RL override risk, stops, or kill switches.

### 3.8 TradingAgents

Source: [TradingAgents GitHub](https://github.com/TauricResearch/TradingAgents), [project site](https://tradingagents-ai.github.io/)

What it does:

- Multi-agent LLM financial trading framework.
- Models a real trading firm with LLM agents:
  - fundamentals analyst
  - sentiment analyst
  - news analyst
  - technical analyst
  - bullish and bearish researchers
  - trader
  - risk management
  - portfolio manager
- Uses dynamic discussions/debates.
- Uses LangGraph.
- Supports multiple LLM providers, local models via Ollama, Docker, structured outputs, checkpoint resume, and persistent decision logs.
- Runs research-style analyses and sends approved orders to a simulated exchange.

Why it matters for you:

TradingAgents is very close to your original "AI firm" mental model, but it proves why your live architecture should be more conservative. It is useful as an LLM research/cold-path pattern, not as a live scalping engine.

Strong ideas to copy:

- Role specialization:
  - Do not ask one LLM to be analyst, trader, risk officer, and reporter.
- Bull/bear debate:
  - Useful for research notes and human review.
  - Especially useful for news interpretation: "temporary shock" vs "structural damage."
- Structured output:
  - LLM outputs should be JSON/schema-validated, not prose that trading code parses loosely.
- Persistent decision log:
  - Keep prior decisions, realized returns, and reflections.
- Checkpointing:
  - Long-running research analyses should resume after crash.
- Model tiering:
  - Cheap/fast model for retrieval/summarization.
  - Stronger model for final classification/reasoning.

What not to copy:

- LLM committee in the live hot path.
- LLM as final trade approver.
- Daily equity-style analysis loop for 5m/15m crypto signals.

Pros:

- Best reference for LLM role design.
- Shows how to separate analyst/researcher/trader/risk roles.
- Supports local models, multiple providers, structured outputs, checkpointing, and decision memory.

Cons:

- Research-oriented, non-deterministic, and sensitive to model choice/temperature/data.
- LLM latency is too high for fast crypto execution.
- "Technical analyst LLM" should not compute indicators; deterministic code should.
- Simulated exchange execution is not enough for live crypto perps.

How I would use it:

- Build your LLM Research Agent as a miniature TradingAgents:
  - News Analyst extracts events.
  - Macro Analyst classifies regime/event risk.
  - Bull/Bear reviewers argue temporary shock vs structural damage.
  - Risk Narrator outputs a multiplier and reason.
- Cache the result in Matrix/Redis.
- Trading pipeline only reads the cached multiplier and event flags.
- Risk Agent can ignore or hard-block based on deterministic rules.

### 3.9 FinGPT and FinRobot

Sources: [FinGPT site](https://fingpt.io/), [FinGPT GitHub](https://github.com/AI4Finance-Foundation/FinGPT), [FinRobot GitHub](https://github.com/AI4Finance-Foundation/FinRobot), [AI4Finance overview](https://ai4finance.org/)

What they do:

- FinGPT provides open-source financial LLM tooling for sentiment, forecasting, RAG, financial documents, and benchmarks.
- FinRobot is an LLM agent platform tailored for financial analysis, research automation, algorithmic trading strategy support, and risk assessment.
- The ecosystem emphasizes open-source financial AI, domain adaptation, and finance-specific workflows.

Why they matter for you:

They are relevant to your Research Agent and CEO-reporting layer, not execution. FinGPT-like tools can help classify:

- news sentiment
- event type
- entity risk
- macro narrative
- social signal noise
- regulatory risk
- exchange/protocol failure risk

Strong algorithms and design ideas:

- Retrieval-augmented generation:
  - Ground event interpretation in recent articles, filings, docs, historical examples, and your own past trade outcomes.
- Sentiment classification:
  - Convert text into structured scores, but calibrate scores against market reactions.
- Financial document parsing:
  - Useful if you ever expand to equities or ETF flow/report analysis.
- Multi-agent financial analysis:
  - Separate sentiment, fundamentals, market data, and risk assessment tools.

Pros:

- Better financial language priors than generic prompting.
- Useful for offline reports and event classification.
- Can be self-hosted or fine-tuned if API cost/privacy matters.

Cons:

- Financial LLM outputs are still probabilistic.
- Forecasting claims need strict validation.
- Crypto news is noisy and time-sensitive; stale sentiment can be worse than no sentiment.

How I would use it:

- Use it as inspiration for the Research Agent stack:
  - RAG over your historical examples docs.
  - Event classifier with strict schema.
  - Sentiment and severity outputs.
  - Source links stored with every classification.
- Do not let it compute technical indicators, position size, stop distance, or order placement.

### 3.10 Hummingbot

Source: [Hummingbot site](https://hummingbot.org/), [Hummingbot GitHub](https://github.com/hummingbot/hummingbot)

What it does:

- Open-source Python framework for automated crypto trading strategies on CEX and DEX venues.
- Strong orientation toward market making, arbitrage, and exchange connectors.
- Supports CLOB CEX, CLOB DEX, AMM DEX, routers, and perpetual connectors.
- Has connector standardization for REST and WebSocket APIs.
- The ecosystem includes Hummingbot API, MCP, DEX Gateway, and research notebooks.

Why it matters for you:

Hummingbot is important for exchange-connector and market-making lessons. It is less relevant to your directional mean-reversion/confluence strategy unless you later add:

- funding-rate arbitrage
- liquidation sniping
- market making around liquidity zones
- cross-exchange basis/arbitrage
- grid strategies

Strong algorithms and design ideas:

- Market making:
  - Quote bid/ask around midprice.
  - Manage inventory skew.
  - Adjust spreads based on volatility/order-book depth.
- Arbitrage:
  - Compare venues after fees/slippage.
  - Execute hedged legs quickly.
- Connector abstraction:
  - Normalize REST/WebSocket across exchanges.
  - Keep strategy code portable across venues.
- DEX Gateway:
  - Separate blockchain/DEX interactions from strategy logic.

Pros:

- Strong crypto exchange connector ecosystem.
- Useful for learning CEX/DEX API abstractions.
- Built for high-frequency crypto bots.
- Good reference if you later add market making or arbitrage agents.

Cons:

- Market making is a different risk problem than directional trading.
- Inventory/adverse-selection risk can be severe.
- Not a backtesting-first framework for your exact multi-agent decision pipeline.

How I would use it:

- Study connector design and WebSocket handling.
- Do not make it the core unless you pivot toward market making/arbitrage.
- Potential later agent: Funding/Arbitrage Agent inspired by Hummingbot.

### 3.11 ABIDES

Source: [ABIDES GitHub](https://github.com/abides-sim/abides)

What it does:

- Agent-Based Interactive Discrete Event Simulation environment.
- Designed for AI agent research in market applications.
- Simulates tens of thousands of trading agents interacting with an exchange agent.
- Supports configurable pairwise network latencies.
- Message design is modeled after NASDAQ ITCH/OUCH.

Why it matters for you:

ABIDES is not for your first backtest engine. It is for a future research problem: "What happens to my strategy under more realistic market microstructure assumptions?"

Strong algorithms and design ideas:

- Discrete-event simulation:
  - Agents send messages at simulated times.
  - Exchange agent matches orders.
  - Latency affects who gets filled.
- Background agents:
  - Simulate noise traders, market makers, liquidity takers, value agents.
- Exchange agent:
  - Simulates order book and matching engine.
- Latency model:
  - Different agents have different network delays to the exchange.

Pros:

- Strong conceptual reference for microstructure simulation.
- Useful if you need order-book-level fill realism.
- Useful for stress-testing market impact and latency.

Cons:

- Too heavy for initial crypto system.
- Requires detailed assumptions about other market participants.
- Public project is older and not a turnkey crypto perp backtester.

How I would use it:

- Do not integrate in Phase 1.
- Borrow concepts later:
  - exchange matching simulation
  - latency distributions
  - background liquidity agents
  - adverse-selection tests

### 3.12 vectorbt, backtesting.py, backtrader, Jesse

Sources: [vectorbt docs](https://vectorbt.dev/), [backtesting.py](https://kernc.github.io/backtesting.py/), [Backtrader](https://www.backtrader.com/), [Jesse](https://jesse.trade/)

What they do:

- vectorbt:
  - Fast vectorized quant analysis/backtesting over pandas/NumPy, accelerated with Numba/Rust.
  - Excellent for parameter sweeps and quick research.
- backtesting.py:
  - Simple Python backtesting framework.
  - Good for single-strategy prototyping.
- Backtrader:
  - Mature event-driven backtesting/trading framework.
  - Slower and less modern, but still conceptually useful.
- Jesse:
  - Crypto trading framework with backtesting, live/paper trading, indicators, multi-symbol/timeframe support, optimization, Monte Carlo, and AI assistant features.

Why they matter for you:

These are research tools, not necessarily the production core. The important distinction:

- Use vectorbt/custom vectorized code for parameter exploration.
- Use an event-driven simulator for final validation.
- Use live-equivalent event replay before paper/live.

Pros:

- Fast learning.
- Useful for parameter sensitivity.
- Useful for sanity-checking indicators and strategy ideas.

Cons:

- Simplified fill models can lie to you.
- Many backtest frameworks do not model:
  - funding payments
  - maker/taker distinction
  - partial fills
  - order queue position
  - stale feeds
  - exchange outages
  - correlated portfolio gates
  - multi-agent arbitration

How I would use them:

- vectorbt for fast sweeps:
  - RSI thresholds
  - ATR multipliers
  - volume z-score thresholds
  - session thresholds
  - confluence weights
- Event-driven engine for final gate.
- Jesse is worth studying for crypto-specific UI/backtest/Monte Carlo ideas.

## 4. Recommended New Finding Alpha Architecture

### 4.1 Principle: Agents Are Typed Engines, Not Personas

Each agent should have:

- Inputs
- Outputs
- State it owns
- State it may read
- Invariants
- Failure behavior
- Test fixtures
- Backtest/live parity rule

The term "agent" should not imply LLM. Most agents are deterministic services.

### 4.2 Proposed Agent Map

| Agent | Deterministic? | Owns | Output |
|---|---:|---|---|
| Data Agent | Yes | REST/WS ingestion, normalization, candle building, quality checks | `MarketEvent`, `CandleEvent`, `BookEvent`, `FundingEvent`, `OIEvent` |
| Feature Agent | Yes | Indicators, structure, order-flow features, z-scores | `FeatureSnapshot` |
| Regime Agent | Mostly yes | trend/range/breakout/high-vol classification | `RegimeState` |
| Signal Agents | Yes | mean reversion, liquidity sweep, trend-follow, squeeze modules | `SignalCandidate` |
| Research Agent | No | news/macro/event interpretation | `ResearchState` |
| Portfolio/Position Agent | Yes | sizing, stops, targets, account-tier policy, DCA plan | `PortfolioIntent` |
| Risk Agent | Yes | veto, mutation, circuit breakers, correlation/portfolio heat | `RiskDecision` |
| Execution Agent | Yes | order state machine, exchange adapter, reconciliation | `OrderIntent`, `ExecutionReport` |
| Analytics Agent | Yes, with optional offline ML | trade logs, metrics, MFE/MAE, performance breakdowns | `PerformanceSnapshot`, reports |
| Research Lab Agent | No, offline only | propose tests, factors, parameter ranges | experiment tickets, never orders |

### 4.3 Event Contracts

Use typed objects. These can be Pydantic models early, then optimized if needed.

```python
class SignalCandidate:
    signal_id: str
    created_at: datetime
    symbol: str
    venue: str
    timeframe: str
    strategy_id: str
    side: Literal["long", "short"]
    horizon_seconds: int
    base_confidence: float
    evidence: dict
    invalidation_price: Decimal
    target_prices: list[Decimal]
    expires_at: datetime
```

```python
class PortfolioIntent:
    signal_id: str
    account_id: str
    symbol: str
    side: Literal["long", "short"]
    entry_type: Literal["limit", "market", "post_only_limit"]
    entry_price: Decimal | None
    stop_price: Decimal
    target_prices: list[Decimal]
    risk_amount: Decimal
    notional: Decimal
    leverage: Decimal
    max_slippage_bps: Decimal
    time_in_force: str
```

```python
class RiskDecision:
    signal_id: str
    decision: Literal["approve", "reject", "mutate", "halt"]
    reason_codes: list[str]
    approved_intent: PortfolioIntent | None
    risk_snapshot: dict
```

### 4.4 Hot Path

The live trading path should look like this:

```text
Exchange/Web data
  -> Data Agent normalizes and validates
  -> Feature Agent computes deterministic features
  -> Regime Agent classifies market state
  -> Signal Agents emit candidates
  -> Coordinator arbitrates simultaneous candidates
  -> Research Agent cached state is attached
  -> Portfolio Agent sizes each surviving candidate
  -> Risk Agent approves/mutates/rejects
  -> Execution Agent places and manages orders
  -> Analytics Agent logs every event
```

The Research Agent does not block the hot path. It updates cached state every N minutes or on event triggers.

### 4.5 Cold Path

```text
News/API/RSS/social/macro feeds
  -> Research Agent collects evidence
  -> LLM classifies event type, severity, affected assets, confidence
  -> deterministic validator checks schema, source age, contradictions
  -> Matrix stores `ResearchState`
  -> hot path reads latest valid state
```

If Research Agent fails:

- Do not stop the system automatically.
- Mark research state stale.
- Raise thresholds or block news-sensitive strategies based on deterministic policy.

## 5. Deterministic Agent Algorithms To Implement

### 5.1 Data Agent

What it should do:

- Maintain warm WebSocket connections to primary and backup exchanges.
- Normalize symbols, timestamps, prices, quantities, funding intervals, precision.
- Build candles locally from trades where needed.
- Store raw events and derived candles.
- Detect stale data, gaps, duplicates, out-of-order messages, exchange status events.
- Reconcile live stream candles with REST backfill.

Algorithms and techniques:

- Sequence handling:
  - Use exchange update IDs where available.
  - Detect skipped sequence numbers.
  - Backfill from REST after reconnect.
- Candle builder:
  - For each trade: bucket by floor(timestamp / timeframe).
  - Update OHLCV.
  - Emit candle only after close plus small exchange-latency grace period.
- Stale feed:
  - `now - last_event_time > threshold`.
  - Separate thresholds for trades, candles, book, funding, OI.
- Normalization:
  - `Decimal` for all prices/quantities.
  - Store exchange precision rules per instrument.
- Warm failover:
  - Primary and backup feeds run at the same time.
  - Failover flips active feed only after quality checks.
- Clock:
  - NTP-synced server clock.
  - Store both exchange timestamp and receive timestamp.

Data storage:

- Redis:
  - latest price/book/features/risk status
  - short TTL hot state
- TimescaleDB or ClickHouse:
  - candles, trades, funding, OI, feature snapshots
- Postgres:
  - orders, trades, decisions, configs, reports

### 5.2 Feature Agent

What it should compute:

- RSI 6/14/24 using Wilder smoothing.
- MACD 12/26/9 using EMA.
- EMA 20/50/200 and slope.
- Bollinger Bands 20, 2 standard deviations, plus `%B` and bandwidth percentile.
- ATR 14 and ATR percentile.
- ADX for trend strength.
- Supertrend using ATR bands.
- VWAP/session VWAP.
- Volume ratio and volume z-score.
- CVD from trade aggressor side.
- Order flow imbalance.
- Funding z-score.
- OI delta and OI z-score.
- Cross-exchange spread.
- Correlation matrix.

Specific algorithms:

- RSI:
  - `avg_gain_t = (avg_gain_{t-1} * (n-1) + gain_t) / n`
  - `avg_loss_t = (avg_loss_{t-1} * (n-1) + loss_t) / n`
  - `RSI = 100 - 100/(1 + avg_gain/avg_loss)`
- MACD:
  - `EMA_fast - EMA_slow`
  - signal line = EMA of MACD
  - histogram = MACD - signal
  - shrinking red histogram = sell momentum decelerating
- Bollinger:
  - middle = rolling SMA
  - upper/lower = SMA +/- k * rolling std
  - `%B = (close - lower) / (upper - lower)`
  - bandwidth = `(upper - lower) / middle`
- ATR:
  - true range = max(high-low, abs(high-prev_close), abs(low-prev_close))
  - Wilder moving average.
- ADX:
  - compute +DM, -DM, smoothed TR, +DI, -DI, DX, ADX.
- CVD:
  - classify trade side from exchange-provided taker side if available.
  - if not available, use tick rule as fallback:
    - uptick trade = buyer aggressive
    - downtick trade = seller aggressive
    - same price inherits previous sign.
- Order flow imbalance:
  - level-1 OFI uses changes in best bid/ask price and size.
  - more robust version sums across top N levels with distance decay.
- Funding z-score:
  - `(current_funding - rolling_mean_30d) / rolling_std_30d`
- OI-price matrix:
  - price up + OI up = new longs/fuel
  - price up + OI down = short covering/exhaustion
  - price down + OI up = new shorts/fuel
  - price down + OI down = long liquidation/capitulation
- Correlation:
  - rolling Pearson correlation on returns.
  - EWMA correlation for faster crash-regime adaptation.

### 5.3 Regime Agent

Purpose:

The system must know when mean reversion is appropriate and when it is dangerous.

Deterministic regime model:

```text
Trending up:
  EMA200 slope > threshold
  price above EMA200
  Supertrend green
  ADX > 25
  swing structure HH/HL

Trending down:
  EMA200 slope < -threshold
  price below EMA200
  Supertrend red
  ADX > 25
  swing structure LH/LL

Ranging:
  EMA200 flat
  ADX < 20
  Bollinger bandwidth normal/contracting
  price mean-crosses frequently

Breakout pending:
  Bollinger bandwidth percentile < 15
  ATR percentile < 20
  range compression for N candles

High volatility / crisis:
  ATR percentile > 90
  realized volatility spike
  spread widens
  market-wide correlation jumps
```

Algorithms:

- EMA slope:
  - Linear regression slope over last N EMA values.
  - Normalize by price or ATR.
- Swing structure:
  - Fractal pivots:
    - swing high if high[i] is max over i-k..i+k.
    - swing low if low[i] is min over i-k..i+k.
  - ZigZag alternative:
    - pivot only if price reverses by X ATR or X percent.
- Choppiness:
  - Choppiness Index or ratio of net movement to total path length.
- Volatility percentile:
  - rank current ATR/realized vol over rolling 90d window.

### 5.4 Structure And Liquidity Agent

This is where your newer Finding Alpha framework is stronger than the original RSI-only bot.

What it should compute:

- Swing highs/lows.
- Support/resistance zones.
- Equal highs/equal lows.
- Session high/low.
- Previous day/week high/low.
- Liquidity sweep detection.
- Close-back-inside confirmation.
- Distance to next liquidity pool.
- Liquidation cluster proxy.

Algorithms:

- Zone clustering:
  - Generate candidate pivot prices.
  - Cluster nearby prices with DBSCAN or ATR-scaled bins.
  - Zone width = max(tick_size * N, ATR * zone_width_factor).
  - Score zone by touches, recency, volume at level, higher-timeframe overlap.
- Equal highs/lows:
  - pivots within `epsilon = max(0.1 * ATR, tick_size * N)`.
  - count >= 2.
- Liquidity sweep:
  - long setup:
    - price trades below support/session low
    - candle closes back above level
    - sweep candle has elevated volume
    - CVD divergence or sell exhaustion
  - short setup mirrors above resistance.
- Liquidation cluster proxy:
  - True liquidation maps need provider data.
  - Approximate cluster levels from price history and OI:
    - estimate leveraged long liquidation levels below recent entries:
      - 50x: ~2 percent below
      - 20x: ~5 percent below
      - 10x: ~10 percent below
    - weight by OI changes near entry zones.
  - Treat this as low-confidence unless validated against Coinglass/Hyblock.

### 5.5 Signal Agents

Do not have one giant strategy. Use multiple deterministic signal modules behind one contract.

#### Mean Reversion Signal

Inputs:

- RSI fast/slow
- Bollinger %B
- MACD histogram direction
- ATR percentile
- volume z-score
- funding z-score
- OI delta
- regime
- session threshold

Long candidate:

```text
RSI_fast < threshold
%B <= 0.05
MACD histogram negative but rising
volume_z > threshold
funding_z <= 0 or extreme negative preferred
OI falling during drop preferred
regime != strong trending down unless setup is at major support
```

Reject if:

- structural crypto crisis active
- ADX very high against trade
- spread abnormal
- funding/OI indicates trend continuation against signal
- no net expected edge after fees

#### Liquidity Sweep Signal

Inputs:

- key levels
- candle wick/close
- CVD divergence
- volume spike
- OI/funding context
- liquidation clusters

Long candidate:

```text
price sweeps below strong support / session low
closes back above level
CVD does not confirm new low or sell CVD weakens
volume spike then fades
short crowding or long capitulation present
target is opposing liquidity pool
```

#### Short Squeeze / Long Squeeze Signal

Long squeeze-up setup:

```text
funding deeply negative
OI elevated or rising into support
RSI oversold
price at structural support
MACD selling momentum shrinking
liquidation clusters above
```

This is one of the strongest crypto-native deterministic ideas in your docs.

#### Trend Follow Pullback Signal

Long:

```text
higher timeframe uptrend
Supertrend green
ADX > 25
price pulls back to EMA20/50 or VWAP
RSI resets to 40-50, not extreme oversold
MACD resumes positive growth
volume confirms bounce
```

This prevents the system from forcing mean reversion in trends.

### 5.6 Portfolio/Position Agent

Use account-tier policy, but make it explicit and versioned.

Core formula:

```text
risk_amount = account_equity * risk_fraction
stop_distance = abs(entry - stop)
quantity = risk_amount / stop_distance
notional = quantity * entry
leverage = notional / margin_allocated
```

Use `Decimal` and exchange precision rounding:

```text
quantity = floor_to_step(quantity, lot_size)
price = round_to_tick(price, tick_size)
notional >= exchange_min_notional
```

Risk fraction should be policy-driven:

| Mode | Account | Base risk | Daily max loss | Notes |
|---|---:|---:|---:|---|
| Paper | any | simulated | simulated | validate mechanics |
| Micro-live | 100-500 | 0.25-0.50 percent | 1-2 percent | test exchange execution |
| Aggressive small | 500-2,000 | 0.50-1.00 percent | 3 percent | only after edge proven |
| Growth | 2,000-10,000 | 0.25-0.75 percent | 2 percent | reduce leverage |
| Preservation | 10,000+ | 0.10-0.50 percent | 1 percent | prioritize survival |

I would not start with 1-2 percent live risk. Use 1-2 percent only in simulated stress tests or after enough live evidence.

Sizing additions:

- Volatility targeting:
  - reduce risk when ATR percentile is high.
  - reduce risk when spread/volatility is abnormal.
- Confidence-to-risk mapping:
  - confidence changes whether the trade is allowed or slightly scales risk.
  - do not let confidence override max risk.
- DCA:
  - total planned risk across all layers must be capped before layer 1.
  - every layer must have independent signal validation.

### 5.7 Risk Agent

The Risk Agent is deterministic and has absolute veto.

Pre-trade checks:

- circuit breaker status
- daily PnL
- current drawdown from peak
- open risk
- position count
- symbol exposure
- direction exposure
- correlation exposure
- event-risk window
- exchange health
- data staleness
- fee/slippage expected edge
- leverage cap
- stop exists and is exchange-supported
- min reward:risk
- max holding time

Algorithms:

- Portfolio heat:
  - `sum(open_trade_risk_amount) / equity`
- Correlation blocking:
  - compute rolling/EWMA correlation on returns.
  - if `corr(existing_symbol, new_symbol) > threshold` and same direction, block or reduce.
- Drawdown:
  - `drawdown = equity / rolling_peak_equity - 1`
- Loss streak:
  - consecutive net losing closed trades.
  - optionally separate by strategy/session/symbol.
- Daily PnL gate:
  - based on realized + mark-to-market open PnL.
- CVaR stress:
  - simulate shock scenarios:
    - BTC -3 percent, ETH/SOL beta-adjusted
    - spreads widen 3x
    - stop slippage 2-5x normal
  - block if stressed loss breaches limits.
- Expected net edge:
  - `gross_target_bps - round_trip_fees_bps - expected_slippage_bps - funding_cost_bps`
  - require minimum margin of safety.

Risk decision should be explainable:

```text
reject:
  reason_codes = ["CORRELATED_EXPOSURE", "EVENT_WINDOW_CPI", "EXPECTED_EDGE_BELOW_FEES"]
```

### 5.8 Execution Agent

The Execution Agent does not decide direction. It manages order mechanics.

Core responsibilities:

- Convert approved intent into exchange-specific order calls.
- Use client order IDs for idempotency.
- Place protective stop immediately after entry logic allows it.
- Prefer bracket/OCO if exchange supports it.
- Reconcile all orders/fills/positions with exchange.
- Handle partial fills.
- Cancel stale orders.
- Switch to emergency exit mode when required.
- Rate-limit API calls.
- Persist every request/response.

Order state machine:

```text
created
  -> submitted
  -> acknowledged
  -> open
  -> partially_filled
  -> filled
  -> cancel_requested
  -> canceled
  -> rejected
  -> expired
  -> error_reconcile
```

Execution algorithms:

- Post-only limit entry:
  - avoid taker fee if strategy permits waiting.
  - cancel/reprice after timeout.
- Market emergency exit:
  - only for risk-off/stop-failed/exchange-health situations.
- Slippage guard:
  - reject marketable orders if spread too wide.
- Rate limiting:
  - token bucket per endpoint category.
  - weighted by exchange endpoint cost.
- Reconciliation loop:
  - poll open orders and positions.
  - compare local state.
  - exchange wins.
- Idempotency:
  - deterministic `client_order_id = strategy_id + signal_id + leg`.
  - on retry, query by client ID before submitting again.

## 6. Non-Deterministic Agent Design

### 6.1 Research Agent

LLM role:

- Classify news and events.
- Summarize macro conditions.
- Produce structured risk multipliers.
- Distinguish:
  - temporary external shock
  - structural crypto damage
  - exchange-specific risk
  - regulatory uncertainty
  - scheduled macro event
  - irrelevant noise

It should not:

- Calculate indicators.
- Size positions.
- Place orders.
- Override risk.
- Be called inline during order placement.

Recommended pipeline:

```text
News/data fetchers
  -> deduplicate articles
  -> entity extraction
  -> relevance filter
  -> LLM structured classification
  -> deterministic schema validation
  -> cache ResearchState in Redis/Postgres
  -> hot path reads cached result
```

Structured output:

```json
{
  "as_of": "2026-05-10T00:00:00Z",
  "assets": ["BTC", "ETH"],
  "event_type": "macro_shock",
  "severity": 0.7,
  "directional_bias": -0.4,
  "confidence_multiplier": 0.6,
  "trade_policy": "raise_thresholds",
  "expires_at": "2026-05-10T00:15:00Z",
  "reason_codes": ["unexpected_geopolitical_escalation"],
  "sources": ["..."]
}
```

Deterministic validation:

- Reject stale output.
- Reject missing source links.
- Reject malformed JSON.
- Clamp multiplier to allowed range.
- Require lower confidence if sources disagree.
- Require hard block for keywords/events:
  - exchange insolvency
  - withdrawals frozen
  - stablecoin depeg
  - major exchange hack

### 6.2 Shadow Mode

Before Research Agent can affect trades:

- Run it in shadow mode for 4-8 weeks.
- For every signal, log:
  - cached research state
  - multiplier it would have applied
  - whether it would block/boost
  - actual trade outcome
- Evaluate:
  - Did blocked trades lose more?
  - Did boosted trades win more?
  - Did crisis detection reduce drawdown?
  - Did stale news cause false blocks?

Only then allow it to adjust thresholds.

### 6.3 Research Lab Agent

This is the best place for LLM creativity.

Allowed:

- Propose new features.
- Generate experiment plans.
- Write SQL queries.
- Compare backtest outputs.
- Summarize why a strategy decayed.
- Suggest parameter ranges.

Not allowed:

- Change production parameters automatically.
- Execute live orders.
- Disable risk checks.

## 7. Backtesting Integration

### 7.1 The Core Rule

Backtesting must run the same agent contracts as live trading.

Bad model:

```text
notebook strategy backtest
  -> separate live bot implementation
  -> divergence
  -> "worked in backtest, failed live"
```

Good model:

```text
same DataEvent/FeatureSnapshot/SignalCandidate/PortfolioIntent/RiskDecision/ExecutionReport contracts
  -> historical replay mode
  -> paper mode
  -> live mode
```

### 7.2 Recommended Backtest Layers

Use three levels:

#### Level 1: Vectorized Research Backtest

Purpose:

- Fast parameter sweeps.
- Feature ablation.
- Sensitivity surfaces.

Tools:

- pandas/NumPy
- vectorbt
- Polars optional

Use for:

- RSI threshold ranges.
- ATR multiplier ranges.
- session thresholds.
- volume/funding/OI z-score thresholds.
- score weighting.

Do not trust for final live readiness.

#### Level 2: Event-Driven Strategy Backtest

Purpose:

- Run exact live agent contracts.
- Model order lifecycle, fees, slippage, funding, stops, partial fills.
- Validate portfolio risk gates and correlated signal arbitration.

Candidates:

- NautilusTrader if adopted.
- Custom event-driven simulator if not.

Required models:

- fee model:
  - maker/taker per exchange
  - VIP tier assumptions
- slippage model:
  - spread-based
  - volatility-based
  - order-book depth if available
- funding:
  - 8-hour payments for held perp positions
- latency:
  - signal-to-order delay
  - exchange ack delay
  - cancel/replace delay
- fill model:
  - market order: fill through book or worst of OHLC proxy
  - limit order: fill only if price trades through, with queue pessimism
  - partial fills if size exceeds depth threshold
- risk gates:
  - daily loss, kill switch, correlation, max positions, event windows
- data quality:
  - stale/missing candles
  - exchange downtime windows if known

#### Level 3: Paper Trading / Live Replay

Purpose:

- Prove real-time mechanics.
- Validate exchange adapters.
- Validate reconciliation.
- Validate alerts and dashboard.

Metrics:

- no unprotected positions
- no duplicate orders
- no rejected orders from precision errors
- expected vs actual fill price
- slippage distribution
- missed fill rate
- cancel failure rate
- stop placement latency
- exchange reconciliation drift

### 7.3 Walk-Forward Validation

Do not optimize on all data and report the result.

Use:

```text
train window: 90 days
validation window: 30 days
test window: 30 days
roll forward by 30 days
repeat
```

For each window:

- choose parameters on train/validation only
- freeze them
- evaluate on test
- aggregate test metrics

Use purging/embargo around labels where future windows can leak into features.

### 7.4 Parameter Sensitivity

Your session notes already describe this correctly. Expand it:

```text
rsi_oversold: [18, 20, 22, 25, 28, 30]
atr_stop_mult: [1.0, 1.25, 1.5, 1.75, 2.0]
volume_z: [0.5, 1.0, 1.5, 2.0]
funding_z: [-2, -1, 0]
min_score: [3, 4, 5]
session_threshold_delta: [-10, 0, +10]
```

Look for:

- wide performance plateau
- enough trades
- stable performance across market regimes
- not just one lucky month
- not just one symbol

Reject:

- narrow spikes
- low trade count
- parameter sets that only work before fees
- strategies that rely on one crisis event for all returns

### 7.5 Metrics

Backtest metrics:

- net return after fees/funding/slippage
- max drawdown
- Calmar ratio
- Sharpe and Sortino
- profit factor
- expectancy per trade
- win rate
- average R
- median R
- MFE/MAE distribution
- time in trade
- exposure time
- trade count
- worst day/week
- largest gap/slippage loss
- liquidation risk proximity

Validation gates:

- minimum 500 historical signal occurrences for broad parameter claims
- minimum 150 completed paper trades before real capital
- out-of-sample profit factor > 1.2-1.3
- drawdown below predetermined limit
- parameter plateau confirmed
- no hidden dependency on one exchange or one symbol

### 7.6 Backtesting News/LLM

The hard part: you cannot let today's LLM knowledge leak into old decisions.

Rules:

- Use archived historical news as of the decision timestamp.
- Store article publish time, ingest time, and source.
- During backtest, only expose articles available before the simulated decision time.
- Cache LLM classifications by article/event/time so runs are reproducible.
- Prefer deterministic event labels for known historical events once manually reviewed.
- Treat LLM backtest as advisory until shadow-mode evidence exists.

### 7.7 Backtest Data Schema

Minimum tables:

```text
market_candles(symbol, venue, timeframe, open_time, close_time, open, high, low, close, volume)
trades(symbol, venue, exchange_ts, receive_ts, price, quantity, aggressor_side)
funding_rates(symbol, venue, ts, rate, next_funding_ts)
open_interest(symbol, venue, ts, value)
features(symbol, venue, timeframe, ts, feature_name, value, version)
signals(signal_id, ts, strategy_id, symbol, timeframe, side, confidence, evidence_json, version)
risk_decisions(signal_id, ts, decision, reason_codes, snapshot_json)
orders(order_id, signal_id, venue, client_order_id, type, status, price, quantity, ts)
fills(fill_id, order_id, venue, price, quantity, fee, liquidity_flag, ts)
trades_closed(trade_id, signal_id, entry_ts, exit_ts, gross_pnl, fees, funding, net_pnl, r_multiple)
```

## 8. Proposed Build Sequence

### Phase 0: Security And Config

- Rotate/remove plaintext key from `finding alpha.txt` if real.
- Add `.env.example`, `.gitignore`, and secret management policy.
- No API key should be in Markdown or repo history.

### Phase 1: Deterministic Event Contracts

Deliverables:

- Pydantic/domain models:
  - MarketEvent
  - CandleEvent
  - FeatureSnapshot
  - RegimeState
  - SignalCandidate
  - ResearchState
  - PortfolioIntent
  - RiskDecision
  - OrderIntent
  - ExecutionReport
- JSON serialization tests.
- Versioned schemas.

### Phase 2: Data + Feature Backtest Dataset

Deliverables:

- Historical candles for BTC/ETH/SOL/XRP from Bybit/Binance/MEXC where available.
- Funding/OI history.
- Feature computation pipeline.
- Feature parity tests against exchange/chart reference.

### Phase 3: Vectorized Research Harness

Deliverables:

- Fast parameter sweep.
- Sensitivity heatmaps.
- No-lookahead checks.
- Fee/funding/slippage approximations.
- First reject/keep decision on the initial strategy modules.

### Phase 4: Event-Driven Simulator

Deliverables:

- Historical replay mode.
- Portfolio state.
- Risk Agent active.
- Order/fill model.
- Daily gates and kill switches.
- Exact same signal/risk/portfolio code used in backtest and paper mode.

### Phase 5: Paper Trading

Deliverables:

- Live data ingestion.
- Paper execution.
- Research Agent shadow mode.
- Dashboard/API.
- Alerts.
- Exchange precision validation.

### Phase 6: Micro-Live Execution

Deliverables:

- Tiny capital.
- Bybit or chosen primary exchange.
- Exchange-side stops verified.
- No DCA at first.
- One timeframe/symbol at first.
- Live replay comparison between expected and actual fills.

## 9. Final Recommended Architecture

```text
                          CEO / Dashboard
                               |
                          API Gateway
                               |
                         Matrix State
          Redis hot state + Postgres decisions + TSDB market data
                               |
    ----------------------------------------------------------------
    |              |             |             |                  |
 Data Agent   Feature Agent  Research Agent  Analytics Agent  Scheduler
    |              |             |             |                  |
    |              v             v             v                  v
    |        FeatureSnapshot  ResearchState  Reports       Backfills/health
    |              |
    v              v
 MarketEvent -> Regime Agent -> Signal Agents -> Coordinator
                                      |
                                      v
                              Portfolio Agent
                                      |
                                      v
                                Risk Agent
                                      |
                             approve / mutate / reject
                                      |
                                      v
                              Execution Agent
                                      |
                                      v
                           Exchange Adapters
                         Bybit / MEXC / Binance
```

Backtest mode replaces Exchange Adapters with historical replay and simulated fills. Everything above the exchange boundary should stay the same.

## 10. Concrete Decisions I Would Make Now

1. Replace the original "7 agents all autonomous" framing with "typed deterministic engines plus LLM research services."
2. Make backtesting the center of the system, not Phase 2 paperwork.
3. Build around these contracts:
   - `SignalCandidate`
   - `PortfolioIntent`
   - `RiskDecision`
   - `OrderIntent`
   - `ExecutionReport`
4. Use Redis Streams if agents run as independent services; use an in-process event bus first if speed of development matters.
5. Use TimescaleDB or ClickHouse for market data, Postgres for decisions/orders/trades, Redis for live state.
6. Use LLMs only in cached cold-path modules until shadow-mode results prove value.
7. Start with 15m/1h strategies before 5m scalps because fees and fill assumptions matter too much on 5m.
8. Study NautilusTrader first before writing your own execution/backtest engine.
9. Study Freqtrade for crypto operational details, not for architecture.
10. Study TradingAgents for LLM role decomposition, not for live execution.
11. Treat RD-Agent/Qlib as inspiration for an offline research lab, not trading runtime.
12. Do not use RL for live decisions until deterministic strategies have a large validated dataset.

## 11. Implementation Stack And API Connections

This section is the practical starting point for building. APIs change, so verify each endpoint against official docs before coding.

### 11.1 Recommended Python Libraries By Layer

| Layer | Libraries | Why |
|---|---|---|
| Typed contracts | `pydantic`, `typing`, `decimal`, `uuid`, `orjson` | strict schemas, JSON serialization, safe money math |
| Async runtime | `asyncio`, `aiohttp`, `websockets`, `tenacity` | REST/WS clients, retries, concurrent ingestion |
| Exchange SDKs | `pybit` for Bybit, raw `aiohttp` for MEXC contract API, official Binance/OKX SDKs or raw REST/WS | avoid over-abstracting execution semantics |
| Dataframes | `pandas`, `polars`, `numpy` | research, feature generation, backtests |
| Indicators | `pandas-ta` or `ta`, plus custom implementations for critical indicators | quick start, but own the formulas used live |
| Fast loops | `numba` optional | parameter sweeps, vectorized research |
| Backtesting | `nautilus_trader`, `vectorbt`, custom event simulator | event parity plus fast sweeps |
| Databases | `redis`, `asyncpg`, `psycopg`, TimescaleDB/Postgres, ClickHouse optional | hot state, durable decisions, time-series storage |
| ML/research | `scikit-learn`, `xgboost`, `statsmodels`, `optuna` | baselines, tree models, drift tests, parameter search |
| LLM/RAG | provider SDKs, `pydantic`, `chromadb` or Postgres `pgvector` | structured news classification and memory |
| Observability | `structlog`, `prometheus-client`, OpenTelemetry optional | audit logs, health metrics, production debugging |
| Testing | `pytest`, `hypothesis`, `freezegun`, `respx` | deterministic unit/property/API tests |

Avoid making ccxt the primary live execution layer. It can be useful for data download or prototyping, but the execution path should preserve venue-specific behavior, precision, order flags, and error codes.

### 11.2 Exchange API Connection Pattern

Use a thin adapter per venue. The rest of the system should never call exchange SDKs directly.

```text
Finding Alpha domain objects
  -> ExchangeAdapter interface
  -> BybitAdapter / MexcAdapter / BinanceDataAdapter / OkxDataAdapter
  -> official REST/WebSocket APIs
```

The adapter should expose:

```python
class ExchangeAdapter:
    async def stream_trades(self, symbol: str): ...
    async def stream_order_book(self, symbol: str, depth: int): ...
    async def stream_klines(self, symbol: str, interval: str): ...
    async def fetch_klines(self, symbol: str, interval: str, start_ms: int, end_ms: int): ...
    async def fetch_funding(self, symbol: str): ...
    async def fetch_open_interest(self, symbol: str): ...
    async def place_order(self, order: OrderIntent): ...
    async def cancel_order(self, client_order_id: str): ...
    async def fetch_open_orders(self): ...
    async def fetch_positions(self): ...
    async def fetch_balances(self): ...
```

### 11.3 Bybit Connection

Official docs show Bybit V5 REST klines at `GET /v5/market/kline`, with `category`, `symbol`, `interval`, `start`, `end`, and `limit` parameters. The official examples use `pybit.unified_trading.HTTP`. WebSocket kline topics use `kline.{interval}.{symbol}` and expose a `confirm` boolean for candle close state. Order creation is through the V5 order endpoint and supports limit and market orders, with market orders protected by Bybit's slippage/IOC limit conversion.

Use Bybit for:

- primary live execution candidate
- historical klines
- WebSocket klines/trades/order book
- funding/open interest
- account, position, order, fill reconciliation

Adapter details:

- Use `pybit.unified_trading.WebSocket` for quick initial WS implementation.
- Consider raw WebSocket later if you need tighter reconnect/heartbeat control.
- Only trade USDT perps after testing precision and stop order semantics in testnet.
- Store Bybit's `orderLinkId` as your idempotency key if supported for the chosen product.

Sources:

- [Bybit REST kline](https://bybit-exchange.github.io/docs/v5/market/kline)
- [Bybit WebSocket kline](https://bybit-exchange.github.io/docs/v5/websocket/public/kline)
- [Bybit create order](https://bybit-exchange.github.io/docs/v5/order/create-order)
- [Bybit open interest](https://bybit-exchange.github.io/docs/v5/market/open-interest)

### 11.4 MEXC Contract Connection

MEXC contract docs show the base URL `https://contract.mexc.com`, public market endpoints that do not require authentication, and private endpoints signed with HMAC SHA256 using access key, request time, and request parameters. The docs also show the WebSocket base update to `wss://contract.mexc.com/edge` and market endpoints for contract detail, depth, fair/index price, funding rate, k-line data, transaction data, and funding history.

Use MEXC for:

- execution only after legal/account/API checks
- market data cross-checks
- backup venue or secondary venue if Bybit is primary

Adapter details:

- Build raw REST client with `aiohttp`.
- Implement signer directly and test against read-only private endpoints first.
- Pull `contract/detail` on startup and store:
  - tick size
  - volume unit
  - min/max volume
  - maker/taker fee
  - leverage limits
  - `apiAllowed`
  - price/quantity precision
- The docs note some order endpoints as "under maintenance" in the contract docs snapshot; verify current production trading endpoint status before planning live execution.

Sources:

- [MEXC Contract API](https://mexcdevelop.github.io/apidocs/contract_v1_en/)
- [MEXC API overview](https://www.mexc.com/mexc-api)

### 11.5 Binance Futures Data Connection

Binance USD-M futures docs provide:

- klines at `GET /fapi/v1/klines`
- open interest at `GET /fapi/v1/openInterest`
- funding history at `GET /fapi/v1/fundingRate`
- kline WebSocket stream names like `<symbol>@kline_<interval>`
- kline stream updates at high frequency and includes whether the kline is closed

Use Binance for:

- high-liquidity reference price
- volume confirmation
- cross-exchange funding/OI comparison
- CVD and order-book depth reference

Do not need Binance execution early unless you choose it as a trading venue.

Sources:

- [Binance USD-M kline REST](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data)
- [Binance USD-M open interest](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest)
- [Binance USD-M funding history](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)
- [Binance USD-M kline WebSocket](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Kline-Candlestick-Streams)

### 11.6 OKX Data Connection

OKX API v5 supports REST and WebSocket APIs for market data, public data, trading account, and trading statistics. Public data includes instruments, funding rate, open interest, mark price, index/mark candlesticks, liquidation orders, and economic calendar channels. Market-data docs also include tickers, history candles, and candlestick WebSocket channels. OKX region/domain rules matter, especially for US/AU/EU registrations.

Use OKX for:

- regional Asia liquidity confirmation
- funding/OI cross-check
- options/derivatives context if later needed
- economic calendar channel if available for your account/domain

Sources:

- [OKX API v5 docs](https://www.okx.com/docs-v5/en)
- [OKX US/AU API docs](https://app.okx.com/docs-v5/en/)
- [OKX EEA API docs](https://my.okx.com/docs-v5/en/)

### 11.7 Data Provider Priority

Minimum viable data:

1. Bybit or chosen execution venue:
   - klines, trades, order book, funding, OI, positions, orders, fills
2. Binance:
   - klines, trades, order book, funding, OI, liquidations if used
3. OKX:
   - funding/OI/order-book confirmation
4. MEXC:
   - if execution or cross-check venue

High-value paid/free additions:

- Coinglass:
  - liquidation heatmaps, aggregate OI, funding, long/short ratios
- Coinalyze:
  - redundant aggregate derivatives data
- Velo:
  - options/volatility/funding analytics
- Glassnode/CryptoQuant:
  - exchange flows, whale movement, stablecoin liquidity
- CryptoPanic/NewsData/RSS:
  - Research Agent input
- TradingEconomics/FMP/ForexFactory:
  - macro calendar

### 11.8 How The Agents Connect To APIs

```text
Data Agent:
  REST backfill + WebSocket streams
  writes raw events and normalized latest state

Feature Agent:
  reads normalized candles/trades/book/funding/OI
  computes indicators and features
  does not call exchange APIs

Signal Agents:
  read FeatureSnapshot + RegimeState + cached ResearchState
  emit SignalCandidate
  do not call exchange APIs

Portfolio Agent:
  reads account state snapshot from Matrix
  sizes intent
  does not call exchange APIs directly

Risk Agent:
  reads account, positions, open orders, current market, risk counters
  approves/rejects
  may request fresh exchange reconciliation before high-risk actions

Execution Agent:
  only component allowed to place/cancel/amend orders
  calls exchange private APIs
  writes ExecutionReport

Analytics Agent:
  reads all events from durable log
  computes metrics and reports
  does not influence hot-path decisions except through approved config changes
```

### 11.9 Minimum Backtesting Modules To Build

Do not start by building a giant backtester. Build these modules in order:

1. Historical data loader:
   - loads candles/funding/OI/trades into the same `MarketEvent` contracts used live.
2. Feature replay:
   - emits `FeatureSnapshot` exactly as live code would.
3. Signal replay:
   - runs signal agents over historical snapshots.
4. Portfolio simulator:
   - turns approved signals into virtual positions.
5. Execution simulator:
   - models limit/market fills, fees, slippage, stops, funding.
6. Risk simulator:
   - enforces daily loss, kill switch, max positions, correlation, portfolio heat.
7. Metrics module:
   - net PnL, R multiples, MFE/MAE, drawdown, Calmar, Sharpe, profit factor, expectancy.
8. Experiment runner:
   - parameter grid, walk-forward, output to CSV/DB.

Minimal event loop:

```python
for event in historical_replay:
    matrix.apply(event)
    features = feature_agent.on_event(event, matrix)
    regime = regime_agent.on_features(features, matrix)
    signals = signal_bus.collect(features, regime, matrix.research_state)
    intents = portfolio_agent.size(signals, matrix.account_state)
    decisions = risk_agent.evaluate(intents, matrix.risk_state)
    reports = execution_simulator.apply(decisions, event, matrix)
    analytics_agent.record(event, features, signals, decisions, reports)
```

The same function boundaries should run in paper/live mode, with `execution_simulator` replaced by `execution_agent`.

### 11.10 First Three Strategies To Backtest

1. Liquidity sweep reversal:
   - sweep session high/low or S/R zone
   - close back inside
   - volume spike
   - CVD divergence
   - target opposite liquidity zone

2. Short/long squeeze:
   - extreme funding z-score
   - high/elevated OI
   - price at structural level
   - RSI extreme
   - MACD deceleration

3. Trend pullback:
   - higher-timeframe trend
   - ADX confirms trend
   - pullback to EMA/VWAP/Supertrend
   - RSI reset
   - volume confirmation

Do not start with 5m generic RSI scalping. It is most vulnerable to fees, slippage, and false fill assumptions.

## 12. Source Links

Primary online sources used:

- [NautilusTrader GitHub](https://github.com/nautechsystems/nautilus_trader)
- [NautilusTrader docs](https://nautilustrader.io/docs/latest/)
- [QuantConnect Algorithm Framework](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview)
- [QuantConnect LEAN GitHub](https://github.com/QuantConnect/Lean)
- [Senex Trader](https://senextrader.com/)
- [Freqtrade docs](https://www.freqtrade.io/en/stable/)
- [FreqAI docs](https://www.freqtrade.io/en/stable/freqai/)
- [Freqtrade GitHub](https://github.com/freqtrade/freqtrade)
- [Microsoft Qlib GitHub](https://github.com/microsoft/qlib)
- [Microsoft RD-Agent GitHub](https://github.com/microsoft/RD-Agent)
- [RD-Agent Quant Microsoft Research page](https://www.microsoft.com/en-us/research/publication/rd-agent-quant-a-multi-agent-framework-for-data-centric-factors-and-model-joint-optimization/)
- [FinRL GitHub](https://github.com/AI4Finance-Foundation/FinRL)
- [FinRL-X GitHub](https://github.com/AI4Finance-Foundation/FinRL-Trading)
- [TradingAgents GitHub](https://github.com/TauricResearch/TradingAgents)
- [TradingAgents project site](https://tradingagents-ai.github.io/)
- [FinGPT site](https://fingpt.io/)
- [FinGPT GitHub](https://github.com/AI4Finance-Foundation/FinGPT)
- [FinRobot GitHub](https://github.com/AI4Finance-Foundation/FinRobot)
- [AI4Finance Foundation](https://ai4finance.org/)
- [Hummingbot site](https://hummingbot.org/)
- [Hummingbot GitHub](https://github.com/hummingbot/hummingbot)
- [ABIDES GitHub](https://github.com/abides-sim/abides)
- [vectorbt docs](https://vectorbt.dev/)
- [backtesting.py](https://kernc.github.io/backtesting.py/)
- [Backtrader](https://www.backtrader.com/)
- [Jesse](https://jesse.trade/)
- [Bybit REST kline](https://bybit-exchange.github.io/docs/v5/market/kline)
- [Bybit WebSocket kline](https://bybit-exchange.github.io/docs/v5/websocket/public/kline)
- [Bybit create order](https://bybit-exchange.github.io/docs/v5/order/create-order)
- [Bybit open interest](https://bybit-exchange.github.io/docs/v5/market/open-interest)
- [MEXC Contract API](https://mexcdevelop.github.io/apidocs/contract_v1_en/)
- [MEXC API overview](https://www.mexc.com/mexc-api)
- [Binance USD-M kline REST](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data)
- [Binance USD-M open interest](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest)
- [Binance USD-M funding history](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)
- [Binance USD-M kline WebSocket](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Kline-Candlestick-Streams)
- [OKX API v5 docs](https://www.okx.com/docs-v5/en)
- [OKX US/AU API docs](https://app.okx.com/docs-v5/en/)
- [OKX EEA API docs](https://my.okx.com/docs-v5/en/)
