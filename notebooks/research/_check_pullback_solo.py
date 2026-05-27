import sys
from decimal import Decimal
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from finding_alpha.analytics.metrics import compute_metrics
from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.validation.event_runner import ValidationConfig, run_event_validation
from finding_alpha.validation.walk_forward import run_walk_forward

DATA = ROOT / "data"
candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
funding = load_funding(DATA, "bybit", "BTCUSDT")
oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

cfg = ValidationConfig(
    strategy_ids=("trend_pullback_v1",),
    portfolio_config=PortfolioConfig(risk_pct=Decimal("0.0025"), max_hold_minutes=720),
    risk_config=RiskConfig(daily_loss_limit_pct=Decimal("0.01"), max_drawdown_pct=Decimal("0.10"), max_open_positions=1),
)
result = run_event_validation(candles, funding, oi, cfg)
wf = run_walk_forward(candles, funding, oi, cfg)
stat = result.strategy_stats["trend_pullback_v1"]
m = stat.metrics
wf_agg = wf.aggregate_metrics

print(f"trend_pullback_v1 (solo, 1h BTCUSDT)")
print(f"  Signals:   {stat.signals_fired}")
print(f"  Approved:  {stat.approved}")
print(f"  Trades:    {m.get('trade_count', 0)}")
print(f"  Win rate:  {float(m.get('win_rate', 0)):.1%}")
print(f"  Exp R:     {float(m.get('expectancy_r', 0) or 0):.4f}")
print(f"  PF:        {float(m.get('profit_factor', 0)):.3f}")
print(f"  Net PnL:   ${float(m.get('net_pnl', 0)):+,.2f}")
print(f"  Max DD R:  {float(m.get('max_drawdown_r', 0)):.2f}")
print(f"  WF:        {wf_agg.get('window_count')} windows, {wf_agg.get('profitable_windows')} profitable, exp_r={float(wf_agg.get('expectancy_r', 0)):.4f}")

# Also read the pullback strategy file to understand it
print()
by_month = defaultdict(list)
for o in stat.outcomes:
    by_month[o.entry_ts.strftime("%Y-%m")].append(o)
monthly = {m: compute_metrics(v) for m, v in sorted(by_month.items())}
print(f"  {'Month':<10} {'Trades':>7} {'Exp R':>9} {'Net PnL':>12}")
for month, mm in monthly.items():
    exp = mm.get("expectancy_r")
    exp_str = f"{float(exp):.3f}" if exp is not None else "  N/A"
    print(f"  {month:<10} {mm.get('trade_count',0):>7} {exp_str:>9}   ${float(mm.get('net_pnl',0)):>+10,.2f}")
