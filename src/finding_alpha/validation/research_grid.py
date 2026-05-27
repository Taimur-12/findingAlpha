"""Fast Phase 7B research grid using the Phase 7 fill model."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

import pandas as pd

from finding_alpha.analytics.metrics import compute_metrics
from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.features.snapshot import build_feature_df, build_snapshot
from finding_alpha.portfolio.agent import PortfolioConfig, size_intent
from finding_alpha.regime.classifier import classify_regime
from finding_alpha.simulation.executor import SimConfig, simulate_trade


ResearchStrategyFn = Callable[[FeatureSnapshot, RegimeState, pd.Series, datetime], SignalCandidate | None]


@dataclass(frozen=True)
class VariantResult:
    strategy_id: str
    signals: int
    trades: int
    metrics: dict
    by_regime: dict[str, dict]
    by_session: dict[str, dict]


def run_research_grid(
    candles: pd.DataFrame,
    funding: pd.DataFrame | None,
    oi: pd.DataFrame | None,
    strategies: dict[str, ResearchStrategyFn],
    warmup_bars: int = 220,
    venue: str = "bybit",
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    equity: Decimal = Decimal("10000"),
    portfolio_config: PortfolioConfig | None = None,
    sim_config: SimConfig | None = None,
    one_position_at_a_time: bool = True,
) -> list[VariantResult]:
    fdf = build_feature_df(candles, funding=funding, oi=oi)
    for col in ("open", "high", "low", "close", "volume", "quote_volume"):
        if col in fdf.columns:
            fdf[col] = pd.to_numeric(fdf[col], errors="coerce")

    portfolio_cfg = portfolio_config or PortfolioConfig()
    sim_cfg = sim_config or SimConfig()
    results: list[VariantResult] = []
    cached_rows = []
    for i in range(warmup_bars, len(fdf) - 1):
        row = fdf.iloc[i]
        now = _decision_ts(row)
        snapshot = build_snapshot(fdf, venue, symbol, timeframe, row_idx=i).model_copy(update={"ts": now})
        regime = classify_regime(snapshot).model_copy(update={"classified_at": now})
        cached_rows.append((i, row, now, snapshot, regime))

    for strategy_id, strategy_fn in strategies.items():
        outcomes = []
        context: dict[str, tuple[str, str]] = {}
        signals = 0
        active_until: datetime | None = None

        for i, row, now, snapshot, regime in cached_rows:
            if one_position_at_a_time and active_until is not None and now < active_until:
                continue
            signal = strategy_fn(snapshot, regime, row, now)
            if signal is None:
                continue
            signals += 1

            intent = size_intent(signal, equity, portfolio_cfg, now)
            if intent is None:
                continue
            intent = intent.model_copy(update={"max_hold_minutes": signal.expected_horizon_minutes})
            outcome = simulate_trade(
                intent,
                fdf.iloc[i + 1 :].reset_index(drop=True),
                sim_cfg,
                signal.strategy_id,
                signal.strategy_version,
                signal.feature_version,
                timeframe,
                now,
            )
            if outcome is None:
                continue
            outcomes.append(outcome)
            context[outcome.outcome_id] = (regime.regime, _session_name(now))
            active_until = outcome.exit_ts

        metrics = compute_metrics(outcomes)
        results.append(
            VariantResult(
                strategy_id=strategy_id,
                signals=signals,
                trades=metrics["trade_count"],
                metrics=metrics,
                by_regime=_breakdown(outcomes, context, 0),
                by_session=_breakdown(outcomes, context, 1),
            )
        )

    return sorted(
        results,
        key=lambda r: (
            r.metrics["expectancy_r"] if r.metrics["expectancy_r"] is not None else -999,
            r.trades,
        ),
        reverse=True,
    )


def _breakdown(outcomes, context: dict[str, tuple[str, str]], idx: int) -> dict[str, dict]:
    grouped = defaultdict(list)
    for outcome in outcomes:
        grouped[context.get(outcome.outcome_id, ("unknown", "unknown"))[idx]].append(outcome)
    return {
        key: {
            "trade_count": metrics["trade_count"],
            "win_rate": metrics["win_rate"],
            "expectancy_r": metrics["expectancy_r"],
            "profit_factor": metrics["profit_factor"],
            "net_pnl": metrics["net_pnl"],
        }
        for key, metrics in ((key, compute_metrics(vals)) for key, vals in grouped.items())
    }


def _decision_ts(row: pd.Series) -> datetime:
    ts = pd.Timestamp(row["close_time"] if "close_time" in row.index else row["open_time"])
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.to_pydatetime()


def _session_name(ts: datetime) -> str:
    hour = ts.hour
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 13:
        return "london"
    if 13 <= hour < 17:
        return "london_ny_overlap"
    if 17 <= hour < 22:
        return "ny"
    return "wind_down"
