"""
Technical indicator computations.

All functions take pd.Series (float dtype) and return pd.Series or pd.DataFrame.
NaN is returned for warmup periods — callers must never back-fill or forward-fill these.
All formulas use Wilder smoothing (EWM alpha=1/period) unless noted.
"""

import numpy as np
import pandas as pd


# ── Momentum ───────────────────────────────────────────────────────────────────

def rsi(close: pd.Series, period: int) -> pd.Series:
    """RSI via Wilder smoothing. NaN for first `period` bars."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    result = 100 - 100 / (1 + rs)
    # Pure uptrend: avg_loss is exactly 0 → RS = ∞ → RSI = 100
    zero_loss = (avg_loss == 0.0) & avg_loss.notna()
    return result.where(~zero_loss, 100.0).rename(f"rsi_{period}")


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD line, signal line, histogram, histogram slope."""
    ema_fast = close.ewm(span=fast, min_periods=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, min_periods=slow, adjust=False).mean()
    line = ema_fast - ema_slow
    sig = line.ewm(span=signal, min_periods=signal, adjust=False).mean()
    hist = line - sig
    return pd.DataFrame({
        "macd_line": line,
        "macd_signal": sig,
        "macd_histogram": hist,
        "macd_histogram_slope": hist.diff(),
    })


# ── Trend / Moving Averages ────────────────────────────────────────────────────

def ema(close: pd.Series, period: int) -> pd.Series:
    """Standard EMA. NaN for first `period` bars."""
    return close.ewm(span=period, min_periods=period, adjust=False).mean().rename(f"ema_{period}")


def ema_slope(ema_series: pd.Series) -> pd.Series:
    """EMA slope as percent change per bar (×100)."""
    return (ema_series.diff() / ema_series.shift(1) * 100).rename("ema_slope")


# ── Volatility ─────────────────────────────────────────────────────────────────

def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
    pct_period: int = 100,
) -> pd.DataFrame:
    """ATR (Wilder) and ATR percentile (0-100) over a rolling pct_period window."""
    tr = _true_range(high, low, close)
    atr_val = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    atr_pct = atr_val.rolling(pct_period, min_periods=pct_period).rank(pct=True) * 100
    return pd.DataFrame({"atr_14": atr_val, "atr_percentile": atr_pct})


def bollinger_bands(
    close: pd.Series,
    period: int = 20,
    n_std: float = 2.0,
    bw_pct_period: int = 100,
) -> pd.DataFrame:
    """Bollinger Bands with percent-B, bandwidth, and bandwidth percentile."""
    middle = close.rolling(period, min_periods=period).mean()
    std = close.rolling(period, min_periods=period).std(ddof=0)
    upper = middle + n_std * std
    lower = middle - n_std * std
    band_width = upper - lower
    pct_b = (close - lower) / band_width.replace(0.0, np.nan)
    bandwidth = band_width / middle.replace(0.0, np.nan)
    bw_percentile = (
        bandwidth.rolling(bw_pct_period, min_periods=bw_pct_period).rank(pct=True) * 100
    )
    return pd.DataFrame({
        "bb_upper": upper,
        "bb_middle": middle,
        "bb_lower": lower,
        "bb_percent_b": pct_b,
        "bb_bandwidth": bandwidth,
        "bb_bandwidth_percentile": bw_percentile,
    })


# ── Directional / Trend strength ───────────────────────────────────────────────

def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """ADX using Wilder smoothing. NaN during warmup."""
    tr = _true_range(high, low, close)
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    dm_plus_raw = (high - prev_high).clip(lower=0)
    dm_minus_raw = (prev_low - low).clip(lower=0)
    # Zero out whichever is smaller (ties → both zero)
    dm_plus = dm_plus_raw.where(dm_plus_raw > dm_minus_raw, 0.0)
    dm_minus = dm_minus_raw.where(dm_minus_raw > dm_plus_raw, 0.0)

    smooth_tr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    smooth_dp = dm_plus.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    smooth_dm = dm_minus.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    di_plus = 100 * smooth_dp / smooth_tr.replace(0.0, np.nan)
    di_minus = 100 * smooth_dm / smooth_tr.replace(0.0, np.nan)
    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0.0, np.nan)
    return dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean().rename("adx_14")


def supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0,
) -> pd.Series:
    """Supertrend direction: 'up' or 'down'. None during warmup."""
    hl2 = (high + low) / 2
    tr = _true_range(high, low, close)
    atr_val = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    basic_upper = (hl2 + multiplier * atr_val).values.astype(float)
    basic_lower = (hl2 - multiplier * atr_val).values.astype(float)
    close_arr = close.values.astype(float)
    n = len(close_arr)

    upper = basic_upper.copy()
    lower = basic_lower.copy()
    direction = np.full(n, np.nan)

    # Find first row where ATR is valid
    first_valid = int(np.argmax(~np.isnan(basic_upper)))
    if np.isnan(basic_upper[first_valid]):
        pass  # all NaN
    else:
        direction[first_valid] = -1.0  # seed: bearish

        for i in range(first_valid + 1, n):
            if np.isnan(basic_upper[i]):
                continue
            # Upper band: tighten only if previous close was below it
            if not (basic_upper[i] < upper[i - 1] or close_arr[i - 1] > upper[i - 1]):
                upper[i] = upper[i - 1]
            # Lower band: tighten only if previous close was above it
            if not (basic_lower[i] > lower[i - 1] or close_arr[i - 1] < lower[i - 1]):
                lower[i] = lower[i - 1]
            # Update direction
            if np.isnan(direction[i - 1]) or direction[i - 1] == -1.0:
                direction[i] = 1.0 if close_arr[i] > upper[i] else -1.0
            else:
                direction[i] = -1.0 if close_arr[i] < lower[i] else 1.0

    result = [None if np.isnan(d) else ("up" if d == 1.0 else "down") for d in direction]
    return pd.Series(result, index=close.index, dtype=object, name="supertrend_direction")
