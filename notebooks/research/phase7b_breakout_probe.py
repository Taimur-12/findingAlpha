"""Probe prior-day breakout continuation variants on 1h and 15m."""

from __future__ import annotations

import sys
from decimal import Decimal
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.simulation.executor import SimConfig
from finding_alpha.strategies.variants import PrevDayBreakoutParams, prev_day_breakout_variant
from finding_alpha.validation.research_grid import run_research_grid


DATA = ROOT / "data"
SESSIONS_ALL = ("asia", "london", "london_ny_overlap", "ny", "wind_down")
SESSIONS_ACTIVE = ("london", "london_ny_overlap")
SESSIONS_OVERLAP = ("london_ny_overlap",)


def run_for_timeframe(timeframe: str, warmup: int) -> None:
    candles = load_candles(DATA, "bybit", "BTCUSDT", timeframe)
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")
    variants = {}
    for side, sessions, vol_z, stop, target, hold in [
        ("both", SESSIONS_ALL, 0.5, 1.0, 2.0, 480),
        ("both", SESSIONS_ALL, 1.0, 1.0, 2.5, 480),
        ("both", SESSIONS_ACTIVE, 0.5, 1.0, 2.0, 480),
        ("both", SESSIONS_ACTIVE, 1.0, 1.0, 2.5, 720),
        ("long", SESSIONS_ACTIVE, 0.5, 1.0, 2.0, 480),
        ("short", SESSIONS_ACTIVE, 0.5, 1.0, 2.0, 480),
        ("short", SESSIONS_OVERLAP, 0.5, 1.0, 2.5, 720),
        ("long", SESSIONS_OVERLAP, 0.5, 1.0, 2.5, 720),
    ]:
        sid = f"pdb_{timeframe}_{side}_s{len(sessions)}_v{vol_z}_b{stop}_t{target}_h{hold}"
        variants[sid] = prev_day_breakout_variant(
            PrevDayBreakoutParams(
                strategy_id=sid,
                side=side,
                allowed_sessions=sessions,
                min_volume_z=vol_z,
                stop_atr=stop,
                target_atr=target,
                horizon_minutes=hold,
            )
        )
    results = run_research_grid(
        candles,
        funding,
        oi,
        variants,
        warmup_bars=warmup,
        timeframe=timeframe,
        portfolio_config=PortfolioConfig(risk_pct=Decimal("0.01"), max_hold_minutes=720),
        sim_config=SimConfig(maker_fee_bps=Decimal("2.0"), taker_fee_bps=Decimal("5.5"), stop_slippage_bps=Decimal("10")),
    )
    print(f"\nTop {timeframe} prior-day breakout variants >=50 trades")
    shown = 0
    for result in results:
        if result.trades < 50:
            continue
        metrics = result.metrics
        print(
            f"{result.strategy_id}: trades={result.trades}, exp={metrics['expectancy_r']:.3f}, "
            f"pf={metrics['profit_factor']:.3f}, win={metrics['win_rate']:.1%}, net={metrics['net_pnl']}"
        )
        shown += 1
        if shown >= 15:
            break


def main() -> None:
    run_for_timeframe("1h", 220)
    run_for_timeframe("15m", 900)


if __name__ == "__main__":
    main()
