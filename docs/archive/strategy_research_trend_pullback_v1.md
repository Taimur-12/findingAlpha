# Strategy Research — trend_pullback_v1

Generated: 2026-05-27  
Dataset: Bybit BTCUSDT 1h, 2025-12-07 to 2026-05-27 (~6 months post-warmup)  
Equity: $10,000 | Risk/trade: 1% | Max hold: 8h  
Fees: maker 0.02% entry, taker 0.055% stop, slippage 0.05%

---

## Hypothesis

In a confirmed trend, price periodically pulls back to the EMA 50 before resuming. Entering on pullbacks to EMA 50 within a strong trend offers an asymmetric risk/reward: the stop is just below the EMA (tight) and the target is a continuation of the prior trend leg (wide). ADX confirms trend strength and RSI filters out extreme momentum readings (overbought/oversold relative to the pullback entry).

---

## Implementation

**File**: `src/finding_alpha/strategies/trend_pullback_v1.py`

**Conditions (long, trend_up regime only)**:
- Regime must be `trend_up` (EMA 20 > 50 > 200, ADX ≥ 20, Supertrend bullish)
- EMA alignment confirmed: `ema_20 > ema_50 > ema_200`
- Price in pullback zone: `close in [ema_50, ema_50 + 1.5×ATR]`
- RSI momentum filter: `40 ≤ rsi_14 ≤ 60` (mid-range, not overbought)
- ADX strength: `adx_14 ≥ 20`
- R:R ≥ 1.5 with 0.5×ATR stop below EMA 50, target at 2.5×ATR above entry

**Conditions (short, trend_down regime only)**:
- Mirror conditions with price in `[ema_50 - 1.5×ATR, ema_50]`
- RSI: `40 ≤ rsi_14 ≤ 60`

**Confidence**: 0.75 if ADX ≥ 28, else 0.65

**Entry**: close of pullback bar  
**Stop**: EMA 50 ± 0.5×ATR  
**Target**: 2.5×ATR from entry (single target)  
**Max hold**: 6h (360 minutes)

---

## Backtest Results

| Metric | Value |
|---|---|
| Signals fired | 251 |
| Outcomes simulated | 251 |
| Entry fill rate | 100% |
| Win rate | 43.4% |
| Expectancy (R) | -0.097 |
| Profit factor | 0.81 |
| Net PnL | -$2,435.23 |
| Max drawdown (R) | 31.36 |
| Fee share of gross | N/A (gross pnl negative) |

**Exit breakdown**:
- Stop loss: 91 (36.3%)
- Max hold timeout: 123 (49.0%)
- Take profit: 37 (14.7%)

---

## Parameter Sensitivity — RSI Range

| RSI range | Trades | Win rate | Expectancy (R) |
|---|---|---|---|
| 35–65 | 254 | 42.9% | -0.110 |
| 40–60 (baseline) | 251 | 43.4% | -0.097 |
| 42–58 (tighter) | 243 | 43.6% | -0.099 |
| 38–55 (asymmetric) | 229 | 42.4% | -0.108 |

---

## Analysis

**High signal frequency — critical problem**: 251 trades over 6 months (~42/month) indicates the strategy is overtrigering. The regime classifier marks `trend_up` for extended periods in a trending market, and the proximity condition `[ema_50, ema_50 + 1.5×ATR]` is wide enough to catch many bars.

**Max hold timeout dominates exits (49%)**: Nearly half of all trades exit at the 6-hour max hold without hitting stop or target. This means price is spending most of its time stalling rather than moving decisively after entry. The 2.5×ATR target is often not reached within 6 bars, suggesting the target is too ambitious for the timeframe, or the entry timing is poor.

**Negative expectancy across all RSI ranges**: The sensitivity grid confirms this is not a parameter tuning problem. No RSI range produces positive expectancy. The strategy's edge is structural — or rather, the edge is not there at current parameters.

**Root cause — entry quality**: The proximity zone `[ema_50, ema_50 + 1.5×ATR]` is too permissive. It allows entry anywhere in a 1.5×ATR band above EMA 50. Bars that are 1.4×ATR above EMA 50 are not really "pulling back to EMA 50" — they're just in the general vicinity. This dilutes signal quality.

**Stop placement tightness**: 0.5×ATR stops on 1h bars are tight enough that normal intrabar volatility triggers stops. BTC routinely moves 0.3-0.5×ATR within a single 1h bar even in calm conditions.

---

## Verdict

**Status**: REJECTED for v1 at current parameters. Requires significant rework before live candidacy.

Core issues:
1. **Too many signals** — 251 in 6 months means ~42/month, which is unsustainable from a risk management perspective. With 1% risk/trade, this is potentially 42% of equity at risk per month (before compounding effects). The portfolio heat cap (6% total open risk) provides some protection, but the overtrading is still problematic.

2. **Max hold timeout dominating** — 49% timeout rate means the trend continuation is not materializing within the hold window. Either the entries are in consolidation pockets, or the 6h hold is too short for the target.

3. **Negative expectancy is consistent** — RSI sensitivity grid shows the issue is not the RSI threshold; all variations produce similar negative results.

**Modifications required before v1 candidacy**:
1. Tighten proximity zone to `[ema_50, ema_50 + 0.75×ATR]` — only take entries very close to EMA 50
2. Add minimum time since last EMA 50 touch (e.g., 8+ bars) to avoid repeated entries in the same zone
3. Increase max hold to 12h or use a trailing stop instead of fixed hold
4. Reduce target to 1.8×ATR or scale out at 1.5×ATR (50%) and trail the remainder
5. Consider requiring Supertrend to have been bullish for 5+ consecutive bars (established trend, not just triggered)

**Not included in v1 live candidate list in current form.**
