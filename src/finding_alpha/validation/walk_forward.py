"""Fixed-parameter walk-forward validation helpers for Phase 7."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from .event_runner import ValidationConfig, ValidationResult, run_event_validation


class WalkForwardWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    train_start: datetime
    train_end: datetime
    validate_start: datetime
    validate_end: datetime
    test_start: datetime
    test_end: datetime


class WalkForwardResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    windows: list[WalkForwardWindow] = Field(default_factory=list)
    test_results: list[ValidationResult] = Field(default_factory=list)
    aggregate_metrics: dict = Field(default_factory=dict)


def build_walk_forward_windows(
    candles: pd.DataFrame,
    train_days: int = 90,
    validate_days: int = 30,
    test_days: int = 30,
    roll_days: int = 30,
) -> list[WalkForwardWindow]:
    if candles.empty:
        return []

    times = pd.to_datetime(candles["open_time"], utc=True)
    start = times.min().to_pydatetime()
    end = times.max().to_pydatetime()
    windows: list[WalkForwardWindow] = []
    cursor = start
    idx = 1

    while True:
        train_start = cursor
        train_end = train_start + timedelta(days=train_days)
        validate_start = train_end
        validate_end = validate_start + timedelta(days=validate_days)
        test_start = validate_end
        test_end = test_start + timedelta(days=test_days)
        if test_start >= end:
            break
        if test_end > end:
            test_end = end
        windows.append(
            WalkForwardWindow(
                index=idx,
                train_start=train_start,
                train_end=train_end,
                validate_start=validate_start,
                validate_end=validate_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
        idx += 1
        cursor = cursor + timedelta(days=roll_days)

    return windows


def run_walk_forward(
    candles: pd.DataFrame,
    funding: pd.DataFrame | None = None,
    oi: pd.DataFrame | None = None,
    config: ValidationConfig | None = None,
    train_days: int = 90,
    validate_days: int = 30,
    test_days: int = 30,
    roll_days: int = 30,
) -> WalkForwardResult:
    """
    Run fixed-parameter walk-forward test windows.

    Phase 7 does not optimize parameters yet; train/validate windows exist as
    the evidence boundary, and the frozen current strategy versions are scored
    only on each test window.
    """
    cfg = config or ValidationConfig()
    windows = build_walk_forward_windows(candles, train_days, validate_days, test_days, roll_days)
    results: list[ValidationResult] = []

    for window in windows:
        # Include pre-test history for indicator warmup, but only score signals
        # after warmup inside the sliced set.
        warmup_start = pd.Timestamp(window.test_start) - timedelta(days=20)
        warmup_mask = (
            (pd.to_datetime(candles["open_time"], utc=True) >= warmup_start)
            & (pd.to_datetime(candles["open_time"], utc=True) <= pd.Timestamp(window.test_end))
        )
        test_candles = candles.loc[warmup_mask].reset_index(drop=True)
        if test_candles.empty:
            continue
        window_cfg = cfg.model_copy(
            update={
                "warmup_bars": min(cfg.warmup_bars, max(1, len(test_candles) // 3)),
                "score_start": window.test_start,
                "score_end": window.test_end,
            }
        )
        results.append(run_event_validation(test_candles, funding=funding, oi=oi, config=window_cfg))

    return WalkForwardResult(
        windows=windows,
        test_results=results,
        aggregate_metrics=_aggregate_walk_forward(results),
    )


def _aggregate_walk_forward(results: list[ValidationResult]) -> dict:
    total_trades = 0
    weighted_expectancy = Decimal("0")
    total_net = Decimal("0")
    profitable_windows = 0

    for result in results:
        metrics = result.all_metrics
        trades = metrics["trade_count"]
        total_trades += trades
        total_net += metrics["net_pnl"]
        if trades and metrics["expectancy_r"] is not None:
            weighted_expectancy += Decimal(str(metrics["expectancy_r"])) * Decimal(trades)
        if metrics["net_pnl"] > Decimal("0"):
            profitable_windows += 1

    return {
        "window_count": len(results),
        "trade_count": total_trades,
        "expectancy_r": (
            float(weighted_expectancy / Decimal(total_trades)) if total_trades else None
        ),
        "net_pnl": total_net,
        "profitable_windows": profitable_windows,
    }
