"""Check regime distribution and pullback long/short split."""
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from finding_alpha.analytics.metrics import compute_metrics
from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.features.snapshot import build_feature_df, build_snapshot
from finding_alpha.portfolio.agent import PortfolioConfig
from finding_alpha.regime.classifier import classify_regime
from finding_alpha.risk.agent import RiskConfig
from finding_alpha.validation.event_runner import ValidationConfig, run_event_validation

DATA = ROOT / "data"
candles = load_candles(DATA, "bybit", "BTCUSDT", "1h")
funding = load_funding(DATA, "bybit", "BTCUSDT")
oi = load_open_interest(DATA, "bybit", "BTCUSDT", "1h")

# Build feature df and compute regime distribution
feature_df = build_feature_df(candles, funding, oi)
print(f"Total bars: {len(feature_df)}")

regimes = Counter()
for i in range(220, len(feature_df)):  # skip warmup
    row = feature_df.iloc[i]
    snapshot = build_snapshot(feature_df, "bybit", "BTCUSDT", "1h", row_idx=i)
    regime = classify_regime(snapshot)
    regimes[regime.regime] += 1

print("\nRegime distribution:")
total = sum(regimes.values())
for r, c in sorted(regimes.items(), key=lambda x: -x[1]):
    print(f"  {r:25s}  {c:5d}  ({c/total:.1%})")

# Run pullback solo and split by side
cfg = ValidationConfig(
    strategy_ids=("trend_pullback_v1",),
    portfolio_config=PortfolioConfig(risk_pct=Decimal("0.0025"), max_hold_minutes=720),
    risk_config=RiskConfig(daily_loss_limit_pct=Decimal("0.01"), max_drawdown_pct=Decimal("0.10"), max_open_positions=1),
)
result = run_event_validation(candles, funding, oi, cfg)
stat = result.strategy_stats["trend_pullback_v1"]
outcomes = stat.outcomes

long_outcomes = [o for o in outcomes if o.side == "long"]
short_outcomes = [o for o in outcomes if o.side == "short"]

print(f"\nPullback total: {len(outcomes)}")
if long_outcomes:
    lm = compute_metrics(long_outcomes)
    print(f"  LONG:  {len(long_outcomes):4d} trades  win={float(lm.get('win_rate',0)):.1%}  "
          f"exp_r={float(lm.get('expectancy_r',0) or 0):.4f}  PF={float(lm.get('profit_factor',0)):.3f}")
if short_outcomes:
    sm = compute_metrics(short_outcomes)
    print(f"  SHORT: {len(short_outcomes):4d} trades  win={float(sm.get('win_rate',0)):.1%}  "
          f"exp_r={float(sm.get('expectancy_r',0) or 0):.4f}  PF={float(sm.get('profit_factor',0)):.3f}")
