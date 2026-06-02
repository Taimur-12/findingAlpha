"""Generate Phase 7B candidate report for prev_day_breakdown_v1."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.analytics.metrics import compute_metrics
from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.validation.event_runner import ValidationConfig, run_event_validation
from finding_alpha.validation.reporting import to_jsonable
from finding_alpha.validation.walk_forward import run_walk_forward


DOCS = ROOT / "docs" / "current"


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
    wf = run_walk_forward(candles, funding, oi, cfg)
    stat = result.strategy_stats["prev_day_breakdown_v1"]
    outcomes = stat.outcomes

    by_month = defaultdict(list)
    for outcome in outcomes:
        by_month[outcome.entry_ts.strftime("%Y-%m")].append(outcome)
    monthly = {month: compute_metrics(vals) for month, vals in sorted(by_month.items())}

    sorted_outcomes = sorted(outcomes, key=lambda o: o.net_pnl, reverse=True)
    top_pnl = sorted_outcomes[0].net_pnl if sorted_outcomes else Decimal("0")
    total_net = stat.metrics["net_pnl"]
    top_trade_share = float(top_pnl / total_net) if total_net > 0 else None
    profitable_months = sum(1 for m in monthly.values() if m["net_pnl"] > 0)

    payload = {
        "result": result,
        "walk_forward": wf,
        "monthly": monthly,
        "top_trade_share_of_net": top_trade_share,
        "profitable_months": profitable_months,
        "month_count": len(monthly),
    }
    (DOCS / "_phase7b_prev_day_breakdown_candidate.json").write_text(
        json.dumps(to_jsonable(payload), indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Phase 7B - prev_day_breakdown_v1 Candidate Report",
        "",
        "## Strategy",
        "",
        "- Short-only prior-day-low breakdown continuation.",
        "- Timeframe: 1h.",
        "- Risk used for validation: 0.25% per trade.",
        "- Entry starts on the candle after the final breakdown candle.",
        "- Stop: 0.75 ATR above entry. Target: 4.5 ATR below entry. Max hold: 12h.",
        "- Sessions: Asia, London, London-NY overlap, wind-down. NY solo blocked.",
        "- Volume filter: volume z-score >= 2.0.",
        "",
        "## Authoritative Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Signals | {stat.signals_fired} |",
        f"| Approved | {stat.approved} |",
        f"| Trades | {stat.metrics['trade_count']} |",
        f"| Win rate | {stat.metrics['win_rate']:.1%} |",
        f"| Expectancy R | {stat.metrics['expectancy_r']:.3f} |",
        f"| Profit factor | {stat.metrics['profit_factor']:.3f} |",
        f"| Net PnL | ${float(stat.metrics['net_pnl']):+,.2f} |",
        f"| Fee share of gross | {stat.metrics['fee_share_of_gross']:.1%} |",
        f"| Max drawdown R | {float(stat.metrics['max_drawdown_r']):.2f} |",
        "",
        "## Walk-Forward",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Windows | {wf.aggregate_metrics['window_count']} |",
        f"| Test trades | {wf.aggregate_metrics['trade_count']} |",
        f"| Aggregate expectancy R | {wf.aggregate_metrics['expectancy_r']:.3f} |",
        f"| Aggregate net PnL | ${float(wf.aggregate_metrics['net_pnl']):+,.2f} |",
        f"| Profitable windows | {wf.aggregate_metrics['profitable_windows']} |",
        "",
        "## Monthly Concentration",
        "",
        "| Month | Trades | Expectancy R | Net PnL |",
        "|---|---:|---:|---:|",
    ]
    for month, metrics in monthly.items():
        exp = metrics["expectancy_r"]
        exp_text = f"{exp:.3f}" if exp is not None else "N/A"
        lines.append(
            f"| {month} | {metrics['trade_count']} | "
            f"{exp_text} | ${float(metrics['net_pnl']):+,.2f} |"
        )
    lines.extend(
        [
            "",
            "## Concentration Checks",
            "",
            f"- Profitable months: {profitable_months}/{len(monthly)}.",
            f"- Largest winning trade share of total net PnL: {top_trade_share:.1%}.",
            "",
            "## Decision",
            "",
            "Do not promote to live or micro-live. This is a valid Phase 8 paper-only candidate if it is explicitly treated as low-frequency and monitored for 6-8 weeks. It does not meet the default 300-trade historical sample rule.",
        ]
    )
    (DOCS / "phase7b_prev_day_breakdown_candidate_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    print("Candidate report written.")


if __name__ == "__main__":
    main()
