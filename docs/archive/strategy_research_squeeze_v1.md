# Strategy Research — squeeze_v1

Generated: 2026-05-27  
Dataset: Bybit BTCUSDT 1h, 2025-12-07 to 2026-05-27 (~6 months post-warmup)  
Equity: $10,000 | Risk/trade: 1% | Max hold: 8h  
Fees: maker 0.02% entry, taker 0.055% stop, slippage 0.05%

---

## Hypothesis

Volatility is mean-reverting. When Bollinger Band bandwidth compresses to historically low levels, a volatility expansion (breakout) is imminent. The direction of the breakout can be filtered using price position relative to the bands and the Supertrend indicator. A breakout above the upper band with a bullish Supertrend suggests an upside expansion; the converse for downside.

---

## Implementation

**File**: `src/finding_alpha/strategies/squeeze_v1.py`

**Conditions (long)**:
- Regime not in `{crisis, high_volatility}` (contradictory to low-vol squeeze setup)
- `bb_bandwidth ≤ 20.0` (compression threshold — bandwidth below 20% of middle band)
- Close > `bb_upper` (initial breakout above the band)
- `supertrend_direction == "up"` (trend confirmation)
- `volume_z_score ≥ 0.5` (light volume filter)
- R:R ≥ 1.5 with stop at `bb_middle`, target at `bb_upper + 2.0×ATR`

**Conditions (short)**:
- Mirror conditions: close < `bb_lower`, supertrend "down"
- Stop at `bb_middle`, target at `bb_lower - 2.0×ATR`

**Entry**: close of breakout bar (limit order)  
**Stop**: Bollinger middle band  
**Target**: 2.0×ATR beyond the band  
**Max hold**: 3h (180 minutes)

---

## Backtest Results

| Metric | Value |
|---|---|
| Signals fired | 7 |
| Outcomes simulated | 7 |
| Entry fill rate | 100% |
| Win rate | 28.6% |
| Expectancy (R) | -0.374 |
| Profit factor | 0.59 |
| Net PnL | -$262.21 |
| Max drawdown (R) | 6.44 |
| Fee share of gross | N/A (gross pnl negative) |

**Exit breakdown**:
- Stop loss: 5 (71.4%)
- Take profit: 2 (28.6%)

---

## Analysis

**Critical issue — sample size**: 7 trades over 6 months is not a meaningful sample. No statistical conclusion can be drawn from 7 observations. The negative results could represent bad luck as much as a bad strategy.

**Fundamental problem with the setup**: The squeeze_v1 logic has an internal contradiction. Regime classification marks high-volatility regimes and blocks the strategy. But low BB bandwidth (the squeeze condition) means the strategy only fires when volatility is low. In trending markets, volatility often stays elevated, so the squeeze condition is rarely met in the best conditions (strong trends). This produces an extremely low signal rate — 7 trades in 6 months.

**Stop placement issue**: The stop at `bb_middle` is approximately 0.5 band-width from entry. After a volatility expansion, price frequently retests the middle band before continuing — making the stop location vulnerable to normal post-breakout noise.

**Win rate (28.6%)**: The 2 winners needed to be 2-3× the size of the average loser to make the strategy work. With 5 losses vs. 2 wins at a -0.374R expectancy, the average winner is not compensating for the losses.

**Signal count problem**: 7 trades is not enough to run a meaningful parameter grid. Any sensitivity analysis would be noise.

---

## Verdict

**Status**: REJECTED for v1 — insufficient signal frequency and negative expectancy.

The core problem is structural: requiring both low volatility (bandwidth compression) AND a strong directional breakout simultaneously produces too few qualifying setups. The 3h max hold is also too short for a 1h-bar strategy — it limits the capture window to 3 bars, often exiting before a real trend can develop.

**If revisiting**:
1. Separate the squeeze detection from the breakout entry — fire signal on the first bar after squeeze resolves into a trend, not during compression
2. Extend max hold to 8-12h to allow trend to develop
3. Require Supertrend flip (change of direction) not just current state
4. Test on 15m bars where squeeze patterns are more frequent

**Not included in v1 live candidate list.**
