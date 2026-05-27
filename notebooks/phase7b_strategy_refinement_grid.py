"""
Phase 7B strategy refinement grid.

This is a research scanner, not a promotion gate. It uses the same next-bar
entry and fill model as Phase 7, but it scans parameterized variants quickly
without drawdown halts. Top variants must still be rerun through Phase 7.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.simulation.executor import SimConfig
from finding_alpha.strategies.variants import (
    LiquiditySweepParams,
    SqueezeParams,
    TrendPullbackParams,
    liquidity_sweep_variant,
    squeeze_variant,
    trend_pullback_variant,
)
from finding_alpha.validation.reporting import to_jsonable
from finding_alpha.validation.research_grid import run_research_grid


DATA = ROOT / "data"
DOCS = ROOT / "docs" / "current"
SESSIONS_ALL = ("asia", "london", "london_ny_overlap", "ny", "wind_down")
SESSIONS_ACTIVE = ("london", "london_ny_overlap")
SESSIONS_OVERLAP = ("london_ny_overlap",)


def main() -> None:
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    variants = {}

    for regimes, sessions, vol_z, wick, target, stop in [
        (("breakout_pending",), SESSIONS_ALL, 1.5, 0.0, 2.5, 0.25),
        (("breakout_pending",), SESSIONS_ALL, 1.5, 0.0, 3.0, 0.25),
        (("breakout_pending",), SESSIONS_ACTIVE, 1.5, 0.0, 2.5, 0.25),
        (("breakout_pending",), SESSIONS_ACTIVE, 2.0, 0.0, 3.0, 0.25),
        (("breakout_pending",), SESSIONS_OVERLAP, 1.5, 0.0, 3.0, 0.25),
        (("range", "breakout_pending"), SESSIONS_ACTIVE, 2.0, 0.30, 3.0, 0.25),
    ]:
        sid = (
            f"ls_r{len(regimes)}_s{len(sessions)}_v{vol_z}_w{wick}"
            f"_t{target}_b{stop}"
        )
        variants[sid] = liquidity_sweep_variant(
            LiquiditySweepParams(
                strategy_id=sid,
                allowed_regimes=regimes,
                allowed_sessions=sessions,
                min_volume_z=vol_z,
                min_wick_atr=wick,
                target_atr=target,
                stop_buffer_atr=stop,
            )
        )

    for side, sessions, proximity, stop, target, min_adx in [
        ("short", SESSIONS_ACTIVE, 0.50, 0.75, 1.50, 20.0),
        ("short", SESSIONS_ACTIVE, 0.50, 1.00, 1.50, 20.0),
        ("short", SESSIONS_ACTIVE, 0.75, 0.75, 2.00, 20.0),
        ("short", SESSIONS_ACTIVE, 0.75, 1.00, 2.00, 25.0),
        ("short", SESSIONS_OVERLAP, 0.75, 0.75, 2.00, 20.0),
        ("both", SESSIONS_ACTIVE, 0.50, 1.00, 1.50, 25.0),
    ]:
        sid = f"tp_{side}_s{len(sessions)}_p{proximity}_b{stop}_t{target}_adx{min_adx}"
        variants[sid] = trend_pullback_variant(
            TrendPullbackParams(
                strategy_id=sid,
                side=side,
                allowed_sessions=sessions,
                proximity_atr=proximity,
                stop_atr=stop,
                target_atr=target,
                min_adx=min_adx,
            )
        )

    for sessions, bw, vol_z, target, hold in [
        (SESSIONS_ALL, 20.0, 0.0, 2.5, 360),
        (SESSIONS_ALL, 30.0, 0.0, 2.5, 720),
        (SESSIONS_ACTIVE, 20.0, 0.0, 2.5, 360),
        (SESSIONS_ACTIVE, 30.0, 0.0, 3.0, 720),
        (SESSIONS_ACTIVE, 20.0, 0.5, 3.0, 720),
        (SESSIONS_OVERLAP, 30.0, 0.0, 3.0, 720),
    ]:
        sid = f"sq_s{len(sessions)}_bw{bw}_v{vol_z}_t{target}_h{hold}"
        variants[sid] = squeeze_variant(
            SqueezeParams(
                strategy_id=sid,
                allowed_sessions=sessions,
                max_bandwidth_pct=bw,
                min_volume_z=vol_z,
                target_atr=target,
                horizon_minutes=hold,
            )
        )

    results = run_research_grid(
        candles,
        funding,
        oi,
        variants,
        portfolio_config=PortfolioConfig(risk_pct=Decimal("0.01"), max_hold_minutes=720),
        sim_config=SimConfig(maker_fee_bps=Decimal("2.0"), taker_fee_bps=Decimal("5.5"), stop_slippage_bps=Decimal("10")),
    )

    payload = [
        {
            "strategy_id": r.strategy_id,
            "signals": r.signals,
            "trades": r.trades,
            "metrics": r.metrics,
            "by_regime": r.by_regime,
            "by_session": r.by_session,
        }
        for r in results
    ]
    out = DOCS / "_phase7b_strategy_refinement_grid.json"
    out.write_text(json.dumps(to_jsonable(payload), indent=2), encoding="utf-8")

    print(f"Scanned {len(results)} variants")
    print("Top variants with >=30 trades:")
    shown = 0
    for r in results:
        if r.trades < 30:
            continue
        m = r.metrics
        print(
            f"{r.strategy_id}: trades={r.trades}, exp={m['expectancy_r']:.3f}, "
            f"pf={m['profit_factor']:.3f}, net={m['net_pnl']}, win={m['win_rate']:.1%}"
        )
        shown += 1
        if shown >= 20:
            break
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
