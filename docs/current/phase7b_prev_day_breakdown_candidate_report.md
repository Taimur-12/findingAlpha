# Phase 7B - prev_day_breakdown_v1 Candidate Report

## Strategy

- Short-only prior-day-low breakdown continuation.
- Timeframe: 1h.
- Risk used for validation: 0.25% per trade.
- Entry starts on the candle after the final breakdown candle.
- Stop: 0.75 ATR above entry. Target: 4.5 ATR below entry. Max hold: 12h.
- Sessions: Asia, London, London-NY overlap, wind-down. NY solo blocked.
- Volume filter: volume z-score >= 2.0.

## Authoritative Metrics

| Metric | Value |
|---|---:|
| Signals | 123 |
| Approved | 95 |
| Trades | 95 |
| Win rate | 31.6% |
| Expectancy R | 0.420 |
| Profit factor | 1.441 |
| Net PnL | $+1,015.03 |
| Fee share of gross | 26.9% |
| Max drawdown R | 20.15 |

## Walk-Forward

| Metric | Value |
|---|---:|
| Windows | 21 |
| Test trades | 71 |
| Aggregate expectancy R | 0.469 |
| Aggregate net PnL | $+843.47 |
| Profitable windows | 9 |

## Monthly Concentration

| Month | Trades | Expectancy R | Net PnL |
|---|---:|---:|---:|
| 2024-06 | 9 | 1.031 | $+229.04 |
| 2024-07 | 5 | -1.060 | $-133.70 |
| 2024-08 | 7 | 1.083 | $+187.72 |
| 2024-09 | 6 | 1.278 | $+195.92 |
| 2024-10 | 2 | 2.205 | $+113.93 |
| 2024-11 | 1 | -1.440 | $-37.84 |
| 2024-12 | 2 | -1.460 | $-76.02 |
| 2025-01 | 1 | -1.300 | $-33.87 |
| 2025-02 | 9 | -0.802 | $-188.61 |
| 2025-03 | 4 | 0.470 | $+47.60 |
| 2025-04 | 5 | 0.132 | $+15.73 |
| 2025-05 | 3 | 1.060 | $+81.92 |
| 2025-06 | 1 | -1.400 | $-36.18 |
| 2025-08 | 7 | 0.953 | $+171.82 |
| 2025-09 | 2 | -2.010 | $-104.83 |
| 2025-11 | 2 | -1.370 | $-70.91 |
| 2025-12 | 4 | 1.325 | $+136.88 |
| 2026-01 | 10 | 2.149 | $+568.19 |
| 2026-02 | 4 | 0.555 | $+60.47 |
| 2026-03 | 5 | -0.280 | $-38.80 |
| 2026-04 | 2 | -0.980 | $-53.93 |
| 2026-05 | 4 | -0.177 | $-19.50 |

## Concentration Checks

- Profitable months: 11/22.
- Largest winning trade share of total net PnL: 15.9%.

## Decision

Do not promote to live or micro-live. This is a valid Phase 8 paper-only candidate if it is explicitly treated as low-frequency and monitored for 6-8 weeks. It does not meet the default 300-trade historical sample rule.