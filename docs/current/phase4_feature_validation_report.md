# Phase 4 — Feature Validation Report

Generated: 2026-05-27  
Module: `src/finding_alpha/features/`  
Test coverage: 38/38 tests passing (`tests/test_features.py`)

---

## Indicator Implementations

### RSI (Relative Strength Index)

Formula: `RSI = 100 - (100 / (1 + RS))` where `RS = avg_gain / avg_loss`

Periods implemented: 6, 14, 24

**Wilder smoothing**: `ewm(alpha=1/period, min_periods=period, adjust=False)`

**Warmup**: First valid output at bar index `period` (not `period - 1`). The `.diff()` call shifts one bar, so warmup = `period` bars of NaN.

**Edge case — pure uptrend (avg_loss = 0)**: When all bars in the window are gains, `avg_loss = 0`. Rather than producing NaN via division, `RSI = 100` is returned directly.

Output column: `rsi_{period}` (e.g., `rsi_14`)

---

### MACD (Moving Average Convergence Divergence)

Parameters: fast=12, slow=26, signal=9

Fast EMA: `ewm(span=12, min_periods=12, adjust=False)`  
Slow EMA: `ewm(span=26, min_periods=26, adjust=False)`  
MACD line: `fast_ema - slow_ema` (valid from bar 25)  
Signal line: `ewm(span=9, min_periods=9, adjust=False)` on MACD (valid from bar 33)  
Histogram: `macd_line - signal_line`

**Warmup**: MACD line valid from index 25. Signal line valid from index 33.

Output columns: `macd_line`, `macd_signal`, `macd_histogram`

---

### EMA (Exponential Moving Average)

Periods implemented: 20, 50, 200

Formula: `ewm(span=period, min_periods=period, adjust=False)`

**Warmup**: First valid output at bar index `period - 1`.

**Slope**: Computed as `(ema - ema.shift(1)) / ema.shift(1) * 100` (percent change per bar).

Output columns: `ema_20`, `ema_50`, `ema_200`, `ema_20_slope`, `ema_50_slope`, `ema_200_slope`

---

### ATR (Average True Range)

Period: 14

True Range: `max(high - low, |high - prev_close|, |low - prev_close|)`  
Implementation: `pd.concat([H-L, |H-C_prev|, |L-C_prev|]).max(axis=1, skipna=True)`

**Key**: `skipna=True` means TR[0] = H[0] - L[0] (valid, not NaN), because the `|H - C_prev|` and `|L - C_prev|` terms are NaN at index 0 and get skipped.

ATR smoothing: Wilder smoothing via `ewm(alpha=1/period, min_periods=period, adjust=False)`

**Warmup**: First valid at bar index `period - 1` (same as EMA, NOT `period` like RSI).

ATR percentile: `rolling(window=252).rank(pct=True)` — measures current ATR relative to trailing 252-bar distribution.

Output columns: `atr_14`, `atr_14_pct`

---

### Bollinger Bands

Period: 20, std_dev: 2.0

Middle band: `rolling(20).mean()`  
Upper/lower: `middle ± 2 × rolling(20).std(ddof=1)`  
%B: `(close - lower) / (upper - lower)`  
Bandwidth: `(upper - lower) / middle`

**Warmup**: First valid at bar index 19.

Output columns: `bb_upper`, `bb_middle`, `bb_lower`, `bb_pct_b`, `bb_bandwidth`

---

### ADX (Average Directional Index)

Period: 14

+DM: `max(high - prev_high, 0)` when > -DM, else 0  
-DM: `max(prev_low - low, 0)` when > +DM, else 0  
Smoothed with Wilder smoothing  
+DI = 100 × smoothed_+DM / ATR; -DI = 100 × smoothed_-DM / ATR  
DX = 100 × |+DI - -DI| / (+DI + -DI)  
ADX = Wilder smooth of DX

**Warmup**: ~28 bars before ADX is fully stable (two Wilder passes of 14 bars each).

Output columns: `adx_14`, `plus_di`, `minus_di`

---

### Supertrend

Period: 10, multiplier: 3.0

Basic upper band: `(high + low) / 2 + 3.0 × ATR`  
Basic lower band: `(high + low) / 2 - 3.0 × ATR`

Band adjustment: iterative — each band can only tighten (upper can only decrease when price is below, lower can only increase when price is above).

Direction seeding: `direction[first_valid] = -1.0` (bullish at first stable bar).

**Warmup**: First valid at bar index `period - 1` (same as ATR).

Output columns: `supertrend`, `supertrend_direction` (-1.0 = bullish, +1.0 = bearish)

---

## Order-Flow Features

### Volume Z-Score

Window: 20 bars  
Formula: `(volume - rolling_mean) / rolling_std`

Output column: `volume_z_score`

**Warmup**: First valid at bar index 19.

---

### Funding Rate Features

Source: Bybit funding rate history, merged onto 1h candles by forward-filling from the nearest prior settlement.

Output columns: `funding_rate`, `funding_z_score`

`funding_z_score`: rolling 20-period z-score of funding rate.

---

### Open Interest Features

Source: Bybit OI 1h snapshots, merged onto candles by timestamp.

`oi_delta`: `oi_value - oi_value.shift(1)` (change per bar)  
`oi_z_score`: rolling 20-period z-score of `oi_delta`

Output columns: `oi_value`, `oi_delta`, `oi_z_score`

---

## Structure Features

### Session VWAP

Computed per UTC day session (00:00–23:59 UTC).  
`vwap = cumsum(close × volume) / cumsum(volume)` within each session.

Output column: `session_vwap`

---

### Session High/Low

Expanding max/min of `high`/`low` within each UTC day session.

Output columns: `session_high`, `session_low`

---

### Previous Day High/Low

Prior day's session high and low, forward-filled across the current day.

Output columns: `prev_day_high`, `prev_day_low`

---

### Previous Week High/Low

Prior ISO week's high and low, forward-filled across the current week.

Output columns: `prev_week_high`, `prev_week_low`

---

## Feature Snapshot

`build_feature_df(candles, funding, oi)` — builds a full DataFrame with all 48 columns above.

`build_snapshot(fdf, venue, symbol, timeframe, row_idx)` — extracts a single `FeatureSnapshot` from a row. Returns `None` for any indicator value that is NaN at that row (first `period-1` bars will have many None values).

---

## Regime Classifier

`classify_regime(snapshot) -> RegimeState`

7-priority rule system (first matching rule wins):

| Priority | Regime | Trigger |
|---|---|---|
| 1 | `crisis` | ATR percentile > 95 |
| 2 | `high_volatility` | ATR percentile > 80 |
| 3 | `trend_up` | EMA 20 > 50 > 200, ADX ≥ 20, supertrend bullish |
| 4 | `trend_down` | EMA 20 < 50 < 200, ADX ≥ 20, supertrend bearish |
| 5 | `breakout_pending` | Bollinger bandwidth < 10th percentile of trailing 252 bars |
| 6 | `range` | ADX < 20 |
| 7 | `unknown` | Fallback when features are None/unavailable |

---

## Warmup Summary

| Indicator | Warmup (bars of NaN) |
|---|---|
| EMA 20 | 19 |
| EMA 50 | 49 |
| EMA 200 | 199 |
| RSI 6 | 6 |
| RSI 14 | 14 |
| RSI 24 | 24 |
| ATR 14 | 13 |
| Bollinger 20 | 19 |
| MACD line | 25 |
| MACD signal | 33 |
| ADX 14 | ~27 |
| Supertrend 10 | 9 |
| Volume Z-score 20 | 19 |

**Safe warmup cutoff**: 220 bars used in backtests (covers EMA 200 at index 199 + ADX double-pass margin).
