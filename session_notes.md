# QuantFusion — Session Notes & Meeting Prep
> Technical review session notes, CEO meeting prep, updated roadmap, and work division.
> Last updated: 2026-05-03

---

## What This Actually Is

Before anything else — be honest about the framing internally.

**It is a sophisticated crypto trading bot.** Automated software that executes trades on crypto futures exchanges based on a rules-based pipeline with an LLM context layer. The "AI quant firm" framing is aspirational branding by the CEO. This is fine — the architecture is genuinely more serious than most retail bots — but the team should not confuse the brand with the reality.

**What separates it from a basic bot:**
- Multi-agent pipeline with clean separation of concerns (each component does one job)
- LLM-powered news context that can filter out systemic events
- Portfolio-level risk management (not just per-trade stops)
- Exchange mesh resilience (failover to backup exchange)
- Multi-timeframe signal aggregation

**What it is NOT (yet, possibly ever):**
- A quant firm in the industry sense — real quant firms have co-location, Level 2 data, proprietary data feeds, teams doing statistical research
- "AI" in the deep learning/autonomous sense — most agents are deterministic Python math; only the Research Agent uses an LLM
- A guaranteed edge — mean reversion on crypto has worked historically but is not guaranteed to continue

---

## Section 1 — Discussion Notes

### 1.1 Exchange Connectivity

**Original plan:** Use ccxt library for both MEXC and Bybit.

**Problem identified:** ccxt has known issues:
- Uses float arithmetic for money — causes silent rounding errors (`0.1 + 0.2 != 0.3` in Python)
- No unified semantics — `fetch_trades()` returns newest-first on some exchanges, oldest-first on others, ccxt doesn't normalize
- No retry logic — a dropped order packet throws an exception and does nothing
- Naive rate limiting — fixed sleep between calls, ignores weighted rate limits (Bybit's order placement has a different cost than a price query)

**Recommendation:** Drop ccxt as primary interface.

| Option | Pros | Cons |
|--------|------|------|
| ccxt | Unified API for 100+ exchanges, community support | Float money, no retries, naive rate limits, semantic inconsistency |
| pybit (official Bybit SDK) | Actively maintained by Bybit, WebSocket built in, handles reconnects | Bybit-only |
| Native MEXC SDK / raw API | Full control, no abstraction leaks | You write and maintain it |

**Decision:** Use `pybit` for Bybit (make it primary exchange — more regulated, has Australian entity). Use MEXC official Python SDK or direct REST/WS for MEXC. Build a thin adapter layer over both so the rest of the system talks to one interface.

**Things to watch out for:**
- Always use `Decimal` (Python's `decimal` module) for any money arithmetic, never float
- Round all order quantities to exchange precision before submitting (exchanges reject orders with too many decimal places)
- MEXC is legally ambiguous for Australian users — verify this before depositing real capital

---

### 1.2 WebSocket Architecture

**Both exchanges need WebSocket connections, but not symmetrically.**

- MEXC WebSocket: **active primary** — receiving live ticks, acting on them
- Bybit WebSocket: **connected and subscribed but passive** — receiving data, not acting unless MEXC fails

**Why keep Bybit warm (not cold):** Cold failover (connect only when MEXC drops) takes 3-10 seconds to establish connection, authenticate, subscribe, and receive first candle. A warm connection failover is sub-second — you just flip which feed you're routing from.

**Things to watch out for:**
- Both WebSocket connections need heartbeat monitoring — exchanges disconnect idle connections
- On reconnect, request recent candle history to fill the gap (WebSocket doesn't backfill missed candles)
- Mark data with a timestamp and flag anything older than 10 seconds as stale — never calculate indicators on stale data

---

### 1.3 Backtesting

**Original plan:** Build custom backtest engine OR use vectorbt.

**vectorbt criticism (from research):** At scale (hundreds of symbols), requires deep Numba optimization knowledge. Complex for portfolio-level P&L across correlated positions. Within-bar entry/exit has known bugs. Learning curve is ~1 week of reading docs before being productive.

**backtesting.py criticism:** Simpler but single-symbol only — cannot model portfolio-level risk (correlation blocking, max concurrent positions). This is a real gap for this system.

| Option | Pros | Cons |
|--------|------|------|
| vectorbt | Portfolio-aware, built-in metrics/charts | Learning curve, Numba complexity at scale |
| backtesting.py | Simple, fast, readable | Single-symbol only, can't model portfolio risk |
| backtrader | Mature, event-driven, multi-asset | Largely unmaintained, slow |
| Custom pandas backtest | Fastest, transparent, exact match to live logic | You write it |

**Recommendation:** Write a custom vectorized backtest in pandas/numpy. For this specific strategy (RSI trigger + 5-point checklist, limit orders, ATR stops, 4 symbols), the backtesting logic is ~200 lines. Benefits:
- Identical logic to live agents — no "worked in backtest, failed live" divergence
- Runs in seconds on 2 years of data
- You understand every line

**Things to watch out for:**
- Lookahead bias: never use data from candle N to make a decision that would be made at the close of candle N-1. The signal fires at candle close — entry price is next candle open or limit price, not the close that triggered it
- Model fees explicitly: 0.02% maker / 0.06% taker per side = 0.04%-0.12% round trip. For 5M scalps targeting 0.05-0.1%, fees consume 40-100% of the profit. All backtest P&L must be fee-adjusted.
- Model slippage: even limit orders queue behind existing orders. Assume 0.01-0.03% slippage on entry fills.

---

### 1.4 Agent Orchestration (LangGraph question)

**Question:** Do we need LangGraph or a similar agent framework?

**Answer: No.**

LangGraph is designed for complex multi-LLM-agent reasoning loops where agents debate, revise, and hand off to each other. Only one of the seven agents (Research Agent) uses an LLM. The other six are deterministic Python math functions.

Using LangGraph would add:
- Framework overhead and latency at every node boundary
- Dependency on an external framework for a linear pipeline
- Complexity that makes debugging harder

**What you actually need:** `asyncio` + Redis pub/sub. Each agent publishes to a Redis channel when it completes. The next agent subscribes to that channel. The Risk Agent subscribes to Position Agent output and either publishes to Execution or blocks the signal. This is idiomatic Python — no framework needed.

---

### 1.5 Freqtrade

**What it is:** Popular open-source crypto trading bot with backtesting, live trading, Telegram, paper trading, and FreqAI (ML) all built in.

| Pros | Cons |
|------|------|
| Saves 2-3 months of scaffolding | Uses ccxt underneath — all the same issues |
| Active community, exchange bugs get fixed | Multi-agent architecture doesn't fit freqtrade's single-strategy class model |
| FreqAI handles ML pipeline natively | Ontology shared state concept has no equivalent |
| Walk-forward backtesting built in | You'd spend as much time fighting the framework as building features |

**Decision:** Don't use freqtrade as a framework. **Do** read its source code for reference — specifically how it handles order state machines, WebSocket reconnection logic, and rate limiting. These are solved problems in freqtrade and worth studying before implementing your own.

---

### 1.6 Research Agent — Full Architecture

**How it works:**

1. Background async loop runs every 5 minutes (completely independent of trading pipeline)
2. Fetches last 20 news articles from CryptoPanic API
3. Filters to articles mentioning BTC/ETH/SOL/XRP
4. Sends to Claude API with a structured prompt requesting JSON output
5. Parses response, writes to Redis shared state
6. Trading pipeline reads cached score from Redis (microseconds, not an API call)

**Claude API prompt structure (rough):**
```
You are a crypto trading risk analyst. Given these recent news articles and current
market context, output JSON:
{
  "overall_sentiment": float (-1.0 to 1.0),
  "event_type": "normal" | "regulatory" | "exchange_risk" | "systemic_crisis",
  "confidence_multiplier": float (0.1 to 1.2),
  "reasoning": "one sentence"
}
Articles: [...]
Current context: BTC -2.3% in last hour, ETH -1.8%
```

**Critical design decision:** Research Agent is NOT in the critical path. It runs independently and caches its result. The trading pipeline reads from cache — never calls the LLM inline.

**Things to watch out for:**
- CryptoPanic free tier lags real events by 5-10 minutes and has rate limits — consider paid tier for live trading
- Confidence multiplier values in the blueprint (0.15x for crisis, 1.1x for positive) are guesses — they need calibration against historical events before trusting them
- Add a secondary trigger: if price drops >3% in 15 minutes, force an immediate Research Agent run regardless of the 5-minute schedule — systemic events move faster than 5 minutes
- Use Claude's JSON mode (structured output) so parsing never fails silently

---

### 1.7 ML Models

**What the roadmap planned (Phase 6):** Random Forest, XGBoost, Logistic Regression, HMM regime detection, indicator weight optimizer, sentiment calibration, strategy decay detector, position size optimizer.

**The overfitting issue (clarified):**

There is NO shortage of historical OHLCV price data — 2 years of 5M candles = ~210,000 data points. The issue is specifically about the Analytics Agent's ML models that learn from YOUR SYSTEM'S LOGGED TRADING DECISIONS. If you go live and collect 2 weeks of trades at 5-8 trades/day = ~100 samples. Training Random Forest on 100 samples with 10+ features will memorize noise.

**Fix:** Simulate historical signals by running your full checklist logic backward over 2 years of data. Label outcomes (did price reach the take-profit before the stop-loss?). This gives you thousands of training samples before going live.

**Remaining honest ML concerns:**
- Crypto market regimes change drastically (2021 bull, 2022 bear, 2023-24 recovery) — what predicted bounces in one regime may not generalize
- The feature space is small (5 confirmations + RSI level + session + sentiment score) — rule-based tuning may outperform ML with this few features
- ML introduces learned exceptions to rules, which is where discipline breaks down

**Recommendation:**
- **Keep:** LLM news context (Research Agent) — this is the highest-value "ML" component
- **Keep if building Phase 6:** Simulate historical signals first, then train — don't train on live-only data
- **Drop entirely:** Indicator weight optimizer, position size optimizer via ML — rule-based is more robust with limited data
- **Defer:** All ML until the rule-based system has proven positive expectancy over 200+ live trades
- **Dropped:** Regime classifier (HMM) — the EMA 200 filter and higher-timeframe override already handle most of what a regime classifier would do. Don't build solutions to problems you haven't observed.

---

### 1.8 Parallel vs Sequential Pair Processing

**What the current plan implies (sequential):**

The system scans one pair at a time through the full pipeline:

```
BTC: Data → Math → Research → Position → Risk → Execution
ETH: Data → Math → Research → Position → Risk → Execution  (then)
SOL: ...
XRP: ...
```

**Problem:** By the time you finish BTC and start XRP, BTC's RSI may have already recovered. If BTC and ETH both trigger RSI extremes simultaneously (common — they're highly correlated), the Risk Agent evaluates them sequentially. It approves BTC, BTC takes position slot 1. Then ETH arrives — the Risk Agent sees it as a new trade and may approve it without knowing BTC just entered. The correlation check is working on stale information.

**What was suggested (parallel):**

```python
# All four pairs analyze simultaneously
btc_signal, eth_signal, sol_signal, xrp_signal = await asyncio.gather(
    analyze_pair('BTCUSDT'),
    analyze_pair('ETHUSDT'),
    analyze_pair('SOLUSDT'),
    analyze_pair('XRPUSDT'),
)

# Risk Agent sees ALL signals before ANY execution
approved = risk_agent.arbitrate([btc, eth, sol, xrp])

# Execute only what Risk Agent approved
for signal in approved:
    await execution_agent.execute(signal)
```

**Pros:** No missed signals, Risk Agent has full picture before committing to any trade, natural asyncio pattern.

**Cons:** More complex shared state (use `asyncio.Lock()` on position counter to prevent two signals claiming the last slot simultaneously), logs are interleaved (need structured logging with per-signal correlation IDs).

**When to implement:** For 15M and 1H timeframes, sequential is fine — signals don't disappear in seconds. Build sequential first, refactor to parallel when adding 5M. Don't over-engineer day one.

---

### 1.9 Fee Modeling (Critical Gap)

This was not in the original blueprint and must be added.

MEXC perpetual futures fees:
- Maker (limit orders): 0.02% per side = 0.04% round trip
- Taker (market orders): 0.06% per side = 0.12% round trip

For the 5-minute scalp layer targeting 0.05-0.1% profit:
- Best case (limit both sides): 0.04% fees on a 0.05% target = 80% of profit gone
- Worst case (any taker fill): 0.12% fees on a 0.05% target = trading at a loss

**Action required:**
- Add fee model to all backtest P&L calculations immediately
- Add minimum net profit filter: only take a trade if expected gross profit > 2.5x fees
- For 5M scalps, this means only taking the highest-conviction setups (5/5 score minimum) with RSI at extreme levels — not 3/5 setups
- Consider whether 5M scalps are viable at small account sizes at all

---

### 1.10 Success Metrics — Who Owns What

Critical clarification: metrics are NOT only the Analytics Agent's concern. They are split across three agents with completely different jobs.

---

**Risk Agent — Real-Time Operational Limits (enforced live, every tick)**

These are guardrails that stop trading *right now* if breached. The Risk Agent checks these continuously.

| Metric | Limit | What Happens |
|--------|-------|--------------|
| Per-trade risk | 0.25% of account | Position sized down before entry |
| Daily loss | -1.5% | All trading stops until tomorrow |
| Daily profit target | +0.5% (scaling) | All trading stops — lock the win |
| Max drawdown from peak | -8% | Kill switch — CEO must manually restart |
| Losing streak | 3 in a row | Pause 30 minutes |
| Session streak | 5 in a row | Stop for the session |
| Concurrent positions | Max 3 | 4th trade blocked regardless of score |
| Correlation | > 0.85 | Second correlated position blocked |

These are not analytics — they are enforcement. They live in Redis as live state, updated after every trade close.

---

**Analytics Agent — Historical Performance Metrics (calculated post-trade, updated after each close)**

These tell you whether the strategy is working over time. No enforcement — pure measurement and reporting.

| Metric | Formula | Target | Notes |
|--------|---------|--------|-------|
| Win rate | Wins / total trades | > 55% (fee-adjusted) | Meaningless below 150 trades — too small a sample |
| Expectancy | (win_rate × avg_win) − (loss_rate × avg_loss) | Always positive | The single most important number |
| Profit factor | Total gross profit / total gross loss | > 1.3 | 1.0 = break even, 1.5 = strong |
| Sharpe ratio | Annualised return / annualised std dev of returns | > 1.5 | Penalises volatility of returns, not just losses |
| Calmar ratio | Annualised return / max drawdown | > 2.0 | More relevant than Sharpe for trading systems — measures return per unit of worst pain |
| Max drawdown | Worst peak-to-trough decline in account value | < 8% | Matches kill switch level |
| Strategy decay | Rolling 30-day win rate trend | Flat or improving | If trending down, edge may be eroding |

**Why Calmar over Sharpe for trading:** Sharpe penalises all volatility including upside volatility. A strategy that has a few very large wins alongside consistent small wins will look worse on Sharpe than it deserves. Calmar only cares about the worst drawdown — which is what actually kills a trading account.

---

**Backtest Validation Metrics — Used Before Going Live (not runtime, used during Phase 3)**

These are one-time checks to validate the strategy before deploying real capital. They live in the backtest engine output, not in the live system.

| Metric | Target | Why |
|--------|--------|-----|
| Walk-forward Sharpe | > 1.5 out-of-sample | In-sample Sharpe is meaningless — the strategy was optimised on that data |
| Walk-forward profit factor | > 1.3 out-of-sample | Same reason |
| Minimum signal count | 500+ occurrences tested | Below this, statistics are not reliable |
| Parameter sensitivity score | Wide plateau (explained in 1.12) | Narrow peak = overfit, wide plateau = robust |
| Calmar ratio (backtest) | > 2.0 | Annualised return / max drawdown across test window |

**Suggested go/no-go criteria (replace the vague blueprint milestones):**
- Backtest gate: walk-forward Sharpe > 1.5, profit factor > 1.3, 500+ signals, parameter sensitivity shows wide plateau
- Paper trading gate: 150+ completed trades, win rate > 55% fee-adjusted, max drawdown < 4%, Calmar > 1.5, no single day hitting daily loss limit more than twice
- First real capital ($100-200): only after both gates hit, no exceptions

---

### 1.11 Analytics Agent — Detailed Specification

The original blueprint spec for Analytics Agent was: "log trades, track metrics, feeds learnings back." This is too vague. Here is what it actually needs to do.

**Inputs:** Every closed trade from Execution Agent (entry price, exit price, side, size, fees paid, entry timestamp, exit timestamp, which confirmations fired, score, session, timeframe, news multiplier at time of entry)

**Outputs:** Performance database + CEO dashboard data + daily report + strategy health signals

---

**Component 1: Trade Log Database (PostgreSQL)**

Every closed trade gets a row with full context:

```
trade_id, symbol, timeframe, side (long/short), entry_price, exit_price,
entry_time, exit_time, hold_duration_minutes, position_size, fees_paid,
gross_pnl, net_pnl (after fees), math_score, confirmations_fired (JSON),
session, news_multiplier, news_event_type, was_dca (bool), dca_layer_count
```

This is the raw material for everything else. Never delete rows — append only.

---

**Component 2: Rolling Performance Calculator**

Recalculates after every trade close. Stores results in Redis for dashboard access.

- Win rate (last 50 trades, last 150 trades, all time) — three windows
- Expectancy (fee-adjusted)
- Profit factor (fee-adjusted)
- Sharpe ratio (rolling 30-day)
- Calmar ratio (rolling 90-day)
- Current drawdown from recent peak
- Strategy decay signal: is 30-day win rate trending up or down?

---

**Component 3: Breakdown Analysis**

Runs nightly, answers: where is the edge actually coming from?

- **Session breakdown:** Win rate and expectancy by session (Asia / London / Prime / NY). Are session thresholds calibrated correctly? Is Asia truly not worth trading?
- **Timeframe breakdown:** 5M vs 15M vs 1H — which produces the best risk-adjusted return?
- **Confirmation contribution:** For each of the 5 confirmation checks, what is the win rate of trades where that check fired vs didn't fire? This tells you which checks are adding predictive value and which are noise.
- **Score distribution:** Are 5/5 trades materially better than 3/5 trades? If not, thresholds need revisiting.
- **Symbol breakdown:** BTC vs ETH vs SOL vs XRP — any pair consistently underperforming?
- **Hold time analysis:** What is the average hold time for winning vs losing trades? Are wins exited too early?

---

**Component 4: Parameter Sensitivity Analysis**

See Section 1.12 for full explanation. This runs as a batch job against the backtest engine whenever parameters are being reviewed (not real-time). Output feeds into the CEO dashboard as a "strategy robustness" score.

---

**Component 5: Daily Report (CEO Morning Briefing)**

Auto-generated every morning (09:00 Melbourne time), sent via Telegram and available on dashboard.

Contents:
- Yesterday's P&L (gross and net of fees), number of trades, win/loss count
- Current account balance vs starting balance (total return %)
- Current drawdown from peak
- Rolling 30-day win rate and whether it's trending up/down
- Any risk events yesterday (kill switch near-trigger, streak breaker fires, etc.)
- Best and worst trade of the day with full context
- Flag if any metric is approaching a threshold (e.g. "drawdown at -5.2%, kill switch at -8%")

---

**Component 6: Dashboard API (FastAPI)**

Endpoints that serve live data to the Next.js frontend:

```
GET /metrics/live          → current balance, open positions, today's P&L
GET /metrics/performance   → all rolling metrics (win rate, Sharpe, Calmar etc.)
GET /metrics/breakdown     → session/symbol/timeframe/confirmation analysis
GET /trades/recent         → last 50 closed trades
GET /trades/{id}           → full context for a single trade
GET /risk/status           → current Risk Agent state (daily P&L vs limits, streak count)
```

---

### 1.12 Parameter Sensitivity Analysis — Full Explanation

**What it is:**

Your strategy has parameters — numbers you chose. RSI threshold of 25. ATR multiplier of 1.5. Volume ratio of 1.5x. Session score minimums of 3/4/5. The question is: are these the right numbers, and more importantly, *how fragile is the strategy if these numbers are slightly wrong?*

Parameter sensitivity analysis answers this by running the backtest across a grid of parameter values and measuring how performance changes.

**The core question it answers:**

> If I change the RSI threshold from 25 to 23 or 27, does the strategy still work, or does it collapse?

A **robust strategy** has a wide plateau — it works across a range of parameter values:

```
RSI threshold:  20   22   24   25   26   28   30
Sharpe ratio:  1.3  1.5  1.6  1.7  1.6  1.4  1.2
                          ↑ wide plateau around 25 ↑
```

A **fragile (overfit) strategy** has a narrow spike — it only works at the exact values you picked:

```
RSI threshold:  20   22   24   25   26   28   30
Sharpe ratio:  0.3  0.4  0.5  1.7  0.4  0.3  0.2
                          ↑ spike only at exactly 25 ↑
```

The spike tells you the parameters were fitted to the historical data, not discovered from it. The strategy doesn't have a real edge — it was curve-fit.

**How to implement it (practical):**

```python
from itertools import product

param_grid = {
    'rsi_oversold':    [20, 22, 25, 28, 30],
    'atr_multiplier':  [1.0, 1.25, 1.5, 1.75, 2.0],
    'volume_ratio':    [1.2, 1.5, 1.8, 2.0],
    'min_score_prime': [3, 4],
}

results = []
for rsi, atr, vol, score in product(*param_grid.values()):
    metrics = run_backtest(rsi_oversold=rsi, atr_mult=atr, 
                           vol_ratio=vol, min_score=score)
    results.append({
        'rsi': rsi, 'atr': atr, 'vol': vol, 'score': score,
        'sharpe': metrics.sharpe,
        'calmar': metrics.calmar,
        'profit_factor': metrics.profit_factor,
        'win_rate': metrics.win_rate,
        'trade_count': metrics.trade_count
    })

df = pd.DataFrame(results)
# Visualise as heatmap: Sharpe across RSI × ATR grid
```

The grid above has 5 × 5 × 4 × 2 = 200 backtest runs. Each run takes a fraction of a second on vectorized pandas. Total runtime: under a minute.

**What to look for in results:**

1. **Is the chosen parameter set near the center of a plateau?** If the best parameters are at the edge of your test range (e.g. RSI=20 is best and you only tested down to 20), your optimum may be outside the range you tested — extend the grid.

2. **Which parameters have the highest sensitivity?** If changing ATR multiplier from 1.5 to 1.25 halves your Sharpe, that parameter is highly sensitive — small errors in estimation hurt badly. These are the parameters to monitor most carefully in live trading.

3. **Which parameters barely matter?** If Sharpe is stable across all volume ratio values, the confirmation check isn't adding much. This is useful information — it might mean the check should be dropped or its threshold reconsidered.

4. **What is the trade count across the grid?** A parameter set that gives Sharpe 2.5 but only 30 trades over 2 years is not statistically meaningful. Filter out any grid point with fewer than 100 trades before drawing conclusions.

**When to run it:**

- Once during Phase 3 (backtest phase) to validate the initial parameters are near a plateau
- Again before going live with real capital
- Any time the CEO wants to change a parameter — run the sensitivity analysis first to understand the neighbourhood
- Not in real-time — this is a batch job run manually or on a weekly schedule

**This replaces ML indicator weight optimization** from the original Phase 6. It answers the same question ("which indicators matter most?") with less risk of overfitting and in a fraction of the time.

---

### 1.13 Hosting

**Original plan:** Local server (RTX 2000 Ada) or VPS.

**Problem:** Local server is risky for 24/7 live trading — power outages, ISP drops, home network instability. The RTX 2000 Ada is irrelevant — this stack has no GPU workload (scikit-learn is CPU-bound, Claude API is remote).

**Recommendation:** VPS in Singapore or Tokyo (geographically closest to MEXC and Bybit exchange servers = lower API latency). DigitalOcean or Vultr droplet at ~$20-40/month. Keep local machine for development and backtesting.

---

## Section 2 — CEO Meeting Talking Points

### 2.1 General / Non-Technical

**What to align on:**

1. **Correct the framing internally:** "AI hedge fund" is good brand positioning externally. Internally, call it what it is — a sophisticated systematic crypto trading bot with an LLM layer. This keeps expectations calibrated.

2. **The return targets need a reality check:** 0.5% daily consistently = 182.5% annually at simple math, compounding to 3000%+ theoretically. The best quant funds in the world target 15-30% annually. Reframe the goal as: prove positive expectancy and Sharpe > 1.5 over 200+ trades. If that's proven, then compound. The daily percentage is an output, not an input.

3. **This is a long build:** The original roadmap says 12-16 weeks to live trading. With proper validation and no shortcuts, 20-24 weeks is realistic. Phase milestones must be hit before moving forward — skipping validation is how trading systems blow up.

4. **Start with paper trading for longer than planned:** The original plan has 2 weeks of paper trading before real money. Suggest 6-8 weeks minimum, with a minimum trade count (150 trades), not just time.

5. **Legal/regulatory check needed before anything:** MEXC's legality for Australian users is ambiguous. Bybit has an Australian entity and ASIC registration. This conversation needs to happen before any capital is committed.

6. **Tax implications:** In Australia, every crypto futures trade is a taxable event. At 5-10 trades/day, that's potentially 2,000+ taxable events per year. Need automated trade logging that exports to crypto tax software (Koinly etc.) from day one — not bolted on later.

### 2.2 Technical Points to Discuss with CEO

These are decisions the CEO needs to understand and approve even if they don't implement them:

1. **Exchange choice:** Recommend making Bybit primary (more regulated, Australian entity, better API quality) and MEXC backup, rather than the reverse. This is a business/risk decision, not just technical.

2. **5M scalps are not viable at $1,000 starting capital:** Per-trade risk of 0.25% = $2.50 per scalp. After fees on MEXC ($0.04-0.12% round trip), there's almost no profit margin. Recommend starting with 15M and 1H only, unlock 5M after account reaches ~$5,000.

3. **The system's primary job is saying NO:** The CEO already wrote this in the blueprint (Section 7, Principle 1). Reinforce it. A good week for this system might be 20 total trades. Not 200. The win rate matters more than trade frequency.

4. **The Research Agent adds cost:** Every 5-minute Claude API call. At ~$0.003 per call × 288 calls/day = ~$0.86/day = ~$26/month in LLM API costs, plus news API costs. Small but worth budgeting.

5. **There will be losing months:** Any trading system, no matter how good, has losing months. The risk cage (daily loss limit, kill switch) is designed for this. The CEO must agree in advance: when the kill switch fires (-8% drawdown), the system stops and CEO reviews before restarting. No overriding the kill switch because "it's about to turn around."

---

## Section 3 — Updated Timeline

Adjusted for proper validation, Research Agent shadow mode during paper trading, no ML until proven edge.

| Phase | What | Duration | Key Deliverable | Gate to Next Phase |
|-------|------|----------|-----------------|-------------------|
| 1 | Foundation | Weeks 1-2 | Dev environment, pybit + MEXC adapters, WebSocket streams live, Redis state, structured logging | Data flowing live for all 4 pairs with failover working |
| 2 | Math Agent + Risk Agent | Weeks 2-5 | All 6 indicators calculated, 5-point checklist, session thresholds, higher-TF override, all risk rules coded | Indicators match exchange chart values; Risk Agent passes stress tests (Luna/FTX/COVID scenarios) |
| 3 | Custom Backtest | Weeks 5-7 | Vectorized pandas backtest, fee-adjusted, walk-forward + parameter sensitivity validation | Walk-forward Sharpe > 1.5, profit factor > 1.3, 500+ signal occurrences, sensitivity plateau confirmed |
| 4 | Position + Execution + Research Agent (shadow) | Weeks 7-10 | Position sizing, DCA layers, paper order engine, Research Agent running in shadow mode (logs what it would do but does not affect trades) | System paper trading live, Research Agent shadow log accumulating |
| 5 | Paper Trading Validation + Shadow Calibration | Weeks 10-16 | 6 weeks of paper trading with Research Agent in shadow mode throughout | 150+ completed trades, win rate > 55% fee-adjusted, max drawdown < 4%; shadow log reviewed and multiplier values calibrated against real outcomes |
| 6 | Research Agent goes active + Analytics Agent + Dashboard | Weeks 16-19 | Flip Research Agent from shadow to active (now affects trades), trade log database, performance metrics, Telegram alerts, Next.js dashboard | Dashboard operational, Research Agent active for minimum 2 weeks of paper trading before real capital |
| 7 | First Real Capital | Week 20+ | Deploy $100-200 real capital on Bybit | All Phase 5 gates met, Research Agent calibrated and active, dashboard operational |
| 8 | Scale | Month 6+ | Increase position sizes as account grows, unlock 5M timeframe, consider ML only after 500+ live trades | 60+ days of live trading with positive expectancy |

**Shadow mode explained:**
The Research Agent is built alongside the paper trading agents but starts in shadow mode — it runs the full pipeline (fetches news, calls Claude API, calculates multipliers) and logs: "this trade had a multiplier of 0.3, I would have blocked it." But the trading system ignores this output and trades anyway. After 6 weeks, you have a dataset: did the trades it would have blocked end up as losses? Did the trades it would have boosted outperform? This calibrates the confidence multiplier values (currently guesses in the blueprint) with real evidence before giving the Research Agent actual veto power.

**What changed from original roadmap:**
- Risk Agent moved to Phase 2 (must be built before any trading simulation)
- Research Agent built in Phase 4 but in shadow mode — not after paper trading
- Paper trading now runs with Research Agent in shadow mode throughout, giving 6 weeks of calibration data
- Research Agent flips to active at the start of Phase 6 (not Phase 6 from scratch)
- Analytics Agent and Dashboard consolidated into Phase 6
- ML dropped from near-term plan entirely
- Regime classifier dropped entirely
- First real capital at Week 20+ (was Week 6-8 in original)

---

## Section 4 — Work Division

### CEO's Role

The CEO wrote a strong conceptual document. The CEO's ongoing value is in decisions that require domain judgment and business context, not code.

**CEO owns:**
- Strategy parameters: which RSI thresholds, which session times, what daily target to set
- Risk appetite decisions: per-trade risk %, daily loss limit, kill switch level — these are business decisions that need owner accountability
- Weekly performance review: reading the Analytics Agent dashboard, identifying whether the edge is holding
- Exchange/legal: confirming Bybit Australia entity, verifying regulatory compliance, managing API keys
- Capital decisions: when to add more capital, when to withdraw, when to pause
- The "why" behind any parameter changes: if win rate drops, CEO decides whether to adjust thresholds or pause — not the developer

**Keep the CEO away from:** specific technical implementation decisions. The CEO should not be deciding whether to use asyncio or threading, which database schema to use, or how to structure the Redis state. These decisions live with the developer.

### Developer (You) Owns

**You own everything technical:**
- Full codebase architecture and implementation
- Exchange adapter layer (pybit + MEXC)
- All agent implementations
- Backtest engine
- Data pipeline and WebSocket management
- Claude API integration (Research Agent)
- Database schema (PostgreSQL for trade logs, Redis for live state)
- Dashboard (Next.js frontend + FastAPI backend)
- Deployment and VPS setup
- Testing and validation

**Specific technical decisions you make independently (then inform CEO):**
- Which libraries to use
- How agents communicate internally
- Database design
- Hosting setup

### Shared / Collaborative

- **Backtesting results review:** Developer runs backtests, both review results together — did the backtest confirm the edge? Are the numbers realistic?
- **Paper trading review:** Weekly sessions reviewing paper trading metrics — CEO brings trading intuition, developer brings statistical interpretation
- **Parameter calibration:** RSI thresholds, ATR multiplier, DCA layer offsets — these are strategy decisions that need both the quant intuition (CEO) and statistical validation (developer)
- **Go/no-go decisions:** Milestone gates before advancing phases — both agree before moving forward

---

## Section 5 — Start Right Now

**This week — Developer:**

1. Set up the Python project structure and virtual environment
2. Get `pybit` installed and test a Bybit WebSocket connection — subscribe to BTC/USDT kline stream, confirm you're receiving candles
3. Check MEXC official Python SDK — test their WebSocket for the same
4. Download 2 years of OHLCV data for BTC/ETH/SOL/XRP at 5M, 15M, 1H from Bybit (use their REST API or a data provider like CryptoDataDownload)
5. Set up Redis locally and write your first Ontology state schema — what keys exist, what format

**This week — CEO:**

1. Verify Bybit Australia entity and confirm whether futures trading is available and compliant
2. Create API keys on Bybit (read-only first — no trading permissions until paper trading phase)
3. Sign up for CryptoPanic API (free tier) and Anthropic API (for Research Agent later)
4. Decide on starting capital amount and confirm it is money that can be fully lost without financial harm
5. Read this document and flag any strategy parameters they want to revisit before the developer starts coding them in

**Do not start:** Research Agent, ML, dashboard, live trading, or any exchange orders (real or paper) until Phase 2 (Math + Risk Agent) is complete and validated.

---

## Quick Reference — Key Decisions Made

| Decision | Choice | Reason |
|----------|--------|--------|
| Exchange library | pybit (Bybit) + native MEXC SDK | ccxt float/retry issues |
| Primary exchange | Bybit | More regulated, Australian entity |
| Backtesting | Custom pandas | Exact logic match to live system |
| Agent orchestration | asyncio + Redis pub/sub | LangGraph overkill for linear pipeline |
| Freqtrade | Reference only, not a framework | Doesn't fit multi-agent architecture |
| LangGraph | No | Only 1 of 7 agents uses LLM |
| ML (Phase 6) | Deferred until 500+ live trades | Overfitting risk with limited samples |
| Regime classifier | Dropped | EMA 200 + higher-TF override already covers it |
| Parallel pair processing | Build sequential first, refactor to parallel for 5M | Don't over-engineer day one |
| 5M scalps | Gated behind $5,000 minimum account | Fees consume profit margin at small sizes |
| Hosting | Singapore/Tokyo VPS ($20-40/month) | Latency to exchange servers; reliability |
| Money arithmetic | Python `Decimal` module everywhere | Float rounding causes silent errors |

---

*Not financial advice. This is a development planning document for a systematic trading system. All capital deployed should be money you can afford to lose entirely.*
