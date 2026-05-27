"""Candidate-only walk-forward check for prev_day_breakdown_v1."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.validation.event_runner import ValidationConfig
from finding_alpha.validation.walk_forward import run_walk_forward


def main() -> None:
    data = ROOT / "data"
    candles = load_candles(data, "bybit", "BTCUSDT", "1h")
    funding = load_funding(data, "bybit", "BTCUSDT")
    oi = load_open_interest(data, "bybit", "BTCUSDT", "1h")
    cfg = ValidationConfig(strategy_ids=("prev_day_breakdown_v1",))
    wf = run_walk_forward(candles, funding, oi, cfg)
    print("aggregate", wf.aggregate_metrics)
    for idx, result in enumerate(wf.test_results, 1):
        metrics = result.all_metrics
        print(
            idx,
            result.start.date(),
            result.end.date(),
            "trades", metrics["trade_count"],
            "exp", metrics["expectancy_r"],
            "pf", metrics["profit_factor"],
            "net", metrics["net_pnl"],
        )


if __name__ == "__main__":
    main()
