"""
Explore SHORT-only composite approaches to reach 300 trades.

Tests:
1. EMA cross SHORT expanded to trend_down + breakout_pending regimes
2. "Strong close" momentum SHORT: close in bottom 25% of bar range, vol_z > 1.0, trend_down
3. Combined strategy: EMA cross + breakdown in one fn (to avoid slot competition)
4. EMA cross SHORT only (baseline for comparison)
"""
from __future__ import annotations
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.strategies.fast_reject import check_features, check_rr
from finding_alpha.validation.event_runner import STRATEGIES, ValidationConfig, run_event_validation
from finding_alpha.validation.walk_forward import run_walk_forward
from finding_alpha.analytics.metrics import compute_metrics

DATA = ROOT / "data"


def run_and_report(fn, strat_id, candles, funding, oi, label: str):
    STRATEGIES[strat_id] = fn
    try:
        cfg = ValidationConfig(
            strategy_ids=(strat_id,),
            portfolio_config=PortfolioConfig(risk_pct=Decimal("0.0025"), max_hold_minutes=720),
            risk_config=RiskConfig(daily_loss_limit_pct=Decimal("0.01"), max_drawdown_pct=Decimal("0.10"), max_open_positions=1),
        )
        result = run_event_validation(candles, funding, oi, cfg)
        wf = run_walk_forward(candles, funding, oi, cfg)
    finally:
        STRATEGIES.pop(strat_id, None)
    stat = result.strategy_stats.get(strat_id)
    if not stat:
        print(f"  {label}: no results")
        return
    m = stat.metrics
    wf_agg = wf.aggregate_metrics
    tc = m.get("trade_count", 0)
    pf = float(m.get("profit_factor", 0))
    exp = float(m.get("expectancy_r") or 0)
    wr = float(m.get("win_rate", 0))
    pw = wf_agg.get("profitable_windows", 0)
    wc = wf_agg.get("window_count", 1)
    wf_pct = pw / wc if wc else 0
    gate = tc >= 300 and pf >= 1.25 and exp > 0 and wf_pct >= 0.50
    print(f"  {label:50s}  sigs={stat.signals_fired:4d}  trd={tc:4d}  "
          f"win={wr:.1%}  exp_r={exp:+.4f}  PF={pf:.3f}  "
          f"wf={pw}/{wc}({wf_pct:.0%})  {'PASS' if gate else 'fail'}")


def main():
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    # ── 1. EMA cross SHORT baseline (trend_down only, no vol filter) ──────────
    def ema_cross_short_td(snapshot, regime, row, now):
        if regime.regime != "trend_down":
            return None
        req = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14")
        rejected, _ = check_features(snapshot, req)
        if rejected: return None
        close = float(snapshot.close); e20 = float(snapshot.ema_20)
        e50 = float(snapshot.ema_50); e200 = float(snapshot.ema_200)
        adx = float(snapshot.adx_14); atr = float(snapshot.atr_14)
        bar_open = float(row["open"])
        if atr <= 0 or adx < 20: return None
        if not (e20 < e50 < e200): return None
        if not (bar_open > e20 >= close): return None
        stop = e50 + 0.5 * atr; target = close - 4.5 * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected: return None
        return SignalCandidate(strategy_id="c1", venue=snapshot.venue, symbol=snapshot.symbol,
            timeframe=snapshot.timeframe, side="short", created_at=now,
            expires_at=now+timedelta(minutes=720), base_confidence=Decimal("0.70"),
            expected_horizon_minutes=720, entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"), target_prices=[Decimal(f"{target:.2f}")],
            evidence={"r": regime.regime}, feature_version=snapshot.feature_version,
            strategy_version="sweep")
    run_and_report(ema_cross_short_td, "c1", candles, funding, oi,
                   "EMA cross SHORT [trend_down only, no vol]")

    # ── 2. EMA cross SHORT expanded to trend_down + breakout_pending ──────────
    def ema_cross_short_expanded(snapshot, regime, row, now):
        if regime.regime not in ("trend_down", "breakout_pending"):
            return None
        req = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14")
        rejected, _ = check_features(snapshot, req)
        if rejected: return None
        close = float(snapshot.close); e20 = float(snapshot.ema_20)
        e50 = float(snapshot.ema_50); e200 = float(snapshot.ema_200)
        adx = float(snapshot.adx_14); atr = float(snapshot.atr_14)
        bar_open = float(row["open"])
        if atr <= 0 or adx < 20: return None
        # Only require EMA stack for trend_down
        if regime.regime == "trend_down" and not (e20 < e50 < e200):
            return None
        if not (bar_open > e20 >= close): return None
        stop = e50 + 0.5 * atr; target = close - 4.5 * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected: return None
        return SignalCandidate(strategy_id="c2", venue=snapshot.venue, symbol=snapshot.symbol,
            timeframe=snapshot.timeframe, side="short", created_at=now,
            expires_at=now+timedelta(minutes=720), base_confidence=Decimal("0.70"),
            expected_horizon_minutes=720, entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"), target_prices=[Decimal(f"{target:.2f}")],
            evidence={"r": regime.regime}, feature_version=snapshot.feature_version,
            strategy_version="sweep")
    run_and_report(ema_cross_short_expanded, "c2", candles, funding, oi,
                   "EMA cross SHORT [trend_down+breakout_pending, no vol]")

    # ── 3. Combined EMA cross + prev_day breakdown (one strategy, SHORT only) ──
    def combined_short(snapshot, regime, row, now):
        if regime.regime not in ("trend_down", "breakout_pending"):
            return None
        req_base = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14")
        rejected, _ = check_features(snapshot, req_base)
        if rejected: return None
        close = float(snapshot.close); e20 = float(snapshot.ema_20)
        e50 = float(snapshot.ema_50); e200 = float(snapshot.ema_200)
        adx = float(snapshot.adx_14); atr = float(snapshot.atr_14)
        bar_open = float(row["open"])
        if atr <= 0: return None
        signal = None

        # EMA cross SHORT (trend_down, EMA stack, ADX >= 20)
        if (regime.regime == "trend_down" and adx >= 20 and e20 < e50 < e200
                and bar_open > e20 >= close):
            stop = e50 + 0.5 * atr
            target = close - 4.5 * atr
            rejected, _ = check_rr(close, stop, target)
            if not rejected:
                signal = ("ema_cross", stop, target)

        # prev_day breakdown SHORT (vol_z >= 2.0, trend_down or breakout_pending)
        if signal is None and snapshot.prev_day_low is not None and snapshot.volume_z_score is not None:
            pdl = float(snapshot.prev_day_low)
            vz = float(snapshot.volume_z_score)
            if vz >= 2.0 and close < pdl:
                stop = close + 0.75 * atr
                target = close - 4.5 * atr
                rejected, _ = check_rr(close, stop, target)
                if not rejected:
                    signal = ("breakdown", stop, target)

        if signal is None:
            return None
        _, stop, target = signal
        return SignalCandidate(strategy_id="c3", venue=snapshot.venue, symbol=snapshot.symbol,
            timeframe=snapshot.timeframe, side="short", created_at=now,
            expires_at=now+timedelta(minutes=720), base_confidence=Decimal("0.70"),
            expected_horizon_minutes=720, entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"), target_prices=[Decimal(f"{target:.2f}")],
            evidence={"type": signal[0], "r": regime.regime},
            feature_version=snapshot.feature_version, strategy_version="sweep")
    run_and_report(combined_short, "c3", candles, funding, oi,
                   "Combined SHORT [EMA cross + breakdown]")

    # ── 4. Full composite: EMA cross + breakdown + pullback SHORT ─────────────
    def full_composite_short(snapshot, regime, row, now):
        if regime.regime not in ("trend_down", "breakout_pending"):
            return None
        req_base = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14")
        rejected, _ = check_features(snapshot, req_base)
        if rejected: return None
        close = float(snapshot.close); e20 = float(snapshot.ema_20)
        e50 = float(snapshot.ema_50); e200 = float(snapshot.ema_200)
        adx = float(snapshot.adx_14); atr = float(snapshot.atr_14)
        rsi = float(snapshot.rsi_14) if snapshot.rsi_14 is not None else 50.0
        bar_open = float(row["open"])
        if atr <= 0: return None
        signal = None

        # Priority 1: EMA cross SHORT
        if (regime.regime == "trend_down" and adx >= 20 and e20 < e50 < e200
                and bar_open > e20 >= close):
            stop = e50 + 0.5 * atr; target = close - 4.5 * atr
            rejected, _ = check_rr(close, stop, target)
            if not rejected:
                signal = ("ema_cross", stop, target)

        # Priority 2: prev_day breakdown SHORT
        if signal is None and snapshot.prev_day_low is not None and snapshot.volume_z_score is not None:
            pdl = float(snapshot.prev_day_low)
            vz = float(snapshot.volume_z_score)
            if vz >= 2.0 and close < pdl:
                stop = close + 0.75 * atr; target = close - 4.5 * atr
                rejected, _ = check_rr(close, stop, target)
                if not rejected:
                    signal = ("breakdown", stop, target)

        # Priority 3: Pullback SHORT (near EMA50 in trend_down)
        if (signal is None and regime.regime == "trend_down" and adx >= 20
                and e20 < e50 < e200 and 40 <= rsi <= 60
                and e50 - 1.5*atr <= close <= e50):
            stop = e50 + 0.5 * atr; target = close - 2.5 * atr
            rejected, _ = check_rr(close, stop, target)
            if not rejected:
                signal = ("pullback", stop, target)

        if signal is None:
            return None
        _, stop, target = signal
        return SignalCandidate(strategy_id="c4", venue=snapshot.venue, symbol=snapshot.symbol,
            timeframe=snapshot.timeframe, side="short", created_at=now,
            expires_at=now+timedelta(minutes=720), base_confidence=Decimal("0.70"),
            expected_horizon_minutes=720, entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"), target_prices=[Decimal(f"{target:.2f}")],
            evidence={"type": signal[0], "r": regime.regime},
            feature_version=snapshot.feature_version, strategy_version="sweep")
    run_and_report(full_composite_short, "c4", candles, funding, oi,
                   "Full composite SHORT [EMA cross + breakdown + pullback]")

    # ── 5. Pullback SHORT only (for reference) ────────────────────────────────
    def pullback_short_only(snapshot, regime, row, now):
        if regime.regime != "trend_down":
            return None
        req = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "rsi_14", "atr_14")
        rejected, _ = check_features(snapshot, req)
        if rejected: return None
        close = float(snapshot.close); e20 = float(snapshot.ema_20)
        e50 = float(snapshot.ema_50); e200 = float(snapshot.ema_200)
        adx = float(snapshot.adx_14); rsi = float(snapshot.rsi_14)
        atr = float(snapshot.atr_14)
        if atr <= 0 or adx < 20 or not (40 <= rsi <= 60): return None
        if not (e20 < e50 < e200): return None
        if not (e50 - 1.5*atr <= close <= e50): return None
        stop = e50 + 0.5 * atr; target = close - 2.5 * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected: return None
        return SignalCandidate(strategy_id="c5", venue=snapshot.venue, symbol=snapshot.symbol,
            timeframe=snapshot.timeframe, side="short", created_at=now,
            expires_at=now+timedelta(minutes=720), base_confidence=Decimal("0.70"),
            expected_horizon_minutes=720, entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"), target_prices=[Decimal(f"{target:.2f}")],
            evidence={"r": regime.regime}, feature_version=snapshot.feature_version,
            strategy_version="sweep")
    run_and_report(pullback_short_only, "c5", candles, funding, oi,
                   "Pullback SHORT only [trend_down]")


if __name__ == "__main__":
    main()
