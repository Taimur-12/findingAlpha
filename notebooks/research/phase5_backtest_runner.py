"""
Phase 5 backtest runner.
Loads 1h Bybit BTCUSDT candles + funding + OI, builds features, runs all three
strategies bar-by-bar, simulates outcomes, and prints per-strategy metrics.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.data.quality import check_candles
from finding_alpha.features.snapshot import build_feature_df, build_snapshot
from finding_alpha.regime.classifier import classify_regime
from finding_alpha.strategies.liquidity_sweep_v1 import find_signal as sweep_signal
from finding_alpha.strategies.squeeze_v1 import find_signal as squeeze_signal
from finding_alpha.strategies.trend_pullback_v1 import find_signal as pullback_signal
from finding_alpha.portfolio.agent import PortfolioConfig, size_intent
from finding_alpha.simulation.executor import SimConfig, simulate_trade
from finding_alpha.analytics.metrics import compute_metrics

BASE = Path(__file__).parent.parent.parent / "data"

PORTFOLIO_CFG = PortfolioConfig(
    risk_pct=Decimal("0.01"),
    max_leverage=Decimal("10"),
    min_notional_usdt=Decimal("10"),
    qty_precision=3,
    price_precision=2,
    max_hold_minutes=480,
)
SIM_CFG = SimConfig()
EQUITY = Decimal("10000")

# ── Load data ──────────────────────────────────────────────────────────────────
print("Loading data...")
candles_1h  = load_candles(BASE, "bybit", "BTCUSDT", "1h")
funding     = load_funding(BASE, "bybit", "BTCUSDT")
oi          = load_open_interest(BASE, "bybit", "BTCUSDT", "1h")

print(f"  1h candles : {len(candles_1h):,} rows  ({candles_1h['open_time'].min().date()} to {candles_1h['open_time'].max().date()})")
print(f"  funding    : {len(funding):,} rows")
print(f"  OI         : {len(oi):,} rows")

# Data quality
qr = check_candles(candles_1h, "1h")
print(f"\nData quality (1h candles):")
print(f"  gaps          : {qr['gap_count']}")
print(f"  duplicates    : {len(qr['duplicate_times'])}")
print(f"  zero-volume   : {len(qr['zero_volume_times'])}")

# ── Build features ────────────────────────────────────────────────────────────
print("\nBuilding feature DataFrame (takes a few seconds)...")
fdf = build_feature_df(candles_1h, funding=funding, oi=oi)
print(f"  Feature DataFrame: {len(fdf)} rows × {len(fdf.columns)} columns")

# Convert candle OHLC to float for sim
fdf["open"]  = pd.to_numeric(fdf["open"],  errors="coerce")
fdf["high"]  = pd.to_numeric(fdf["high"],  errors="coerce")
fdf["low"]   = pd.to_numeric(fdf["low"],   errors="coerce")
fdf["close"] = pd.to_numeric(fdf["close"], errors="coerce")

# ── Bar-by-bar scan ───────────────────────────────────────────────────────────
WARMUP = 220   # skip first 220 bars (EMA 200 + ADX warmup)

strategies = {
    "liquidity_sweep_v1": {"signals": [], "outcomes": [], "skipped": 0},
    "squeeze_v1":          {"signals": [], "outcomes": [], "skipped": 0},
    "trend_pullback_v1":   {"signals": [], "outcomes": [], "skipped": 0},
}

print(f"\nScanning {len(fdf) - WARMUP} bars (skipping first {WARMUP} warmup bars)...")

for i in range(WARMUP, len(fdf)):
    row     = fdf.iloc[i]
    now_ts  = pd.Timestamp(row["open_time"])
    if now_ts.tzinfo is None:
        now_ts = now_ts.tz_localize("UTC")
    now     = now_ts.to_pydatetime()

    snapshot = build_snapshot(fdf, "bybit", "BTCUSDT", "1h", row_idx=i)
    regime   = classify_regime(snapshot)

    bar_high = float(row["high"])
    bar_low  = float(row["low"])

    future_df = fdf.iloc[i + 1:].reset_index(drop=True)

    # — liquidity_sweep_v1 ———————————————————————————————————————————————
    sig = sweep_signal(snapshot, regime, bar_high, bar_low, now)
    if sig is not None:
        intent = size_intent(sig, EQUITY, PORTFOLIO_CFG, now)
        if intent is not None:
            outcome = simulate_trade(
                intent, future_df, SIM_CFG,
                "liquidity_sweep_v1", "1.0", "1.0", "1h", now,
            )
            strategies["liquidity_sweep_v1"]["signals"].append(sig)
            if outcome is not None:
                strategies["liquidity_sweep_v1"]["outcomes"].append(outcome)
            else:
                strategies["liquidity_sweep_v1"]["skipped"] += 1

    # — squeeze_v1 ——————————————————————————————————————————————————————————
    sig = squeeze_signal(snapshot, regime, now)
    if sig is not None:
        intent = size_intent(sig, EQUITY, PORTFOLIO_CFG, now)
        if intent is not None:
            outcome = simulate_trade(
                intent, future_df, SIM_CFG,
                "squeeze_v1", "1.0", "1.0", "1h", now,
            )
            strategies["squeeze_v1"]["signals"].append(sig)
            if outcome is not None:
                strategies["squeeze_v1"]["outcomes"].append(outcome)
            else:
                strategies["squeeze_v1"]["skipped"] += 1

    # — trend_pullback_v1 ————————————————————————————————————————————————————
    sig = pullback_signal(snapshot, regime, now)
    if sig is not None:
        intent = size_intent(sig, EQUITY, PORTFOLIO_CFG, now)
        if intent is not None:
            outcome = simulate_trade(
                intent, future_df, SIM_CFG,
                "trend_pullback_v1", "1.0", "1.0", "1h", now,
            )
            strategies["trend_pullback_v1"]["signals"].append(sig)
            if outcome is not None:
                strategies["trend_pullback_v1"]["outcomes"].append(outcome)
            else:
                strategies["trend_pullback_v1"]["skipped"] += 1

# ── Print metrics ─────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("PHASE 5 BACKTEST RESULTS — Bybit BTCUSDT 1h")
print("="*70)
print(f"Dataset  : {fdf.iloc[WARMUP]['open_time'].date()} to {fdf.iloc[-1]['open_time'].date()}")
print(f"Equity   : ${float(EQUITY):,.0f}  |  Risk/trade: 1%  |  Max hold: 8h")
print(f"Fees     : maker 0.02% entry, taker 0.055% stop, conservative slippage 0.05%")
print()

results = {}

for name, data in strategies.items():
    outcomes = data["outcomes"]
    signals  = data["signals"]
    m = compute_metrics(outcomes)

    results[name] = {
        "signals_fired": len(signals),
        "outcomes_simulated": len(outcomes),
        "entry_not_filled": data["skipped"],
        **m,
    }

    print(f"── {name} ──")
    print(f"  Signals fired     : {len(signals)}")
    print(f"  Outcomes simulated: {len(outcomes)}  (entry not filled: {data['skipped']})")
    print(f"  Win rate          : {m['win_rate']:.1%}" if m['win_rate'] is not None else "  Win rate          : N/A")
    print(f"  Expectancy (R)    : {m['expectancy_r']:.3f}" if m['expectancy_r'] is not None else "  Expectancy (R)    : N/A")
    print(f"  Profit factor     : {m['profit_factor']:.2f}" if m['profit_factor'] is not None else "  Profit factor     : N/A")
    print(f"  Net PnL           : ${float(m['net_pnl']):+,.2f}")
    print(f"  Max drawdown (R)  : {float(m['max_drawdown_r']):.2f}")
    if m['fee_share_of_gross'] is not None:
        print(f"  Fee share/gross   : {m['fee_share_of_gross']:.1%}")
    print(f"  Exit reasons      : {m['by_exit_reason']}")
    print()

# ── Parameter sensitivity (RSI threshold grid for trend_pullback) ────────────
print("="*70)
print("PARAMETER SENSITIVITY — trend_pullback_v1 RSI range")
print("="*70)

rsi_grids = [
    (35, 65), (40, 60), (42, 58), (38, 55),
]

from finding_alpha.strategies import trend_pullback_v1 as tp_module

for rsi_low, rsi_high in rsi_grids:
    tp_outcomes = []
    orig_low  = tp_module._RSI_LOW
    orig_high = tp_module._RSI_HIGH
    tp_module._RSI_LOW  = float(rsi_low)
    tp_module._RSI_HIGH = float(rsi_high)

    for i in range(WARMUP, len(fdf)):
        row      = fdf.iloc[i]
        now_ts   = pd.Timestamp(row["open_time"])
        if now_ts.tzinfo is None:
            now_ts = now_ts.tz_localize("UTC")
        now      = now_ts.to_pydatetime()
        snapshot = build_snapshot(fdf, "bybit", "BTCUSDT", "1h", row_idx=i)
        regime   = classify_regime(snapshot)
        sig = pullback_signal(snapshot, regime, now)
        if sig is not None:
            intent = size_intent(sig, EQUITY, PORTFOLIO_CFG, now)
            if intent is not None:
                future_df = fdf.iloc[i + 1:].reset_index(drop=True)
                outcome = simulate_trade(intent, future_df, SIM_CFG, "trend_pullback_v1", "1.0", "1.0", "1h", now)
                if outcome is not None:
                    tp_outcomes.append(outcome)

    tp_module._RSI_LOW  = orig_low
    tp_module._RSI_HIGH = orig_high

    m = compute_metrics(tp_outcomes)
    wr = f"{m['win_rate']:.1%}" if m['win_rate'] is not None else "N/A"
    er = f"{m['expectancy_r']:.3f}" if m['expectancy_r'] is not None else "N/A"
    print(f"  RSI [{rsi_low:2d}–{rsi_high:2d}]  trades={m['trade_count']:3d}  win_rate={wr:6s}  expectancy={er}")

print()
print("Script complete.")

# Save raw results for report generation
import json as _json
_out = {}
for k, v in results.items():
    _out[k] = {
        kk: str(vv) if isinstance(vv, Decimal) else vv
        for kk, vv in v.items()
        if not isinstance(vv, (dict, list)) or kk in ("by_exit_reason",)
    }
Path(__file__).parent.parent.parent / "docs" / "current"
out_path = Path(__file__).parent.parent.parent / "docs" / "current" / "_backtest_results.json"
with open(out_path, "w") as f:
    _json.dump(_out, f, indent=2, default=str)
print(f"Results saved to {out_path}")
