"""
Targeted vol_z threshold sweep for the best EMA cross setup.
Setup: ema50 anchor, stop=0.5*ATR, target=4.5*ATR, trend_up/down with EMA stack.
Test vol_z from 0.0 to 1.5 in steps of 0.25.
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
from collections import defaultdict

DATA = ROOT / "data"
_REQUIRED_BASE = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14")
_REQUIRED_VZ = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14", "volume_z_score")


def _make_fn(vol_z_min: float):
    strat_id = f"emacross_vz{vol_z_min:.2f}"
    req = _REQUIRED_VZ if vol_z_min > 0 else _REQUIRED_BASE

    def fn(snapshot: FeatureSnapshot, regime: RegimeState, row: pd.Series, now: datetime) -> Optional[SignalCandidate]:
        if regime.regime not in ("trend_up", "trend_down"):
            return None
        rejected, _ = check_features(snapshot, req)
        if rejected:
            return None
        close = float(snapshot.close)
        e20 = float(snapshot.ema_20)
        e50 = float(snapshot.ema_50)
        e200 = float(snapshot.ema_200)
        adx = float(snapshot.adx_14)
        atr = float(snapshot.atr_14)
        bar_open = float(row["open"])
        if atr <= 0 or adx < 20:
            return None
        if vol_z_min > 0:
            vz = float(snapshot.volume_z_score)
            if vz < vol_z_min:
                return None

        if regime.regime == "trend_up":
            if not (e20 > e50 > e200):
                return None
            if not (bar_open < e20 <= close):
                return None
            stop = e50 - 0.5 * atr
            target = close + 4.5 * atr
            side = "long"
        else:
            if not (e20 < e50 < e200):
                return None
            if not (bar_open > e20 >= close):
                return None
            stop = e50 + 0.5 * atr
            target = close - 4.5 * atr
            side = "short"

        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None
        return SignalCandidate(
            strategy_id=strat_id,
            venue=snapshot.venue, symbol=snapshot.symbol, timeframe=snapshot.timeframe,
            side=side, created_at=now, expires_at=now + timedelta(minutes=720),
            base_confidence=Decimal("0.70"), expected_horizon_minutes=720,
            entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"),
            target_prices=[Decimal(f"{target:.2f}")],
            evidence={"adx": f"{adx:.1f}", "regime": regime.regime},
            feature_version=snapshot.feature_version, strategy_version="sweep",
        )
    fn.__name__ = strat_id
    return fn, strat_id


def run_v(vol_z_min, candles, funding, oi):
    fn, strat_id = _make_fn(vol_z_min)
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
        return None
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
    outcomes = stat.outcomes
    long_m = compute_metrics([o for o in outcomes if o.side == "long"])
    short_m = compute_metrics([o for o in outcomes if o.side == "short"])
    return dict(tc=tc, pf=pf, exp=exp, wr=wr, pw=pw, wc=wc, wf_pct=wf_pct, gate=gate,
                long_pf=float(long_m.get("profit_factor", 0)),
                short_pf=float(short_m.get("profit_factor", 0)),
                long_n=len([o for o in outcomes if o.side == "long"]),
                short_n=len([o for o in outcomes if o.side == "short"]),
                signals=stat.signals_fired)


def main():
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    print(f"{'vol_z':>6} | {'sigs':>6} {'trd':>6} L/S {'win%':>6} {'exp_r':>7} {'PF':>6} "
          f"{'longPF':>7} {'shrtPF':>7} {'wf':>8} | GATE")
    print("-" * 105)

    for vol_z in [0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]:
        r = run_v(vol_z, candles, funding, oi)
        if r is None:
            print(f"{vol_z:>6.2f} | (no results)")
            continue
        print(f"{vol_z:>6.2f} | {r['signals']:>6} {r['tc']:>6} {r['long_n']}/{r['short_n']:<4} "
              f"{r['wr']:>6.1%} {r['exp']:>7.4f} {r['pf']:>6.3f} "
              f"{r['long_pf']:>7.3f} {r['short_pf']:>7.3f} "
              f"{r['pw']}/{r['wc']:>4} ({r['wf_pct']:>3.0%}) | "
              f"{'PASS' if r['gate'] else 'fail'}")


if __name__ == "__main__":
    main()
