# Finding Alpha — Strategy & Indicator Intelligence

> This document is the core knowledge base for the Finding Alpha trading intelligence system.
> It teaches the reasoning engine how markets work, how indicators function individually and together,
> what different market conditions look like, and how to select the right strategy for the current environment.
> This is not a rulebook — it is a thinking framework. The system should reason from principles, not follow rigid scripts.

---

## Part 1: How Markets Actually Work

### Price is driven by supply and demand imbalance

At every moment, there are people wanting to buy and people wanting to sell. Price moves when one side overwhelms the other. If more people want to buy than sell at the current price, price rises until enough sellers appear. If more people want to sell than buy, price falls until enough buyers step in.

This is not random. Large moves happen because of:
- Forced liquidations (leveraged traders getting wiped out, creating cascade selling or buying)
- News events (geopolitical, economic, regulatory — shifts sentiment across millions of participants simultaneously)
- Institutional flows (hedge funds, banks, ETF inflows/outflows — large capital moving in one direction)
- Technical levels (many traders watch the same support/resistance levels, creating self-fulfilling reactions)
- Session transitions (different global participants come online and react to what happened while they were asleep)

### Markets alternate between two states

**Trending:** Price moves persistently in one direction. Pullbacks are shallow and short-lived. Trying to catch reversals during a trend is dangerous — "don't fight the trend."

**Ranging/Mean-reverting:** Price oscillates around a central value. Moves to extremes tend to reverse. Buying at the bottom of the range and selling at the top is profitable — "buy low, sell high."

The critical skill is identifying which state the market is currently in. Applying a mean reversion strategy during a strong trend loses money. Applying a trend following strategy during a range loses money. The system must detect the current regime and adapt.

### Volatility clusters

Markets go through periods of high volatility and low volatility. These cluster together — volatile periods tend to stay volatile, calm periods tend to stay calm. But transitions between them are often sudden and violent. A long period of low volatility (tight Bollinger Bands, low ATR) often precedes a sudden explosive move. This is the Bollinger squeeze phenomenon.

### Liquidity and market structure

Price doesn't move in a vacuum. It moves through an order book where buy orders (bids) and sell orders (asks) are stacked at different levels. When price moves through an area with thin orders, it moves fast. When it hits a wall of orders, it slows down or reverses.

Stop losses are clustered at obvious levels — just below support, just above resistance. Smart money (institutions, market makers) knows where these stops are and often pushes price into them to trigger forced selling/buying, then reverses. This is the "liquidity grab" or "stop hunt" that frequently occurs at session opens, especially London.

---

## Part 2: Trading Strategies — When Each One Works

### Strategy 1: Mean Reversion

**Core idea:** When price moves too far from its average, it tends to snap back. Like a rubber band — stretch it too far and it returns.

**When it works:**
- Ranging/sideways markets
- After panic selling or euphoric buying that exhausts participants
- At established support and resistance levels
- When volume spikes indicate forced liquidations (everyone who wanted to sell already sold)

**When it fails:**
- During strong trends — price keeps going instead of reverting
- During structural breaks — the "average" itself is shifting (e.g., exchange collapse, regulatory ban)
- During low volume drifts — price moves slowly without conviction, no real snap-back force

**Key indicators:** RSI (oversold/overbought extremes), Bollinger Bands (price at the walls), funding rate (crowded positioning), volume spikes (exhaustion)

### Strategy 2: Trend Following

**Core idea:** Once a trend establishes, it tends to continue. Jump on the moving train and ride it.

**When it works:**
- After breakouts from consolidation ranges
- During macro momentum shifts (new bull or bear market beginning)
- When volume confirms the trend direction
- During news-driven moves that fundamentally change the outlook

**When it fails:**
- In choppy, sideways markets — you get whipsawed buying high and selling low
- At the end of exhausted trends — you enter just as the trend is dying
- During fakeout breakouts — price briefly breaks a level then reverses

**Key indicators:** EMA crossovers, Supertrend, MACD direction, ADX (trend strength), price making higher highs and higher lows (uptrend) or lower highs and lower lows (downtrend)

### Strategy 3: Breakout Trading

**Core idea:** When price breaks out of a consolidation range or key level with conviction, it tends to continue in the breakout direction.

**When it works:**
- After long periods of tight consolidation (Bollinger squeeze)
- When volume confirms the breakout (high volume = real, low volume = fake)
- When the breakout aligns with the higher timeframe trend direction
- At key psychological levels or historical support/resistance

**When it fails:**
- Fakeout breakouts — price briefly pierces a level then reverses (very common)
- In choppy markets where there is no real consolidation preceding the breakout
- When volume is low — suggests the breakout lacks conviction

**Key indicators:** Bollinger Band width (squeeze detection), volume confirmation, Supertrend flip, support/resistance levels

### Strategy 4: Momentum/Scalping

**Core idea:** Ride short bursts of momentum. Quick in, quick out. Many small profits.

**When it works:**
- During high volume sessions (London-NY overlap)
- When multiple indicators align on short timeframes
- After news catalysts that create directional momentum
- In liquid markets with tight spreads

**When it fails:**
- During low volume (Asia session) — moves are small and unreliable
- In choppy, directionless markets — you get stopped out repeatedly
- When spreads widen during low liquidity

**Key indicators:** RSI on 5M, MACD histogram momentum, volume spikes, Supertrend on short timeframes

### How to detect the current regime

The system should continuously assess which regime is active:

- **ATR trending up + EMA 200 sloping clearly + Supertrend consistent colour for 20+ candles** = trending market, use trend following
- **ATR flat or declining + price oscillating around EMA 200 + Bollinger Bands narrowing** = ranging market, use mean reversion
- **ATR suddenly spikes + Bollinger Bands rapidly expanding + volume explosion** = breakout/volatility event, be cautious until direction is clear
- **RSI staying in 40-60 range + low volume + tight candles** = dead market, reduce activity

---

## Part 3: Technical Indicators — Complete Guide

### 3.1 RSI (Relative Strength Index)

**What it measures:** The speed and magnitude of recent price changes, expressed as a number between 0 and 100.

**How it works:** It compares the average size of up-moves to the average size of down-moves over a period. If price has been going up consistently, RSI is high. If down consistently, RSI is low.

**Two periods used:**
- RSI 6 (fast): Reacts quickly to recent moves. Shows the "right now" pulse. Useful for scalping timeframes.
- RSI 24 (slow): Smooths out noise. Shows the bigger picture momentum. Useful for confirming the fast RSI.

**How to interpret:**

| RSI Range | Meaning | Context Matters |
|-----------|---------|----------------|
| 0-15 | Extremely oversold | Rare. Either panic capitulation (bounce likely) or structural collapse (more downside) |
| 15-25 | Strongly oversold | Good long candidate IF other indicators confirm |
| 25-35 | Moderately oversold | Possible long, needs strong confirmation |
| 35-65 | Neutral zone | No directional signal from RSI alone |
| 65-75 | Moderately overbought | Possible short, needs strong confirmation |
| 75-85 | Strongly overbought | Good short candidate IF other indicators confirm |
| 85-100 | Extremely overbought | Rare. Either euphoric blow-off top (reversal likely) or parabolic breakout |

**Critical nuance: RSI divergence**

When price makes a new low but RSI makes a higher low, selling momentum is weakening even though price is still falling. This is "bullish divergence" — one of the strongest reversal signals. The reverse (price makes new high but RSI makes lower high) is "bearish divergence."

**The trap:** RSI can stay oversold for days during a real crash. RSI below 20 during the Luna collapse or FTX implosion would have been a losing long entry. The system must consider WHY RSI is oversold, not just that it IS oversold.

### 3.2 MACD (Moving Average Convergence Divergence)

**What it measures:** Whether momentum is accelerating or decelerating.

**Components:**
- DIF line (MACD line): The gap between the 12-period EMA and 26-period EMA. When the fast EMA pulls away from the slow EMA, momentum is strong.
- DEA line (Signal line): A 9-period EMA of the DIF line. Smooths out the MACD.
- Histogram: The difference between DIF and DEA. THIS IS THE MOST IMPORTANT COMPONENT.

**How to interpret the histogram:**

- **Solid green bars (getting bigger):** Buying momentum accelerating. Buyers pressing the gas harder. Strong bullish.
- **Hollow green bars (getting smaller):** Buying momentum fading. Buyers easing off. Warning that the move may be ending.
- **Solid red bars (getting bigger):** Selling momentum accelerating. Sellers pressing the gas harder. DO NOT buy into this.
- **Hollow red bars (getting smaller):** Selling momentum fading. Sellers running out of steam. This is where bounces start.

**Key signals:**
- Histogram crossing zero from negative to positive: Momentum has officially flipped bullish. This is equivalent to the fast EMA crossing above the slow EMA.
- Histogram crossing zero from positive to negative: Momentum has officially flipped bearish.
- Histogram shrinking: The current force (buying or selling) is losing strength regardless of which side of zero it's on.

**MACD divergence:** Same concept as RSI divergence. Price makes a new low but MACD histogram makes a higher low — bullish divergence. Very strong signal.

### 3.3 EMA (Exponential Moving Average)

**What it measures:** The smoothed average price over a period, weighted toward recent data.

**Key EMAs:**
- EMA 10: Very fast, hugs price closely. Used for short-term trend on scalping timeframes.
- EMA 20: Fast. Often used as dynamic support/resistance on 15M and 1H charts.
- EMA 50: Medium. The intermediate trend. Institutional traders watch this.
- EMA 200: The big picture trend. THE most widely watched moving average in all of finance. Price above EMA 200 = bull market. Price below = bear market.

**How to interpret:**
- Price above EMA: The market is performing better than its recent average. Bullish bias.
- Price below EMA: The market is performing worse than its recent average. Bearish bias.
- EMA slope: A rising EMA confirms an uptrend. A flat EMA suggests ranging. A falling EMA confirms a downtrend. The slope matters as much as the position.

**EMA crossovers:**
- Golden cross: Short EMA crosses above long EMA. Bullish signal. The shorter the EMAs, the more frequent but less reliable the signal.
- Death cross: Short EMA crosses below long EMA. Bearish signal.
- EMA 50 crossing above EMA 200 is a major institutional signal that often triggers large capital flows.

**EMA as dynamic support/resistance:** During uptrends, price often bounces off the EMA 20 or EMA 50 like a floor. During downtrends, price often gets rejected at these EMAs like a ceiling. When price "respects" an EMA (bounces off it multiple times), that EMA becomes a key level to watch.

### 3.4 Bollinger Bands

**What it measures:** How far price has deviated from its recent average, adjusted for current volatility.

**Components:**
- Middle band: 20-period simple moving average (the centre of the hallway)
- Upper band: Middle + 2 standard deviations (the ceiling)
- Lower band: Middle - 2 standard deviations (the floor)

**How to interpret:**
- Price touching upper band: Stretched unusually high. Overbought. Potential short in ranging markets, but can "walk the band" in strong uptrends.
- Price touching lower band: Stretched unusually low. Oversold. Potential long in ranging markets, but can "walk the band" in strong downtrends.
- Price in the middle: Normal. No extreme signal.

**Band width — the squeeze:**
- Narrow bands (low bandwidth): Volatility is compressed. The market is coiling. A big move is coming but direction is unknown. Prepare for a breakout.
- Wide bands (high bandwidth): Volatility is expanded. The market has just made a big move. Bands will eventually contract again.
- The transition from narrow to wide is the breakout moment. The direction of the breakout (up or down out of the squeeze) determines the trade.

**%B indicator:** Measures where price is within the bands. 0 = at lower band, 0.5 = at middle, 1.0 = at upper band. Below 0 or above 1 means price has broken outside the bands. Useful for quantifying how extreme the position is.

**Walking the band:** In strong trends, price can stay pressed against one band for extended periods. The upper band becomes dynamic support in a strong uptrend. The lower band becomes dynamic resistance in a strong downtrend. This is where mean reversion fails and trend following works. Identifying band walks early is critical to avoiding false reversal entries.

### 3.5 ATR (Average True Range)

**What it measures:** The average size of recent candles — how much price typically moves per candle. It's the market's heartbeat.

**How it's calculated:** For each candle, the "true range" is the largest of: high minus low, high minus previous close, low minus previous close. ATR is the average of true ranges over 14 periods.

**How to interpret:**
- ATR rising: Volatility is increasing. Candles are getting bigger. The market is becoming more active.
- ATR falling: Volatility is decreasing. Candles are getting smaller. The market is calming down.
- ATR at extreme highs: A volatile event is underway (crash, breakout, news-driven move). Stops need to be wider.
- ATR at extreme lows: The market is dead quiet. A breakout is likely coming (similar to Bollinger squeeze).

**Practical uses:**
- Stop loss placement: Set stops at 1.5x-2.5x ATR from entry. This ensures the stop is outside normal noise but close enough to protect capital. Tight stops (1.5x) for high-confidence trades, wide stops (2.5x) for lower confidence.
- Position sizing: risk_amount / (ATR * stop_multiplier) = position size. This automatically sizes the trade proportional to current volatility.
- Volatility detection: ATR percentile rank tells you if current volatility is historically high or low for this asset.

### 3.6 Supertrend

**What it measures:** The direction of the prevailing trend using a combination of ATR and a multiplier, plotted as a line on the price chart that flips between support (below price, green) and resistance (above price, red).

**How it's calculated:**
- Upper band = (high + low) / 2 + (multiplier × ATR)
- Lower band = (high + low) / 2 - (multiplier × ATR)
- When price closes above the upper band, the Supertrend flips to bullish (green, plotted below price)
- When price closes below the lower band, the Supertrend flips to bearish (red, plotted above price)

**Default settings:** ATR period 10, multiplier 3. For more responsive signals, use ATR 7 and multiplier 2. For smoother, fewer signals, use ATR 14 and multiplier 3.

**How to interpret:**
- Green line below price: Uptrend is active. The line acts as dynamic support. Price bouncing off the green line is a buying opportunity within the trend.
- Red line above price: Downtrend is active. The line acts as dynamic resistance. Price getting rejected at the red line is a shorting opportunity within the trend.
- Flip from red to green: Trend reversal to bullish. Potential long entry. More reliable when confirmed by volume and other indicators.
- Flip from green to red: Trend reversal to bearish. Potential short entry.

**Triple Supertrend strategy:**
Using three Supertrend lines with different settings provides better signal quality:
- Supertrend 1: ATR 10, Multiplier 1 (fast, reactive)
- Supertrend 2: ATR 11, Multiplier 2 (medium)
- Supertrend 3: ATR 12, Multiplier 3 (slow, smooth)

When 2 out of 3 agree on direction AND the trend aligns with EMA 200, the signal is high quality. When all 3 agree, it's the strongest signal.

**Combining Supertrend with mean reversion:**
- Supertrend shows the trend direction
- RSI shows when price is oversold WITHIN that trend
- The best mean reversion trades happen when RSI is oversold but Supertrend is still green (bullish) — you're buying a dip within an uptrend, not fighting the trend
- If RSI is oversold AND Supertrend is red, mean reversion is risky because you're fighting the trend

**Strengths:** Extremely clear visual signals. Works brilliantly in trending markets. Great for trailing stop losses.
**Weakness:** Generates false signals in sideways/choppy markets. The line flips back and forth producing whipsaws. Must be filtered by other indicators.

### 3.7 Volume

**What it measures:** How many units (or dollars) were traded during a period. It measures participation and conviction.

**How to interpret:**
- High volume on a price move: The move has conviction. Many participants agree on the direction. Likely to continue.
- Low volume on a price move: The move lacks conviction. Few participants involved. Likely to reverse or fizzle out.
- Volume spike during a selloff: Panic selling. Forced liquidations. Capitulation. Often marks the bottom because everyone who wanted to sell has sold.
- Volume spike during a rally: Euphoric buying. FOMO. Can mark the top if the buying exhausts itself.
- Declining volume during a trend: The trend is losing participation. Warning that the trend may be ending.

**Volume ratio:** Current volume divided by the 20-period average volume. A ratio above 1.5x indicates meaningful activity. Above 3x indicates an extreme event.

**On-balance volume (OBV):** Cumulative volume that adds volume on up days and subtracts on down days. When OBV is rising while price is flat, smart money is accumulating (bullish). When OBV is falling while price is flat, smart money is distributing (bearish).

### 3.8 Funding Rate (Crypto Futures Specific)

**What it measures:** Which side (longs or shorts) is more crowded in the futures market. It's a fee exchanged between longs and shorts every 8 hours.

**How to interpret:**
- Positive funding: Longs pay shorts. Too many people are long. The crowd expects price to go up. Contrarian signal: if everyone is already long, who is left to buy?
- Negative funding: Shorts pay longs. Too many people are short. The crowd expects price to go down. Contrarian signal: if everyone is already short, who is left to sell?
- Extreme positive (> +0.05%): Longs are extremely crowded. High risk of a long squeeze cascade.
- Extreme negative (< -0.05%): Shorts are extremely crowded. High risk of a short squeeze cascade.

**Short squeeze mechanics:** When shorts are crowded (negative funding) and price bounces even slightly, some shorts start losing money. The most leveraged ones get liquidated (forced to buy). That forced buying pushes price higher, which liquidates more shorts, which pushes price higher. Chain reaction upward. This is why negative funding + oversold RSI is the ideal long setup.

### 3.9 Open Interest

**What it measures:** The total number of active futures contracts. Every position (long or short) adds to OI. When someone opens a new position, OI rises. When someone closes, OI falls.

**How to interpret during a price drop:**
- OI rising during a drop: New shorts are entering the market. Fresh selling pressure. More downside likely. NOT the time for mean reversion.
- OI falling during a drop: Existing longs are closing (capitulating). They're giving up and leaving. The selling is from exits, not new entries. Once they're all gone, selling stops. Potential bottom.

**How to interpret during a price rise:**
- OI rising during a rally: New longs entering. Fresh buying pressure. Rally has fuel.
- OI falling during a rally: Shorts are closing (covering). The buying is from exits, not new conviction. Rally may not sustain.

### 3.10 Correlation

**What it measures:** How similarly two assets move. Ranges from -1 (perfect inverse) to +1 (perfect together). Zero means no relationship.

**Key crypto correlations:**
- BTC/ETH: Typically 0.85-0.92. They move almost identically. Holding both is essentially one position with double exposure.
- BTC/SOL: Typically 0.80-0.88. Similar but SOL has more independent moves.
- BTC/XRP: Typically 0.70-0.82. More independent than ETH but still correlated.

**Why it matters for risk:** If you open a long on BTC and a long on ETH, you think you have two separate trades. You don't. You have one trade with double the risk. If BTC drops, ETH drops with it, and you lose on both simultaneously.

**Correlation is not constant.** During calm markets, correlations can be lower (assets do their own thing). During crashes, correlations spike toward 1.0 — everything drops together. This is called "correlation convergence" and it's when diversification fails most.

### 3.11 ADX (Average Directional Index)

**What it measures:** The strength of the current trend, regardless of direction. It doesn't tell you if the trend is up or down, just how strong it is.

**How to interpret:**
- ADX below 20: No meaningful trend. Ranging/sideways market. Use mean reversion strategies.
- ADX 20-40: Trend is developing or moderate. Can use either trend following or mean reversion depending on other indicators.
- ADX above 40: Strong trend in place. Use trend following. Avoid mean reversion — the trend will overpower reversals.
- ADX above 60: Extremely strong trend. Rare. Very dangerous to counter-trade.

**ADX rising:** Trend is strengthening regardless of direction.
**ADX falling:** Trend is weakening. Possible transition to ranging.

**Combining ADX with Supertrend:** When ADX is above 25 and Supertrend is green, the uptrend is confirmed and strong. When ADX is below 20 and Supertrend keeps flipping, the market is choppy and Supertrend signals should be ignored.

### 3.12 VWAP (Volume Weighted Average Price)

**What it measures:** The average price weighted by volume throughout the trading session. It shows the "fair value" price based on where the most trading volume occurred.

**How to interpret:**
- Price above VWAP: Buyers are in control. The majority of the day's volume was traded at lower prices, so current buyers are paying above average.
- Price below VWAP: Sellers are in control. The majority of volume was traded at higher prices.
- VWAP as dynamic support/resistance: Institutional traders often use VWAP as a benchmark. Price tends to gravitate toward it.

**Useful for intraday trading:** VWAP resets each day. It's most relevant for within-session trades.

### 3.13 Stochastic RSI

**What it measures:** The RSI of the RSI — it applies the stochastic oscillator formula to RSI values. This makes it more sensitive than standard RSI and oscillates between 0 and 1.

**How to interpret:**
- Above 0.8: Overbought
- Below 0.2: Oversold
- Crossover of the K and D lines: Trading signal (similar to MACD crossover but for the oscillator)

**Advantage over standard RSI:** More sensitive, generates signals earlier. Useful on short timeframes where standard RSI might not reach extreme levels.
**Disadvantage:** More false signals due to increased sensitivity.

### 3.14 Ichimoku Cloud

**What it measures:** Multiple aspects of the market at once — trend direction, support/resistance, and momentum. It consists of five lines and a "cloud" formed between two of them.

**Quick interpretation:**
- Price above the cloud: Bullish
- Price below the cloud: Bearish
- Price inside the cloud: Indecisive
- Thick cloud: Strong support/resistance
- Thin cloud: Weak support/resistance, potential breakout zone

**Most useful for:** Identifying the overall trend context quickly. If the cloud is bullish and thick, mean reversion longs have strong structural support.

---

## Part 4: Indicator Combinations — How They Work Together

### The principle: no indicator works alone

Every indicator has strengths and weaknesses. RSI can stay oversold during crashes. MACD lags behind price. Supertrend generates whipsaws in ranges. Volume can be misleading during low-liquidity sessions. The power comes from combining multiple indicators that confirm each other from different angles.

### Combination 1: Mean Reversion Setup (Primary Strategy)

**Required:**
- RSI below 25 (oversold extreme)
- MACD histogram negative AND shrinking (sellers fading)
- Price at or below lower Bollinger Band (abnormally low)

**Strengthening factors:**
- Volume spike above 1.5x average (capitulation selling)
- Funding rate negative (shorts crowded — squeeze potential)
- Open interest dropping (longs capitulating — exhaustion)
- Supertrend still green on higher timeframe (dip within uptrend, not trend reversal)
- EMA 200 above price on higher timeframe (bull market context)

### Combination 2: Trend Following Setup

**Required:**
- Supertrend green (uptrend active)
- Price above EMA 200 (bull market confirmed)
- ADX above 25 (trend has strength)

**Entry trigger:**
- RSI pulls back to 40-50 range (healthy pullback within trend)
- Price touches Supertrend line or EMA 20 (dynamic support test)
- MACD histogram positive and growing (momentum resuming)
- Volume increasing on the bounce (buyers returning)

### Combination 3: Breakout Setup

**Required:**
- Bollinger Band width at a low percentile (squeeze — tight bands)
- ATR at recent lows (volatility compressed)
- Price consolidating in a narrow range for 20+ candles

**Entry trigger:**
- Price breaks above upper Bollinger Band with volume spike
- Supertrend flips to green
- MACD crosses zero line from negative to positive
- Volume is 2x+ average on the breakout candle

### Combination 4: Short Squeeze Setup

**Required:**
- Funding rate strongly negative (< -0.03%)
- Open interest high (many shorts in the market)
- RSI oversold (price has been pushed down)
- MACD histogram shrinking (selling pressure fading)

**Entry:** Long. A small bounce can trigger a cascade of short liquidations, creating a self-reinforcing upward move.

### How indicators can conflict — and what to do

When RSI says oversold but Supertrend is red and EMA 200 is above price, the indicators are conflicting. RSI suggests a long, but the trend indicators suggest the downtrend is intact.

**Resolution framework:**
1. Higher timeframe wins. If the 1H Supertrend is red, 5M RSI oversold signals are suspect.
2. Trend indicators beat oscillators in trending markets. If ADX is above 30, trust Supertrend over RSI.
3. Oscillators beat trend indicators in ranging markets. If ADX is below 20, trust RSI over Supertrend.
4. Volume is the tiebreaker. If volume confirms the move, the move is real regardless of what other indicators say.

---

## Part 5: Risk and Position Management Principles

### Position sizing must be mathematical

Never decide position size based on "feeling confident" or "this looks like a sure thing." Every position is sized by:

```
risk_amount = account_balance × risk_per_trade (0.25%)
stop_distance = ATR × stop_multiplier (1.5x to 2.5x)
position_size = risk_amount / stop_distance
```

Higher confidence trades get tighter stops (1.5x ATR) which allows larger positions within the same risk budget. Lower confidence trades get wider stops (2.5x ATR) which forces smaller positions.

### Stop loss is non-negotiable

Every position must have a stop loss set ON THE EXCHANGE (not just in the system). This ensures capital protection even if the entire system crashes. A position without a stop loss does not exist in this system.

Never move a stop loss further away from entry. You can move it closer (trailing stop to lock in profit) but never wider. Widening a stop is the first step to blowing up an account.

### The risk hierarchy

1. Per-trade risk (0.25%) — limits damage from any single trade
2. Concurrent position limit (3) — limits total exposure
3. Correlation check (0.85) — prevents hidden concentration
4. Losing streak breaker (3 consecutive) — catches regime changes early
5. Daily loss limit (-1.5%) — prevents catastrophic days
6. Daily profit target (+0.5%) — locks in gains, prevents overtrading
7. Max drawdown kill switch (-8%) — last line of defence

### Dollar-cost averaging (DCA)

Instead of entering full size at one price, split into layers:
- Layer 1 at initial trigger (1/3 size)
- Layer 2 if price moves further against you (1/3 at better price)
- Layer 3 at extreme level (final 1/3)

Each layer must pass its own analysis independently. DCA is not an excuse to average down on a losing trade. It's a structured approach to building a position when the setup is confirmed at multiple levels.

---

## Part 6: Market Sessions — Character and Patterns

### Asia Session (UTC 00:00-08:00 / Melbourne 11am-7pm)

**Character:** Quiet, low volume, narrow ranges. Tokyo, Hong Kong, Singapore, Sydney are active. Institutional activity is low. Price tends to drift sideways.

**What to expect:** Asia builds a range — a high and a low — that the next session will react to. The range is defined by the session's highest high and lowest low.

**Trading approach:** Mostly observe. Signals during Asia are unreliable due to low volume. Only trade extreme setups (very high confidence). Use this time to mark the range levels that London will target.

### London Session (UTC 08:00-17:00 / Melbourne 7pm-4am)

**Character:** Aggressive, high volume, fakeouts. European institutional money enters. This is where the day's first major moves happen.

**What to expect:** London's signature move is the liquidity grab. It pushes price OUTSIDE Asia's range to trigger stop losses, collects the liquidity, then reverses. This creates excellent mean reversion setups.

**Typical pattern:** 
1. London opens and price moves sharply in one direction
2. It breaks above Asia's high or below Asia's low
3. Stop losses are triggered, creating forced selling/buying
4. Within 30-90 minutes, price reverses
5. The reversal move often continues for several hours

**Trading approach:** Wait for the first 30 minutes to see which direction London pushes. Then watch for exhaustion signals (RSI oversold, MACD shrinking, volume spike). Enter the reversal when confirmed.

### London-NY Overlap (UTC 13:00-17:00 / Melbourne 12am-4am)

**Character:** Maximum volume, maximum volatility. Both London and New York are active simultaneously. This is the most important 4-hour window of the entire 24-hour cycle.

**What to expect:** The biggest, cleanest moves happen here. NYSE opens around 1:30 AM Melbourne time and often creates the single most volatile hour. US stock market movements drag crypto with them — if S&P dumps, BTC follows within minutes.

**Trading approach:** This is the prime zone. Be most active here. Confidence thresholds can be lower because the signal quality is highest due to volume. One clean trade during this window can hit the daily target.

### New York Solo (UTC 17:00-22:00 / Melbourne 4am-9am)

**Character:** Still active but slightly less volatile than the overlap. NY continues what it started or reverses. Volume gradually declines toward the end.

**Trading approach:** Still tradeable. Good for catching follow-through moves from the overlap. Reduce activity as the session winds down.

### Session Transitions — Where Opportunities Hide

The 30 minutes around each session open is the most volatile period. This is when the new session reacts to what the previous session did. The greatest volume imbalances and most forced liquidations occur during these transitions.

---

## Part 7: Adapting to Conditions

### The system should not apply one strategy rigidly

The intelligence engine should continuously assess:

1. **What is the current trend?** (EMA 200 slope, Supertrend direction, ADX value)
2. **How volatile is the market?** (ATR level, Bollinger width)
3. **What session is it?** (affects expected volume and move quality)
4. **What is the news context?** (crisis, uncertainty, or calm)
5. **What is the crowd positioning?** (funding rate, open interest)

Based on these inputs, the system selects the appropriate approach:

- Trending + high volatility + high volume session = trend following with Supertrend
- Ranging + moderate volatility + any session = mean reversion with RSI/Bollinger
- Low volatility + tight bands + any session = watch for breakout, prepare but don't enter
- Crisis news + any conditions = reduce exposure or stop trading entirely
- Extreme funding + oversold RSI = prioritise short squeeze setup

The ability to switch between strategies based on conditions is what separates an intelligent trading system from a fixed-rule algorithm.
