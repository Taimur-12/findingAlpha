# Strategy Research — liquidity_sweep_v1

Generated: 2026-05-27  
Dataset: Bybit BTCUSDT 1h, 2025-12-07 to 2026-05-27 (~6 months post-warmup)  
Equity: $10,000 | Risk/trade: 1% | Max hold: 8h  
Fees: maker 0.02% entry, taker 0.055% stop, slippage 0.05%

---

## Hypothesis

Large players accumulate or distribute by sweeping liquidity pools sitting above swing highs or below swing lows. After the sweep, price reclaims the level quickly — trapped longs/shorts are forced to cover, propelling a move in the opposite direction. The setup requires:
1. A significant wick below a key structural low (long setup) or above a structural high (short setup)
2. Price closing back above (or below) the swept level within the same bar
3. A volume spike confirming institutional participation

---

## Implementation

**File**: `src/finding_alpha/strategies/liquidity_sweep_v1.py`

**Conditions (long)**:
- Regime not in `{crisis, high_volatility, trend_down}`
- `prev_day_low` is available
- Bar low ≤ `prev_day_low` (sweep of prior day low)
- Bar close > `prev_day_low` (reclaim within the bar)
- `volume_z_score ≥ 1.5` (volume spike)
- R:R ≥ 1.5 after 0.25×ATR stop buffer below sweep low

**Conditions (short)**:
- Regime not in `{crisis, high_volatility, trend_up}`
- `prev_day_high` is available
- Bar high ≥ `prev_day_high` (sweep of prior day high)
- Bar close < `prev_day_high` (reclaim within the bar)
- `volume_z_score ≥ 1.5`
- R:R ≥ 1.5

**Entry**: close of sweep bar (limit order at close price)  
**Stop**: sweep extreme ± 0.25×ATR buffer  
**Target**: 2.0×ATR from entry (single target, full position)  
**Max hold**: 4h (240 minutes)

Ambiguous signals where both long and short fire on the same bar → return None (rare but possible on a bar that sweeps both high and low).

---

## Backtest Results

| Metric | Value |
|---|---|
| Signals fired | 21 |
| Outcomes simulated | 21 |
| Entry fill rate | 100% |
| Win rate | 47.6% |
| Expectancy (R) | +0.030 |
| Profit factor | 1.04 |
| Net PnL | +$62.12 |
| Max drawdown (R) | 6.34 |
| Fee share of gross | 79.8% |

**Exit breakdown**:
- Stop loss: 11 (52.4%)
- Take profit: 7 (33.3%)
- Max hold timeout: 3 (14.3%)

---

## Analysis

**Signal frequency**: 21 trades over ~6 months = ~3.5 trades/month. Very low frequency. This makes the expectancy estimate statistically unreliable — 21 trades is not enough to distinguish skill from noise.

**Fee drag is critical**: Fee share of gross PnL is 79.8%. At 2×ATR targets on 1h bars, the gross winner is typically $100-$200 but fees consume ~$80-$160 of that. The strategy is marginally profitable before fees and roughly breakeven after.

**R:R structure**: With 0.25×ATR stop buffer and 2.0×ATR target, the theoretical R:R is approximately 2.0/1.25 = 1.6. In practice, entries at the close of the sweep bar mean we're often entering partway into the reclaim move, reducing the actual R captured.

**Stop loss rate (52%)**: More losses than wins, but the wins are larger — this is the expected shape for a reversal strategy. The positive expectancy (+0.03R) is fragile given the sample size.

**Max drawdown**: 6.34R over 21 trades is high for the signal count. A losing streak of 6-7 trades would wipe the entire run's gains.

---

## Verdict

**Status**: MARGINAL — needs more data and refinement before promotion.

Strengths:
- Positive expectancy (barely)
- Clear structural logic (sweep + reclaim is a well-understood pattern)
- Low signal frequency means few commissions

Weaknesses:
- 21-trade sample is too small for statistical confidence
- Fee drag at 79.8% of gross is unsustainable — needs larger R targets or tighter stops
- Borderline profit factor (1.04) means any regime change could flip negative

**Next steps if continuing research**:
1. Test on longer dataset (2 years+) for sample size
2. Increase ATR target multiplier to 2.5-3.0× to reduce fee share
3. Add sweep depth filter (minimum wick distance below level) to improve signal quality
4. Consider time-of-day filter (London/NY session overlaps only)
