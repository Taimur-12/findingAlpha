# Finding Alpha — Historical Examples, Exchange Mechanics & Macro Correlations

> This document provides the intelligence engine with real-world examples of how specific market setups
> played out, exchange-specific mechanics that affect execution, and the macro correlation framework
> that connects crypto to traditional finance. These are not theoretical concepts — they are documented
> events with real prices, real timelines, and real outcomes that the system should pattern-match against.

---

## Part 1: Real Historical Market Events — What Actually Happened

### Example 1: The COVID Crash & Recovery (March 2020)

**Setup (March 12, 2020):**
- BTC price: dropped from $7,900 to $3,800 in 48 hours (-52%)
- RSI on daily: hit 8.7 — the lowest reading in BTC's history
- Volume: 5-10x average across all exchanges — pure panic liquidations
- Funding rate: plunged to -0.375% (8-hour rate) — extreme short crowding
- Open interest: collapsed by 40%+ as leveraged longs were wiped out
- S&P 500: dropped 9.5% on March 12 (circuit breaker triggered twice)
- VIX: spiked to 82.69 — highest since the 2008 financial crisis
- DXY: surged to 102.8 as everyone fled to USD cash

**What the indicators showed at the bottom ($3,800):**
- RSI 6: 4.2 (essentially zero — never seen before or since)
- MACD: histogram deeply negative but started showing TINY signs of shrinking on the 4H
- Bollinger Bands: price was 4 standard deviations below the mean — statistically impossible to sustain
- Volume: peaked at 8x on the crash candle, then started declining — capitulation exhaustion
- ATR: exploded to $1,200 (normally $300) — extreme volatility

**What happened next:**
- Day 1-3: Dead cat bounce from $3,800 to $5,500 on LOW volume (fake recovery)
- Day 4-7: Retest of $4,400 — HIGHER LOW than $3,800. RSI divergence appeared.
- Week 2: Recovery to $6,500 with increasing volume. MACD crossed zero.
- Week 4: Back at $7,000. Supertrend flipped green on daily.
- Month 3: $10,000. Full V-recovery.
- Month 12: $60,000. Parabolic bull run driven by Fed money printing.

**Lesson for the system:**
The bottom was identifiable in real-time by: RSI single digits + volume peak (capitulation) + funding extreme negative + OI collapse (forced longs liquidated = selling exhaustion). BUT the first bounce was a dead cat bounce (low volume). The real entry was on the retest at $4,400 when RSI showed divergence. The system should have bought the retest, not the first bounce.

---

### Example 2: Luna/Terra Collapse (May 2022)

**Setup (May 7-13, 2022):**
- UST stablecoin began losing its $1 peg, dropping to $0.98, then $0.90, then $0.10
- Luna (the backing token) went from $80 to $0.00001 — effectively zero
- BTC dropped from $40,000 to $26,700 over 6 days (-33%)

**What the indicators showed:**
- RSI on BTC daily: hit 18 on May 12 — deeply oversold
- Volume: massive but SUSTAINED over multiple days — not a single capitulation spike
- Funding: went negative but NOT extreme (-0.02%) — shorts weren't crowded enough for a squeeze
- OI: dropped significantly but new shorts kept opening (OI bouncing back up during the decline)
- MACD: deeply negative with NO signs of shrinking — momentum still accelerating downward

**Why this was NOT a buy signal despite RSI being oversold:**
- The selling was STRUCTURAL, not emotional. Luna's mechanism was broken — it mathematically had to keep printing and selling.
- Volume was sustained, not spiking and fading. No capitulation exhaustion pattern.
- OI was rising during the drop = new shorts entering, not just longs liquidating.
- The contagion was unknown — nobody knew which other firms had exposure to Luna.

**What happened next:**
- BTC bounced briefly to $31,000 (dead cat bounce on low volume)
- Then dropped further to $26,000
- Then Three Arrows Capital collapsed (June) → BTC to $17,500
- Then Celsius froze withdrawals → more selling
- Then FTX collapsed (November) → BTC to $15,400
- Total recovery time: 14 months to get back to $40,000

**Lesson for the system:**
When the cause of the crash is WITHIN the crypto ecosystem (exchange/protocol failure), do NOT apply mean reversion. The RSI will look oversold but the mean itself is shifting down. The system should identify structural vs emotional crashes:
- Emotional crash (war, tariffs, flash crash): mean reversion works. Buy the oversold.
- Structural crash (exchange failure, stablecoin depeg, fraud): mean reversion fails. Stay out.

---

### Example 3: FTX Collapse — The Contagion Chain (November 2022)

**Timeline:**
- Nov 2: CoinDesk publishes Alameda's balance sheet (FTT exposure revealed)
- Nov 6: Binance CEO announces FTT sell-off. FTT drops 10%.
- Nov 7: Bank run begins on FTX. $6 billion withdrawn in 72 hours.
- Nov 8: Binance offers to buy FTX. BTC drops 13% in one day.
- Nov 9: Binance withdraws offer. BTC drops another 14%. BTC at $15,800.
- Nov 11: FTX files bankruptcy.

**What the indicators showed on Nov 9 (potential bottom):**
- RSI daily: 22
- Volume: 4x average
- Funding: -0.08% (shorts crowded)
- OI: collapsed 30% in 48 hours

**Why the system should NOT have bought:**
- Despite "oversold" indicators, FTX's bankruptcy was just the beginning
- BlockFi, Celsius, Voyager — contagion chains were still unfolding
- Nobody knew the full scope of exposure
- The selling wasn't just futures — spot holders were panic-selling to get off exchanges entirely

**Recovery:**
- BTC bottomed at $15,400 in November 2022
- Didn't recover to $21,000 until January 2023
- Full recovery to $40,000+ took until January 2024
- Driven by ETF approval narrative and halving cycle

**Lesson:** When you see "exchange," "insolvency," "frozen withdrawals," "contagion" in the news — the system should halt ALL trading immediately. These events have cascading effects that take weeks to fully play out.

---

### Example 4: Trump Tariff Flash Crash (October 2025)

**Setup:**
- Oct 10: Large whale wallets opened massive short positions. No news. Unusual on-chain activity.
- Oct 11: Trump announces 100% tariff on all Chinese imports via Truth Social
- Immediate reaction: S&P drops 2%, BTC drops 10% within hours
- $19 billion in futures positions liquidated in 24 hours — largest single-day wipeout in crypto history

**What the indicators showed during the crash:**
- RSI 1H: dropped from 55 to 12 in 3 hours
- Volume: 6x average — pure liquidation cascade
- Funding: flipped from +0.02% to -0.05% within hours (longs liquidated, shorts took control)
- OI: dropped 25% (massive forced closure of leveraged longs)

**What made this DIFFERENT from Luna/FTX:**
- The cause was EXTERNAL (trade policy), not internal to crypto
- Crypto's infrastructure was fine — no exchange was broken
- The selling was 100% liquidation-driven, not structural
- Once the cascade completed, there were no more forced sellers

**Recovery:**
- Bottomed within 6-8 hours of the announcement
- Bounced 5% within 24 hours on reduced but increasing volume
- RSI divergence appeared on the retest
- Full recovery within 2 weeks

**Lesson:** External shock + liquidation cascade + intact infrastructure = buy the dip after capitulation confirms. The key signal was OI collapsing (longs wiped out = selling exhaustion) + volume peaking then declining + funding going extreme negative (short squeeze setup building).

---

### Example 5: Bitcoin ETF Approval Rally (January 2024)

**Setup:**
- SEC approved spot Bitcoin ETFs on January 10, 2024
- BTC had rallied from $27,000 to $46,000 in anticipation (buy the rumour)
- On the actual day of approval: BTC briefly spiked to $49,000 then SOLD OFF to $42,000

**What happened — the "sell the news" pattern:**
- Everyone who wanted to buy had already bought during the rumour phase
- At the actual event, there were no new buyers left
- Short-term holders took profit
- BTC dropped 15% in the week after approval

**But then:**
- ETF inflows were massive — billions of dollars per week
- This created sustained buying pressure over MONTHS
- BTC went from $42,000 to $73,000 by March 2024
- Then consolidated, then $100,000+ by end of 2024

**Lesson:** News events that are widely anticipated often cause "sell the news" reactions. The system should NOT buy on the day of an expected positive event. Wait for the sell-off, then enter as the SUSTAINED effect (ETF inflows, rate cuts, etc.) takes over. Short-term bearish, medium-term very bullish.

---

### Example 6: Short Squeeze Setup (Real Pattern)

**Setup conditions that precede short squeezes:**
- Funding rate deeply negative (< -0.05% per 8 hours)
- Open interest HIGH (many shorts in the market)
- Price at or near a strong support level
- RSI oversold (20-30 range)
- MACD histogram negative but SHRINKING

**What happens:**
1. Price bounces slightly off support (normal price action)
2. The most leveraged shorts (50x, 100x) get liquidated first
3. Their forced buy orders push price up more
4. Next tier of shorts (20x) starts getting liquidated
5. Their forced buys push price up further — cascade begins
6. Shorts rush to manually close (adding more buy pressure)
7. Price rockets 5-15% in minutes to hours

**Real example — BTC March 2024:**
- Funding hit -0.06% after BTC dropped from $73,000 to $60,000
- OI remained elevated — shorts were piling in expecting further decline
- RSI hit 25 on the 4H chart
- Price bounced from $60,000 and squeezed back to $70,000 in 3 days (+16%)

**Lesson:** Extreme negative funding + elevated OI + oversold RSI at support = highest-probability long setup in crypto. The system should actively scan for this combination.

---

## Part 2: Macro Correlation Framework

### BTC vs DXY (US Dollar Index) — The Inverse Dance

The DXY measures USD strength against a basket of major currencies (EUR, JPY, GBP, CAD, SEK, CHF). It is the single most important macro indicator for crypto.

**The relationship:**
- DXY up = dollar stronger = crypto weaker (typically)
- DXY down = dollar weaker = crypto stronger (typically)
- Historical correlation: approximately -0.65 (moderately inverse)

**Why this works:**
- When USD strengthens, global liquidity tightens. Capital flows into USD and out of risk assets.
- When USD weakens, global liquidity loosens. Capital flows out of USD into risk assets including crypto.
- This is a GLOBAL LIQUIDITY mechanism, not a direct price link.

**Real data points:**
- Q1 2022: DXY surged from 96 to 105. BTC dropped from $47,000 to $29,000.
- Q4 2022: DXY peaked at 114. BTC bottomed at $15,400. Both extremes hit simultaneously.
- Q4 2023: DXY dropped from 107 to 101. BTC rallied from $27,000 to $44,000.
- 2024: DXY relatively stable 101-106. BTC rallied on ETF flows — the correlation partially decoupled because institutional ETF demand created independent BTC demand.

**Important nuance for 2024-2026:**
The inverse correlation has WEAKENED since spot Bitcoin ETFs launched in January 2024. Institutional capital now flows into BTC independently of USD dynamics. When the dollar strengthens, some of that capital still goes into Bitcoin ETFs as a strategic allocation. The system should still monitor DXY but weight it less heavily than pre-ETF era.

**How the system should use DXY:**
- DXY rising sharply → reduce long bias, increase confidence threshold for longs by +10
- DXY falling sharply → increase long bias, reduce confidence threshold for longs by -5
- DXY stable → neutral, no adjustment
- DXY making multi-month highs → bearish macro backdrop, be cautious
- DXY making multi-month lows → bullish macro backdrop, be aggressive

### BTC vs S&P 500 (SPY) — The Risk Asset Link

BTC and the S&P 500 move together approximately 60-70% of the time. During crises, this correlation spikes to 80-90%.

**Why:**
- Institutional investors treat BTC as a risk asset alongside stocks
- When they reduce risk (sell stocks), they also sell crypto
- When they increase risk (buy stocks), they also buy crypto
- The same macro factors (Fed policy, economic data, geopolitics) drive both

**Key patterns:**
- NYSE opens at UTC 14:30. BTC reacts within SECONDS to the S&P opening direction.
- If S&P gaps up 1%+, BTC typically rallies 2-3% during the overlap
- If S&P gaps down 1%+, BTC typically drops 2-4% during the overlap
- S&P after-hours futures (6 PM ET onwards) often signal the next day's crypto direction

**How the system should use SPY:**
- Check S&P pre-market futures before the London-NY overlap
- If pre-market is significantly negative (-0.5%+), raise long confidence threshold by +10
- If pre-market is significantly positive (+0.5%+), lower long confidence threshold by -5
- During NYSE open (first 30 minutes), weight S&P direction very heavily

### BTC vs VIX (Volatility Index) — The Fear Gauge

VIX measures expected S&P 500 volatility. Higher VIX = more fear = more volatility expected.

**The relationship:**
- VIX spike = risk-off = crypto sells off (initially)
- VIX crash = risk-on = crypto rallies
- VIX above 30 = extreme fear = major market stress
- VIX above 40 = panic = potential capitulation zone

**Real data:**
- March 2020: VIX hit 82.69. BTC at $3,800. Both extreme simultaneously.
- October 2025 tariff crash: VIX spiked above 35. BTC dropped 10%.
- Normal conditions: VIX 12-20. Crypto trades normally.

**How the system should use VIX:**
- VIX below 15: calm markets, trade normally
- VIX 15-25: moderate uncertainty, standard operations
- VIX 25-35: elevated fear, raise confidence thresholds by +10, reduce position sizes
- VIX above 35: extreme fear, only highest-conviction trades or no trading
- VIX spiking rapidly (up 20%+ in one day): immediate risk reduction, close marginal positions

### BTC vs Gold — The Digital Gold Narrative

Gold and BTC sometimes move together (both "hard money" alternatives) and sometimes diverge (BTC is risk-on, gold is risk-off).

**When they correlate:**
- During sustained inflation fears — both are inflation hedges
- During banking crises — both benefit from "broken traditional system" narrative
- During USD weakness — both benefit from dollar devaluation

**When they diverge:**
- During acute market panic — gold goes up (safe haven), BTC goes down (risk asset)
- During crypto-specific events — BTC moves independently of gold
- During risk-on rallies — BTC outperforms gold significantly

**How the system should use gold:**
- If gold is surging while BTC is dropping: crypto is being treated as risk-off. Caution on longs.
- If gold and BTC are both surging: macro conditions strongly favour hard assets. Bullish.
- If gold is dropping while BTC is rising: pure risk-on rally. Enjoy but watch for reversal.

### BTC vs US 10-Year Treasury Yield

Treasury yields represent the "risk-free" return. When yields rise, risk assets become less attractive because you can earn more by simply holding bonds.

**The relationship:**
- Yields rising = bonds paying more = capital flows from risk assets to bonds = bearish crypto
- Yields falling = bonds paying less = capital flows from bonds to risk assets = bullish crypto
- Rapid yield rises (bond market crash) = very bearish for crypto short-term

**How the system should use yields:**
- 10Y yield rising above 4.5%: macro headwind for crypto, raise confidence thresholds
- 10Y yield falling below 4.0%: macro tailwind for crypto, lower confidence thresholds
- Yield inversion (2Y higher than 10Y): recession signal, mixed for crypto

### BTC Dominance — The Altcoin Rotation Signal

BTC dominance measures BTC's market cap as a percentage of total crypto market cap.

**How to interpret:**
- BTC dominance rising: money flowing from alts to BTC. "Risk-off" within crypto. Trade BTC only.
- BTC dominance falling: money flowing from BTC to alts. "Risk-on" within crypto. Alts may outperform.
- BTC dominance at extremes (>65%): alt season may be approaching
- BTC dominance at lows (<40%): potential alt bubble, BTC may catch up

---

## Part 3: MEXC Exchange-Specific Mechanics

### Three prices that matter

**Last Price:** The most recent trade execution price on MEXC. This is what you see on the chart. Your limit orders fill against this price.

**Index Price:** Weighted average of the spot price across major exchanges (Binance, OKX, Bybit, etc.). This is the "real" market price regardless of what's happening on MEXC specifically.

**Fair Price (Mark Price):** Calculated from the index price plus a funding basis adjustment. THIS is what MEXC uses for liquidation calculations and unrealized P&L. Not the last price.

**Why this matters:**
- Your position might show a loss based on fair price even if the last price hasn't moved much
- A sudden spike in MEXC's last price (due to thin order book) will NOT trigger your liquidation — the fair price stays stable
- This PROTECTS you from exchange-specific manipulation
- When setting stops, understand that the stop triggers on the last price but liquidation triggers on the fair price

### Funding rate timing on MEXC

**Settlement times:** Every 8 hours at UTC 00:00, 08:00, 16:00 (Melbourne: 11 AM, 7 PM, 3 AM)

**What happens at settlement:**
- The funding payment is calculated and exchanged between longs and shorts
- If funding is positive: longs pay shorts
- If funding is negative: shorts pay longs
- The payment is deducted from/added to your margin balance

**Pre-settlement behaviour:**
- 30-60 minutes before settlement, traders who would have to pay often close their positions to avoid the fee
- This creates predictable selling pressure before positive funding settlements (longs closing)
- And predictable buying pressure before negative funding settlements (shorts closing)

**How the system should exploit this:**
- Monitor funding rate approaching settlement
- If funding is extreme positive and settlement is in 30 minutes: expect selling pressure. Don't enter longs.
- After settlement: the pressure resolves. Better entry for longs.
- If funding is extreme negative and settlement is approaching: expect buying pressure. Don't enter shorts.

### MEXC liquidation mechanics

**Tiered liquidation:** MEXC doesn't liquidate your entire position at once. For larger positions, it liquidates in tiers — closing portions of the position progressively. This is better for the trader (less slippage) but means partial liquidations can occur where you lose part of your position but keep the rest.

**Isolated vs cross margin:**
- Isolated margin: each position has its own margin. Liquidation of one position doesn't affect others. Use this for Finding Alpha — keeps risk contained per trade.
- Cross margin: all positions share one margin pool. A loss on one position can liquidate ALL positions. Never use this.

**Auto-margin addition:** MEXC has a feature to automatically add margin to a losing position to prevent liquidation. The system should NEVER enable this — it turns a planned $15 loss into an unplanned $50+ loss by throwing more money at a losing trade.

### MEXC leverage up to 500x — why we never use it

MEXC offers up to 500x leverage on some pairs. At 500x, a 0.2% move against you = 100% loss (total liquidation). This is gambling, not trading.

**Our leverage limits:**
- 5M scalps: max 20x
- 15M trades: max 15x
- 1H swings: max 10x

These limits ensure that even in a flash crash where the stop loss doesn't fill exactly at the planned price (slippage), the additional loss is manageable.

### Order types on MEXC

**Limit order (primary):** Set a price, wait for it to be filled. Lower fees (maker rebate on some tiers). Use for entries when you have a specific price target.

**Market order (emergency only):** Execute immediately at best available price. Higher fees (taker fee). Use only for emergency exits when you need out NOW.

**Stop loss order:** A conditional order that becomes a market order when the trigger price is reached. ALWAYS set on the exchange, not just in the system. This ensures the stop executes even if the system crashes.

**Take profit order:** Same as stop loss but in the profitable direction. Set on the exchange alongside the stop loss when entering the trade.

**Trailing stop (if available):** A stop that automatically follows price as it moves in your favour. Useful for riding trends.

---

## Part 4: Exchange Cross-Reference Signals

### When MEXC and Binance disagree

If MEXC shows a funding rate of +0.05% but Binance shows +0.02%, the signal is MEXC-specific. It might be due to:
- Lower liquidity on MEXC creating temporary imbalance
- A large trader on MEXC specifically
- MEXC's index price calculation creating a slight divergence

**Rule:** Only trust funding/OI signals that are confirmed across at least 2 of the 3 major exchanges (Binance, Bybit, OKX). MEXC-only signals are noise.

### Volume discrepancies

MEXC's volume can be inflated by wash trading or promotional trading competitions. When evaluating volume signals:
- Check if Binance volume confirms the spike
- If MEXC shows 5x volume but Binance shows 1.5x, the real signal is 1.5x
- Cross-exchange volume confirmation makes the signal 3x more reliable

### Liquidation data accuracy

MEXC's liquidation data is only for MEXC. Real market-moving liquidation cascades happen across ALL exchanges simultaneously. Use Coinglass aggregated liquidation data for the true picture. A $50M liquidation on MEXC alone is notable. A $500M liquidation across all exchanges is a market event.
