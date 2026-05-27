"""
Precision tuning around V4 (best candidate: 251 trades, PF 1.276, wf 10/21=48%).
Need: ~50 more trades + 1 more profitable window.

Tests:
- V4 + pullback[vol_z>=0.3, td only]
- V4 + pullback[vol_z>=0.5, td only]
- V4 + pullback[vol_z>=0.1, td only]
- V4 but EMA cross also allows vol_z>=0.1 filter
- V4 but EMA cross also fires in breakout_pending (entry-anchored stop)
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
    print(f"  {label:70s} trd={tc:4d} exp={exp:+.3f} PF={pf:.3f} "
          f"wf={pw}/{wc}({wf_pct:.0%}) {'PASS' if gate else 'fail'}")


def _base(sn, reg, row):
    """Return base features for SHORT strategies. Returns None if invalid."""
    req=("close","ema_20","ema_50","ema_200","adx_14","atr_14","prev_day_low","volume_z_score")
    rejected,_=check_features(sn,req)
    if rejected: return None
    return (float(sn.close), float(sn.ema_20), float(sn.ema_50), float(sn.ema_200),
            float(sn.adx_14), float(sn.atr_14), float(sn.prev_day_low),
            float(sn.volume_z_score), float(row["open"]))


def main():
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    # V4 baseline: EMA cross + breakdown[vz>=1.0]
    def v4(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        b = _base(sn, reg, row)
        if not b: return None
        c,e20,e50,e200,adx,atr,pdl,vz,bo = b
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=1.0 and c<pdl:
            return _sig("v4",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and bo>e20>=c:
            return _sig("v4",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        return None
    run_v(v4,"v4",candles,funding,oi, "V4 baseline [251 trd, PF 1.276, wf 10/21=48%]")

    # V4A: V4 + pullback[vz>=0.3, td only]
    def v4a(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req=("close","ema_20","ema_50","ema_200","adx_14","rsi_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); rsi=float(sn.rsi_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=1.0 and c<pdl:
            return _sig("v4a",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and bo>e20>=c:
            return _sig("v4a",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        if (reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and vz>=0.3
                and 40<=rsi<=60 and e50-1.5*atr<=c<=e50):
            return _sig("v4a",sn,e50+0.5*atr,c-2.5*atr,reg,now)
        return None
    run_v(v4a,"v4a",candles,funding,oi, "V4 + pullback[vz>=0.3, td only]")

    # V4B: V4 + pullback[vz>=0.5, td only]
    def v4b(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req=("close","ema_20","ema_50","ema_200","adx_14","rsi_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); rsi=float(sn.rsi_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=1.0 and c<pdl:
            return _sig("v4b",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and bo>e20>=c:
            return _sig("v4b",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        if (reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and vz>=0.5
                and 40<=rsi<=60 and e50-1.5*atr<=c<=e50):
            return _sig("v4b",sn,e50+0.5*atr,c-2.5*atr,reg,now)
        return None
    run_v(v4b,"v4b",candles,funding,oi, "V4 + pullback[vz>=0.5, td only]")

    # V4C: V4 but EMA cross also fires with vol_z >= 0.1
    def v4c(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        b = _base(sn, reg, row)
        if not b: return None
        c,e20,e50,e200,adx,atr,pdl,vz,bo = b
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=1.0 and c<pdl:
            return _sig("v4c",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if (reg.regime=="trend_down" and adx>=20 and vz>=0.1 and e20<e50<e200 and bo>e20>=c):
            return _sig("v4c",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        return None
    run_v(v4c,"v4c",candles,funding,oi, "V4 but EMA cross vol_z>=0.1")

    # V4D: V4C + pullback[vz>=0.3, td only]
    def v4d(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req=("close","ema_20","ema_50","ema_200","adx_14","rsi_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); rsi=float(sn.rsi_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=1.0 and c<pdl:
            return _sig("v4d",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if (reg.regime=="trend_down" and adx>=20 and vz>=0.1 and e20<e50<e200 and bo>e20>=c):
            return _sig("v4d",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        if (reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and vz>=0.3
                and 40<=rsi<=60 and e50-1.5*atr<=c<=e50):
            return _sig("v4d",sn,e50+0.5*atr,c-2.5*atr,reg,now)
        return None
    run_v(v4d,"v4d",candles,funding,oi, "V4D: breakdown[vz>=1]+cross[vz>=0.1]+pullback[vz>=0.3]")

    # V4E: all signals but stricter stop/target (0.5/3.0) for pullback
    def v4e(sn, reg, row, now):
        if reg.regime not in ("trend_down","breakout_pending"): return None
        req=("close","ema_20","ema_50","ema_200","adx_14","rsi_14","atr_14","prev_day_low","volume_z_score")
        rejected,_=check_features(sn,req)
        if rejected: return None
        c=float(sn.close); e20=float(sn.ema_20); e50=float(sn.ema_50); e200=float(sn.ema_200)
        adx=float(sn.adx_14); rsi=float(sn.rsi_14); atr=float(sn.atr_14)
        pdl=float(sn.prev_day_low); vz=float(sn.volume_z_score); bo=float(row["open"])
        if atr<=0: return None
        if reg.regime in ("trend_down","breakout_pending") and vz>=1.0 and c<pdl:
            return _sig("v4e",sn,c+0.75*atr,c-4.5*atr,reg,now)
        if (reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and bo>e20>=c):
            return _sig("v4e",sn,e50+0.5*atr,c-4.5*atr,reg,now)
        if (reg.regime=="trend_down" and adx>=20 and e20<e50<e200 and vz>=0.3
                and 40<=rsi<=60 and c<=e50 and c>=e50-atr):  # tighter proximity: 1 ATR
            return _sig("v4e",sn,e50+0.5*atr,c-3.0*atr,reg,now)
        return None
    run_v(v4e,"v4e",candles,funding,oi, "V4 + tighter pullback[prox=1ATR, vz>=0.3, target=3.0]")


if __name__ == "__main__":
    main()
