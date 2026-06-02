# Phase 7 - Authoritative Event-Driven Validation Report

Generated: 2026-05-27
Dataset: bybit BTCUSDT 1h
Period scored: 2024-06-05 to 2026-05-27

## Validation Rules

- Candle N can generate a signal only after that candle is final.
- Entry simulation starts at candle N+1, never on the signal candle.
- Open simulated positions remain active until their exit timestamp.
- Same-candle stop/target ambiguity is resolved by stop loss first.
- Position sizing uses floored quantity precision and risk checks before simulation.

## Combined Portfolio Metrics

| Metric | Value |
|---|---:|
| Trades | 46 |
| Win rate | 34.8% |
| Expectancy R | -0.036 |
| Profit factor | 0.943 |
| Gross PnL | $+393.56 |
| Fees | $+506.21 |
| Net PnL | $-242.04 |
| Max drawdown R | 11.540 |
| Fee share of gross | 128.6% |

## Strategy Metrics

| Strategy | Signals | Approved | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL | Max DD R | Entry Misses |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| liquidity_sweep_v1 | 81 | 11 | 11 | 9.1% | -1.056 | 0.061 | $-1,103.11 | 11.620 | 0 |
| squeeze_v1 | 41 | 38 | 38 | 47.4% | 0.017 | 1.036 | $+37.96 | 6.700 | 0 |
| trend_pullback_v1 | 692 | 39 | 39 | 38.5% | -0.202 | 0.564 | $-775.22 | 10.940 | 0 |
| prev_day_breakdown_v1 | 123 | 36 | 36 | 27.8% | 0.370 | 1.385 | $+1,246.09 | 11.760 | 0 |

## Rejection Counts

### liquidity_sweep_v1

| Reason | Count |
|---|---:|
| RISK_DRAWDOWN_LIMIT | 70 |

### squeeze_v1

| Reason | Count |
|---|---:|
| RISK_MAX_POSITIONS | 3 |

### trend_pullback_v1

| Reason | Count |
|---|---:|
| RISK_DRAWDOWN_LIMIT | 584 |
| RISK_MAX_POSITIONS | 69 |

### prev_day_breakdown_v1

| Reason | Count |
|---|---:|
| RISK_DRAWDOWN_LIMIT | 71 |
| RISK_MAX_POSITIONS | 16 |

## Regime Breakdown

### liquidity_sweep_v1

| Regime | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |
|---|---:|---:|---:|---:|---:|
| breakout_pending | 1 | 0.0% | -1.380 | 0.000 | $-124.00 |
| range | 10 | 10.0% | -1.024 | 0.068 | $-979.11 |

### squeeze_v1

| Regime | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |
|---|---:|---:|---:|---:|---:|
| breakout_pending | 22 | 40.9% | -0.190 | 0.659 | $-434.55 |
| range | 3 | 0.0% | -0.617 | 0.000 | $-190.28 |
| trend_down | 5 | 60.0% | 0.604 | 2.899 | $+302.85 |
| trend_up | 8 | 75.0% | 0.460 | 2.358 | $+359.94 |

### trend_pullback_v1

| Regime | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |
|---|---:|---:|---:|---:|---:|
| trend_down | 32 | 34.4% | -0.212 | 0.565 | $-663.57 |
| trend_up | 7 | 57.1% | -0.160 | 0.556 | $-111.65 |

### prev_day_breakdown_v1

| Regime | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |
|---|---:|---:|---:|---:|---:|
| breakout_pending | 5 | 40.0% | 1.280 | 2.306 | $+686.65 |
| trend_down | 31 | 25.8% | 0.224 | 1.233 | $+559.44 |

## Session Breakdown

### liquidity_sweep_v1

| Session | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |
|---|---:|---:|---:|---:|---:|
| asia | 1 | 0.0% | -1.710 | 0.000 | $-161.17 |
| london | 3 | 33.3% | -0.600 | 0.294 | $-159.45 |
| london_ny_overlap | 7 | 0.0% | -1.159 | 0.000 | $-782.49 |

### squeeze_v1

| Session | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |
|---|---:|---:|---:|---:|---:|
| asia | 4 | 50.0% | 0.375 | 2.271 | $+159.96 |
| london | 8 | 62.5% | 0.106 | 1.183 | $+86.23 |
| london_ny_overlap | 15 | 40.0% | 0.120 | 1.264 | $+167.67 |
| ny | 7 | 57.1% | 0.070 | 1.290 | $+43.14 |
| wind_down | 4 | 25.0% | -0.995 | 0.025 | $-419.04 |

### trend_pullback_v1

| Session | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |
|---|---:|---:|---:|---:|---:|
| asia | 13 | 38.5% | -0.026 | 0.908 | $-27.41 |
| london | 11 | 36.4% | -0.425 | 0.398 | $-453.69 |
| london_ny_overlap | 2 | 0.0% | -0.685 | 0.000 | $-140.45 |
| ny | 11 | 45.5% | -0.037 | 0.897 | $-41.52 |
| wind_down | 2 | 50.0% | -0.545 | 0.155 | $-112.15 |

### prev_day_breakdown_v1

| Session | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |
|---|---:|---:|---:|---:|---:|
| asia | 11 | 45.5% | 1.539 | 3.557 | $+1,826.79 |
| london | 7 | 14.3% | -0.334 | 0.722 | $-289.95 |
| london_ny_overlap | 15 | 20.0% | -0.291 | 0.741 | $-546.55 |
| wind_down | 3 | 33.3% | 1.033 | 2.144 | $+255.80 |

## No-Lookahead Proof

Passed: `True`
Rows checked: 3

## Walk-Forward Summary

Windows: 21
Trades: 433
Expectancy R: -0.016
Net PnL: $-552.35
Profitable windows: 9

## Promotion Decision

DO NOT PROMOTE. No strategy meets Phase 7 promotion gates.
