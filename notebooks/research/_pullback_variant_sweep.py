"""
Sweep variants of the pullback strategy with entry-anchored stop.
Compare stop anchoring: EMA50-based (original) vs entry-based.
Also test different stop ATR multiples.
"""
from __future__ import annotations
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
from finding_alpha.analytics.metrics import compute_metrics
from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.strategies.fast_reject import check_features, check_rr
from finding_alpha.validation.event_runner import STRATEGIES, ValidationConfig, run_event_validation
from finding_alpha.validation.walk_forward import run_walk_forward

DATA = ROOT / "data"
_REQUIRED = ("close", "ema_20", "ema_50", "ema_200", "adx_14", "rsi_14", "atr_14")
_HORIZON = 720  # 12h (same as breakdown family for apples-to-apples)


def _session_name(ts: datetime) -> str:
    h = ts.hour
    if 0 <= h < 7:   return "asia"
    if 7 <= h < 13:  return "london"
    if 13 <= h < 17: return "london_ny_overlap"
    if 17 <= h < 22: return "ny"
    return "wind_down"


def _make_pullback_fn(
    stop_atr: float,
    target_atr: float,
    entry_anchored: bool,
    proximity_atr: float,
    min_adx: float,
    rsi_lo: float,
    rsi_hi: float,
    sessions: frozenset | None,
    horizon: int = _HORIZON,
):
    strat_id = (f"pb_{stop_atr:.2f}_{target_atr:.1f}_"
                f"{'ea' if entry_anchored else 'ema'}_"
                f"prox{proximity_atr:.1f}_adx{min_adx:.0f}_"
                f"rsi{rsi_lo:.0f}-{rsi_hi:.0f}")

    def fn(snapshot: FeatureSnapshot, regime: RegimeState, row: pd.Series, now: datetime) -> Optional[SignalCandidate]:
        if regime.regime not in ("trend_up", "trend_down"):
            return None
        if sessions and _session_name(now) not in sessions:
            return None
        rejected, _ = check_features(snapshot, _REQUIRED)
        if rejected:
            return None
        close = float(snapshot.close)
        e20, e50, e200 = float(snapshot.ema_20), float(snapshot.ema_50), float(snapshot.ema_200)
        adx = float(snapshot.adx_14)
        rsi = float(snapshot.rsi_14)
        atr = float(snapshot.atr_14)
        if atr <= 0 or adx < min_adx or not (rsi_lo <= rsi <= rsi_hi):
            return None

        if regime.regime == "trend_up":
            if not (e20 > e50 > e200):
                return None
            if not (e50 <= close <= e50 + proximity_atr * atr):
                return None
            if entry_anchored:
                stop = close - stop_atr * atr
                target = close + target_atr * atr
            else:
                stop = e50 - stop_atr * atr
                target = close + target_atr * atr
            side = "long"

        else:  # trend_down
            if not (e20 < e50 < e200):
                return None
            if not (e50 - proximity_atr * atr <= close <= e50):
                return None
            if entry_anchored:
                stop = close + stop_atr * atr
                target = close - target_atr * atr
            else:
                stop = e50 + stop_atr * atr
                target = close - target_atr * atr
            side = "short"

        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None
        return SignalCandidate(
            strategy_id=strat_id,
            venue=snapshot.venue,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            side=side,
            created_at=now,
            expires_at=now + timedelta(minutes=horizon),
            base_confidence=Decimal("0.70"),
            expected_horizon_minutes=horizon,
            entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"),
            target_prices=[Decimal(f"{target:.2f}")],
            evidence={"adx": f"{adx:.1f}", "rsi": f"{rsi:.1f}", "regime": regime.regime},
            feature_version=snapshot.feature_version,
            strategy_version="sweep",
        )
    fn.__name__ = strat_id
    return fn, strat_id


def run_variant(fn, strat_id, candles, funding, oi):
    STRATEGIES[strat_id] = fn
    try:
        cfg = ValidationConfig(
            strategy_ids=(strat_id,),
            portfolio_config=PortfolioConfig(risk_pct=Decimal("0.0025"), max_hold_minutes=720),
            risk_config=RiskConfig(
                daily_loss_limit_pct=Decimal("0.01"),
                max_drawdown_pct=Decimal("0.10"),
                max_open_positions=1,
            ),
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
    return dict(tc=tc, pf=pf, exp=exp, wr=wr, pw=pw, wc=wc, wf_pct=wf_pct, gate=gate)


def main():
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    SESS_ALL = frozenset({"asia", "london", "london_ny_overlap", "ny", "wind_down"})

    variants = [
        # Original EMA-anchored  (baseline)
        dict(stop_atr=0.5, target_atr=2.5, entry_anchored=False, proximity_atr=1.5, min_adx=20, rsi_lo=40, rsi_hi=60, sessions=None),
        # Entry-anchored stop, same params
        dict(stop_atr=0.5, target_atr=2.5, entry_anchored=True, proximity_atr=1.5, min_adx=20, rsi_lo=40, rsi_hi=60, sessions=None),
        # Entry-anchored, wider target (4.5 ATR)
        dict(stop_atr=0.5, target_atr=4.5, entry_anchored=True, proximity_atr=1.5, min_adx=20, rsi_lo=40, rsi_hi=60, sessions=None),
        # Entry-anchored, 0.75 stop/4.5 target (matches breakdown R:R)
        dict(stop_atr=0.75, target_atr=4.5, entry_anchored=True, proximity_atr=1.5, min_adx=20, rsi_lo=40, rsi_hi=60, sessions=None),
        # Entry-anchored, tighter proximity (price closer to EMA50)
        dict(stop_atr=0.5, target_atr=2.5, entry_anchored=True, proximity_atr=0.75, min_adx=20, rsi_lo=40, rsi_hi=60, sessions=None),
        # Entry-anchored, wider proximity
        dict(stop_atr=0.5, target_atr=2.5, entry_anchored=True, proximity_atr=2.5, min_adx=20, rsi_lo=40, rsi_hi=60, sessions=None),
        # Lower ADX threshold (more signals)
        dict(stop_atr=0.5, target_atr=2.5, entry_anchored=True, proximity_atr=1.5, min_adx=15, rsi_lo=40, rsi_hi=60, sessions=None),
        # Wider RSI (more signals)
        dict(stop_atr=0.5, target_atr=2.5, entry_anchored=True, proximity_atr=1.5, min_adx=20, rsi_lo=30, rsi_hi=70, sessions=None),
        # Lower ADX + wider RSI
        dict(stop_atr=0.5, target_atr=2.5, entry_anchored=True, proximity_atr=1.5, min_adx=15, rsi_lo=30, rsi_hi=70, sessions=None),
        # 0.75/4.5 + lower ADX + wider RSI (most permissive)
        dict(stop_atr=0.75, target_atr=4.5, entry_anchored=True, proximity_atr=1.5, min_adx=15, rsi_lo=30, rsi_hi=70, sessions=None),
        # Best bet combo: tight proximity + lower ADX
        dict(stop_atr=0.5, target_atr=2.5, entry_anchored=True, proximity_atr=0.75, min_adx=15, rsi_lo=30, rsi_hi=70, sessions=None),
    ]

    print(f"{'anchor':>8} {'stop':>5} {'tgt':>5} {'prox':>5} {'adx':>4} {'rsi':>8} | "
          f"{'trades':>7} {'win%':>6} {'exp_r':>7} {'PF':>6} {'wf':>8} | GATE")
    print("-" * 100)

    for v in variants:
        fn, strat_id = _make_pullback_fn(**v)
        r = run_variant(fn, strat_id, candles, funding, oi)
        if r is None:
            continue
        anchor = "entry" if v["entry_anchored"] else "ema50"
        print(f"{anchor:>8} {v['stop_atr']:>5.2f} {v['target_atr']:>5.1f} {v['proximity_atr']:>5.2f} "
              f"{v['min_adx']:>4.0f} {v['rsi_lo']:.0f}-{v['rsi_hi']:.0f} | "
              f"{r['tc']:>7} {r['wr']:>6.1%} {r['exp']:>7.4f} {r['pf']:>6.3f} "
              f"{r['pw']}/{r['wc']:>4} ({r['wf_pct']:>3.0%}) | {'PASS' if r['gate'] else 'fail'}")


if __name__ == "__main__":
    main()
