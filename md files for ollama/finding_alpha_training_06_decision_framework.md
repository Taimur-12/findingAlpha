# Finding Alpha — Master Decision Framework

> This document is the final reasoning chain. It ties all previous knowledge files together into
> a single decision process. When live data arrives, the intelligence engine follows this framework
> step by step to arrive at a trade decision. It covers both futures trading (income generation)
> and spot accumulation (wealth building) — the two pillars of a complete asset management operation.

---

## Part 1: The Two Pillars

### Pillar 1 — Futures Trading (Income)

Active, high-frequency, leveraged trading on perpetual futures. Goal: generate consistent daily returns through multiple trades. This is the cash flow engine of the firm.

- Timeframes: 5M, 15M, 1H
- Direction: both long and short
- Leverage: 10-20x (calculated from stop distance)
- Hold duration: minutes to hours
- Risk per trade: 1-2% of account
- Daily target: +3-5%
- Edge: speed, precision, 24/7 operation, contextual reasoning

### Pillar 2 — Spot Accumulation (Wealth)

Slow, strategic, unleveraged buying of BTC and ETH in spot markets during institutional accumulation phases. Goal: build long-term holdings that appreciate over full market cycles.

- Timeframe: daily, weekly
- Direction: long only (buy and hold)
- Leverage: none (1x spot)
- Hold duration: months to years
- Allocation: a percentage of futures profits reinvested into spot
- Edge: buying when retail is panicking, holding through cycles

**How they work together:**
Futures generate daily income. A portion of that income (20-30% of weekly profits) is allocated to spot purchases during favourable accumulation windows. The spot portfolio grows over time through both appreciation and regular contributions. Futures are the salary. Spot is the retirement fund.

---

## Part 2: The Futures Decision Chain

Every potential trade must pass through these stages IN ORDER. If it fails at any stage, the trade is rejected. No skipping stages.

### Stage 1: System State Check

Before looking at any chart or indicator, verify:

```
Questions:
1. Is the system operational? (all agents online, data feeds current)
2. Are we within risk limits? (daily P&L, drawdown, position count)
3. Is there a circuit breaker active? (losing streak, session pause)
4. Are there any scheduled high-impact events in the next 2 hours?
```

If ANY answer is negative, STOP. Do not evaluate trades.

### Stage 2: Macro Context Assessment

Read the current macro environment:

```
Inputs:
- DXY direction and magnitude (rising/falling, by how much)
- S&P 500 / Nasdaq pre-market or live direction
- VIX level (calm <15, moderate 15-25, elevated 25-35, extreme >35)
- 10Y Treasury yield trend
- News sentiment from Research Agent (multiplier value)
- Any active geopolitical events
```

**Output:** Macro score from -3 to +3
- -3: Multiple macro headwinds (DXY surging, SPY dumping, VIX spiking, war escalation)
- -2: Significant macro headwind
- -1: Mild headwind
- 0: Neutral
- +1: Mild tailwind
- +2: Significant macro tailwind (DXY falling, SPY rallying, VIX low, positive news)
- +3: Multiple macro tailwinds converging

**Adjustment:**
- Macro -3 to -2: Add +20 to confidence threshold (much harder to take trades)
- Macro -1: Add +10 to confidence threshold
- Macro 0: No adjustment
- Macro +1: Subtract -5 from confidence threshold
- Macro +2 to +3: Subtract -10 from confidence threshold (easier to take trades)

### Stage 3: Market Structure Assessment

Determine the current market phase on the HIGHER timeframe (1H for 5M/15M entries, daily for 1H entries):

```
Inputs:
- EMA 200 slope (rising, flat, falling)
- Supertrend direction on higher TF
- ADX value (trending strength)
- Recent swing highs and swing lows pattern
- Bollinger Band width (squeezed, normal, expanded)
```

**Output:** Market regime classification
- **Trending up:** EMA 200 rising + Supertrend green + ADX > 25 + higher highs, higher lows
- **Trending down:** EMA 200 falling + Supertrend red + ADX > 25 + lower highs, lower lows
- **Ranging:** EMA 200 flat + Supertrend flipping frequently + ADX < 20
- **Breakout pending:** Bollinger squeeze + ADX < 15 + tight range for 20+ candles
- **High volatility:** ATR > 2x average + wide Bollinger + ADX may be high or low

**Strategy selection based on regime:**
- Trending up → longs only, use Supertrend for entries, trend follow
- Trending down → shorts only, use Supertrend for entries, trend follow
- Ranging → both directions, use RSI/Bollinger for mean reversion
- Breakout pending → wait for breakout with volume, then enter with the direction
- High volatility → reduce position size, widen stops, trade only highest confidence

### Stage 4: Positioning Assessment

Read the current market positioning:

```
Inputs:
- Funding rate (current + z-score vs 30-day mean)
- Open interest (current + 24h delta + direction relative to price)
- Long/short ratio (if available)
- Liquidation clusters above and below current price
- Cross-exchange confirmation (do Binance, Bybit, OKX agree with MEXC?)
```

**Output:** Positioning bias
- **Longs crowded:** Funding strongly positive + OI high + long/short ratio > 1.5 → contrarian SHORT bias
- **Shorts crowded:** Funding strongly negative + OI high + long/short ratio < 0.7 → contrarian LONG bias (squeeze setup)
- **Neutral:** Funding near zero + OI stable → no positioning bias, trade on technicals
- **Deleveraging:** OI dropping rapidly + funding normalising → leverage flush in progress, wait for it to complete

### Stage 5: Technical Signal Detection

Now look at the entry timeframe indicators:

```
Inputs (per pair, per timeframe):
- RSI fast (6) and slow (24) values
- MACD histogram value and direction (growing/shrinking)
- Bollinger Band position (%B — where is price within the bands)
- Supertrend direction and distance from current price
- Volume ratio (current vs 20-period average)
- ATR (current volatility level)
```

**For a LONG signal, calculate confidence:**
- RSI contribution (0-30 points): deeper oversold = more points
- MACD contribution (0-20 points): negative + shrinking = maximum points
- EMA contribution (0-15 points): above EMA 200 = maximum points
- Bollinger contribution (0-15 points): at or below lower band = maximum points
- Volume contribution (0-10 points): high volume spike = maximum points
- Funding contribution (0-10 points): negative funding = maximum points

**For a SHORT signal, mirror the above inverted.**

Total confidence: 0-100 scale.

### Stage 6: Confluence Scoring

Combine all stages into a final decision:

```
Base confidence: from Stage 5 (0-100)
Macro adjustment: from Stage 2 (+/- 10-20 points)
Regime alignment: 
  - Signal matches regime direction: +10
  - Signal neutral to regime: +0
  - Signal fights regime: -15 (dangerous)
Positioning alignment:
  - Positioning supports signal (e.g., shorts crowded for a long): +10
  - Positioning neutral: +0
  - Positioning fights signal (e.g., longs crowded for a long): -10
News multiplier: from Research Agent (0.0x to 1.15x)

Final confidence = (base + macro_adj + regime_adj + positioning_adj) × news_multiplier
```

### Stage 7: Trade or No Trade

Compare final confidence against session threshold:

| Session | Threshold |
|---------|----------|
| Asia | 65 |
| London | 45 |
| London-NY Overlap | 35 |
| New York | 40 |
| Wind-down | 50 |

**If final confidence >= threshold: PROCEED to Stage 8**
**If final confidence < threshold: NO TRADE**

### Stage 8: Position Sizing and Execution

```
Inputs:
- Account balance
- Risk per trade (based on confidence level: 0.75% to 2.0%)
- ATR on entry timeframe
- Stop multiplier (based on confidence: 0.75x to 2.0x ATR)

Calculations:
- risk_amount = balance × risk_per_trade
- stop_distance = ATR × stop_multiplier
- position_size = risk_amount / stop_distance
- leverage = (position_size × price) / balance
- take_profit = entry ± (stop_distance × R:R_ratio)

Checks:
- Is leverage within limits? (5M: max 20x, 15M: max 15x, 1H: max 10x)
- Is position count within limit? (max 3)
- Is this pair correlated with an open position? (correlation < 0.85)
- Is portfolio heat within limit? (total risk across all positions < 4.5%)
```

**If ALL checks pass: EXECUTE the trade**
**If ANY check fails: ADJUST or REJECT**

### Stage 9: Post-Entry Management

Once the trade is live:
- Monitor for stop loss and take profit hits
- At +0.5R: move stop to breakeven
- At +1R: take 50% off, trail rest
- At +1.5R: take another 25% off
- If thesis changes (news event, regime shift): close manually
- If maximum hold time exceeded: close at current price
- Log everything — entry indicators, exit indicators, outcome, reasoning

---

## Part 3: The Spot Accumulation Strategy

### When to accumulate spot

The system should identify ACCUMULATION WINDOWS — periods when smart money is buying and retail is selling. These windows are characterised by:

**On-chain signals (when available):**
- Exchange outflows increasing (coins moving OFF exchanges = accumulation)
- Stablecoin inflows to exchanges increasing (dry powder arriving = buying imminent)
- Whale wallets increasing their holdings
- Long-term holder supply increasing
- Miner accumulation (not selling)

**Market structure signals:**
- Price in the lower 25% of its 52-week range
- RSI on weekly timeframe below 40
- Fear & Greed Index below 25 (extreme fear)
- BTC dominance rising (money flowing to safety within crypto)
- Multiple capitulation events in recent weeks (liquidation cascades, exchange failures)

**Macro signals:**
- Fed signalling future rate cuts (even if not cutting yet)
- DXY showing signs of peaking
- VIX elevated but starting to decline from extreme
- Gold rallying (hard asset demand increasing)

### How to accumulate

**Method 1 — DCA from futures profits**
- Every week, transfer 20-30% of net futures profits to spot account
- Buy BTC and/or ETH at market price regardless of short-term direction
- This averages in over time and removes timing pressure
- Simple, disciplined, no overthinking required

**Method 2 — Strategic buys during fear events**
- When Fear & Greed Index drops below 20
- When weekly RSI drops below 30
- When multiple crash events have occurred recently
- Buy spot in larger chunks (5-10% of available capital per buy)
- These are the "blood in the streets" moments

**Method 3 — Institutional accumulation mirroring**
- Watch for signs of institutional buying (ETF inflows, whale wallet growth)
- Buy spot when institutions are buying but retail is selling
- The divergence between smart money and dumb money is the signal
- Requires on-chain data (Glassnode/CryptoQuant) for best results

### Spot allocation rules

- Never spend more than 50% of total capital on spot at any time
- Maintain a cash reserve for futures margin and emergencies
- Split spot holdings: 70% BTC, 30% ETH (or adjust based on cycle position)
- Never sell spot during drawdowns — the whole point is long-term holding
- Only sell spot during euphoria phases (RSI weekly above 85, extreme greed, BTC dominance falling rapidly)

### The cycle-aware accumulation framework

Based on the Bitcoin halving cycle (approximately 4 years):

**Year 1 post-halving (2024-2025): Bull market building**
- Accumulate moderately during pullbacks
- Focus more on futures income (volatility is high)
- Buy spot during 20%+ corrections

**Year 2 post-halving (2025-2026): Potential peak and distribution**
- Reduce spot accumulation
- Begin planning to sell portions of spot near cycle top
- Focus on futures income with both long and short positions
- Watch for extreme greed + declining BTC dominance = cycle top signal

**Year 3-4 post-halving (2026-2028): Bear market / accumulation**
- Maximum spot accumulation phase
- Buy aggressively during capitulation events
- Futures income is harder (less volatility, more choppy)
- This is where the biggest long-term gains are made — buying when nobody wants to buy

---

## Part 4: The Complete Reasoning Output Format

When the LLM evaluates a potential trade, it should output a structured response:

```
=== FINDING ALPHA — Trade Evaluation ===

MACRO CONTEXT:
  DXY: [value, direction] → [impact]
  SPY: [value, direction] → [impact]
  VIX: [value] → [regime]
  News: [sentiment score] → [multiplier]
  Macro score: [X/6] → confidence adjustment [+/- Y]

MARKET STRUCTURE:
  Regime: [trending up/down, ranging, breakout pending, high vol]
  Higher TF bias: [bullish/bearish/neutral]
  Strategy selected: [mean reversion / trend follow / breakout]

POSITIONING:
  Funding: [value, z-score] → [crowded long/short/neutral]
  OI: [delta, direction] → [new positions / liquidations]
  Liquidation clusters: [above at $X, below at $Y]
  Positioning bias: [contrarian long/short/neutral]

TECHNICAL SIGNAL:
  Pair: [symbol]
  Timeframe: [5M/15M/1H]
  RSI: [value] → [X points]
  MACD: [histogram, direction] → [X points]
  EMA: [position] → [X points]
  Bollinger: [%B] → [X points]
  Volume: [ratio] → [X points]
  Funding: [value] → [X points]
  Supertrend: [direction]
  Base confidence: [X/100]

CONFLUENCE:
  Base: [X]
  Macro adj: [+/- Y]
  Regime adj: [+/- Z]
  Positioning adj: [+/- W]
  News multiplier: [V]x
  Final confidence: [result]
  Session threshold: [threshold]

DECISION: [TRADE / NO TRADE]
  Direction: [LONG / SHORT]
  Reasoning: [2-3 sentences explaining WHY]

EXECUTION (if TRADE):
  Entry: $[price]
  Stop loss: $[price] ([X]x ATR)
  Take profit 1: $[price] (1:1 R:R, close 50%)
  Take profit 2: $[price] (1:1.5 R:R, trail rest)
  Position size: [X] units ($[Y] notional)
  Risk amount: $[Z] ([W]% of account)
  Leverage: [X]x
```

This structured output ensures every decision is traceable, auditable, and learnable. The Analytics Agent logs the full output for every evaluation, including NO TRADE decisions. This creates the dataset for future ML training — not just what the system traded, but what it CHOSE NOT to trade and why.

---

## Part 5: Decision Shortcuts — When to Act Immediately

Some situations don't need the full 9-stage evaluation:

### Immediate STOP trading:
- Exchange hack/insolvency news → block all trades, close marginal positions
- Stablecoin depeg detected → block all trades
- Kill switch approached (-12% drawdown) → reduce to 1 position max
- System error detected → pause until resolved

### Immediate CLOSE positions:
- Major unexpected news event occurs with open positions
- VIX spikes above 40 with leveraged positions open
- Exchange API starts returning errors → close everything, verify stops on exchange
- Flash crash (-5% in 5 minutes) with longs open → close longs, evaluate for short

### Immediate OPPORTUNITY:
- Extreme negative funding + RSI < 20 + volume spike + support level + higher TF Supertrend green → SHORT SQUEEZE SETUP. High confidence long. Act fast — these resolve within hours.
- Extreme positive funding + RSI > 80 + volume spike + resistance level + higher TF Supertrend red → LONG SQUEEZE SETUP. High confidence short.
- Post-capitulation (OI collapsed 30%+, funding extreme, RSI single digits) + news stabilising → BOTTOM FORMATION. Enter cautiously with reduced size.

---

## Part 6: Learning and Adaptation

### What the system should track over time

For every trade (both taken and rejected):
- The confidence score and each component
- The actual outcome (win/loss/breakeven)
- The maximum favourable excursion (how far it went in your favour)
- The maximum adverse excursion (how far it went against you before recovering or stopping out)
- Time to outcome (how many candles until SL or TP hit)
- Which indicators were most accurate for this specific setup

### How to identify strategy decay

If the system notices:
- Win rate dropping below 50% over 20+ trades → strategy may be failing
- Average P&L turning negative → risk/reward is off
- Stops being hit more frequently → market regime may have changed
- Confidence 60+ trades losing more than confidence 40 trades → the scoring is miscalibrated

Alert the CEO and recommend pausing for review.

### Continuous improvement cycle

1. Trade for 2 weeks with current parameters
2. Review all trades — which worked, which didn't, why
3. Identify patterns in winners vs losers
4. Adjust indicator weights, thresholds, or strategy selection
5. Paper trade the adjustments for 1 week
6. If improved, deploy. If not, revert.
7. Repeat.

The system never stops learning. Every trade is data. Every day refines the model. The firm that stops learning stops earning.

---

## Part 7: The Asset Management Firm Mindset

### You are not a trader. You are a firm.

A trader takes trades. A firm manages risk, allocates capital, generates income, builds wealth, and reports to stakeholders. Finding Alpha operates as a firm:

- **Data Agent** = the analyst desk, gathering intelligence
- **Math Agent** = the quant team, crunching numbers
- **Research Agent** = the macro research division, reading the world
- **Position Agent** = the portfolio manager, sizing allocations
- **Risk Agent** = the chief risk officer, with absolute veto power
- **Execution Agent** = the trading desk, placing orders
- **Analytics Agent** = the performance team, tracking results
- **Manager** = the COO, coordinating everything
- **LLM (Ollama/Claude)** = the CIO, making strategic decisions
- **CEO (Ibrahim)** = sets the mission, reviews results, makes final calls

This is not a bot. This is an organisation. Each component has a role. Each role has boundaries. The whole is greater than the sum of its parts because they collaborate through Matrix — the shared intelligence layer where every data point connects to every other.

The firm's competitive advantages:
1. Never sleeps — operates 24/7 across all sessions
2. Never emotional — no revenge trading, no FOMO, no panic
3. Contextually aware — reads news AND market data together
4. Continuously learning — every trade improves the next
5. Scalable — same architecture works from $1,000 to $1,000,000
6. Adaptable — switches strategies based on market regime
7. Disciplined — risk rules are absolute, no exceptions

This is Finding Alpha. An AI quant firm that finds the edge others miss.
