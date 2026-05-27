"""Focused 1h prior-day breakout refinement around the best initial probe."""

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
SESSIONS_NO_NY = ("asia", "london", "london_ny_overlap", "wind_down")


def main() -> None:
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")
    variants = {}
    for side, sessions, vol_z, stop, target, hold in product(
        ["both", "short"],
        [SESSIONS_ALL, SESSIONS_NO_NY],
        [1.0, 1.5],
        [0.75, 1.0],
        [2.5, 3.0, 3.5],
        [480, 720],
    ):
        sid = f"pdb1h_{side}_s{len(sessions)}_v{vol_z}_b{stop}_t{target}_h{hold}"
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
        warmup_bars=220,
        timeframe="1h",
        portfolio_config=PortfolioConfig(risk_pct=Decimal("0.01"), max_hold_minutes=960),
        sim_config=SimConfig(maker_fee_bps=Decimal("2.0"), taker_fee_bps=Decimal("5.5"), stop_slippage_bps=Decimal("10")),
    )
    print("Top 1h breakout refinements >=100 trades")
    shown = 0
    for result in results:
        if result.trades < 100:
            continue
        m = result.metrics
        print(
            f"{result.strategy_id}: trades={result.trades}, exp={m['expectancy_r']:.3f}, "
            f"pf={m['profit_factor']:.3f}, win={m['win_rate']:.1%}, net={m['net_pnl']}"
        )
        shown += 1
        if shown >= 25:
            break


if __name__ == "__main__":
    main()
