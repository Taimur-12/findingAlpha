# QuantFusion — AI Quant Firm Blueprint

> Complete architectural blueprint for an autonomous AI-powered quantitative trading firm.
> Built on Palantir's Ontology (connected intelligence) and Anduril's Lattice (autonomous execution).
> Last updated: March 2026

---

## 1. Vision

QuantFusion is a one-person AI hedge fund. Every role in a traditional quant trading firm is replaced by a specialised AI agent. The human (CEO) sets strategy and reviews performance. Everything else is autonomous, 24/7.

**Core thesis:** Rather than hiring people, we hire AI. Same structure, same hierarchy, same chain of command — different employees.

---# QuantFusionAI Quant Firm — Complete Blueprint

###### A one-person AI hedge fund that replaces every role in a traditional quant firm with autonomous AI agents.

###### Built on Palantir's connected intelligence and Anduril's autonomous execution.

Architecture Palantir Ontology (connected data) + Anduril Lattice (autonomous execution)

Strategy Multi-timeframe mean reversion scalping on crypto futures

Markets BTC, ETH, SOL, XRP on MEXC (primary) and Bybit (backup)

AI Agents 7 autonomous agents + 1 human CEO

Target 0.5% daily (scaling to 1%) through compounding

Risk Model 6-layer risk cage with kill switch


## 1. The Vision

###### QuantFusion operates as a fully autonomous AI-powered quant trading firm. The core thesis is simple:

###### rather than hiring people, we hire AI. Every role in a traditional hedge fund — researcher, analyst, portfolio

###### manager, risk manager, trader, data engineer, performance analyst — is replaced by a specialised AI

###### agent that works 24/7, never sleeps, never gets emotional, and never takes holidays.

###### The human (CEO) does one thing: set the strategy, define risk limits, and review weekly performance.

###### Everything else is autonomous. The AI employees work for the cost of API calls and electricity.

### The Palantir Foundation

###### Palantir's AIP platform is built on the concept of an Ontology — a unified data layer where everything is

###### connected to everything else. A soldier's position is linked to nearby threats, available weapons, rules of

###### engagement, and mission objectives. Nothing exists in isolation.

###### In QuantFusion, the Ontology works identically. The BTC price is connected to the RSI reading, which is

###### connected to the MACD histogram, which is connected to the volume spike, which is connected to the

###### funding rate, which is connected to the news sentiment, which is connected to the current session time,

###### which is connected to existing open positions, which is connected to the daily P&L; and drawdown level.

###### One giant interconnected web.

###### When any single piece of data changes, the entire web updates. A negative news article doesn't just

###### update the Research Agent — it ripples through the entire system. The Risk Agent tightens limits. The

###### Position Agent reduces size. The Math Agent adjusts confidence. Every agent reacts because everything

###### is connected.

### The Anduril Foundation

###### Anduril's Lattice platform enables autonomous execution at machine speed with intent-based commands.

###### A commander doesn't micro-manage each drone — they say 'protect this airbase' and Lattice figures out

###### how: which drones to deploy, where to position them, how to coordinate, when to escalate.

###### In QuantFusion, the CEO doesn't say 'buy 0.5 BTC at $64,200 with a stop at $63,400.' The CEO says

###### 'trade BTC mean reversion, 0.5% daily target, 3% max daily loss' and the system handles everything

###### autonomously — when to enter, how much, where to stop, when to add DCA layers, when to take profit,

###### when to stop for the day.

###### Lattice also provides mesh resilience — no single point of failure. If one drone goes down, others cover. In

###### QuantFusion, if MEXC's API dies, the system reroutes to Bybit. If a news feed dies, the system trades on

###### math alone but raises its confirmation threshold. Every position has exchange-side stop losses that survive

###### even a complete server crash.


## 2. Firm Structure — Traditional vs AI

###### Every role in a traditional quant firm maps directly to an AI agent in QuantFusion. The hierarchy, chain of

###### command, and information flow remain identical — only the employees change from human to AI.

Traditional Role AI Agent Status Core Responsibility

CEO / CIO You (Ibrahim) Human Sets strategy, risk appetite, reviews performance

Head of Research Research Agent Autonomous Reads news, sentiment scoring, confidence multiplier

Quant Analyst Math Agent Autonomous Calculates indicators, runs checklist, produces score

Portfolio Manager Position Agent Autonomous Position sizing, DCA layers, portfolio exposure

Risk Manager Risk Agent Autonomous Enforces all limits, absolute veto power, kill switch

Trader Execution Agent Autonomous Places orders via exchange API, manages stops/TPs

Data Engineer Data Agent Autonomous Real-time data feeds, WebSocket, backup sources

Performance Analyst Analytics Agent Autonomous Logs trades, tracks metrics, feeds learnings back

#### Trade flow — how a decision moves through the firm

```
Data
Agent
Feeds
```
```
Math
Agent
Scores
```
```
Research
Agent
Adjusts
```
```
Position
Agent
Sizes
```
```
Risk
Agent
Approves
```
```
Execution
Agent
Trades
```
```
Analytics
Agent
Learns
```
Every trade passes through this exact chain. No shortcuts. No agent can skip a step. Information flows right, decisions flow right,
results feed back left.


## 3. Agent Roles — Detailed Specifications

### 3.1 Data Agent — The Plumbing

###### The Data Agent is the foundation of the entire system. Without clean, real-time data, nothing else works. It

###### maintains persistent connections to exchange APIs and aggregates all incoming information into the

###### shared Ontology.

Data Source Method Update Frequency Purpose
Price (BTC/ETH/SOL/XRP) WebSocket stream Real-time (every tick) Core price data for all calculations
Volume WebSocket stream Per candle close Volume ratio calculation (vs MA20)
Order book depth REST API polling Every 5 seconds Liquidity analysis, slippage estimation
Funding rates REST API polling Every 8 hours Crowd positioning (long vs short)
Open interest REST API polling Every 1 minute Market participation tracking
News feeds API + scraping Every 5 minutes Sentiment analysis input
On-chain data API (future phase) Every 15 minutes Whale movement detection

###### Mesh resilience: If MEXC WebSocket drops, switch to Bybit within 2 seconds. If both drop, flag stale data

###### and pause trading. Never trade on old data.

### 3.2 Math Agent — The Brain

###### The Math Agent is the quantitative core. It receives raw data from the Ontology, calculates all technical

###### indicators across all timeframes, and produces a raw score for every potential trade setup.

Indicator Settings Role in System
RSI (dual) RSI 6 (fast) + RSI 24 (slow) Primary trigger — wakes up the system
MACD 12, 26, 9 (default) Momentum confirmation — are sellers/buyers fading?
EMA 200 200-period exponential MA Trend filter — bull or bear market?
Bollinger Bands 20-period, 2 std dev Volatility confirmation — price at the wall?
ATR 14-period Stop loss sizing — 1.5x ATR from entry
Volume ratio Current vs MA(20) Conviction check — crowd behind the move?

###### The Math Agent produces a raw score (0-5) from the confirmation checklist. It has no opinions — only

###### numbers. The score is then passed to the Research Agent for contextual adjustment.


### 3.3 Research Agent — The Context Layer

###### The Research Agent is the LLM-powered intelligence layer. While the Math Agent sees numbers, the

###### Research Agent reads and understands context. It's the difference between 'RSI is 14' and 'RSI is 14

###### because the SEC just sued the largest exchange.'

###### It takes the Math Agent's raw score and applies a confidence multiplier based on news context. This is

###### Bayesian updating: prior belief (math score) multiplied by new evidence (news) equals posterior belief

###### (adjusted score).

Scenario Math Score News Context Multiplier Adjusted
Normal dip 4/5 Profit-taking, ETF inflows strong 1.1x 4.4 = STRONG
Uncertain 4/5 Mixed signals, regulatory noise 0.8x 3.2 = MODERATE
Crisis 4/5 SEC sues exchange, systemic risk 0.15x 0.6 = NO TRADE

### 3.4 Position Agent — The Portfolio Manager

###### The Position Agent decides HOW MUCH to trade. It never decides what or when — that comes from Math

###### and Research. It takes the approved signal and calculates the optimal position size, manages DCA layers,

###### and considers the portfolio as a whole.

###### Position sizing formula: risk_amount = account_balance x 0.25% (per-trade cap). stop_distance = 1.5 x

###### ATR. position_size = risk_amount / stop_distance.

###### DCA management: Layer 1 at RSI threshold (1/3 position). Layer 2 if RSI drops 5 more points (add 1/3).

###### Layer 3 at extreme oversold (final 1/3). Each layer passes its own checklist independently.

###### Portfolio awareness: Checks existing positions and exposure. If already 2/3 of risk budget is deployed,

###### the third position gets reduced size. Never overcommits.

### 3.5 Risk Agent — The Guardian

###### The Risk Agent is the most important agent in the system because its job is keeping the firm alive. It has

###### absolute veto power — it can override every other agent and shut down all trading instantly. It is the only

###### agent whose decisions cannot be overridden.

Rule Limit What happens when triggered
Per-trade risk cap 0.25% of account Position sized down — never exceeded
Max concurrent positions 3 trades open 4th trade blocked regardless of score
Correlation check > 0.85 blocked Can't long BTC + ETH simultaneously
Losing streak breaker 3 consecutive losses Pause trading for 30 minutes
Session streak breaker 5 consecutive losses Stop trading for the entire session
Daily loss limit -1.5% of account ALL trading stops until tomorrow
Daily profit target +0.5% (scaling to 1%) ALL trading stops — lock the win
Max drawdown kill switch -8% from account peak ALL trading stops. CEO must review and restart.


Session thresholds Varies by session Asia: 5/5 needed. London: 4/5. Prime: 3/5.


### 3.6 Execution Agent — The Trader

###### The Execution Agent is the hands of the firm. It doesn't think, analyse, or decide — it executes what the

###### other agents have approved. It connects to exchange APIs and places orders with precision.

Function Details
Order placement Limit orders at specified entry price. Never market orders (avoid slippage).
Stop loss Set ON THE EXCHANGE — survives server crash. Always 1.5x ATR from entry.
Take profit Set when RSI target is reached (45-50 zone = mean reversion complete).
DCA management Monitors for layer 2/3 entries. Adjusts stops on all layers when adding.
Order monitoring Tracks fill status. If limit order not filled in 5 minutes, cancel and reassess.
Exchange failover If MEXC API returns errors 3x, switch to Bybit. Anduril mesh principle.

### 3.7 Analytics Agent — The Learning Loop

###### The Analytics Agent closes the feedback loop. After every trade, it logs every detail and calculates

###### performance metrics. Over time, it learns which indicators are most predictive and adjusts weights. This is

###### the Palantir Ontology feedback: decisions lead to outcomes, outcomes lead to learning, learning leads to

###### better decisions.

Metric What it tracks Target
Win rate Winning trades / total trades Above 60%
Expectancy (win_rate x avg_win) - (loss_rate x avg_loss) Positive always
Sharpe ratio Return / risk (annualised) Above 2.
Profit factor Total profit / total loss Above 1.
Best session Which session produces highest returns Optimise allocation
Best indicator Which confirmation is most predictive Adjust weights
Avg hold time How long positions stay open Optimise exits
Max drawdown Worst peak-to-trough decline Below -8%


## 4. Strategy — Multi-Timeframe Mean

## Reversion

###### The system watches three timeframes simultaneously and catches mean reversion opportunities at

###### different scales. Higher timeframes always override lower ones.

```
Timeframe Role RSI Trigger Hold Time Trades/Day Profit/Trade
5-minute Sniper scalps < 25 or > 75 5-30 min 5-10 0.05-0.1%
15-minute Workhorse < 28 or > 72 15 min-2 hrs 3-6 0.1-0.2%
1-hour Big catch < 25 or > 75 1-8 hrs 0-2 0.2-0.5%
```
#### Session-aware thresholds (Melbourne time)

Session Melbourne Time Min Score Mode

Asia 11am - 7pm 5/5 Observe only

London open 7pm - 12am 4/5 Alert

London-NY overlap 12am - 4am 3/5 PRIME ZONE

NY solo 4am - 9am 3/5 Active

Wind-down 9am - 11am 4/5 Review & adjust

#### Compounding roadmap

Phase Period Daily Target Starting Capital Expected End

Prove edge Month 1 0.5% $1,000 ~$1,

Scale target Month 2-3 0.75% $1,160 ~$1,

Full deploy Month 4+ 1.0% $1,800+ Compounding


## 5. Mesh Resilience — Anduril Lattice

## Principle

###### Every possible failure mode has a predefined fallback. The system degrades gracefully — it never crashes

###### completely. Like Anduril's drone mesh, if one node goes down, others compensate.

Failure Detection Fallback Recovery
MEXC API down 3 consecutive API errors Switch to Bybit API Auto-retry MEXC every 5 min
Price feed stale No update > 10 seconds Switch to backup feed Alert CEO if > 2 min stale
News feed dies No response > 15 min Trade math-only, raise to 5/5 Resume normal when feed returns
Server crash Heartbeat check fails Exchange stops protect capital Auto-restart on recovery
Internet drops No connectivity All positions have exchange stops Resume when connection returns
Exchange maintenanceScheduled or detected Pause trading, hold positions Resume when exchange is back
Abnormal spread Spread > 3x normal Pause entry, hold existing Resume when spread normalises

###### The golden safety net: Every position ALWAYS has a stop loss set on the exchange itself. Even if every

###### system, server, and connection fails simultaneously, the exchange-side stop loss protects your capital. An

###### unprotected position never exists.


## 6. System Architecture Diagram

###### The complete QuantFusion system architecture showing how every component connects. Data flows from

###### top to bottom. The Ontology sits at the centre connecting everything. The feedback loop from Analytics

###### back to the Ontology enables continuous learning.

##### QuantFusion System Architecture

```
You (CEO)
Sets strategy & reviews
```
```
THE ONTOLOGY — Shared State (Palantir)
All data connected: price, indicators, positions, risk metrics, news, session
```
```
Data Agent
Collects all feeds
```
```
Math Agent
Calculates & scores
```
```
Research Agent
News & sentiment
```
```
Position Agent
Sizes trades & DCA
```
```
Risk Agent
Approves or BLOCKS
```
```
Execution Agent
Places orders
```
```
Analytics Agent
Logs, learns, feeds back
```
```
Feedback loop
```
```
MEXC (Primary)
Futures API
```
```
Bybit (Backup)
Mesh resilience
Anduril Lattice — Autonomous execution, mesh resilience, no single point of failure
```

## 7. Key Principles

###### 1. The system's primary job is saying NO.

###### Most signals get rejected. A system that trades all the time is a system that loses money. Quality over

###### quantity — even with high-frequency, each trade must meet the checklist.

###### 2. Position sizing is a formula, not a feeling.

###### Every position is calculated from risk budget and ATR. Never 'I feel like going bigger on this one.' Math

###### decides size, always.

###### 3. Same signal, different correct action.

###### RSI at 14 during a normal dip = buy. RSI at 14 during an exchange collapse = don't touch it. Context

###### matters. That's why the Research Agent exists.

###### 4. Compounding small wins is the business model.

###### Not home runs. Not 10x trades. Consistent 0.05-0.2% trades, 10 times a day, compounding daily. The

###### casino model.

###### 5. Higher timeframe always overrides lower.

###### If the 1-hour chart says bearish, the 5-minute chart cannot go long. The big picture sets the rules.

###### 6. When the daily target is hit, stop.

###### Don't give back profits. Lock the win. Walk away. The system enforces this automatically.

###### 7. Every failure has a fallback.

###### No single point of failure. Mesh resilience. Exchange-side stops. The system survives anything.

###### 8. Start small, prove the edge, then scale.

###### Month 1: prove it works. Month 2-3: scale the target. Month 4+: scale the capital. Never skip this

###### progression.

This is NOT financial advice. Trading involves risk. No system guarantees profits. Start with paper trading,
validate statistically, then deploy with capital you can afford to lose.




## 2. Architectural Foundations

### 2.1 Palantir Ontology — Connected Intelligence

The Ontology is a unified data layer where everything is connected to everything else. No data exists in isolation.

**How it works in QuantFusion:**
- BTC price → connected to → RSI reading → connected to → MACD histogram → connected to → volume spike → connected to → funding rate → connected to → news sentiment → connected to → current session → connected to → open positions → connected to → daily P&L → connected to → drawdown level
- When ANY piece of data changes, the entire web updates
- Every agent reads from and writes to the same shared state
- A news event doesn't just update one agent — it ripples through the entire system

**Why it matters:**
- No silos. No disconnected information.
- Every agent sees the full picture at all times.
- Decisions are contextual, not isolated.

### 2.2 Anduril Lattice — Autonomous Execution

Lattice enables autonomous execution at machine speed with intent-based commands and mesh resilience.

**Intent-based commands:**
- You DON'T say: "Buy 0.5 BTC at $64,200 with 30x leverage and a stop at $63,400"
- You DO say: "Trade BTC mean reversion, 0.5% daily target, 3% max daily loss"
- The system handles: when to enter, how much, where to stop, DCA layers, take profit, daily shutoff

**Mesh resilience — no single point of failure:**
- MEXC API dies → switch to Bybit
- News feed dies → trade math-only, raise threshold to 5/5
- Price feed lags → detect stale data, switch to backup
- Server crashes → exchange-side stops protect all positions
- Internet drops → all positions have exchange-set stops

---

## 3. Firm Structure

### Traditional Quant Firm → QuantFusion AI Firm

| Traditional Role | AI Agent | Status | Core Responsibility |
|-----------------|----------|--------|-------------------|
| CEO / CIO | You (Ibrahim) | Human | Sets strategy, risk appetite, reviews performance |
| Head of Research | Research Agent (LLM) | Autonomous | News reading, sentiment scoring, confidence multiplier |
| Quant Analyst | Math Agent | Autonomous | Indicator calculation, checklist scoring, raw signals |
| Portfolio Manager | Position Agent | Autonomous | Position sizing, DCA layers, portfolio exposure |
| Risk Manager | Risk Agent | Autonomous | All risk limits, absolute veto power, kill switch |
| Trader | Execution Agent | Autonomous | Order placement via exchange API, stop/TP management |
| Data Engineer | Data Agent | Autonomous | Real-time feeds, WebSocket, backup sources |
| Performance Analyst | Analytics Agent | Autonomous | Trade logging, metrics, learning feedback loop |

### Decision Flow (Chain of Command)

```
Data Agent → Math Agent → Research Agent → Position Agent → Risk Agent → Execution Agent → Analytics Agent
     ↑                                                                                           |
     └───────────────────────── Feedback Loop (Ontology) ─────────────────────────────────────────┘
```

Every trade passes through this exact chain. No shortcuts. No agent can skip a step.

---

## 4. Agent Specifications

### 4.1 Data Agent — The Plumbing

**Role:** Maintains all data connections and feeds raw information into the Ontology.

**Data sources:**

| Source | Method | Frequency | Purpose |
|--------|--------|-----------|---------|
| Price (BTC/ETH/SOL/XRP) | WebSocket | Real-time | Core price data |
| Volume | WebSocket | Per candle | Volume ratio calculation |
| Order book depth | REST API | Every 5 sec | Liquidity/slippage analysis |
| Funding rates | REST API | Every 8 hrs | Crowd positioning |
| Open interest | REST API | Every 1 min | Market participation |
| News feeds | API + scraping | Every 5 min | Sentiment input |
| On-chain data | API (future) | Every 15 min | Whale detection |

**Mesh resilience:**
- If MEXC WebSocket drops → switch to Bybit within 2 seconds
- If both drop → flag stale data, pause trading
- Never trade on stale data

---

### 4.2 Math Agent — The Brain

**Role:** Calculates all technical indicators across all timeframes and produces a raw score.

**Indicators calculated:**

| Indicator | Settings | Role |
|-----------|----------|------|
| RSI (dual) | RSI 6 + RSI 24 | Primary trigger |
| MACD | 12, 26, 9 | Momentum confirmation |
| EMA 200 | 200-period | Trend filter |
| Bollinger Bands | 20, 2 std dev | Volatility confirmation |
| ATR | 14-period | Stop loss sizing (1.5x ATR) |
| Volume ratio | Current vs MA(20) | Conviction check |

**5-Point Confirmation Checklist:**

| # | Check | Long +1 if | Short +1 if |
|---|-------|-----------|-------------|
| 1 | EMA 200 trend | Price above EMA 200 | Price below EMA 200 |
| 2 | MACD momentum | Red bars shrinking | Green bars shrinking |
| 3 | Volume conviction | Volume > 1.5x MA(20) | Volume > 1.5x MA(20) |
| 4 | Funding rate | Negative (shorts crowded) | Positive (longs crowded) |
| 5 | Open interest | OI dropping (capitulation) | OI dropping (euphoria fading) |

Output: Raw score 0-5 → passed to Research Agent.

---

### 4.3 Research Agent — The Context Layer

**Role:** LLM-powered intelligence that reads news and applies a confidence multiplier to the Math Agent's raw score.

**Process:**
1. Reads crypto news, social sentiment, whale alerts every 5 minutes
2. Classifies each event as bullish / bearish / neutral with score (-1.0 to +1.0)
3. Identifies event type: normal volatility vs systemic crisis
4. Applies confidence multiplier to raw math score

**Bayesian updating:** Prior (math score) × Evidence (news context) = Posterior (adjusted score)

| Scenario | Math Score | News | Multiplier | Result |
|----------|-----------|------|------------|--------|
| Normal dip | 4/5 | Profit-taking, ETF inflows | 1.1x | 4.4 = STRONG BUY |
| Uncertain | 4/5 | Mixed regulatory signals | 0.8x | 3.2 = MODERATE |
| Crisis | 4/5 | SEC sues exchange | 0.15x | 0.6 = NO TRADE |

---

### 4.4 Position Agent — The Portfolio Manager

**Role:** Decides HOW MUCH to trade. Never what or when.

**Position sizing formula:**
```
risk_amount = account_balance × 0.25% (per-trade cap)
stop_distance = 1.5 × ATR
position_size = risk_amount / stop_distance
margin_needed = position_size / leverage
```

**DCA layer management:**
- Layer 1: RSI hits threshold → enter 1/3 position
- Layer 2: RSI drops 5 more points → add 1/3 at better price
- Layer 3: Extreme oversold → add final 1/3
- Each layer passes its own checklist independently
- 5M scalps do NOT use DCA — single entry, quick exit

**Portfolio awareness:**
- Tracks total exposure across all open positions
- If 2/3 of risk budget deployed, reduces size of next trade
- Correlation check: won't add correlated positions (BTC+ETH = same bet)

---

### 4.5 Risk Agent — The Guardian

**Role:** The most important agent. Keeps the firm alive. Has absolute veto power that cannot be overridden.

**Non-negotiable rules:**

| Rule | Limit | Action When Triggered |
|------|-------|--------------------|
| Per-trade risk cap | 0.25% of account | Position sized down |
| Max concurrent positions | 3 trades open | 4th trade blocked |
| Correlation check | > 0.85 blocked | Duplicate bets prevented |
| Losing streak breaker | 3 losses in a row | Pause 30 minutes |
| Session streak breaker | 5 losses in a row | Stop for the session |
| Daily loss limit | -1.5% max | ALL trading stops until tomorrow |
| Daily profit target | +0.5% (scaling) | ALL trading stops — lock the win |
| Max drawdown kill switch | -8% from peak | ALL trading stops. CEO reviews. |
| Session thresholds | Varies | Asia: 5/5. London: 4/5. Prime: 3/5 |

---

### 4.6 Execution Agent — The Trader

**Role:** Places orders. Doesn't think, analyse, or decide.

| Function | Details |
|----------|---------|
| Order placement | Limit orders only — never market (avoid slippage) |
| Stop loss | Set ON THE EXCHANGE — survives server crash |
| Take profit | Triggered when RSI reaches 45-50 zone |
| DCA management | Monitors for layer 2/3 entries, adjusts all stops |
| Order timeout | Cancel unfilled limit orders after 5 minutes |
| Exchange failover | 3 API errors → switch to Bybit (Anduril mesh) |

**Critical safety:** Every position ALWAYS has a stop loss on the exchange. Unprotected positions never exist.

---

### 4.7 Analytics Agent — The Learning Loop

**Role:** Closes the feedback loop. Logs, learns, improves.

**Metrics tracked:**

| Metric | Target |
|--------|--------|
| Win rate | Above 60% |
| Expectancy | Always positive |
| Sharpe ratio | Above 2.0 |
| Profit factor | Above 1.5 |
| Best session | Optimise allocation |
| Best indicator | Adjust confirmation weights |
| Max drawdown | Below -8% |

**Feedback loop (Palantir principle):**
- Decisions → Outcomes → Learning → Better decisions
- Which indicators predicted best? → Increase their weight
- Which sessions produced most profit? → Focus there
- Which timeframe has best risk-adjusted returns? → Allocate more

---

## 5. Strategy — Multi-Timeframe Mean Reversion Scalping

### Core Principle
When price stretches too far in one direction, it snaps back. The system catches these snap-backs across multiple timeframes, taking many small profitable trades per day.

### Timeframes

| Timeframe | Role | RSI Trigger | Hold Time | Trades/Day | Profit/Trade |
|-----------|------|-------------|-----------|------------|--------------|
| 5-minute | Sniper scalps | < 25 or > 75 | 5-30 min | 5-10 | 0.05-0.1% |
| 15-minute | Workhorse | < 28 or > 72 | 15 min-2 hrs | 3-6 | 0.1-0.2% |
| 1-hour | Big catch | < 25 or > 75 | 1-8 hrs | 0-2 | 0.2-0.5% |

**Rule: Higher timeframe always overrides lower.** If 1H is bearish, 5M cannot go long.

### Session Schedule (Melbourne Time)

| Session | Time | Mode | Score Needed |
|---------|------|------|-------------|
| Asia | 11am-7pm | Observe only | 5/5 |
| London open | 7pm-12am | Alert | 4/5 |
| London-NY overlap | 12am-4am | PRIME ZONE | 3/5 |
| NY solo | 4am-9am | Active | 3/5 |
| Review | 9am-11am | CEO briefing | — |

### Daily Cycle
1. **Asia (daytime)**: System watches, tracks range. You're at uni or working.
2. **London (evening)**: System on alert. First possible trades.
3. **Prime zone (overnight)**: Maximum activity. Best signals. You're asleep.
4. **NY (early morning)**: Closing positions. Daily target check.
5. **Morning**: You wake up, check dashboard, review, adjust. CEO briefing.

---

## 6. Compounding Roadmap

| Phase | Period | Daily Target | Start | End |
|-------|--------|-------------|-------|-----|
| Prove edge | Month 1 | 0.5% | $1,000 | ~$1,160 |
| Scale target | Month 2-3 | 0.75% | $1,160 | ~$1,800 |
| Full deploy | Month 4+ | 1.0% | $1,800+ | Compounding |

**Rules:**
- Never withdraw during growth phase — let profits compound
- Position sizes auto-adjust as account grows
- Scale target ONLY after proving consistency
- At 1% daily: $1,000 → ~$10,000+ in one year

---

## 7. Mesh Resilience — Failure Modes

| Failure | Detection | Fallback | Recovery |
|---------|-----------|----------|----------|
| MEXC API down | 3 consecutive errors | Switch to Bybit | Retry MEXC every 5 min |
| Price feed stale | No update > 10 sec | Backup feed | Alert CEO if > 2 min |
| News feed dies | No response > 15 min | Math-only, raise to 5/5 | Resume when feed returns |
| Server crash | Heartbeat fails | Exchange stops active | Auto-restart |
| Internet drops | No connectivity | Exchange stops active | Resume on reconnect |
| Abnormal spread | > 3x normal | Pause entries | Resume when normal |

**Golden safety net:** Every position has a stop loss on the exchange. Even total system failure = capital protected.

---

## 8. Key Principles

1. **The system's primary job is saying NO.** Most signals get rejected. Quality over quantity.
2. **Position sizing is a formula, not a feeling.** Math decides size, always.
3. **Same signal, different correct action** depending on context. That's why Research Agent exists.
4. **Compounding small wins is the business model.** Not home runs. The casino model.
5. **Higher timeframe always overrides lower.** Big picture sets the rules.
6. **When daily target is hit, stop.** Lock the win. Don't give it back.
7. **Every failure has a fallback.** Mesh resilience. No single point of failure.
8. **Start small, prove, then scale.** Never skip this progression.

---

## 9. Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python (FastAPI) |
| Exchange connectivity | ccxt library |
| Data streaming | WebSocket (asyncio) |
| LLM (Research Agent) | Claude API (Anthropic) |
| Knowledge base | ChromaDB (vector store) |
| Frontend dashboard | Next.js |
| Hosting | Local server (RTX 2000 Ada) or VPS |
| Notifications | Telegram Bot API |

---

## 10. Build Phases

### Phase 1: Math Bot (Weeks 1-3)
- Implement all indicator calculations
- Build trigger gate and confirmation checklist
- Build risk cage with all limits
- Paper trading mode

### Phase 2: Backtesting (Weeks 3-5)
- Test against 1-2 years historical data
- Calculate win rate, Sharpe, profit factor
- Monte Carlo stress testing
- Adjust parameters

### Phase 3: Data Infrastructure (Weeks 5-7)
- WebSocket connections to MEXC/Bybit
- Real-time data pipeline
- Ontology shared state implementation
- Backup feed failover

### Phase 4: LLM Context Layer (Weeks 7-10)
- News API integration
- Sentiment scoring pipeline
- Confidence multiplier system
- A/B test: math-only vs math+context

### Phase 5: Full Deployment (Week 10+)
- Live trading with small capital ($100-$200)
- Monitor all metrics
- Gradual capital increase
- Scale daily target after proving edge

---

## Disclaimer

This is NOT financial advice. Trading involves significant risk of loss. No system guarantees profits. Even the best quant funds have losing periods. Never trade with money you cannot afford to lose. Start with paper trading, validate statistically, then deploy cautiously.
