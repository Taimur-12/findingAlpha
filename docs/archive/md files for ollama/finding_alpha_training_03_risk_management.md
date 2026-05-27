# Finding Alpha — Risk & Position Management Intelligence

> This document teaches the intelligence engine how to think about risk, position sizing,
> portfolio exposure, and capital preservation. Risk management is not a set of rules to follow —
> it is a way of thinking. The system should internalise the principles behind each rule so it can
> reason about risk in novel situations, not just apply hardcoded limits.
> The system operates with a small account and uses leverage aggressively. The goal is rapid growth
> through high volume trading with controlled risk per trade, not conservative capital preservation.
> Grow fast, stay disciplined, compound through frequency.

---

## Part 1: The Philosophy of Risk for Small Accounts

### The small account reality

A $500-$2,000 account trading with 0.25% risk per trade makes $1.25-$5.00 per winning trade. That is not meaningful. It takes months to see real growth. The account needs to grow fast enough to compound into something substantial.

The solution is not reckless gambling. It is CONTROLLED aggression — higher risk per trade, higher leverage, more trades, faster exits. The risk per trade increases but the DISCIPLINE stays the same. Every trade still has a calculated stop loss, a defined risk amount, and a maximum loss. The difference is that each trade risks 1-2% instead of 0.25%, and leverage is used to amplify position sizes.

### The scaling plan

The system should adapt its risk profile based on account size:

| Account Size | Risk Per Trade | Max Leverage | Daily Loss Limit | Daily Target | Approach |
|-------------|---------------|-------------|-----------------|-------------|----------|
| $100-$500 | 2.0% | 15-20x | -8% | +5% | Aggressive scalping, high frequency |
| $500-$2,000 | 1.5% | 10-15x | -6% | +4% | Active trading, moderate frequency |
| $2,000-$10,000 | 1.0% | 5-10x | -4% | +3% | Balanced, reduce aggression |
| $10,000-$50,000 | 0.5% | 3-5x | -3% | +2% | Conservative growth |
| $50,000+ | 0.25% | 1-3x | -1.5% | +1% | Capital preservation mode |

As the account grows, the system automatically becomes more conservative. This protects larger capital while allowing smaller accounts to grow aggressively.

### The golden rules (adapted for aggressive trading)

**Rule 1: Every trade has a calculated risk amount.**
Whether you risk 1% or 2%, it is a PLANNED number. No trade is taken without knowing exactly how much you can lose. The number is bigger than the conservative approach but it is still controlled.

**Rule 2: The stop loss is sacred — even more so with leverage.**
With 10-20x leverage, a 2% move against you without a stop loss can wipe out 20-40% of your account. The stop loss is not optional. It is set ON THE EXCHANGE before the trade is confirmed. No exceptions.

**Rule 3: Leverage is a position sizing tool, not a risk tool.**
Leverage does NOT change how much you risk. You still risk 1-2% per trade. Leverage changes the POSITION SIZE you can take with your margin. A 10x leveraged $2,000 position with a $20 stop loss risks $20 — exactly the same as a 1x $200 position with a $20 stop loss. The leverage lets you capture the full move, not increase the risk.

**Rule 4: Compound through frequency, not size.**
Make 10 trades risking 1.5% each instead of 1 trade risking 15%. Each trade is independent. If you win 6 and lose 4, you net positive. One bad trade doesn't destroy you. Volume is the edge, not size.

**Rule 5: Scale down risk as the account grows.**
A $500 account can afford to be aggressive because losing it, while painful, is recoverable. A $50,000 account cannot afford the same aggression because losing 20% = $10,000. The system must automatically reduce risk as the account grows.

---

## Part 2: Position Sizing — Aggressive but Calculated

### The core formula (same math, bigger numbers)

```
risk_per_trade = 1.5% of account balance (adjustable 1-2%)
risk_amount = account_balance × 0.015
stop_distance = ATR × stop_multiplier
position_size = risk_amount / stop_distance
leverage_needed = (position_size × price) / account_balance
```

**Example with $1,000 account, BTC at $70,000, ATR $400:**

High confidence (stop mult 1.0x ATR):
- Risk amount: $1,000 × 0.015 = $15.00
- Stop distance: $400 × 1.0 = $400
- Position size: $15.00 / $400 = 0.0375 BTC
- Position value: 0.0375 × $70,000 = $2,625
- Leverage needed: $2,625 / $1,000 = 2.6x
- If price hits stop loss, you lose exactly $15.00

Medium confidence (stop mult 1.5x ATR):
- Stop distance: $400 × 1.5 = $600
- Position size: $15.00 / $600 = 0.025 BTC
- Position value: 0.025 × $70,000 = $1,750
- Leverage needed: 1.75x
- Same $15.00 risk, smaller position, more room

Lower confidence (stop mult 2.0x ATR):
- Stop distance: $400 × 2.0 = $800
- Position size: $15.00 / $800 = 0.01875 BTC
- Position value: 0.01875 × $70,000 = $1,312
- Leverage needed: 1.3x
- Same $15.00 risk, smallest position, most room

### Scalping mode (5-minute timeframe)

For quick 5M scalps, the ATR is much smaller (maybe $80 for BTC on 5M), allowing tighter stops and more leverage:

- Risk amount: $15.00
- ATR on 5M: $80
- Stop distance: $80 × 1.0 = $80
- Position size: $15.00 / $80 = 0.1875 BTC
- Position value: $13,125
- Leverage needed: 13.1x
- Target: $80-$120 profit ($80 at 1:1 R:R, $120 at 1:1.5)

This is where leverage becomes essential. A $13,000 position on a $1,000 account requires 13x leverage. But the RISK is still only $15 — the stop loss at $80 below entry ensures this. The leverage lets you capture meaningful dollar amounts from small percentage moves.

### Risk per trade by confidence level

| Confidence | Risk Per Trade | Stop Multiplier | Reasoning |
|-----------|---------------|----------------|-----------|
| 35-45 | 0.75% | 2.0x ATR | Low confidence — still take it but reduce risk |
| 45-55 | 1.0% | 1.5x ATR | Moderate — standard aggressive |
| 55-65 | 1.5% | 1.25x ATR | Good — full standard risk |
| 65-75 | 2.0% | 1.0x ATR | High — maximum risk, tight stop |
| 75+ | 2.0% | 0.75x ATR | Very high — tight stop, big position |

### Maximum leverage limits

Even with aggressive sizing, leverage has absolute limits:

| Timeframe | Max Leverage | Reasoning |
|----------|-------------|-----------|
| 5-minute | 20x | Tight stops, quick exits, high frequency |
| 15-minute | 15x | Standard scalping timeframe |
| 1-hour | 10x | Wider stops needed, less leverage |

**Never exceed these limits regardless of confidence.** A 50x leveraged position with a $15 stop can still lose $15 — but if the exchange has slippage during a flash crash, the stop may not fill at the expected price. Lower leverage provides a buffer against slippage.

---

## Part 3: Stop Loss Strategies

### ATR-based stops (primary method)

**Stop multipliers by confidence (aggressive):**

| Confidence | Stop Multiplier | Reasoning |
|-----------|----------------|-----------|
| 75+ | 0.75x ATR | Extremely tight — price should move immediately |
| 65-75 | 1.0x ATR | Tight — high conviction entry |
| 55-65 | 1.25x ATR | Standard — moderate room |
| 45-55 | 1.5x ATR | Wider — give it room to work |
| 35-45 | 2.0x ATR | Widest — lower conviction, needs space |

### Structure-based stop adjustment

The ATR stop should be fine-tuned based on price structure:
- If there's a clear support level just below the ATR stop, move the stop BELOW the support (slightly further away but better positioned)
- If the ATR stop is in no-man's-land between two levels, move it below the nearest support
- A stop at a technical level is less likely to be hit by random noise

### Trailing stops for profit protection

**Breakeven trail:**
- Move stop to entry when profit reaches 1x ATR
- Risk is now zero — worst case is a scratch trade

**ATR trail:**
- Once in profit, trail the stop at 1x ATR behind the highest profit point
- This locks in progressively more profit as the trade moves in your favour

**Supertrend trail:**
- Use Supertrend line as the stop level
- When Supertrend flips, close the trade
- Best in trending markets — can ride moves for many R multiples

**Quick scalp trail (for 5M trades):**
- At +0.5R: move stop to breakeven
- At +1R: take 50% off, trail rest at breakeven
- At +1.5R: take remaining off or trail at +0.5R
- Speed is key on 5M — don't give back profit waiting for bigger moves

### Take profit strategies (aggressive)

**For scalps (5M):**
- Primary target: 1:1 R:R (risk $15, target $15)
- Extended target: 1:1.5 R:R ($22.50)
- Quick in, quick out. Don't get greedy on scalps.

**For standard trades (15M):**
- Primary target: 1:1.5 R:R
- Extended target: 1:2 R:R
- Take 50% at primary, trail the rest

**For swing trades (1H):**
- Primary target: 1:2 R:R
- Extended target: 1:3 R:R with Supertrend trail
- These trades justify patience — let them run

**Partial take profit (scaling out):**
- Take 50% off at 1:1 R:R (guaranteed profit)
- Move stop to breakeven on remaining 50%
- Let remaining run to 1:1.5 or 1:2 or trail
- This guarantees profit while keeping upside open

---

## Part 4: Dollar-Cost Averaging (DCA) — Aggressive Edition

### DCA for small accounts

**Layer 1 (initial): 40% of full position**
- Enter when confidence is above threshold
- Set stop for full intended position

**Layer 2 (confirmation): 35% of full position**
- Enter when price drops further AND a fresh signal confirms
- Must independently pass analysis
- Average entry price improves

**Layer 3 (extreme): 25% of full position**
- Enter at extreme levels (RSI < 15, multiple timeframe confirmation)
- Best entry of the three — highest conviction

**Total risk across all layers = risk_per_trade limit (1.5%)**
- Layer 1: 0.6% risk
- Layer 2: 0.5% risk
- Layer 3: 0.4% risk
- Total: 1.5% maximum

**Critical rule:** Each layer must pass its OWN analysis. DCA is not averaging down on a bad trade. If the reason for the trade no longer exists, do NOT add more layers. Cut the loss instead.

---

## Part 5: The Risk Hierarchy — Seven Layers (Aggressive Edition)

### Layer 1: Per-Trade Risk Cap (1-2%)

Limits maximum loss from any single trade. At 1.5% risk with 60% win rate, you can sustain 4 consecutive losses before hitting the daily limit. The backtested 63% win rate provides comfortable margin.

### Layer 2: Maximum Concurrent Positions (3)

Three positions at 1.5% each = 4.5% maximum simultaneous risk. During high-risk environments, reduce to 2 positions.

### Layer 3: Correlation Guard (0.85)

Correlated positions are hidden concentration. BTC and ETH longs are effectively one trade with double exposure.

### Layer 4: Losing Streak Breaker

- 3 consecutive losses → 15-minute pause
- 5 losses in a session → 1-hour pause
- Borderline losses: raise threshold. Strong-signal losses: full review.

### Layer 5: Daily Loss Limit (-6%)

Buffer zones:
- At -3%: Reduce risk per trade to 1.0%
- At -4.5%: Reduce to 0.5%
- At -5.5%: Only confidence above 70
- At -6%: Full stop

### Layer 6: Daily Profit Target (+4%)

Flexible target:
- After +2%: Reduce risk to 1.0% (protect gains, keep trading)
- After +3%: Reduce risk to 0.5% (cautious but active)
- After +4%: Full stop — lock the win

### Layer 7: Kill Switch (-15%)

Early warning escalation:
- At -8%: Alert CEO. Reduce risk to 1.0%.
- At -10%: Urgent alert. Reduce to 0.5%. Highest-confidence only.
- At -12%: Critical alert. 1 position max.
- At -15%: Kill switch. Manual restart required.

---

## Part 6: Portfolio Management

### Trade frequency targets

| Session | Expected Trades | Reasoning |
|---------|----------------|-----------|
| Asia | 0-2 | Low volume — only extreme setups |
| London | 2-4 | Active, reacts to Asia range |
| London-NY Overlap | 3-6 | Prime zone — maximum activity |
| New York | 2-4 | Follow-through from overlap |
| Wind-down | 0-1 | Reduce activity |
| **Daily total** | **5-15** | **Compound through volume** |

### Directional balance

- Ideal: mix of long and short positions
- Acceptable: 2 in one direction, 1 in the other
- Risky: all 3 same direction — only in strong trends

---

## Part 7: Managing Winning Trades (Aggressive)

**At +0.5R:** Move stop to breakeven. Zero-risk established quickly.

**At +1R:** Take 50% off. Trail remaining at breakeven. Trade already paid for itself.

**At +1.5R:** Take another 25% off. Trail remaining at +0.5R. Guaranteed $15+ profit.

**At +2R or beyond:** Close remaining or trail with Supertrend. Bonus territory.

### The "no regret" principle

Take profit at planned levels without regret. Consistent small profits beat occasional large profits that come with frequent large losses.

---

## Part 8: Managing Losing Trades

At 1.5% risk per trade with 60% win rate and 1:1.5 R:R:
- 10 trades: 6 wins × $22.50 = $135, 4 losses × $15 = $60
- Net: +$75 per 10 trades
- Each loss is the cost of admission for that $75 profit

### Post-loss protocol

1. Stop hit as planned? → Move on.
2. Slippage issue? → Check leverage and liquidity.
3. 3+ in a row? → Pause and check regime.
4. NEVER increase size on next trade to "make it back."
5. Require HIGHER confidence for trade after a loss, not lower.

---

## Part 9: The Scaling Plan — From $1,000 to $100,000

### Phase 1: $1,000 → $5,000 (Aggressive)
- Risk: 1.5-2.0%, Leverage: 10-20x, Trades/day: 5-15, Target: +3-5% daily
- Timeline: 2-4 months. Focus: validate the system.

### Phase 2: $5,000 → $20,000 (Moderate)
- Risk: 1.0-1.5%, Leverage: 5-10x, Trades/day: 3-10, Target: +2-3% daily
- Focus: consistency over aggression.

### Phase 3: $20,000 → $100,000 (Conservative)
- Risk: 0.5-1.0%, Leverage: 3-5x, Trades/day: 2-6, Target: +1-2% daily
- Focus: capital preservation, larger absolute profits.

### Phase 4: $100,000+ (Institutional)
- Risk: 0.25-0.5%, Leverage: 1-3x
- Add portfolio optimisation (NVIDIA CVaR), multiple strategies
- Focus: risk-adjusted returns, Sharpe ratio.

The system automatically adjusts parameters when account milestones are reached.

---

## Part 10: Recovery Protocol

### After daily loss limit (-6%)
1. Trading stops. Existing positions managed.
2. CEO notified. Next day: first 3 trades at 1.0% risk. If profitable, restore to 1.5%.

### After losing streak (3 consecutive)
1. 15-minute pause. Re-check news, regime, volatility.
2. Resume with confidence threshold +10 points.
3. Next loss: 1-hour pause.

### After kill switch (-15%)
1. ALL trading stops permanently. Urgent CEO alert.
2. Manual review required. On restart: first 10 trades at 0.5% risk.

### After system crash
1. Check all open positions. Verify exchange-side stops.
2. Close positions past max holding time. Log failure.
3. Resume with reduced risk for first 3 trades.
