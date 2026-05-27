"""
Analytics — compute summary metrics from a list of TradeOutcome objects.

compute_metrics(outcomes) → dict

Returned keys:
  trade_count, win_count, loss_count, win_rate,
  expectancy_r (mean R), median_r, avg_r,
  gross_pnl, total_fees, net_pnl,
  profit_factor,
  max_drawdown_r,         <- largest peak-to-trough in cumulative R
  fee_share_of_gross,     <- total_fees / gross_pnl (when gross_pnl > 0)
  by_exit_reason,         <- {reason: count}
  by_strategy,            <- {strategy_id: {trade_count, win_rate, expectancy_r}}
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from finding_alpha.contracts.execution import TradeOutcome


def compute_metrics(outcomes: list[TradeOutcome]) -> dict[str, Any]:
    if not outcomes:
        return {
            "trade_count": 0, "win_count": 0, "loss_count": 0,
            "win_rate": None, "expectancy_r": None, "median_r": None,
            "avg_r": None, "gross_pnl": Decimal("0"), "total_fees": Decimal("0"),
            "net_pnl": Decimal("0"), "profit_factor": None,
            "max_drawdown_r": Decimal("0"), "fee_share_of_gross": None,
            "by_exit_reason": {}, "by_strategy": {},
        }

    r_multiples = [float(o.r_multiple) for o in outcomes if o.r_multiple is not None]
    wins   = [r for r in r_multiples if r > 0]
    losses = [r for r in r_multiples if r <= 0]

    gross_pnl  = sum((o.gross_pnl for o in outcomes), Decimal("0"))
    total_fees = sum((o.total_fees for o in outcomes), Decimal("0"))
    net_pnl    = sum((o.net_pnl    for o in outcomes), Decimal("0"))

    win_count  = len(wins)
    loss_count = len(losses)
    trade_count = len(outcomes)

    win_rate    = win_count / trade_count if trade_count else None
    avg_r       = sum(r_multiples) / len(r_multiples) if r_multiples else None
    median_r    = _median(r_multiples)
    expectancy_r = avg_r

    gross_wins   = sum(r for r in r_multiples if r > 0)
    gross_losses = abs(sum(r for r in r_multiples if r < 0))
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else None

    max_dd_r = _max_drawdown(r_multiples)

    fee_share = (
        float(total_fees) / float(gross_pnl)
        if gross_pnl > Decimal("0") else None
    )

    by_exit_reason: dict[str, int] = {}
    for o in outcomes:
        by_exit_reason[o.exit_reason] = by_exit_reason.get(o.exit_reason, 0) + 1

    by_strategy: dict[str, dict] = {}
    for o in outcomes:
        sid = o.strategy_id
        if sid not in by_strategy:
            by_strategy[sid] = {"outcomes": []}
        by_strategy[sid]["outcomes"].append(o)
    for sid, d in by_strategy.items():
        by_strategy[sid] = _strategy_summary(d["outcomes"])

    return {
        "trade_count": trade_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": win_rate,
        "expectancy_r": expectancy_r,
        "median_r": median_r,
        "avg_r": avg_r,
        "gross_pnl": gross_pnl,
        "total_fees": total_fees,
        "net_pnl": net_pnl,
        "profit_factor": profit_factor,
        "max_drawdown_r": Decimal(f"{max_dd_r:.4f}"),
        "fee_share_of_gross": fee_share,
        "by_exit_reason": by_exit_reason,
        "by_strategy": by_strategy,
    }


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2


def _max_drawdown(r_multiples: list[float]) -> float:
    if not r_multiples:
        return 0.0
    peak = 0.0
    cumulative = 0.0
    max_dd = 0.0
    for r in r_multiples:
        cumulative += r
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _strategy_summary(outcomes: list[TradeOutcome]) -> dict:
    rs = [float(o.r_multiple) for o in outcomes if o.r_multiple is not None]
    wins = [r for r in rs if r > 0]
    return {
        "trade_count": len(outcomes),
        "win_rate": len(wins) / len(outcomes) if outcomes else None,
        "expectancy_r": sum(rs) / len(rs) if rs else None,
    }
