"""Focused short-only 1h prior-day breakdown probe."""

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
SESSIONS_NO_NY = ("asia", "london", "london_ny_overlap", "wind_down")


def main() -> None:
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")
    variants = {}
    for vol_z, stop, target, hold in product(
        [1.5, 2.0],
        [0.50, 0.75, 1.00],
        [3.0, 3.5, 4.0, 4.5],
        [720, 960],
    ):
        sid = f"pdb1h_short_nonny_v{vol_z}_b{stop}_t{target}_h{hold}"
        variants[sid] = prev_day_breakout_variant(
            PrevDayBreakoutParams(
                strategy_id=sid,
                side="short",
                allowed_sessions=SESSIONS_NO_NY,
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
    print("Top focused short breakdown variants >=60 trades")
    shown = 0
    for result in results:
        if result.trades < 60:
            continue
        m = result.metrics
        print(
            f"{result.strategy_id}: trades={result.trades}, exp={m['expectancy_r']:.3f}, "
            f"pf={m['profit_factor']:.3f}, win={m['win_rate']:.1%}, net={m['net_pnl']}"
        )
        print(f"  by_session={result.by_session}")
        shown += 1
        if shown >= 15:
            break


if __name__ == "__main__":
    main()
