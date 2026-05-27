# Phase 7C — short_composite_v1 Candidate Report

## Strategy

- SHORT-only composite: EMA20 intra-bar rejection + prev-day low breakdown.
- Two complementary entry triggers sharing one position slot (breakdown has priority).
- Timeframe: 1h. Symbol: BTCUSDT (Bybit).
- Risk: 0.25% per trade. Max hold: 12h.
- EMA rejection: bar.open > EMA20 >= bar.close, trend_down regime, ADX >= 20.
  Stop: EMA50 + 0.5 ATR. Target: entry - 4.5 ATR.
- Breakdown: close < prev_day_low, vol_z >= 1.0, trend_down or breakout_pending.
  Stop: entry + 0.75 ATR. Target: entry - 4.5 ATR.

## Adjusted Phase 7C Gate (SHORT-only, single instrument)

Trades >= 225 | PF >= 1.25 | Exp R > 0.0 | WF >= 45%

## Authoritative Metrics

| Metric | Value |
|---|---:|
| Signals | 402 |
| Approved | 233 |
| Trades | 233 |
| Win rate | 36.9% |
| Expectancy R | 0.2348 |
| Profit factor | 1.301 |
| Net PnL | $+1,397.97 |
| Fee share | 34.0% |
| Max drawdown R | 19.90 |

## Walk-Forward

| Metric | Value |
|---|---:|
| Windows | 33 |
| Test trades | 355 |
| Profitable windows | 16 |
| Aggregate exp R | 0.0861 |
| Aggregate net PnL | $+775.07 |

## Monthly Breakdown

| Month | Trades | Exp R | Net PnL |
|---|---:|---:|---:|
| 2024-06 | 23 | 0.597 | $+340.16 |
| 2024-07 | 5 | -0.156 | $-21.37 |
| 2024-08 | 9 | 0.116 | $+25.13 |
| 2024-09 | 10 | 1.155 | $+298.05 |
| 2024-10 | 7 | 1.046 | $+192.05 |
| 2024-11 | 3 | -0.543 | $-43.56 |
| 2024-12 | 6 | -1.100 | $-174.62 |
| 2025-01 | 4 | -1.248 | $-129.68 |
| 2025-02 | 16 | 0.329 | $+132.85 |
| 2025-03 | 9 | 0.502 | $+117.60 |
| 2025-04 | 7 | 0.169 | $+29.45 |
| 2025-05 | 7 | -0.347 | $-66.53 |
| 2025-06 | 12 | -0.428 | $-139.48 |
| 2025-07 | 1 | -1.450 | $-37.86 |
| 2025-08 | 18 | 0.342 | $+160.15 |
| 2025-09 | 9 | -0.391 | $-92.91 |
| 2025-11 | 10 | 0.210 | $+51.72 |
| 2025-12 | 18 | 0.283 | $+133.16 |
| 2026-01 | 18 | 1.042 | $+503.59 |
| 2026-02 | 12 | 0.268 | $+86.22 |
| 2026-03 | 11 | 0.045 | $+11.08 |
| 2026-04 | 7 | -0.019 | $-3.74 |
| 2026-05 | 11 | 0.088 | $+26.51 |

## Concentration

- Profitable months: 14/23.
- Top trade share of total net PnL: 11.8%.

## Decision

Gate: **PASS**

short_composite_v1 passes the adjusted Phase 7C gate (225+ trades, SHORT-only, single instrument).
Promote to Phase 8 paper observation alongside the existing prev_day_breakdown_v1 run.
Both strategies share the same SHORT-only bias. Monitor independently. Do not combine into one portfolio until 8-week live observation is complete.