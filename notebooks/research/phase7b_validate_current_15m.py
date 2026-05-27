"""Validate current Phase 5 strategies on the extended 15m Bybit dataset."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.validation.event_runner import ValidationConfig, run_event_validation


def main() -> None:
    data = ROOT / "data"
    candles = load_candles(data, "bybit", "BTCUSDT", "15m")
    funding = load_funding(data, "bybit", "BTCUSDT")
    oi = load_open_interest(data, "bybit", "BTCUSDT", "1h")
    for sid in ("liquidity_sweep_v1", "squeeze_v1", "trend_pullback_v1"):
        cfg = ValidationConfig(
            timeframe="15m",
            strategy_ids=(sid,),
            risk_config=RiskConfig(
                daily_loss_limit_pct=Decimal("1"),
                max_drawdown_pct=Decimal("1"),
                max_open_positions=1,
                max_portfolio_heat_pct=Decimal("1"),
            ),
        )
        result = run_event_validation(candles, funding, oi, cfg)
        stat = result.strategy_stats[sid]
        metrics = stat.metrics
        print(
            sid,
            "signals", stat.signals_fired,
            "approved", stat.approved,
            "trades", metrics["trade_count"],
            "win", metrics["win_rate"],
            "exp", metrics["expectancy_r"],
            "pf", metrics["profit_factor"],
            "net", metrics["net_pnl"],
        )


if __name__ == "__main__":
    main()
