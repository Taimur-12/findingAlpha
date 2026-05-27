"""Low-risk Phase 7 run for prev_day_breakdown_v1 using 0.25% risk/trade."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.validation.event_runner import ValidationConfig, run_event_validation


def main() -> None:
    data = ROOT / "data"
    candles = load_candles(data, "bybit", "BTCUSDT", "1h")
    funding = load_funding(data, "bybit", "BTCUSDT")
    oi = load_open_interest(data, "bybit", "BTCUSDT", "1h")
    cfg = ValidationConfig(
        strategy_ids=("prev_day_breakdown_v1",),
        portfolio_config=PortfolioConfig(risk_pct=Decimal("0.0025"), max_hold_minutes=720),
        risk_config=RiskConfig(
            daily_loss_limit_pct=Decimal("0.01"),
            max_drawdown_pct=Decimal("0.10"),
            max_open_positions=1,
            max_portfolio_heat_pct=Decimal("0.01"),
        ),
    )
    result = run_event_validation(candles, funding, oi, cfg)
    stat = result.strategy_stats["prev_day_breakdown_v1"]
    print("signals", stat.signals_fired)
    print("approved", stat.approved)
    print("rejections", stat.rejection_reasons)
    print("metrics", stat.metrics)
    print("by_session", stat.by_session)
    print("by_regime", stat.by_regime)
    print("final_equity", result.final_equity, "peak", result.peak_equity)


if __name__ == "__main__":
    main()
