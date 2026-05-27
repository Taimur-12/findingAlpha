"""
Phase 7 authoritative event-driven validation runner.

Runs real local Bybit BTCUSDT data through:
  CandleEvent -> features -> regime -> strategies -> portfolio/risk -> sim -> analytics

Outputs:
  docs/current/phase7_authoritative_event_validation_report.md
  docs/current/_phase7_event_validation_results.json
"""

from __future__ import annotations

import sys
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.simulation.executor import SimConfig
from finding_alpha.validation.event_runner import ValidationConfig, run_event_validation
from finding_alpha.validation.reporting import to_jsonable, write_json_report, write_markdown_report
from finding_alpha.validation.walk_forward import run_walk_forward


DATA = ROOT / "data"
DOCS = ROOT / "docs" / "current"


def main() -> None:
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    config = ValidationConfig(
        venue="bybit",
        symbol="BTCUSDT",
        timeframe="1h",
        initial_equity=Decimal("10000"),
        warmup_bars=220,
        one_position_at_a_time=True,
        use_signal_horizon_as_max_hold=True,
        strategy_ids=("liquidity_sweep_v1", "squeeze_v1", "trend_pullback_v1", "prev_day_breakdown_v1"),
        portfolio_config=PortfolioConfig(
            risk_pct=Decimal("0.01"),
            max_leverage=Decimal("10"),
            min_notional_usdt=Decimal("10"),
            qty_precision=3,
            price_precision=2,
            max_hold_minutes=480,
        ),
        risk_config=RiskConfig(
            daily_loss_limit_pct=Decimal("0.03"),
            max_drawdown_pct=Decimal("0.10"),
            max_open_positions=1,
            max_portfolio_heat_pct=Decimal("0.02"),
            max_snapshot_age_seconds=300,
            block_on_funding_stale=False,
        ),
        sim_config=SimConfig(
            maker_fee_bps=Decimal("2.0"),
            taker_fee_bps=Decimal("5.5"),
            stop_slippage_bps=Decimal("10"),
        ),
    )

    result = run_event_validation(candles, funding=funding, oi=oi, config=config)
    independent_results = {}
    for strategy_id in config.strategy_ids:
        single_config = config.model_copy(update={"strategy_ids": (strategy_id,)})
        independent_results[strategy_id] = run_event_validation(
            candles,
            funding=funding,
            oi=oi,
            config=single_config,
        )
    walk_forward = run_walk_forward(candles, funding=funding, oi=oi, config=config)

    write_json_report(result, DOCS / "_phase7_event_validation_results.json")
    (DOCS / "_phase7_independent_strategy_results.json").write_text(
        json.dumps(to_jsonable(independent_results), indent=2),
        encoding="utf-8",
    )
    write_markdown_report(
        result,
        DOCS / "phase7_authoritative_event_validation_report.md",
        walk_forward=walk_forward,
        independent_results=independent_results,
    )

    print("Phase 7 validation complete.")
    print(f"Period: {result.start.date()} to {result.end.date()}")
    print(f"Overall trades: {result.all_metrics['trade_count']}")
    print(f"Overall expectancy R: {result.all_metrics['expectancy_r']}")
    print(f"Overall net PnL: {result.all_metrics['net_pnl']}")
    print(f"No-lookahead passed: {result.no_lookahead['passed']}")
    print("Standalone strategy results:")
    for sid, independent in independent_results.items():
        stat = independent.strategy_stats[sid]
        print(
            f"{sid}: signals={stat.signals_fired}, approved={stat.approved}, "
            f"trades={stat.metrics['trade_count']}, expectancy={stat.metrics['expectancy_r']}, "
            f"net_pnl={stat.metrics['net_pnl']}"
        )


if __name__ == "__main__":
    main()
