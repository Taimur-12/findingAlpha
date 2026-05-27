# Finding Alpha — News Interpretation & Historical Patterns

> This document teaches the intelligence engine how to interpret real-world events and their impact on cryptocurrency markets.
> It covers geopolitical events, economic events, crypto-specific events, historical crash and rally patterns,
> and the decision framework for translating news context into trading adjustments.
> The system should use this knowledge to reason about current events, not just match keywords.

---

## Part 1: The Relationship Between News and Crypto Markets

### Crypto does not move in isolation

Cryptocurrency markets, especially Bitcoin, are deeply connected to global events. The idea that crypto is "decentralised and independent" is a narrative, not a reality. In practice, BTC moves with the S&P 500 approximately 60-70% of the time, and this correlation spikes during crises. When the stock market crashes, crypto crashes harder. When the stock market rallies, crypto rallies harder. Crypto is a high-beta risk asset — it amplifies whatever the traditional market is doing.

### The two-phase news reaction

Almost every major negative event follows the same pattern in crypto:

**Phase 1 — Immediate shock (minutes to hours):** Panic selling, cascading liquidations, sharp price drop. Leveraged longs get wiped out. The drop is typically 5-15% for BTC and 15-40% for altcoins within hours.

**Phase 2 — Recovery (days to weeks):** Once the panic subsides and the situation stabilises, price recovers. Often, the recovery carries price higher than where it was before the event. This is because the liquidation cascade removes weak-handed, over-leveraged participants, leaving a cleaner, healthier market structure.

The critical skill is distinguishing between events that follow this two-phase pattern (temporary shocks) and events that create genuine structural damage (permanent regime changes). The LLM must learn this distinction.

### Speed of reaction by event type

Different types of events hit the market at different speeds:

| Event Type | Reaction Time | Initial Impact | Recovery Time |
|-----------|--------------|----------------|---------------|
| Military strike/attack | Seconds to minutes | -5% to -15% | 24-72 hours |
| Exchange hack/collapse | Minutes to hours | -10% to -30% | Weeks to months |
| Fed rate decision | Minutes | -3% to +3% | Hours to days |
| Regulatory action (SEC) | Hours | -5% to -20% | Days to weeks |
| Tariff announcements | Hours | -5% to -15% | Days to weeks |
| ETF approval/rejection | Minutes to hours | -5% to +10% | Days |
| Inflation data (CPI) | Minutes | -2% to +2% | Hours |
| Bank failure | Hours to days | -10% to -20% | Weeks |
| Pandemic/health crisis | Days | -30% to -50% | Months |

---

## Part 2: Geopolitical Events and Their Impact

### Wars and Military Conflicts

**General pattern:** Military escalation is immediately bearish for crypto. The initial reaction is always a sell-off because institutional traders liquidate risk assets to move into cash and treasuries (the "risk-off" trade). However, sustained military conflict often eventually becomes bullish for BTC as it strengthens the "digital gold" and "escape from traditional finance" narratives.

**Iran-Israel Conflict (April 2024):**
- Iran launched drones and missiles at Israel
- BTC dropped 8% in a single Saturday night session, falling from approximately $67,000 to $61,000
- ETH and SOL saw steeper declines, with some altcoins losing up to 20%
- Recovery: Market stabilised within 48 hours once it became clear the escalation would not lead to full-scale regional war
- Lesson: The initial drop was a liquidity event (forced liquidations), not a fundamental change. The system should have identified this within hours by monitoring whether the conflict was escalating or de-escalating

**Israel Strikes on Iran (mid-2025):**
- Direct strikes on Iranian soil — a significant escalation
- BTC dipped from $110,000 to $103,000 — a 6% correction
- Over $1 billion in long positions liquidated in 24 hours
- Surprisingly, within two months, BTC rallied 62% to hit new all-time highs
- Lesson: War volatility acts as a "springboard" — the liquidation clears out leveraged positions and creates a cleaner base for the next rally. The system should buy the dip after the initial panic subsides, not during it.

**Iran-US Tensions (2026):**
- Ongoing ceasefire negotiations, confusion over Strait of Hormuz
- BTC struggling in the $65,000-$70,000 range
- Market more fragile than previous incidents because of accumulated leverage liquidations
- Lesson: Repeated geopolitical shocks on an already-weakened market are more dangerous than shocks on a healthy market. Context matters.

**Russia-Ukraine War (2022-ongoing):**
- Initial invasion: BTC dropped but then showed resilience
- Long-term: Contributed to general "risk-off" sentiment but BTC demonstrated diversification potential
- Ukraine used crypto donations for military funding, strengthening the legitimacy narrative
- Lesson: Ongoing conflicts create persistent bearish pressure but also reinforce crypto's utility narrative. The system should not trade ON the war but should account for it as background sentiment.

**Key principles for war events:**
1. First reaction is ALWAYS bearish — do not buy the initial drop
2. Wait for confirmation that the situation is stabilising (ceasefire talks, no further escalation)
3. The bounce after the initial panic is usually strong and fast
4. Altcoins drop 2-3x harder than BTC during geopolitical events
5. If oil prices spike because of the conflict, that creates secondary bearish pressure through inflation expectations
6. Strait of Hormuz disruption is a specific extreme scenario — 20% of global oil flows through it. Blockade = massive global economic disruption

### Sanctions and Trade Wars

**Trump Tariffs (October 2025 — 100% on Chinese imports):**
- Triggered the largest single-day liquidation event in crypto history — $19 billion in 24 hours
- Bigger than Luna collapse, bigger than COVID crash, bigger than FTX
- BTC dropped 10% in hours, altcoins dropped 50-80%
- The crash was amplified by the fact that two days before the announcement, large wallets opened massive short positions — suggesting insider knowledge
- S&P 500 fell 2% — its sharpest single-day drop since April
- Recovery pattern typical of liquidity flushes — leverage wiped out, strong hands bought the dip
- Lesson: Trade war announcements are immediate and severe. The system should monitor for tariff-related news and reduce exposure before anticipated announcements. After the flush, it's a buying opportunity.

**Trump Tariffs (February 2025):**
- Additional tariff threats created $2.2 billion in liquidations
- BTC dropped to $91,200 before bouncing to $93,600
- ETH crashed to $2,500, down 20% in 24 hours
- Lesson: Repeated tariff escalations create compounding damage. Each subsequent tariff threat hits a market that hasn't fully recovered from the last one.

**General sanctions impact:**
- Countries under sanctions (Iran, Russia) see increased crypto adoption as citizens use it to bypass financial restrictions
- This creates genuine demand but also regulatory risk — governments may crack down on crypto to prevent sanctions evasion
- The system should treat sanctions as bearish in the short term (regulatory risk) but potentially bullish medium-term (adoption driver)

### Elections and Political Transitions

**Trump Election Victory (November 2024):**
- Bitcoin surged to $89,000 — a 30% increase in one week
- Pro-crypto stance and promises to make the US a "crypto capital" drove euphoric buying
- Continued surge pushed BTC above $100,000 and eventually to $105,000+
- Lesson: Political outcomes that favour crypto regulation clarity create powerful bullish momentum. The system should increase activity during confirmed pro-crypto political outcomes.

**Regulatory clarity vs uncertainty:**
- Clear, favourable regulations = bullish (investors know the rules)
- Regulatory uncertainty = bearish (investors fear the unknown)
- Hostile regulatory actions = immediately bearish but creates buying opportunities after the initial shock

---

## Part 3: Economic Events and Their Impact

### Federal Reserve Decisions

The Federal Reserve is the single most important institution for crypto prices outside of the crypto industry itself. Its decisions on interest rates directly affect the attractiveness of risk assets like crypto.

**Rate hikes (bearish for crypto):**
- Higher interest rates make safe assets (Treasury bonds, savings accounts) more attractive
- Capital flows out of risk assets (stocks, crypto) into yield-bearing instruments
- A rate hike that exceeds market expectations is more bearish than one that matches expectations
- The system should monitor Fed fund futures to understand what the market has priced in

**Rate cuts (bullish for crypto):**
- Lower interest rates make safe assets less attractive
- Capital flows into risk assets seeking higher returns
- Rate cuts signal that the Fed believes the economy needs support, which can trigger "risk-on" sentiment
- However, emergency rate cuts (unexpected) can be bearish because they signal the economy is in worse shape than expected

**Fed language matters as much as actions:**
- "Hawkish" language (talking about more hikes, persistent inflation) = bearish even without action
- "Dovish" language (talking about pausing, watching data, cutting soon) = bullish even without action
- The system should parse Fed statements for tone shifts, not just rate decisions

**January 2025 example:**
- BTC dipped below $90,000 when concerns emerged that the Fed might delay anticipated rate cuts
- This triggered "risk-off" sentiment across all markets
- Lesson: Even the EXPECTATION of Fed policy changes moves markets. The system doesn't need to wait for the actual decision.

### Inflation Data (CPI, PPI)

**Higher than expected inflation = bearish:**
- Suggests the Fed will keep rates higher for longer
- Raises cost of living, reduces disposable income for investment
- BTC typically drops 2-5% on hot CPI prints

**Lower than expected inflation = bullish:**
- Suggests the Fed may cut rates sooner
- "Goldilocks" data — economy healthy but not overheating
- BTC typically rallies 2-5% on cool CPI prints

**Core vs headline inflation:**
- Core CPI (excludes food and energy) is what the Fed watches most
- The system should focus on core CPI surprises, not headline numbers
- Oil price spikes (from geopolitical events) inflate headline CPI but not core — the system should understand this distinction

### Employment Data (Jobs Reports)

**Strong jobs report = mixed for crypto:**
- Strong economy means the Fed may keep rates higher (bearish)
- But strong economy means more capital available for investment (bullish)
- The net effect depends on whether the market is more focused on rates or growth

**Weak jobs report = mixed for crypto:**
- Weak economy means the Fed may cut rates (bullish)
- But weak economy means less capital, potential recession (bearish)
- Extreme weakness (recession fears) is bearish in the short term but bullish medium-term (rate cuts coming)

### Bank Failures

**Silicon Valley Bank (SVB) — March 2023:**
- SVB collapsed due to interest rate risk on its bond portfolio
- BTC initially dropped 10% on contagion fears
- But then rallied significantly as the narrative shifted to "this is why you need decentralised money"
- The banking crisis strengthened BTC's fundamental narrative
- Lesson: Bank failures that don't directly involve crypto can be bullish for crypto after the initial panic, because they reinforce the "broken traditional system" narrative

**Credit Suisse (March 2023):**
- Combined with SVB, created fears of a 2008-style banking crisis
- BTC rallied during this period — a key moment where crypto acted as a genuine safe haven
- Lesson: Systemic banking stress is actually bullish for crypto's narrative, though the system should wait for the initial contagion panic to pass

---

## Part 4: Crypto-Specific Events

### Exchange Collapses

**FTX Collapse (November 2022):**
- Timeline: CoinDesk report on Alameda's balance sheet → Binance announces FTT sell-off → bank run on FTX → Binance offers to buy → Binance withdraws → FTX bankruptcy
- BTC fell from $21,000 to below $16,000 — more than 20% decline over two months
- The collapse wiped out billions in customer funds and triggered cascading failures across the industry (BlockFi, Celsius, Voyager, Three Arrows Capital)
- Recovery took months, not days
- Lesson: Exchange collapses are STRUCTURAL events, not temporary shocks. The system should immediately halt trading when an exchange collapse is detected and not attempt to buy the dip. Recovery from structural events takes weeks to months, not hours.

**How to distinguish exchange problems from market problems:**
- If the news is about a specific exchange (hack, insolvency, frozen withdrawals) = structural crypto risk. Reduce exposure significantly.
- If the news is about general market conditions (sell-off, correction, profit-taking) = normal volatility. Trade normally or look for opportunities.
- If the news mentions "contagion," "interconnected," or "exposure to" = the problem is spreading. Maximum caution.

**Luna/Terra Collapse (May 2022):**
- The algorithmic stablecoin UST lost its peg to the dollar
- Luna crashed from $119 to near zero — $45 billion in value destroyed in one week
- BTC fell from $40,000 to $26,000
- The collapse exposed the interconnectedness of crypto — many firms had exposure to Luna/UST
- This triggered a chain of failures: Three Arrows Capital, Celsius, Voyager, eventually FTX
- Lesson: Stablecoin depegs are the most dangerous type of crypto-specific event because they undermine trust in the entire system. If a major stablecoin starts losing its peg, the system should immediately reduce all exposure.

### ETF Approvals and Rejections

**Bitcoin Spot ETF Approval (January 2024):**
- Historic moment — first spot BTC ETFs approved in the US
- Created sustained institutional demand as traditional investors could now access BTC through familiar vehicles
- Massive inflows — billions of dollars flowed into BTC through ETFs
- Contributed to the rally that took BTC from $40,000 to above $100,000
- Lesson: ETF approvals create sustained bullish pressure over months, not just a one-day spike. The system should treat ETF-related news as a regime change, not a single event.

**ETF rejection or delay = bearish but temporary:**
- The disappointment causes a sell-off
- But the expectation of eventual approval provides a floor
- Recovery usually happens within days

### Regulatory Actions

**SEC lawsuits against exchanges:**
- SEC suing Coinbase or Binance creates immediate fear
- Typically causes 5-15% drops
- But the market has become somewhat desensitised to SEC actions since 2023
- The system should monitor but not overreact to routine SEC enforcement

**Crypto bans by countries:**
- China banning crypto mining (2021) caused a massive short-term crash
- But long-term, the mining just moved elsewhere and the network became more decentralised
- Country-level bans in smaller economies have minimal impact
- Only a US ban would be truly catastrophic — and this is extremely unlikely given current political support

### Whale Movements and On-Chain Data

**Large wallet movements:**
- Whales moving BTC to exchanges = potential sell pressure (they're preparing to sell)
- Whales moving BTC off exchanges = bullish (they're holding for the long term)
- When old wallets suddenly become active = pay attention. Smart money moves first.
- The October 2025 crash was preceded by large wallets opening massive short positions days before the tariff announcement — this is insider-level signal

**Miner behaviour:**
- Miners selling large amounts = bearish (they need cash, may be capitulating)
- Miners accumulating = bullish (they expect higher prices)
- Hash rate reaching all-time highs = network confidence is strong

---

## Part 5: Historical Crash Patterns — What the Data Shows

### COVID Crash (March 2020)

**What happened:**
- Global pandemic panic triggered simultaneous sell-off across all asset classes
- BTC crashed from $9,000 to $3,800 — a 58% decline in less than two weeks
- The crash was driven by forced liquidations and a rush to cash

**Recovery:**
- BTC rebounded from $3,800 to $9,000 within two months
- Then continued surging to $64,000 by April 2021
- The crash was followed by unprecedented money printing by central banks, which devalued cash and drove demand for hard assets like BTC

**Indicators during the crash:**
- RSI hit single digits on multiple timeframes — extreme oversold
- Volume was astronomical — panic selling exhaustion
- Funding rates went deeply negative — shorts were extremely crowded
- The recovery began when volume peaked (capitulation complete) and RSI divergence appeared

**Lesson for the system:** Pandemic-level crashes are buying opportunities of a lifetime, but ONLY after the capitulation peak in volume. Do not try to catch the falling knife during the crash. Wait for volume to spike (everyone who wanted to sell has sold) and RSI to show divergence.

### Luna/Terra Collapse (May 2022)

**What happened:**
- UST algorithmic stablecoin lost its dollar peg
- Luna went from $119 to near zero
- BTC fell from $40,000 to $26,000 over several weeks
- Cascading failures across the industry followed for months

**Recovery:**
- Slow — it took months for BTC to stabilise around $20,000
- No V-shaped recovery like COVID because the damage was structural (company failures, frozen funds, legal proceedings)
- Eventually recovered but the road was long

**Lesson for the system:** When the crisis is WITHIN the crypto industry (exchange collapse, stablecoin failure), recovery is slow because trust is damaged. This is fundamentally different from an external shock (pandemic, war) where crypto's infrastructure is fine and the sell-off is purely sentiment-driven.

### FTX Collapse (November 2022)

**What happened:**
- Second-largest exchange collapsed due to fraud
- BTC fell from $21,000 to below $16,000
- Billions in customer funds lost
- Criminal charges, arrests, industry-wide contagion

**Recovery:**
- Very slow — BTC didn't recover to $21,000 until early 2023
- But then accelerated through 2023 into 2024
- The recovery was driven by institutional adoption (ETFs) and the halving cycle

**Lesson for the system:** Fraud-based collapses create the longest recovery periods because they damage trust at the deepest level. The system should not attempt to trade during active fraud revelations.

### Trump Tariff Crash (October 2025)

**What happened:**
- 100% tariff on all Chinese imports announced
- $19 billion liquidated in 24 hours — the largest single-day wipeout in crypto history
- BTC dropped 10%, altcoins dropped 50-80%

**Recovery:**
- Typical of leverage flushes — once the excess leverage was cleared, the market began rebuilding
- Preceded by whale short positions being opened days before — insider activity

**Lesson for the system:** Trade war events are short-term shocks similar to military events. The initial crash is violent but recovery follows once the market absorbs the news. The system should watch for insider activity (unusual whale movements, massive short positions appearing without news) as early warning.

### February 2025 Tariff Crash

**What happened:**
- Additional tariff threats triggered $2.2 billion in liquidations
- BTC to $91,200, ETH to $2,500
- Altcoins lost 50%+ of value

**Pattern recognition:** This was the SECOND tariff shock hitting a market that hadn't fully recovered from previous shocks. The compounding effect made it worse.

**Lesson:** Repeated shocks to a weakened market are more dangerous than isolated shocks to a healthy market. The system should track "market health" based on how recently the last major shock occurred and how far price has recovered.

---

## Part 6: How to Interpret News in Real-Time

### The decision framework

When the Research Agent receives news, the intelligence engine should reason through these questions:

**Question 1: What type of event is this?**
- Geopolitical (war, sanctions, elections) → Expect 5-15% BTC drop, 15-40% altcoin drop, recovery in days to weeks
- Economic (Fed, CPI, jobs) → Expect 2-5% BTC move, recovery in hours to days
- Crypto-specific (exchange, regulation, hack) → Impact varies wildly. Exchange collapse = weeks of damage. ETF approval = weeks of gains.
- Trade/tariff → Expect 5-15% BTC drop, massive liquidations, recovery in days

**Question 2: Is this a temporary shock or structural damage?**
- Temporary: War escalation, tariff announcement, hot CPI data, Fed hawkish language → The system should look for buying opportunities after the initial panic
- Structural: Exchange collapse, stablecoin depeg, fraud revelation, major regulatory ban → The system should halt trading and wait for clarity

**Question 3: How is the market positioned?**
- High leverage + negative event = cascading liquidations = much worse than expected
- Low leverage + negative event = contained sell-off = less damage
- Check open interest and funding rates to gauge leverage levels

**Question 4: Has the market already priced this in?**
- If the event was widely anticipated (scheduled Fed meeting, expected tariff), the market has already moved. The actual event may cause less reaction than expected — "buy the rumour, sell the news."
- If the event is a genuine surprise (unexpected military strike, surprise bankruptcy), the market has NOT priced it in. Expect the full reaction.

**Question 5: What is the current market state?**
- Healthy market (BTC at highs, low leverage, positive sentiment) + negative event = temporary dip, buy opportunity
- Fragile market (recent crash, high leverage, negative sentiment) + negative event = compounding damage, stay out
- This is where context from the Math Agent matters — is the market already oversold before the news hits?

### Sentiment multiplier logic

Based on the reasoning above, the intelligence engine should output a multiplier:

| Situation | Multiplier | Rationale |
|-----------|-----------|-----------|
| Crisis event detected (exchange collapse, major hack) | 0.0 (block all trades) | Structural damage, unknown severity |
| Active military escalation, no de-escalation signals | 0.15 | Too dangerous, cascade risk |
| Bearish macro + bearish crypto news | 0.3 | Multiple headwinds, high risk |
| Bearish macro OR bearish crypto news (not both) | 0.6 | One headwind, manageable |
| Mildly bearish (general uncertainty, no specific event) | 0.8 | Proceed with caution |
| Neutral (no significant news) | 1.0 | Trade normally |
| Mildly bullish (positive economic data, pro-crypto politics) | 1.05 | Slight edge |
| Bullish (rate cuts confirmed, ETF approvals, ceasefire) | 1.1 | Favourable conditions |
| Very bullish (multiple positive catalysts converging) | 1.15 | Maximum but not reckless |

### The difference between keywords and context

The keyword system sees "war" and scores it as bearish. But consider these headlines:

- "War erupts between Iran and Israel" → Bearish. New conflict = risk-off.
- "War between Iran and Israel ended with ceasefire" → Bullish. Conflict resolution = risk-on.
- "War veteran receives medal of honour" → Neutral. Not relevant to markets.

All three contain the word "war" but have completely different implications. The LLM must read the full headline and understand the MEANING, not just detect the keyword. This is the fundamental advantage of LLM reasoning over keyword matching.

Similarly:
- "Bitcoin crash wipes out $2 billion" → Bearish. Active damage.
- "Bitcoin recovers from crash, trading above $70,000" → Bullish. Recovery confirmed.
- "Experts warn of potential crash" → Mildly bearish. Prediction, not reality.

### Time sensitivity of news

Not all news is equally urgent:

**Act immediately (within current scan):**
- Exchange hack or insolvency announcement
- Military strike or attack
- Emergency Fed action
- Flash crash with $1B+ liquidations

**Act within next few scans (5-15 minutes):**
- Tariff announcements
- CPI/jobs data release
- Regulatory lawsuit announcement
- Major whale movement detected

**Monitor and adjust gradually (hours):**
- Ceasefire negotiations
- Political election results
- ETF application progress
- General macro sentiment shifts

**Background awareness (days):**
- Ongoing war situation
- General economic trajectory
- Industry adoption trends
- Regulatory evolution

---

## Part 7: Combining News with Technical Analysis

### When news and indicators agree

If the Research Agent detects bearish news AND the Math Agent shows overbought conditions (RSI above 75, price at upper Bollinger), the confluence is very strong. Short with high confidence.

If the Research Agent detects bullish news AND the Math Agent shows oversold conditions (RSI below 25, price at lower Bollinger), the confluence is also very strong. Long with high confidence.

Agreement between fundamental (news) and technical (indicators) analysis produces the highest-quality trade signals.

### When news and indicators disagree

**Scenario: Indicators say buy but news says sell**
Example: RSI is at 20 (deeply oversold) but a major exchange just announced insolvency.

Resolution: NEWS WINS. The indicators are showing oversold because of genuine, structural selling that will continue. Do not buy the dip during structural events. The indicators will be "wrong" (or rather, the mean they're expecting price to revert to has itself shifted down).

**Scenario: News says buy but indicators say sell**
Example: ETF just got approved (bullish) but RSI is at 80 (overbought).

Resolution: Wait for a pullback. The news is genuinely bullish and will create sustained buying over weeks. But in the short term, overbought indicators mean a pullback is likely before the next leg up. Let the excited buyers push price up, wait for the inevitable pullback, then enter.

**Scenario: Violent news drop but indicators reach extreme oversold quickly**
Example: Military strike causes BTC to drop 10% in an hour. RSI hits 12. Volume is 5x average. Funding rate goes deeply negative.

Resolution: This is the ideal contrarian setup IF the event is a temporary shock (not structural). The extreme indicators suggest capitulation exhaustion. The high volume confirms forced selling. The negative funding shows shorts are crowded. If the military situation is stabilising (no further escalation), this is a high-conviction long entry.

### The volume confirmation principle

Volume is the universal truth-teller that resolves conflicts between news and indicators:

- If bearish news drops but volume is low → The market doesn't care. Continue trading normally.
- If bearish news drops and volume explodes → The market cares a lot. Respect the move.
- If bullish news hits but volume is low → Fake rally. Don't chase.
- If bullish news hits and volume explodes → Real rally. Get involved.

Volume confirms whether the news has actually changed participant behaviour or if it's just noise.

---

## Part 8: What Recovery Looks Like vs Dead Cat Bounce

### Dead cat bounce (false recovery)

After a crash, price often bounces sharply. This is NOT necessarily the start of a real recovery. A "dead cat bounce" occurs when:
- The bounce happens on LOW volume (no real buying conviction)
- The bounce retraces only 20-30% of the drop (weak)
- RSI barely moves off oversold (no momentum shift)
- MACD stays negative with no sign of histogram shrinking
- News situation has NOT changed (the cause of the crash is still active)
- The bounce is driven by short covering, not new buying

### Real recovery

A genuine recovery shows:
- Increasing volume on the bounce (new buyers entering)
- Retracement of 50%+ of the drop (strong reversal)
- RSI divergence (price at new low but RSI at higher low)
- MACD histogram shrinking toward zero (selling momentum dying)
- News situation stabilising or improving
- Funding rate normalising from extreme negative back toward neutral
- Open interest stabilising (new positions being built, not just exits)

### The system's approach to post-crash trading

1. During the crash: DO NOT trade. Watch. Monitor. Log.
2. At the potential bottom: Look for capitulation signals (extreme volume, extreme RSI, extreme negative funding)
3. First bounce: Observe only. Is it dead cat bounce or real recovery?
4. Confirmation: If volume increases, RSI shows divergence, and news stabilises → enter cautiously with reduced size
5. Sustained recovery: If the move continues with healthy volume → add to position
6. Full recovery: Resume normal trading parameters

This graduated approach prevents the system from buying the dead cat bounce while still catching the real recovery.
