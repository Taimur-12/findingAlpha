# Phase 7B - Waqar Strategy 1 EMA Probe

## Interpretation

- Timeframe: 15m BTCUSDT Bybit.
- EMA set: 9, 13, 21, 55, 300.
- Literal trend definition: EMA55 crossing above EMA300 marks uptrend; crossing below marks downtrend.
- Validation uses next-candle execution, 0.25% simulated risk, fees/slippage/funding model, and one open position at a time.
- Geometry grid: 0.75-1.5 ATR stop, 1.5-3.0 ATR target, 90-360 minute max hold.

## Top Variant/Geometry Results

| Variant | Geometry | Signals | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL | Max DD R | Fee Share |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned_stack_adx20_fast_cross | runner_1p0_3p0_360m | 376 | 376 | 30.9% | -0.370 | 0.675 | $-3,460.34 | 149.60 | N/A |
| aligned_stack_adx20_fast_cross | scalp_1p0_1p5_180m | 385 | 385 | 41.6% | -0.388 | 0.575 | $-3,707.92 | 165.99 | N/A |
| fast_9_13_cross_in_55_300_trend | scalp_1p0_1p5_180m | 789 | 789 | 40.2% | -0.501 | 0.497 | $-9,833.71 | 408.33 | N/A |
| fast_9_13_cross_in_55_300_trend | runner_1p0_3p0_360m | 762 | 762 | 28.7% | -0.531 | 0.570 | $-10,071.85 | 412.20 | N/A |
| aligned_stack_adx20_fast_cross | scalp_0p75_1p5_90m | 397 | 397 | 34.0% | -0.574 | 0.478 | $-5,676.79 | 242.54 | N/A |
| literal_55_300_cross | scalp_1p0_1p5_180m | 286 | 286 | 35.3% | -0.583 | 0.427 | $-4,151.72 | 168.25 | N/A |
| fast_9_13_cross_in_55_300_trend | scalp_0p75_1p5_90m | 814 | 814 | 32.1% | -0.707 | 0.410 | $-14,340.71 | 582.38 | N/A |
| literal_55_300_cross | scalp_0p75_1p5_90m | 286 | 286 | 30.8% | -0.745 | 0.376 | $-5,306.53 | 215.03 | N/A |
| literal_55_300_cross | runner_1p0_3p0_360m | 286 | 286 | 21.3% | -0.776 | 0.393 | $-5,517.74 | 225.24 | N/A |

## Decision

Rejected.

This probe does not alter the Phase 8 recommendation unless a variant clears the same evidence bar as the existing candidate.