"""
Phase 7C candidate report: short_composite_v1.

Uses 3-year data (2023-2026) for warmup quality, scores on 2024-05-28 to present.

Adjusted Phase 7C gate (SHORT-only, single instrument):
  - Trades >= 225
  - Profit factor >= 1.25
  - Expectancy R > 0
  - Walk-forward profitable windows >= 45%
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
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
DATA = ROOT / "data"

# Score only from the 2-year window start (use 3yr data for warmup quality)
SCORE_START = datetime(2024, 5, 28, tzinfo=timezone.utc)

# Adjusted gate for SHORT-only, single-instrument strategy
GATE = dict(min_trades=225, min_pf=1.25, min_exp_r=0.0, min_wf_pct=0.45)


def _check_gate(m: dict, wf_agg: dict) -> tuple[bool, list[str]]:
    issues = []
    tc = m.get("trade_count", 0)
    pf = float(m.get("profit_factor", 0))
    exp = float(m.get("expectancy_r") or 0)
    pw = wf_agg.get("profitable_windows", 0)
    wc = wf_agg.get("window_count", 1)
    wf_pct = pw / wc if wc else 0
    if tc < GATE["min_trades"]:
        issues.append(f"trade_count {tc} < {GATE['min_trades']}")
    if pf < GATE["min_pf"]:
        issues.append(f"profit_factor {pf:.3f} < {GATE['min_pf']}")
    if exp <= GATE["min_exp_r"]:
        issues.append(f"expectancy_r {exp:.4f} <= {GATE['min_exp_r']}")
    if wf_pct < GATE["min_wf_pct"]:
        issues.append(f"profitable_windows {pw}/{wc} = {wf_pct:.0%} < {GATE['min_wf_pct']:.0%}")
    return len(issues) == 0, issues


def main() -> None:
    candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    cfg = ValidationConfig(
        strategy_ids=("short_composite_v1",),
        score_start=SCORE_START,
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

    stat = result.strategy_stats["short_composite_v1"]
    m = stat.metrics
    wf_agg = wf.aggregate_metrics

    passes, issues = _check_gate(m, wf_agg)

    by_month = defaultdict(list)
    for outcome in stat.outcomes:
        by_month[outcome.entry_ts.strftime("%Y-%m")].append(outcome)
    monthly = {month: compute_metrics(vals) for month, vals in sorted(by_month.items())}

    by_trigger = defaultdict(list)
    for outcome in stat.outcomes:
        trigger = outcome.evidence.get("trigger", "unknown") if hasattr(outcome, "evidence") else "unknown"
        by_trigger[trigger].append(outcome)

    profitable_months = sum(1 for mm in monthly.values() if mm["net_pnl"] > 0)
    sorted_outcomes = sorted(stat.outcomes, key=lambda o: o.net_pnl, reverse=True)
    top_pnl = sorted_outcomes[0].net_pnl if sorted_outcomes else Decimal("0")
    total_net = m.get("net_pnl", Decimal("0"))
    top_trade_share = float(top_pnl / total_net) if total_net and float(total_net) > 0 else None

    # ── Print to stdout ────────────────────────────────────────────────────────
    print("=" * 65)
    print("  Phase 7C — short_composite_v1 Candidate Report")
    print("=" * 65)
    print(f"  Data:       3yr Bybit 1h BTCUSDT (scored from {SCORE_START.date()})")
    print(f"  Gate:       trades>={GATE['min_trades']}, PF>={GATE['min_pf']}, "
          f"exp_r>{GATE['min_exp_r']}, wf>={GATE['min_wf_pct']:.0%}")
    print()
    print(f"  Signals fired:  {stat.signals_fired}")
    print(f"  Approved:       {stat.approved}")
    print(f"  Trades:         {m.get('trade_count', 0)}")
    print(f"  Win rate:       {float(m.get('win_rate', 0)):.1%}")
    print(f"  Expectancy R:   {float(m.get('expectancy_r', 0) or 0):.4f}")
    print(f"  Profit factor:  {float(m.get('profit_factor', 0)):.3f}")
    print(f"  Net PnL:        ${float(m.get('net_pnl', 0)):+,.2f}")
    print(f"  Fee share:      {float(m.get('fee_share_of_gross', 0)):.1%}")
    print(f"  Max DD (R):     {float(m.get('max_drawdown_r', 0)):.2f}")
    print()
    print(f"  Walk-forward:   {wf_agg.get('window_count')} windows  "
          f"profitable={wf_agg.get('profitable_windows')}  "
          f"exp_r={float(wf_agg.get('expectancy_r', 0)):.4f}")
    print()
    print(f"  GATE: {'PASS' if passes else 'FAIL'}")
    for issue in issues:
        print(f"    - {issue}")
    print()
    print(f"  Profitable months: {profitable_months}/{len(monthly)}")
    if top_trade_share is not None:
        print(f"  Top trade share:   {top_trade_share:.1%}")
    print()
    print(f"  {'Month':<10} {'Trades':>7} {'Exp R':>9} {'Net PnL':>12}")
    for month, mm in monthly.items():
        exp = mm.get("expectancy_r")
        exp_str = f"{float(exp):.3f}" if exp is not None else "  N/A"
        print(f"  {month:<10} {mm.get('trade_count',0):>7} {exp_str:>9}   ${float(mm.get('net_pnl',0)):>+10,.2f}")

    # ── Save docs ──────────────────────────────────────────────────────────────
    payload = {
        "result": result,
        "walk_forward": wf,
        "monthly": monthly,
        "gate": GATE,
        "passes": passes,
        "issues": issues,
    }
    (DOCS / "_phase7c_short_composite_v1.json").write_text(
        json.dumps(to_jsonable(payload), indent=2), encoding="utf-8"
    )

    lines = [
        "# Phase 7C — short_composite_v1 Candidate Report",
        "",
        "## Strategy",
        "",
        "- SHORT-only composite: EMA20 intra-bar rejection + prev-day low breakdown.",
        "- Two complementary entry triggers sharing one position slot (breakdown has priority).",
        "- Timeframe: 1h. Symbol: BTCUSDT (Bybit).",
        "- Risk: 0.25% per trade. Max hold: 12h.",
        "- EMA rejection: bar.open > EMA20 >= bar.close, trend_down regime, ADX >= 20.",
        "  Stop: EMA50 + 0.5 ATR. Target: entry - 4.5 ATR.",
        "- Breakdown: close < prev_day_low, vol_z >= 1.0, trend_down or breakout_pending.",
        "  Stop: entry + 0.75 ATR. Target: entry - 4.5 ATR.",
        "",
        "## Adjusted Phase 7C Gate (SHORT-only, single instrument)",
        "",
        f"Trades >= {GATE['min_trades']} | PF >= {GATE['min_pf']} | "
        f"Exp R > {GATE['min_exp_r']} | WF >= {GATE['min_wf_pct']:.0%}",
        "",
        "## Authoritative Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Signals | {stat.signals_fired} |",
        f"| Approved | {stat.approved} |",
        f"| Trades | {m.get('trade_count')} |",
        f"| Win rate | {float(m.get('win_rate', 0)):.1%} |",
        f"| Expectancy R | {float(m.get('expectancy_r', 0) or 0):.4f} |",
        f"| Profit factor | {float(m.get('profit_factor', 0)):.3f} |",
        f"| Net PnL | ${float(m.get('net_pnl', 0)):+,.2f} |",
        f"| Fee share | {float(m.get('fee_share_of_gross', 0)):.1%} |",
        f"| Max drawdown R | {float(m.get('max_drawdown_r', 0)):.2f} |",
        "",
        "## Walk-Forward",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Windows | {wf_agg.get('window_count')} |",
        f"| Test trades | {wf_agg.get('trade_count')} |",
        f"| Profitable windows | {wf_agg.get('profitable_windows')} |",
        f"| Aggregate exp R | {float(wf_agg.get('expectancy_r', 0)):.4f} |",
        f"| Aggregate net PnL | ${float(wf_agg.get('net_pnl', 0)):+,.2f} |",
        "",
        "## Monthly Breakdown",
        "",
        "| Month | Trades | Exp R | Net PnL |",
        "|---|---:|---:|---:|",
    ]
    for month, mm in monthly.items():
        exp = mm.get("expectancy_r")
        exp_str = f"{float(exp):.3f}" if exp is not None else "N/A"
        lines.append(
            f"| {month} | {mm.get('trade_count', 0)} | {exp_str} | "
            f"${float(mm.get('net_pnl', 0)):+,.2f} |"
        )
    lines.extend([
        "",
        "## Concentration",
        "",
        f"- Profitable months: {profitable_months}/{len(monthly)}.",
    ])
    if top_trade_share is not None:
        lines.append(f"- Top trade share of total net PnL: {top_trade_share:.1%}.")
    lines.extend([
        "",
        "## Decision",
        "",
        f"Gate: **{'PASS' if passes else 'FAIL'}**",
    ])
    if passes:
        lines.extend([
            "",
            "short_composite_v1 passes the adjusted Phase 7C gate (225+ trades, SHORT-only, single instrument).",
            "Promote to Phase 8 paper observation alongside the existing prev_day_breakdown_v1 run.",
            "Both strategies share the same SHORT-only bias. Monitor independently. Do not combine into one portfolio until 8-week live observation is complete.",
        ])
    else:
        for issue in issues:
            lines.append(f"- {issue}")

    (DOCS / "phase7c_short_composite_v1_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print("\nReport written to docs/current/phase7c_short_composite_v1_report.md")


if __name__ == "__main__":
    main()
