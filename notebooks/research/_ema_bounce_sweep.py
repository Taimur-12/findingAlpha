"""
Test EMA20 bounce strategy variants.

LONG: trend_up regime, bar.low <= ema_20, close > ema_20 (wick down to EMA20, recovered)
SHORT: trend_down regime, bar.high >= ema_20, close < ema_20 (wick up to EMA20, rejected)

Uses row.low/row.high from bar data — passed through adapter.
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
_REQUIRED = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "atr_14")


def _make_ema_bounce_fn(
    stop_atr: float, target_atr: float,
    min_adx: float, min_vol_z: float | None,
    use_vol_z: bool,
    stop_anchor: str,  # "entry" or "ema50"
    horizon: int = 720,
):
    strat_id = f"emabounce_{stop_atr:.2f}_{target_atr:.1f}_{stop_anchor}_adx{min_adx:.0f}"
    req = list(_REQUIRED)
    if use_vol_z:
        req.append("volume_z_score")

    def fn(snapshot: FeatureSnapshot, regime: RegimeState, row: pd.Series, now: datetime) -> Optional[SignalCandidate]:
        if regime.regime not in ("trend_up", "trend_down"):
            return None
        rejected, _ = check_features(snapshot, tuple(req))
        if rejected:
            return None
        close = float(snapshot.close)
        e20 = float(snapshot.ema_20)
        e50 = float(snapshot.ema_50)
        e200 = float(snapshot.ema_200)
        adx = float(snapshot.adx_14)
        atr = float(snapshot.atr_14)
        bar_low = float(row["low"])
        bar_high = float(row["high"])
        if atr <= 0 or adx < min_adx:
            return None
        if use_vol_z:
            vz = float(snapshot.volume_z_score)
            if vz < (min_vol_z or 0):
                return None

        if regime.regime == "trend_up":
            if not (e20 > e50 > e200):
                return None
            # Bar wicked through EMA20 but closed above it
            if not (bar_low <= e20 < close):
                return None
            if stop_anchor == "entry":
                stop = close - stop_atr * atr
            else:
                stop = e50 - stop_atr * atr
            target = close + target_atr * atr
            side = "long"

        else:  # trend_down
            if not (e20 < e50 < e200):
                return None
            # Bar wicked through EMA20 but closed below it
            if not (close < e20 <= bar_high):
                return None
            if stop_anchor == "entry":
                stop = close + stop_atr * atr
            else:
                stop = e50 + stop_atr * atr
            target = close - target_atr * atr
            side = "short"

        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None
        return SignalCandidate(
            strategy_id=strat_id,
            venue=snapshot.venue, symbol=snapshot.symbol, timeframe=snapshot.timeframe,
            side=side, created_at=now, expires_at=now + timedelta(minutes=horizon),
            base_confidence=Decimal("0.70"), expected_horizon_minutes=horizon,
            entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"),
            target_prices=[Decimal(f"{target:.2f}")],
            evidence={"adx": f"{adx:.1f}", "regime": regime.regime},
            feature_version=snapshot.feature_version, strategy_version="sweep",
        )
    fn.__name__ = strat_id
    return fn, strat_id


def run_variant(fn, strat_id, candles, funding, oi):
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
    return dict(tc=tc, pf=pf, exp=exp, wr=wr, pw=pw, wc=wc, wf_pct=wf_pct, gate=gate,
                signals=stat.signals_fired)


def main():
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    variants = [
        dict(stop_atr=0.5,  target_atr=2.5, min_adx=20, min_vol_z=None, use_vol_z=False, stop_anchor="ema50"),
        dict(stop_atr=0.5,  target_atr=2.5, min_adx=20, min_vol_z=None, use_vol_z=False, stop_anchor="entry"),
        dict(stop_atr=0.75, target_atr=4.5, min_adx=20, min_vol_z=None, use_vol_z=False, stop_anchor="entry"),
        dict(stop_atr=0.75, target_atr=4.5, min_adx=15, min_vol_z=None, use_vol_z=False, stop_anchor="entry"),
        dict(stop_atr=0.5,  target_atr=2.5, min_adx=15, min_vol_z=None, use_vol_z=False, stop_anchor="ema50"),
        dict(stop_atr=0.5,  target_atr=4.5, min_adx=15, min_vol_z=None, use_vol_z=False, stop_anchor="ema50"),
        dict(stop_atr=0.5,  target_atr=2.5, min_adx=20, min_vol_z=1.0, use_vol_z=True, stop_anchor="ema50"),
        dict(stop_atr=0.75, target_atr=4.5, min_adx=20, min_vol_z=1.0, use_vol_z=True, stop_anchor="entry"),
        dict(stop_atr=1.0,  target_atr=4.5, min_adx=15, min_vol_z=None, use_vol_z=False, stop_anchor="entry"),
    ]

    print(f"{'anchor':>8} {'stop':>5} {'tgt':>5} {'adx':>4} {'volz':>5} | "
          f"{'sigs':>6} {'trd':>6} {'win%':>6} {'exp_r':>7} {'PF':>6} {'wf':>8} | GATE")
    print("-" * 100)

    for v in variants:
        fn, strat_id = _make_ema_bounce_fn(**v)
        r = run_variant(fn, strat_id, candles, funding, oi)
        if r is None:
            continue
        vz = f"{v['min_vol_z']:.1f}" if v['use_vol_z'] else "  -"
        print(f"{v['stop_anchor']:>8} {v['stop_atr']:>5.2f} {v['target_atr']:>5.1f} "
              f"{v['min_adx']:>4.0f} {vz:>5} | "
              f"{r['signals']:>6} {r['tc']:>6} {r['wr']:>6.1%} {r['exp']:>7.4f} "
              f"{r['pf']:>6.3f} {r['pw']}/{r['wc']:>4} ({r['wf_pct']:>3.0%}) | "
              f"{'PASS' if r['gate'] else 'fail'}")


if __name__ == "__main__":
    main()
