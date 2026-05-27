"""
Phase 7C probe — prev_day_breakout_v1 (bidirectional).

Tests two configs back-to-back:
  A) 1h BTCUSDT — 2024-05-27 to 2026-05-27
  B) 15m BTCUSDT — same date range

Promotion gate (must pass ALL):
  - Trade count >= 300
  - Profit factor >= 1.25
  - Expectancy R > 0
  - Walk-forward profitable windows >= 50%

Usage:
    python notebooks/phase7c_probe.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
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


def _run_config(timeframe: str) -> dict:
    candles = load_candles(DATA, "bybit", "BTCUSDT", timeframe)
    funding = load_funding(DATA, "bybit", "BTCUSDT")
    # OI only available at 1h; fall back for other timeframes
    try:
        oi = load_open_interest(DATA, "bybit", "BTCUSDT", timeframe)
    except FileNotFoundError:
        oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

    cfg = ValidationConfig(
        timeframe=timeframe,
        strategy_ids=("prev_day_breakout_v1",),
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
    stat = result.strategy_stats["prev_day_breakout_v1"]
    outcomes = stat.outcomes

    by_month: dict = defaultdict(list)
    for o in outcomes:
        by_month[o.entry_ts.strftime("%Y-%m")].append(o)
    monthly = {m: compute_metrics(v) for m, v in sorted(by_month.items())}

    long_outcomes = [o for o in outcomes if o.side == "long"]
    short_outcomes = [o for o in outcomes if o.side == "short"]

    return {
        "timeframe": timeframe,
        "stat": stat,
        "metrics": stat.metrics,
        "wf": wf,
        "monthly": monthly,
        "long_metrics": compute_metrics(long_outcomes) if long_outcomes else {},
        "short_metrics": compute_metrics(short_outcomes) if short_outcomes else {},
        "long_count": len(long_outcomes),
        "short_count": len(short_outcomes),
    }


def _gate_check(r: dict) -> tuple[bool, list[str]]:
    m = r["metrics"]
    wf_agg = r["wf"].aggregate_metrics
    issues = []
    tc = m.get("trade_count", 0)
    pf = m.get("profit_factor", 0)
    exp = m.get("expectancy_r")
    pw = wf_agg.get("profitable_windows", 0)
    wc = wf_agg.get("window_count", 1)
    if tc < 300:
        issues.append(f"trade_count {tc} < 300")
    if float(pf) < 1.25:
        issues.append(f"profit_factor {float(pf):.3f} < 1.25")
    if exp is None or float(exp) <= 0:
        issues.append(f"expectancy_r {float(exp) if exp else 'N/A'} <= 0")
    if wc > 0 and pw / wc < 0.50:
        issues.append(f"profitable_windows {pw}/{wc} = {pw/wc:.0%} < 50%")
    return len(issues) == 0, issues


def _print_config(r: dict) -> None:
    tf = r["timeframe"]
    m = r["metrics"]
    stat = r["stat"]
    wf_agg = r["wf"].aggregate_metrics
    passes, issues = _gate_check(r)

    print(f"\n{'='*60}")
    print(f"  prev_day_breakout_v1  [{tf}]")
    print(f"{'='*60}")
    print(f"  Signals fired:  {stat.signals_fired}")
    print(f"  Approved:       {stat.approved}")
    print(f"  Trades:         {m.get('trade_count', 0)}  "
          f"(long={r['long_count']}  short={r['short_count']})")
    print(f"  Win rate:       {float(m.get('win_rate', 0)):.1%}")
    print(f"  Expectancy R:   {float(m.get('expectancy_r', 0)):.4f}")
    print(f"  Profit factor:  {float(m.get('profit_factor', 0)):.3f}")
    print(f"  Net PnL:        ${float(m.get('net_pnl', 0)):+,.2f}")
    print(f"  Fee share:      {float(m.get('fee_share_of_gross', 0)):.1%}")
    print(f"  Max DD (R):     {float(m.get('max_drawdown_r', 0)):.2f}")
    print()
    print(f"  Walk-forward:   {wf_agg.get('window_count')} windows  "
          f"profitable={wf_agg.get('profitable_windows')}  "
          f"exp_r={float(wf_agg.get('expectancy_r', 0)):.4f}")
    print()
    print(f"  LONG  — trades={r['long_count']}  "
          f"exp_r={float(r['long_metrics'].get('expectancy_r', 0)):.4f}  "
          f"pf={float(r['long_metrics'].get('profit_factor', 0)):.3f}")
    print(f"  SHORT — trades={r['short_count']}  "
          f"exp_r={float(r['short_metrics'].get('expectancy_r', 0)):.4f}  "
          f"pf={float(r['short_metrics'].get('profit_factor', 0)):.3f}")
    print()
    print(f"  GATE: {'PASS' if passes else 'FAIL'}")
    if not passes:
        for issue in issues:
            print(f"    - {issue}")
    print()
    print("  Monthly breakdown:")
    print(f"  {'Month':<10} {'Trades':>7} {'Exp R':>9} {'Net PnL':>12}")
    for month, mm in r["monthly"].items():
        exp = mm.get("expectancy_r")
        exp_str = f"{float(exp):.3f}" if exp is not None else "  N/A"
        print(f"  {month:<10} {mm.get('trade_count',0):>7} {exp_str:>9} "
              f"  ${float(mm.get('net_pnl',0)):>+10,.2f}")


def main() -> None:
    print("Phase 7C Probe — prev_day_breakout_v1 (bidirectional)")
    print("Running 1h config...")
    r1h = _run_config("1h")

    r15m = None
    candles_15m = load_candles(DATA, "bybit", "BTCUSDT", "15m")
    if candles_15m is not None and not candles_15m.empty:
        print("Running 15m config...")
        r15m = _run_config("15m")
    else:
        print("15m data not available, skipping.")

    _print_config(r1h)
    if r15m is not None:
        _print_config(r15m)

    # Save JSON for later analysis
    payload: dict = {"1h": to_jsonable(r1h["metrics"])}
    if r15m is not None:
        payload["15m"] = to_jsonable(r15m["metrics"])
    (DOCS / "_phase7c_probe_results.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    print("\nResult JSON written to docs/current/_phase7c_probe_results.json")

    # Final verdict
    passes_1h, _ = _gate_check(r1h)
    passes_15m = False
    if r15m is not None:
        passes_15m, _ = _gate_check(r15m)

    print("\n" + "="*60)
    print("  VERDICT")
    print("="*60)
    if passes_1h:
        print("  PROMOTE: prev_day_breakout_v1 @ 1h passes all gates.")
    elif passes_15m:
        print("  PROMOTE: prev_day_breakout_v1 @ 15m passes all gates.")
    else:
        print("  NO PROMOTE: neither config passes all gates.")
        print("  -> Investigate parameter variants (wider stop, lower vol filter)")
        print("    or try a different strategy family.")
    print("="*60)


if __name__ == "__main__":
    main()
