"""
Composite SHORT strategy tests — v2 (fixed stop validation).
Goal: find a combined SHORT approach that reaches 300 trades with PF >= 1.25.
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

DATA = ROOT / "data"


def _short_signal(strat_id, snapshot, side, stop, target, regime, now):
    rejected, _ = check_rr(float(snapshot.close), stop, target)
    if rejected:
        return None
    return SignalCandidate(
        strategy_id=strat_id, venue=snapshot.venue, symbol=snapshot.symbol,
        timeframe=snapshot.timeframe, side=side, created_at=now,
        expires_at=now + timedelta(minutes=720), base_confidence=Decimal("0.70"),
        expected_horizon_minutes=720, entry_reference=snapshot.close,
        invalidation_price=Decimal(f"{stop:.2f}"),
        target_prices=[Decimal(f"{target:.2f}")],
        evidence={"r": regime.regime},
        feature_version=snapshot.feature_version, strategy_version="sweep",
    )


def run_and_report(fn, strat_id, candles, funding, oi, label):
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
    print(f"  {label:60s} sigs={stat.signals_fired:4d} trd={tc:4d} "
          f"win={wr:.1%} exp={exp:+.4f} PF={pf:.3f} "
          f"wf={pw}/{wc}({wf_pct:.0%}) {'PASS' if gate else 'fail'}")


def main():
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    # ── C1: EMA cross SHORT (trend_down only, baseline reference) ─────────────
    def c1(snapshot, regime, row, now):
        if regime.regime != "trend_down": return None
        req = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14")
        rejected, _ = check_features(snapshot, req)
        if rejected: return None
        close = float(snapshot.close); e20=float(snapshot.ema_20); e50=float(snapshot.ema_50)
        e200=float(snapshot.ema_200); adx=float(snapshot.adx_14); atr=float(snapshot.atr_14)
        bar_open = float(row["open"])
        if atr<=0 or adx<20 or not (e20<e50<e200) or not (bar_open>e20>=close): return None
        return _short_signal("c1", snapshot, "short", e50+0.5*atr, close-4.5*atr, regime, now)
    run_and_report(c1, "c1", candles, funding, oi, "EMA cross SHORT [td only, baseline 122]")

    # ── C2: C1 + prev_day breakdown SHORT (shared slot, breakdown gets priority when both fire) ──
    def c2(snapshot, regime, row, now):
        if regime.regime not in ("trend_down", "breakout_pending"): return None
        req = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14", "prev_day_low", "volume_z_score")
        rejected, _ = check_features(snapshot, req)
        if rejected: return None
        close=float(snapshot.close); e20=float(snapshot.ema_20); e50=float(snapshot.ema_50)
        e200=float(snapshot.ema_200); adx=float(snapshot.adx_14); atr=float(snapshot.atr_14)
        pdl=float(snapshot.prev_day_low); vz=float(snapshot.volume_z_score)
        bar_open=float(row["open"])
        if atr<=0: return None
        # Priority 1: breakdown (strongest signal)
        if regime.regime in ("trend_down","breakout_pending") and vz>=2.0 and close<pdl:
            return _short_signal("c2", snapshot, "short", close+0.75*atr, close-4.5*atr, regime, now)
        # Priority 2: EMA cross
        if (regime.regime=="trend_down" and adx>=20 and e20<e50<e200
                and bar_open>e20>=close):
            return _short_signal("c2", snapshot, "short", e50+0.5*atr, close-4.5*atr, regime, now)
        return None
    run_and_report(c2, "c2", candles, funding, oi, "EMA cross + breakdown SHORT [combo]")

    # ── C3: C2 + pullback SHORT (3-signal composite) ─────────────────────────
    def c3(snapshot, regime, row, now):
        if regime.regime not in ("trend_down", "breakout_pending"): return None
        req = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "rsi_14", "atr_14",
               "prev_day_low", "volume_z_score")
        rejected, _ = check_features(snapshot, req)
        if rejected: return None
        close=float(snapshot.close); e20=float(snapshot.ema_20); e50=float(snapshot.ema_50)
        e200=float(snapshot.ema_200); adx=float(snapshot.adx_14); atr=float(snapshot.atr_14)
        rsi=float(snapshot.rsi_14); pdl=float(snapshot.prev_day_low); vz=float(snapshot.volume_z_score)
        bar_open=float(row["open"])
        if atr<=0: return None
        # Priority 1: breakdown
        if regime.regime in ("trend_down","breakout_pending") and vz>=2.0 and close<pdl:
            return _short_signal("c3", snapshot, "short", close+0.75*atr, close-4.5*atr, regime, now)
        # Priority 2: EMA cross
        if (regime.regime=="trend_down" and adx>=20 and e20<e50<e200
                and bar_open>e20>=close):
            return _short_signal("c3", snapshot, "short", e50+0.5*atr, close-4.5*atr, regime, now)
        # Priority 3: pullback near EMA50
        if (regime.regime=="trend_down" and adx>=20 and e20<e50<e200
                and 40<=rsi<=60 and e50-1.5*atr<=close<=e50):
            return _short_signal("c3", snapshot, "short", e50+0.5*atr, close-2.5*atr, regime, now)
        return None
    run_and_report(c3, "c3", candles, funding, oi, "EMA cross + breakdown + pullback SHORT")

    # ── C4: Breakdown SHORT only (original, for reference) ───────────────────
    def c4(snapshot, regime, row, now):
        if regime.regime not in ("trend_down","breakout_pending"): return None
        req = ("close", "prev_day_low", "atr_14", "volume_z_score")
        rejected, _ = check_features(snapshot, req)
        if rejected: return None
        close=float(snapshot.close); pdl=float(snapshot.prev_day_low)
        atr=float(snapshot.atr_14); vz=float(snapshot.volume_z_score)
        if atr<=0 or vz<2.0 or close>=pdl: return None
        return _short_signal("c4", snapshot, "short", close+0.75*atr, close-4.5*atr, regime, now)
    run_and_report(c4, "c4", candles, funding, oi, "Breakdown SHORT only [original 95]")

    # ── C5: EMA cross SHORT with lower vol_z=0.1 filter ──────────────────────
    def c5(snapshot, regime, row, now):
        if regime.regime != "trend_down": return None
        req = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14", "volume_z_score")
        rejected, _ = check_features(snapshot, req)
        if rejected: return None
        close=float(snapshot.close); e20=float(snapshot.ema_20); e50=float(snapshot.ema_50)
        e200=float(snapshot.ema_200); adx=float(snapshot.adx_14); atr=float(snapshot.atr_14)
        vz=float(snapshot.volume_z_score)
        bar_open=float(row["open"])
        if atr<=0 or adx<20 or vz<0.1: return None
        if not (e20<e50<e200) or not (bar_open>e20>=close): return None
        return _short_signal("c5", snapshot, "short", e50+0.5*atr, close-4.5*atr, regime, now)
    run_and_report(c5, "c5", candles, funding, oi, "EMA cross SHORT [vol_z>=0.1]")

    # ── C6: C5 (vol_z>=0.1 EMA cross) + breakdown composite ─────────────────
    def c6(snapshot, regime, row, now):
        if regime.regime not in ("trend_down","breakout_pending"): return None
        req = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14",
               "prev_day_low", "volume_z_score")
        rejected, _ = check_features(snapshot, req)
        if rejected: return None
        close=float(snapshot.close); e20=float(snapshot.ema_20); e50=float(snapshot.ema_50)
        e200=float(snapshot.ema_200); adx=float(snapshot.adx_14); atr=float(snapshot.atr_14)
        pdl=float(snapshot.prev_day_low); vz=float(snapshot.volume_z_score)
        bar_open=float(row["open"])
        if atr<=0: return None
        # Priority 1: breakdown
        if regime.regime in ("trend_down","breakout_pending") and vz>=2.0 and close<pdl:
            return _short_signal("c6", snapshot, "short", close+0.75*atr, close-4.5*atr, regime, now)
        # Priority 2: EMA cross (vol_z>=0.1 filter)
        if (regime.regime=="trend_down" and adx>=20 and vz>=0.1 and e20<e50<e200
                and bar_open>e20>=close):
            return _short_signal("c6", snapshot, "short", e50+0.5*atr, close-4.5*atr, regime, now)
        return None
    run_and_report(c6, "c6", candles, funding, oi, "EMA cross [vol_z>=0.1] + breakdown SHORT combo")


if __name__ == "__main__":
    main()
