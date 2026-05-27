"""
Phase 7C variant sweep — find parameters that pass the 300-trade gate.

Tests SHORT-only prev_day_breakdown family with varying:
  - volume_z threshold: 0.5, 1.0, 1.5, 2.0
  - sessions: restricted (no NY) vs all
  - stop ATR: 0.75, 1.0, 1.25

Prints a table so we can pick the best combo that passes all gates.

Usage:
    python notebooks/phase7c_variant_sweep.py
"""

from __future__ import annotations

import sys
from decimal import Decimal
from datetime import datetime, timedelta
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
from finding_alpha.validation.event_runner import (
    STRATEGIES, ValidationConfig, run_event_validation, StrategyFn,
)
from finding_alpha.validation.walk_forward import run_walk_forward

DATA = ROOT / "data"

_ALLOWED_REGIMES_SHORT = frozenset({"trend_down", "breakout_pending"})
_SESSIONS_RESTRICTED = frozenset({"asia", "london", "london_ny_overlap", "wind_down"})
_SESSIONS_ALL = frozenset({"asia", "london", "london_ny_overlap", "ny", "wind_down"})
_HORIZON_MINUTES = 720
_REQUIRED = ("close", "prev_day_low", "atr_14", "volume_z_score")


def _session_name(ts: datetime) -> str:
    hour = ts.hour
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 13:
        return "london"
    if 13 <= hour < 17:
        return "london_ny_overlap"
    if 17 <= hour < 22:
        return "ny"
    return "wind_down"


def _make_short_fn(vol_z_min: float, sessions: frozenset, stop_atr: float, target_atr: float) -> StrategyFn:
    strat_id = f"sweep_{vol_z_min:.1f}_{stop_atr:.2f}"

    def fn(snapshot: FeatureSnapshot, regime: RegimeState, row: pd.Series, now: datetime) -> Optional[SignalCandidate]:
        if regime.regime not in _ALLOWED_REGIMES_SHORT:
            return None
        if _session_name(now) not in sessions:
            return None
        rejected, _ = check_features(snapshot, _REQUIRED)
        if rejected:
            return None
        close = float(snapshot.close)
        prev_day_low = float(snapshot.prev_day_low)
        atr = float(snapshot.atr_14)
        volume_z = float(snapshot.volume_z_score)
        if atr <= 0 or volume_z < vol_z_min:
            return None
        if close >= prev_day_low:
            return None
        stop = close + stop_atr * atr
        target = close - target_atr * atr
        rejected, _ = check_rr(close, stop, target)
        if rejected:
            return None
        return SignalCandidate(
            strategy_id=strat_id,
            venue=snapshot.venue,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            side="short",
            created_at=now,
            expires_at=now + timedelta(minutes=_HORIZON_MINUTES),
            base_confidence=Decimal("0.70"),
            expected_horizon_minutes=_HORIZON_MINUTES,
            entry_reference=snapshot.close,
            invalidation_price=Decimal(f"{stop:.2f}"),
            target_prices=[Decimal(f"{target:.2f}")],
            evidence={"vol_z": f"{volume_z:.2f}", "regime": regime.regime},
            feature_version=snapshot.feature_version,
            strategy_version="sweep",
        )

    fn.__name__ = strat_id
    return fn, strat_id


def main() -> None:
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    variants = []
    for vol_z in [0.5, 1.0, 1.5, 2.0]:
        for sessions_label, sessions in [("no_ny", _SESSIONS_RESTRICTED), ("all", _SESSIONS_ALL)]:
            for stop_atr, target_atr in [(0.75, 4.5), (1.0, 4.5), (1.25, 4.5), (0.75, 3.0)]:
                variants.append((vol_z, sessions_label, sessions, stop_atr, target_atr))

    print(f"{'vol_z':>6} {'sessions':>8} {'stop':>5} {'target':>6} | "
          f"{'trades':>7} {'win%':>6} {'exp_r':>7} {'PF':>6} {'wf_pass':>8} | GATE")
    print("-" * 90)

    for vol_z, sessions_label, sessions, stop_atr, target_atr in variants:
        fn, strat_id = _make_short_fn(vol_z, sessions, stop_atr, target_atr)

        from finding_alpha.validation.event_runner import STRATEGIES as S
        custom_strats = {strat_id: fn}

        cfg = ValidationConfig(
            timeframe="1h",
            strategy_ids=(strat_id,),
            portfolio_config=PortfolioConfig(risk_pct=Decimal("0.0025"), max_hold_minutes=720),
            risk_config=RiskConfig(
                daily_loss_limit_pct=Decimal("0.01"),
                max_drawdown_pct=Decimal("0.10"),
                max_open_positions=1,
                max_portfolio_heat_pct=Decimal("0.01"),
            ),
        )

        # Temporarily inject the strategy
        S[strat_id] = fn
        try:
            result = run_event_validation(candles, funding, oi, cfg)
            wf = run_walk_forward(candles, funding, oi, cfg)
        finally:
            S.pop(strat_id, None)

        stat = result.strategy_stats.get(strat_id)
        if stat is None:
            continue
        m = stat.metrics
        wf_agg = wf.aggregate_metrics

        tc = m.get("trade_count", 0)
        pf = float(m.get("profit_factor", 0))
        exp = float(m.get("expectancy_r", 0))
        wr = float(m.get("win_rate", 0))
        pw = wf_agg.get("profitable_windows", 0)
        wc = wf_agg.get("window_count", 1)
        wf_pct = pw / wc if wc else 0

        gate = (tc >= 300) and (pf >= 1.25) and (exp > 0) and (wf_pct >= 0.50)
        gate_str = "PASS" if gate else "fail"

        print(f"{vol_z:>6.1f} {sessions_label:>8} {stop_atr:>5.2f} {target_atr:>6.1f} | "
              f"{tc:>7} {wr:>6.1%} {exp:>7.4f} {pf:>6.3f} {pw}/{wc:>4} ({wf_pct:>3.0%}) | {gate_str}")


if __name__ == "__main__":
    main()
