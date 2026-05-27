"""
Final targeted sweep: can any variant reach all 4 gates?

Best candidates to tune:
- C3-base: 278 trades, PF 1.225, exp +0.163, wf 8/21=38%  [trade count NEAR gate, wf fails]
- C2:       220 trades, PF 1.444, exp +0.313, wf 8/21=38%  [trade count fails, wf fails]

Need: wf improvement + trade count near 300.

Approaches:
1. C3 with quality filters on pullback (vol_z >= 0.3) → reduces count but improves wf
2. C3 with wider regime for pullback (also breakout_pending)
3. C2 + lower vol_z on breakdown (1.5 instead of 2.0) to get more breakdown trades
4. Explore "high_volatility regime" for EMA cross (add hv regime)
"""
from __future__ import annotations
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
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


def _sig(sid, snapshot, stop, target, regime, now):
    rejected, _ = check_rr(float(snapshot.close), stop, target)
    if rejected: return None
    return SignalCandidate(
        strategy_id=sid, venue=snapshot.venue, symbol=snapshot.symbol,
        timeframe=snapshot.timeframe, side="short", created_at=now,
        expires_at=now+timedelta(minutes=720), base_confidence=Decimal("0.70"),
        expected_horizon_minutes=720, entry_reference=snapshot.close,
        invalidation_price=Decimal(f"{stop:.2f}"),
        target_prices=[Decimal(f"{target:.2f}")],
        evidence={"r": regime.regime}, feature_version=snapshot.feature_version,
        strategy_version="sweep")


def run_v(fn, sid, candles, funding, oi, label):
    STRATEGIES[sid] = fn
    try:
        cfg = ValidationConfig(
            strategy_ids=(sid,),
            portfolio_config=PortfolioConfig(risk_pct=Decimal("0.0025"), max_hold_minutes=720),
            risk_config=RiskConfig(daily_loss_limit_pct=Decimal("0.01"), max_drawdown_pct=Decimal("0.10"), max_open_positions=1),
        )
        result = run_event_validation(candles, funding, oi, cfg)
        wf = run_walk_forward(candles, funding, oi, cfg)
    finally:
        STRATEGIES.pop(sid, None)
    stat = result.strategy_stats.get(sid)
    if not stat: return
    m = stat.metrics
    wf_agg = wf.aggregate_metrics
    tc = m.get("trade_count", 0); pf = float(m.get("profit_factor", 0))
    exp = float(m.get("expectancy_r") or 0); wr = float(m.get("win_rate", 0))
    pw = wf_agg.get("profitable_windows", 0); wc = wf_agg.get("window_count", 1)
    wf_pct = pw / wc if wc else 0
    gate = tc>=300 and pf>=1.25 and exp>0 and wf_pct>=0.50
    print(f"  {label:65s} trd={tc:4d} exp={exp:+.3f} PF={pf:.3f} "
          f"wf={pw}/{wc}({wf_pct:.0%}) {'PASS' if gate else 'fail'}")


def main():
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    # V1: C3 with vol_z>=0.3 on pullback (quality filter)
    def v1(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req = ("close","ema_20","ema_50","ema_200","adx_14","rsi_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); rsi=float(sn.rsi_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=2.0 and c<pdl:
            return _sig("v1",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and bo>e20>=c:
            return _sig("v1",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        if (reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and 40<=rsi<=60
                and vz>=0.3 and e50-1.5*atr<=c<=e50):
            return _sig("v1",sn,e50+0.5*atr,c-2.5*atr,reg,now)
        return None
    run_v(v1,"v1",candles,funding,oi, "C3 pullback vol_z>=0.3 [expects ~230-260 trd, better wf?]")

    # V2: C3 pullback in trend_down+breakout_pending (wider regime for pullback)
    def v2(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req=("close","ema_20","ema_50","ema_200","adx_14","rsi_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); rsi=float(sn.rsi_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=2.0 and c<pdl:
            return _sig("v2",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and bo>e20>=c:
            return _sig("v2",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        # pullback in both regimes
        if (reg.regime in ("trend_down","breakout_pending") and adx>=20 and 40<=rsi<=60
                and e50-1.5*atr<=c<=e50):
            return _sig("v2",sn,e50+0.5*atr,c-2.5*atr,reg,now)
        return None
    run_v(v2,"v2",candles,funding,oi, "C3 pullback in td+bp regimes [wider, expects ~290-310]")

    # V3: C2 (cross+breakdown) with breakdown vol_z lowered to 1.5
    def v3(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req=("close","ema_20","ema_50","ema_200","adx_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=1.5 and c<pdl:
            return _sig("v3",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and bo>e20>=c:
            return _sig("v3",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        return None
    run_v(v3,"v3",candles,funding,oi, "EMA cross + breakdown[vol_z>=1.5] combo")

    # V4: C2 with breakdown vol_z=1.0
    def v4(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req=("close","ema_20","ema_50","ema_200","adx_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=1.0 and c<pdl:
            return _sig("v4",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and bo>e20>=c:
            return _sig("v4",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        return None
    run_v(v4,"v4",candles,funding,oi, "EMA cross + breakdown[vol_z>=1.0] combo")

    # V5: EMA cross with RSI < 50 filter (confirming momentum) + breakdown
    def v5(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req=("close","ema_20","ema_50","ema_200","adx_14","rsi_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); rsi=float(sn.rsi_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=2.0 and c<pdl:
            return _sig("v5",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if (reg.regime=="trend_down" and adx>=20 and rsi<50 and e20<e50<e200 and bo>e20>=c):
            return _sig("v5",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        return None
    run_v(v5,"v5",candles,funding,oi, "EMA cross[RSI<50] + breakdown combo")

    # V6: V2 with vol_z>=0.3 on pullback
    def v6(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req=("close","ema_20","ema_50","ema_200","adx_14","rsi_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); rsi=float(sn.rsi_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=2.0 and c<pdl:
            return _sig("v6",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and bo>e20>=c:
            return _sig("v6",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        if (reg.regime in ("trend_down","breakout_pending") and adx>=20 and vz>=0.3
                and 40<=rsi<=60 and e50-1.5*atr<=c<=e50):
            return _sig("v6",sn,e50+0.5*atr,c-2.5*atr,reg,now)
        return None
    run_v(v6,"v6",candles,funding,oi, "V2 + pullback[vol_z>=0.3] in td+bp")


if __name__ == "__main__":
    main()
