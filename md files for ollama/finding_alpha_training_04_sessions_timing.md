# Finding Alpha — Market Sessions, Timing & Microstructure Intelligence

> This document teaches the intelligence engine the rhythm of global markets — how each session behaves,
> where the real opportunities are, how institutional money moves, and how to time entries for maximum edge.
> Crypto trades 24/7 but not all hours are equal. The system that understands WHY 2am Melbourne time
> produces the best trades will consistently outperform the system that treats all hours the same.

---

## Part 1: Why Timing Matters in a 24/7 Market

### Not all hours are equal

Crypto markets never close but they breathe in a rhythm dictated by global financial centres. When Tokyo opens, Japanese institutions start trading. When London opens, European banks come in with massive capital. When New York opens, the world's largest pool of money activates. Each transition creates a predictable pattern of volatility, volume, and opportunity.

Trading during Asia session with the same parameters as the London-NY overlap is like fishing in a puddle vs fishing in the ocean. The puddle might occasionally have a fish, but the ocean consistently delivers.

### Volume is the lifeblood of signals

Technical indicators need volume to work. RSI oversold at 22 with 3x average volume means something completely different from RSI oversold at 22 with 0.1x average volume. The first is potential capitulation exhaustion — a high-quality mean reversion signal. The second is price drifting down slowly with nobody participating — unreliable, could continue drifting for hours.

Volume concentrates during specific hours:
- 30% of daily crypto volume occurs during the London-NY overlap (4 hours out of 24)
- 25% during London solo and NY solo combined (9 hours)
- The remaining 45% is spread across Asia and wind-down (11 hours)

This means 55% of daily volume is compressed into 13 hours. The system should be most active during those hours and most cautious outside them.

### The session transition effect

The most volatile moments in any 24-hour period are the 30-45 minutes around each major session open. This is when:
- New participants react to what happened while they were asleep
- Overnight orders get triggered
- Stop losses placed during quiet hours get hunted
- Institutional order flow enters the market

These transitions are where the best and worst trades happen. The system should be alert and ready during transitions, not sleeping or scanning slowly.

---

## Part 2: The Five Sessions — Detailed Behaviour

### Asia Session

**UTC: 00:00 - 08:00**
**Melbourne: 11:00 AM - 7:00 PM**
**Key cities: Tokyo, Hong Kong, Singapore, Sydney, Seoul**

**Character:**
Asia is the quiet kid in class. Volume is low, moves are small, and the market tends to drift sideways. Japanese and Korean retail traders are active but institutional capital is limited compared to London and NY. The market is waiting for Europe to wake up and set the tone.

**Typical behaviour:**
- Price establishes a range within the first 2-3 hours
- This range is defined by the session high and session low
- Price oscillates within this range, testing both sides
- Volume gradually decreases as the session progresses
- Breakout attempts usually fail due to lack of follow-through volume

**What the system should do:**
- Mark the Asia range high and low — these become key levels for London
- Trade only extreme setups (confidence 65+)
- Expect mean reversion within the Asia range to work because there isn't enough volume to sustain breakouts
- Reduce scan frequency to every 90 seconds (saves API calls, reduces noise)
- Do NOT chase moves — they usually reverse within the range

**What to watch for:**
- Chinese economic data releases (GDP, PMI, trade data) — these occur during Asia and can create genuine moves
- Bank of Japan interest rate decisions — affects JPY which can cascade to BTC/JPY pairs
- Korean regulatory announcements — Korea is a major crypto market
- If Asia breaks significantly out of a multi-day range with volume, pay attention — it could be the start of a larger move

**The Asia trap:**
Sometimes Asia creates a fake breakout — price moves 1-2% in one direction, luring traders in, then reverses. This is because there isn't enough volume to sustain the move. The system should treat Asia breakouts with extreme scepticism unless volume confirms (2x+ average).

**Confidence threshold: 65/100**
Only the highest-quality setups justify trading during Asia.

---

### London Session

**UTC: 08:00 - 13:00**
**Melbourne: 7:00 PM - 12:00 AM**
**Key cities: London, Frankfurt, Zurich, Amsterdam**

**Character:**
London is the predator. European institutional money enters the market with massive capital and aggressive intent. This session sets the tone for the entire day. The first hour of London is among the most volatile and opportunistic periods.

**Typical behaviour — The London Playbook:**

**Step 1: The fake move (first 15-30 minutes)**
- London opens and price pushes sharply in one direction
- This move targets the Asia range boundary (high or low)
- The goal: trigger stop losses placed by Asian session traders

**Step 2: The liquidity grab (30-60 minutes)**
- Price breaks through the Asia high or low
- Stop losses fire, creating forced buying/selling
- This liquidity is absorbed by London institutions who are entering on the OTHER side
- Volume spikes as stops cascade

**Step 3: The reversal (60-90 minutes)**
- The move exhausts itself — the stop losses have all been triggered
- Price reverses sharply in the opposite direction
- This reversal often travels the entire Asia range and then beyond

**Step 4: The trend (90 minutes+)**
- The reversal establishes the London session's trend
- This trend typically continues for 2-4 hours
- The system should ride this trend with the Supertrend and trailing stops

**How the system should trade London:**

1. **First 15 minutes: OBSERVE ONLY.** Do not trade. Watch which direction London pushes. Note the volume.
2. **15-45 minutes: IDENTIFY THE GRAB.** If price breaks Asia's range with spiking volume, this is the liquidity grab. Do NOT trade WITH the breakout — it's about to reverse.
3. **45-90 minutes: LOOK FOR THE REVERSAL.** RSI becomes oversold (if the grab was down) or overbought (if the grab was up). MACD histogram starts shrinking. Volume peaks and begins declining. Supertrend shows signs of flipping.
4. **90+ minutes: ENTER THE REVERSAL.** When indicators confirm, enter against the initial move with moderate-high confidence. This is one of the highest-quality setups in the entire 24-hour cycle.
5. **Trail the position** as the reversal develops into the London trend.

**What to watch for:**
- UK economic data (GDP, CPI, employment) — released at 7:00 AM GMT
- ECB interest rate decisions — massive impact on EUR and risk sentiment
- European bank earnings — affect broader financial sentiment
- Geopolitical developments during European morning — NATO announcements, EU sanctions

**Confidence threshold: 45/100**
London provides high-quality signals due to strong volume. Lower confidence threshold is justified because the signal-to-noise ratio is much better than Asia.

---

### London-New York Overlap

**UTC: 13:00 - 17:00**
**Melbourne: 12:00 AM - 4:00 AM**
**Key cities: London (still open) + New York, Chicago, Boston**

**Character:**
This is the Super Bowl of trading. Both European and American institutional money is active simultaneously. Volume peaks. Moves are the largest and cleanest. The single highest-quality 4-hour window in the entire 24-hour cycle.

**Why it's special:**
- Maximum global liquidity — London hasn't closed, NY has just opened
- NYSE opens at 1:30 AM Melbourne time — the most volatile single moment of any 24-hour period
- S&P 500 movements directly drag crypto — if S&P dumps at open, BTC follows within seconds
- Options and futures expiry events often occur during this window
- Institutional order flow peaks — hedge funds, banks, pension funds all active

**Typical behaviour:**

**Pre-NYSE (UTC 13:00-14:30):**
- London trend continues or consolidates
- US pre-market futures provide early signals about NYSE direction
- Crypto positions for the expected NYSE movement
- Lower volatility as traders wait for the open

**NYSE Open (UTC 14:30-15:30):**
- EXPLOSION of volatility
- The first 15 minutes after NYSE open are the most volatile of the day
- S&P direction immediately impacts BTC — 80%+ correlation during this window
- If S&P opens up 1%+, BTC typically rallies 2-3%
- If S&P opens down 1%+, BTC typically drops 2-4%
- Massive volume on both sides

**Post-Open Settlement (UTC 15:30-17:00):**
- Initial volatility settles
- A trend establishes — either continuation of the opening move or reversal
- This period offers the cleanest trend-following opportunities
- Supertrend signals during this period have the highest reliability

**How the system should trade the overlap:**

1. **Check US pre-market futures** (S&P 500, Nasdaq futures) before NYSE open. These indicate the likely direction.
2. **Position BEFORE the open** if confidence is high based on pre-market + London trend alignment.
3. **At NYSE open: OBSERVE the first 5-10 minutes.** The initial spike is often a fakeout. Wait for direction to confirm.
4. **After confirmation: ENTER aggressively.** This is the highest-volume, highest-quality window. Confidence thresholds can be at their lowest (35/100) because volume makes signals more reliable.
5. **Scalp the volatility.** Multiple quick trades on 5M timeframe can capture significant moves during this window.
6. **Use Supertrend on 15M** for the post-open trend. Enter when Supertrend confirms direction after the initial volatility settles.

**What to watch for:**
- US economic data releases (CPI, jobs report, Fed minutes) — often released at 8:30 AM ET (UTC 13:30)
- Fed press conferences — always during overlap hours
- S&P 500 and Nasdaq movement — the primary driver of crypto during this window
- Options expiry — large open interest at specific BTC price levels can act as magnets or barriers

**The most profitable single trade pattern:**
1. London establishes a trend (say, bullish)
2. Pre-market S&P futures are green (confirms the bull case)
3. BTC pulls back slightly during pre-open as traders take profit
4. RSI dips to 40-45 on 15M (healthy pullback, not oversold)
5. NYSE opens and confirms the bullish direction
6. BTC rallies strongly on the volume influx
7. System enters long on the 15M with Supertrend confirmation

This pattern occurs 2-3 times per week and consistently produces +1.5-2R profits.

**Confidence threshold: 35/100**
The lowest threshold of any session because volume quality is the highest. Even moderate signals work during the overlap because the volume provides follow-through.

---

### New York Session (Solo)

**UTC: 17:00 - 22:00**
**Melbourne: 4:00 AM - 9:00 AM**
**Key cities: New York, Chicago (London has closed)**

**Character:**
London has gone home. NY continues alone. Volume is still decent but declining. The session often continues the trend established during the overlap or begins to reverse as profit-taking starts.

**Typical behaviour:**
- First 1-2 hours: continuation of overlap trend with declining volume
- Mid-session: often a reversal or at least a retracement as traders book profits
- Last 1-2 hours: volume drops significantly, moves become unreliable
- End of session: often a fade — whatever happened during the day gets partially reversed

**How the system should trade NY solo:**
- Trade with the established trend for the first 1-2 hours
- Watch for exhaustion signals (RSI divergence, MACD shrinking, declining volume)
- Take profits more quickly than during the overlap — moves are less likely to sustain
- Reduce activity in the last 2 hours as volume drops
- Don't start new positions after UTC 20:00 unless confidence is very high (60+)

**What to watch for:**
- Fed speeches or announcements (can occur at any time during NY)
- US stock market close (UTC 21:00) — sometimes creates a final burst of volatility
- Energy market movements — oil prices affecting inflation expectations
- Corporate earnings from major tech companies (after-hours) — can shift sentiment

**Confidence threshold: 40/100**

---

### Wind-Down Session

**UTC: 22:00 - 00:00**
**Melbourne: 9:00 AM - 11:00 AM**
**Key cities: None major — gap between NY close and Tokyo open**

**Character:**
The dead zone. NY has closed, Tokyo hasn't opened yet. Volume is at its daily low. Price often drifts aimlessly or slowly reverses the day's moves. This is the worst time to trade.

**Typical behaviour:**
- Very low volume — moves are unreliable
- Price often retraces toward the daily VWAP
- Fake breakouts common due to thin order books
- Spread widens on some exchanges

**How the system should trade wind-down:**
- Mostly don't. Observe and prepare for Asia/London.
- Only extreme setups justify entry (confidence 50+)
- If positions are open, consider closing them before wind-down to avoid overnight drift
- Use this time to review the day's trades and plan for the next session

**What to watch for:**
- Nothing typically happens during wind-down
- Occasionally, a surprise news event during dead hours can cause exaggerated moves because the order book is thin
- Australian economic data may be released during this window (affects AUD, minor impact on crypto)

**Confidence threshold: 50/100**

---

## Part 3: The Weekly Rhythm

### Monday

**Character:** Markets react to weekend news. Gaps are possible (especially if major events occurred over the weekend). Volume builds gradually as global participants return. Often sets the tone for the week.

**System approach:** Start cautiously. Observe the first few hours. If the direction is clear, trade with it. Monday trends often extend through Tuesday.

### Tuesday - Wednesday

**Character:** The most active trading days. Volume peaks. Economic data releases are concentrated on these days (CPI, Fed minutes, jobs data). The cleanest signals and biggest moves typically occur Tuesday-Wednesday.

**System approach:** Maximum activity. This is where the system should be most aggressive with trade frequency.

### Thursday

**Character:** Still active. Weekly options expiry (for some exchanges) can create volatility. Often sees profit-taking from Tuesday-Wednesday moves.

**System approach:** Active but watch for reversal of the week's trend. Thursday reversals are common.

### Friday

**Character:** Volume declines as the week winds down. Traders reduce exposure before the weekend. "Weekend risk" — holding positions over a weekend where unexpected events can occur — makes traders cautious.

**System approach:** Reduce activity. Close positions by end of NY session if possible. Avoid opening new positions in the last few hours of Friday.

### Weekend (Saturday - Sunday)

**Character:** Lowest volume of the week. Retail-dominated (institutions are mostly offline). Moves can be sharp but unreliable due to thin liquidity. Weekend pumps or dumps often reverse by Monday.

**System approach:** Trade only extreme setups. Reduce position sizes (halve the standard risk) because weekend liquidity makes stops less reliable. Be prepared for Sunday night "gap" as Asian markets open for the new week.

---

## Part 4: Calendar Events and Their Timing

### Monthly recurring events

| Event | Typical Day | Time (UTC) | Impact | How to Trade |
|-------|-----------|-----------|--------|-------------|
| US CPI | ~13th | 13:30 | High | Wait for release, trade the reaction |
| US PPI | ~14th | 13:30 | Medium | Similar to CPI but less impact |
| US Jobs (NFP) | 1st Friday | 13:30 | High | Wait for release, volatile reaction |
| FOMC Decision | 8 times/year | 19:00 | Very High | Reduce exposure before, trade after |
| FOMC Minutes | 3 weeks after decision | 19:00 | Medium | Parsed for tone shifts |
| UK CPI | ~15th | 07:00 | Medium | Affects GBP and London sentiment |
| ECB Decision | 6 times/year | 13:15 | High | Affects EUR and European risk appetite |
| BTC Options Expiry | Last Friday | 08:00 | Medium-High | Price gravitates to max pain level |
| BTC Futures Expiry | Quarterly | Varies | High | Increased volatility week before |

### How to trade around events

**Before the event (1-2 hours):**
- Reduce or close existing positions
- Raise confidence threshold by +15 points
- Do not open new positions unless they'll be closed before the event
- The market often consolidates pre-event — Bollinger Bands tighten

**During the event (first 5-15 minutes):**
- OBSERVE ONLY. The initial reaction is often a fakeout.
- Price may spike one way then completely reverse
- Volume explodes but direction is unclear
- The system should NOT auto-trade during this window

**After the event (15-60 minutes):**
- Direction establishes
- Volume confirms the real move
- This is when the system should enter — after the dust settles
- The post-event move often continues for hours

### The "buy the rumour, sell the news" pattern

When a positive event is widely anticipated (e.g., expected rate cut, expected ETF approval):
1. Price rallies in the days/weeks BEFORE the event (buying the rumour)
2. When the event actually happens, price often DROPS (selling the news)
3. This is because everyone who wanted to buy has already bought in anticipation
4. At the actual event, there are no new buyers left — only sellers taking profit

The system should recognise this pattern and not blindly buy on positive news if the market has already rallied significantly into the event.

---

## Part 5: Institutional Money Flow Patterns

### How institutions trade differently from retail

Retail traders:
- Enter and exit with market orders
- Create volume spikes
- Chase moves after they've happened
- Trade based on emotion and FOMO
- Mostly active during their local hours

Institutional traders:
- Use algorithms to execute large orders gradually (TWAP, VWAP algorithms)
- Split orders across hours or days to avoid moving the market
- Anticipate events rather than react to them
- Use dark pools and OTC desks for large trades
- Active primarily during London and NY

### Reading institutional activity

**Signs of institutional accumulation (bullish):**
- Price holds steady but volume is above average (they're buying without pushing price up)
- OBV (On-Balance Volume) rising while price is flat
- Large buy walls appearing on the order book at key support levels
- Open interest rising gradually (new positions being built)
- Funding rate staying neutral despite price not moving (balanced buying)

**Signs of institutional distribution (bearish):**
- Price makes new highs but on declining volume (fewer participants)
- OBV falling while price is rising or flat
- Large sell walls appearing above the current price
- Unusual whale transfers to exchanges
- Rising open interest with funding rate going positive (leveraged longs building up — fragile)

### The accumulation-distribution cycle

1. **Accumulation:** Smart money quietly buys at low prices. Volume is moderate. Price moves sideways or makes subtle higher lows. RSI stays in 40-55 range. This can last days to weeks.

2. **Mark-up:** Once accumulation is complete, price breaks out. Volume surges. MACD crosses positive. Supertrend flips green. Retail traders notice and start buying (FOMO). This phase is profitable for trend-following.

3. **Distribution:** Smart money begins selling to retail buyers at high prices. Price makes new highs but volume declines. RSI shows bearish divergence. MACD histogram starts shrinking. This can last days.

4. **Mark-down:** Price drops. Volume spikes as retail panics. Stop losses cascade. Smart money watches from the sidelines with cash ready to accumulate again at lower prices.

The system should learn to identify which phase the market is currently in and adjust its strategy accordingly:
- Accumulation → Prepare for long entries, start building positions
- Mark-up → Trend follow, ride the Supertrend
- Distribution → Take profits, tighten stops, prepare for shorts
- Mark-down → Mean reversion at extreme levels, or trend follow short

---

## Part 6: Crypto-Specific Timing Patterns

### Funding rate settlement times

Funding rates are exchanged between longs and shorts every 8 hours on most exchanges:
- UTC 00:00 (Melbourne 11:00 AM)
- UTC 08:00 (Melbourne 7:00 PM)
- UTC 16:00 (Melbourne 3:00 AM)

**Before settlement:** If funding is strongly positive (longs paying shorts), some longs will close before settlement to avoid the fee. This creates selling pressure in the 30-60 minutes before settlement.

**After settlement:** The fee has been paid. The pressure that was building pre-settlement resolves. Price often bounces after negative settlement events.

**The system should:** Monitor funding rates and time entries around settlement. Entering a long just AFTER a negative funding settlement (when selling pressure resolves) is a higher-quality entry than entering during the build-up.

### Options and futures expiry

**Monthly BTC options expiry (last Friday of the month):**
- "Max pain" — the price at which the most options expire worthless
- Price tends to gravitate toward max pain in the days before expiry
- After expiry, the gravitational pull releases and price can move freely
- The system should note the max pain level and expect price to be attracted to it before expiry, then potentially break away after

**Quarterly futures expiry:**
- Larger impact than monthly options
- Increased volatility in the week before expiry
- Basis trading (difference between spot and futures price) narrows
- The system should reduce position sizes during expiry week and be ready for increased volatility

### The weekend effect

Crypto shows statistical patterns around weekends:
- Friday afternoon (UTC): Volume decreases, traders reduce risk
- Saturday: Lower volume, retail-dominated, can see sharp but unreliable moves
- Sunday evening (UTC): Volume begins increasing as Asia prepares for Monday
- Sunday night "gap": If major news occurred over the weekend, Sunday's Asian open can create a sharp move

**System approach to weekends:**
- Friday: Close most positions before NY close
- Saturday: Half-size positions only, 50% of normal risk
- Sunday: Resume normal activity as Asia opens, but cautious until London confirms direction

### The halving cycle

Bitcoin undergoes a "halving" approximately every 4 years (every 210,000 blocks). The block reward for miners is cut in half, reducing the supply of new BTC entering the market.

**Historical pattern:**
- 12-18 months before halving: Accumulation begins, price gradually rises
- 0-6 months before halving: Acceleration of the rally, FOMO builds
- 0-12 months after halving: Parabolic bull run, new all-time highs
- 12-18 months after halving: Distribution, correction, eventual bear market

The most recent halving was in April 2024. Based on historical patterns:
- 2024-2025: Bull market expected
- 2025-2026: Potential peak and beginning of correction
- The system should be aware of where we are in the cycle and adjust long-term bias accordingly

---

## Part 7: Optimal Entry Timing Within a Candle

### The anatomy of a good entry

**For long entries:**
- Best timing: Enter during the lower wick of a candle, not at the close
- Watch for a candle that opens, drops (creating a wick), then starts to recover
- If you enter during the recovery part of the wick, you get a better price than waiting for the close
- Confirmation: The body of the candle starts forming above the midpoint

**For short entries:**
- Best timing: Enter during the upper wick of a candle
- Watch for a candle that opens, spikes up (creating a wick), then starts to fall
- Enter during the reversal from the wick
- Confirmation: The body starts forming below the midpoint

### Avoiding bad entry timing

**Don't chase candles:**
- If a 5M candle has already moved 80% of its typical range (ATR), don't enter
- The move has already happened — you're paying the worst price
- Wait for the next candle or a pullback

**Don't enter at candle boundaries:**
- The last 10 seconds of a candle can be manipulated to close at a specific level
- The first 10 seconds of a new candle can gap
- Enter in the middle of candle development when the direction is established

**The "test and confirm" principle:**
- Price drops to a level (test)
- Price bounces (initial reaction)
- Price drops back toward the level but not as deep (retest)
- Price bounces again with more conviction (confirmation)
- ENTER on the retest bounce, not on the initial test

This is how professional traders enter. They don't buy the first touch of support. They wait for the retest that confirms the level is holding.

---

## Part 8: Time-Based Exit Rules

### Maximum holding periods

Trades that don't work within a reasonable timeframe should be closed, even if the stop hasn't been hit:

| Timeframe | Max Hold | Reasoning |
|----------|---------|-----------|
| 5-minute | 30 minutes | If it hasn't worked in 6 candles, the setup failed |
| 15-minute | 2 hours | 8 candles should be enough to reach target |
| 1-hour | 12 hours | Overnight holding is acceptable but not beyond |

**Why time exits matter:**
- A trade that sits at breakeven for hours is tying up capital and margin
- The longer a trade is open, the more it's exposed to unexpected events
- If the expected move hasn't materialised, the thesis is likely wrong
- Close at current price and redeploy the capital on a fresh setup

### Session-end rules

- Positions opened during London should ideally be closed before London ends (or trailed tightly)
- Positions opened during the overlap should be closed or trailed before NY solo winds down
- Avoid carrying positions through session transitions unless the trade is significantly in profit and well-trailed
- NEVER hold a scalp (5M) through a session transition — the gap can destroy the trade

### End-of-day protocol

At the end of each 24-hour cycle (around UTC 00:00):
1. Close any positions that aren't significantly in profit
2. Trail stops tight on any remaining positions
3. Log all daily trades and performance
4. Reset daily counters (P&L, trade count, loss streaks)
5. Assess whether conditions for tomorrow warrant continued activity
