import sys
from decimal import Decimal
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.validation.event_runner import ValidationConfig, run_event_validation, STRATEGIES

DATA = ROOT / "data"
candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
funding = load_funding(DATA, "bybit", "BTCUSDT")
oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

cfg = ValidationConfig(
    strategy_ids=tuple(STRATEGIES.keys()),
    portfolio_config=PortfolioConfig(risk_pct=Decimal("0.0025"), max_hold_minutes=720),
    risk_config=RiskConfig(daily_loss_limit_pct=Decimal("0.01"), max_drawdown_pct=Decimal("0.10"), max_open_positions=1),
)
result = run_event_validation(candles, funding, oi, cfg)
for sid, stat in sorted(result.strategy_stats.items()):
    m = stat.metrics
    tc = m.get("trade_count", 0)
    pf = float(m.get("profit_factor", 0))
    exp = float(m.get("expectancy_r") or 0)
    print(f"{sid:35s}  signals={stat.signals_fired:4d}  approved={stat.approved:4d}  trades={tc:4d}  PF={pf:.3f}  exp_r={exp:.4f}")
