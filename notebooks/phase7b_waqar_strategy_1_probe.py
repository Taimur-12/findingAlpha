"""Probe Waqar Strategy 1 EMA technique on 15m BTCUSDT data.

User hypothesis:
- 15m scalping.
- EMA 55 crossing above EMA 300 marks uptrend.
- EMA 55 crossing below EMA 300 marks downtrend.
- EMA 9, 13, 21, and 55 act as confirmation.

This script tests the literal crossover plus practical scalping variants without
promoting the strategy into the Phase 8 candidate set.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.analytics.metrics import compute_metrics
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.data.storage import load_candles, load_funding, load_open_interest
from finding_alpha.features.snapshot import build_feature_df
from finding_alpha.portfolio.agent import PortfolioConfig, size_intent
from finding_alpha.simulation.executor import SimConfig, simulate_trade
from finding_alpha.validation.reporting import to_jsonable


DOCS = ROOT / "docs" / "current"
STRATEGY_ID = "waqar_strategy_1"
EMA_PERIODS = (9, 13, 21, 55, 300)
RISK_PCT = Decimal("0.0025")
GEOMETRIES = (
    ("scalp_0p75_1p5_90m", 0.75, 1.5, 90),
    ("scalp_1p0_1p5_180m", 1.0, 1.5, 180),
    ("runner_1p0_3p0_360m", 1.0, 3.0, 360),
)


def main() -> None:
    data = ROOT / "data"
    candles = load_candles(data, "bybit", "BTCUSDT", "15m")
    funding = load_funding(data, "bybit", "BTCUSDT")
    oi = load_open_interest(data, "bybit", "BTCUSDT", "1h")

    fdf = build_feature_df(candles, funding=funding, oi=oi)
    close = pd.to_numeric(fdf["close"], errors="coerce")
    for period in EMA_PERIODS:
        fdf[f"ema_{period}"] = close.ewm(
            span=period,
            min_periods=period,
            adjust=False,
        ).mean()
    for col in ("open", "high", "low", "close", "volume", "quote_volume"):
        fdf[col] = pd.to_numeric(fdf[col], errors="coerce")

    variants = {
        "literal_55_300_cross": _literal_cross_signal,
        "fast_9_13_cross_in_55_300_trend": _fast_9_13_cross_signal,
        "aligned_stack_adx20_fast_cross": _adx_stack_fast_cross_signal,
    }

    payload = []
    for name, signal_fn in variants.items():
        for geometry_name, stop_atr, target_atr, horizon_minutes in GEOMETRIES:
            result = _run_variant(
                fdf,
                name,
                geometry_name,
                signal_fn,
                stop_atr,
                target_atr,
                horizon_minutes,
            )
            payload.append(result)

    payload = sorted(
        payload,
        key=lambda row: (
            row["metrics"]["expectancy_r"] if row["metrics"]["expectancy_r"] is not None else -999,
            row["metrics"]["trade_count"],
        ),
        reverse=True,
    )
    (DOCS / "_phase7b_waqar_strategy_1_probe.json").write_text(
        json.dumps(to_jsonable(payload), indent=2),
        encoding="utf-8",
    )
    _write_markdown(payload)
    _print_summary(payload)


def _run_variant(
    fdf: pd.DataFrame,
    variant: str,
    geometry_name: str,
    signal_fn,
    stop_atr: float,
    target_atr: float,
    horizon_minutes: int,
) -> dict:
    outcomes = []
    context: dict[str, tuple[str, str]] = {}
    signals = 0
    active_until: datetime | None = None
    portfolio_config = PortfolioConfig(risk_pct=RISK_PCT, max_hold_minutes=horizon_minutes)
    max_future_bars = max(2, horizon_minutes // 15 + 1)

    for i in range(max(EMA_PERIODS), len(fdf) - 1):
        row = fdf.iloc[i]
        prev = fdf.iloc[i - 1]
        now = _decision_ts(row)
        if active_until is not None and now < active_until:
            continue

        signal = signal_fn(row, prev, now, variant, stop_atr, target_atr, horizon_minutes)
        if signal is None:
            continue
        signals += 1

        intent = size_intent(signal, Decimal("10000"), portfolio_config, now)
        if intent is None:
            continue
        intent = intent.model_copy(update={"max_hold_minutes": signal.expected_horizon_minutes})
        outcome = simulate_trade(
            intent,
            fdf.iloc[i + 1 : i + 1 + max_future_bars].reset_index(drop=True),
            SimConfig(),
            signal.strategy_id,
            signal.strategy_version,
            signal.feature_version,
            "15m",
            now,
        )
        if outcome is None:
            continue
        outcomes.append(outcome)
        context[outcome.outcome_id] = (_ema_regime(row), _session_name(now))
        active_until = outcome.exit_ts

    return {
        "variant": variant,
        "geometry": geometry_name,
        "stop_atr": stop_atr,
        "target_atr": target_atr,
        "horizon_minutes": horizon_minutes,
        "signals": signals,
        "metrics": compute_metrics(outcomes),
        "by_ema_regime": _breakdown(outcomes, context, 0),
        "by_session": _breakdown(outcomes, context, 1),
        "monthly": _monthly(outcomes),
    }


def _literal_cross_signal(
    row: pd.Series,
    prev: pd.Series,
    now: datetime,
    variant: str,
    stop_atr: float,
    target_atr: float,
    horizon_minutes: int,
) -> SignalCandidate | None:
    if not _has_required(row, prev):
        return None
    long_signal = (
        prev["ema_55"] <= prev["ema_300"]
        and row["ema_55"] > row["ema_300"]
        and row["ema_9"] > row["ema_13"] > row["ema_21"] > row["ema_55"]
    )
    short_signal = (
        prev["ema_55"] >= prev["ema_300"]
        and row["ema_55"] < row["ema_300"]
        and row["ema_9"] < row["ema_13"] < row["ema_21"] < row["ema_55"]
    )
    return _build_signal(row, now, variant, long_signal, short_signal, stop_atr, target_atr, horizon_minutes)


def _fast_9_13_cross_signal(
    row: pd.Series,
    prev: pd.Series,
    now: datetime,
    variant: str,
    stop_atr: float,
    target_atr: float,
    horizon_minutes: int,
) -> SignalCandidate | None:
    if not _has_required(row, prev):
        return None
    long_signal = (
        row["ema_55"] > row["ema_300"]
        and prev["ema_9"] <= prev["ema_13"]
        and row["ema_9"] > row["ema_13"] > row["ema_21"] > row["ema_55"]
    )
    short_signal = (
        row["ema_55"] < row["ema_300"]
        and prev["ema_9"] >= prev["ema_13"]
        and row["ema_9"] < row["ema_13"] < row["ema_21"] < row["ema_55"]
    )
    return _build_signal(row, now, variant, long_signal, short_signal, stop_atr, target_atr, horizon_minutes)


def _adx_stack_fast_cross_signal(
    row: pd.Series,
    prev: pd.Series,
    now: datetime,
    variant: str,
    stop_atr: float,
    target_atr: float,
    horizon_minutes: int,
) -> SignalCandidate | None:
    if not _has_required(row, prev):
        return None
    adx = float(row.get("adx_14", 0.0))
    fast_long = prev["ema_9"] <= prev["ema_13"] and row["ema_9"] > row["ema_13"]
    fast_short = prev["ema_9"] >= prev["ema_13"] and row["ema_9"] < row["ema_13"]
    long_stack = row["ema_9"] > row["ema_13"] > row["ema_21"] > row["ema_55"] > row["ema_300"]
    short_stack = row["ema_9"] < row["ema_13"] < row["ema_21"] < row["ema_55"] < row["ema_300"]
    return _build_signal(
        row,
        now,
        variant,
        adx >= 20.0 and fast_long and long_stack,
        adx >= 20.0 and fast_short and short_stack,
        stop_atr,
        target_atr,
        horizon_minutes,
    )


def _build_signal(
    row: pd.Series,
    now: datetime,
    variant: str,
    long_signal: bool,
    short_signal: bool,
    stop_atr: float,
    target_atr: float,
    horizon_minutes: int,
) -> SignalCandidate | None:
    if long_signal == short_signal:
        return None
    close = float(row["close"])
    atr = float(row["atr_14"])
    if atr <= 0:
        return None
    if long_signal:
        stop = close - stop_atr * atr
        target = close + target_atr * atr
        side = "long"
    else:
        stop = close + stop_atr * atr
        target = close - target_atr * atr
        side = "short"
    return SignalCandidate(
        strategy_id=f"{STRATEGY_ID}:{variant}",
        venue="bybit",
        symbol="BTCUSDT",
        timeframe="15m",
        side=side,
        created_at=now,
        expires_at=now + timedelta(minutes=horizon_minutes),
        base_confidence=Decimal("0.55"),
        expected_horizon_minutes=horizon_minutes,
        entry_reference=Decimal(f"{close:.2f}"),
        invalidation_price=Decimal(f"{stop:.2f}"),
        target_prices=[Decimal(f"{target:.2f}")],
        evidence={
            "ema_9": f"{float(row['ema_9']):.2f}",
            "ema_13": f"{float(row['ema_13']):.2f}",
            "ema_21": f"{float(row['ema_21']):.2f}",
            "ema_55": f"{float(row['ema_55']):.2f}",
            "ema_300": f"{float(row['ema_300']):.2f}",
            "atr_14": f"{atr:.2f}",
            "stop_atr": f"{stop_atr:.2f}",
            "target_atr": f"{target_atr:.2f}",
            "horizon_minutes": str(horizon_minutes),
            "variant": variant,
        },
        feature_version="1.0",
        strategy_version="research",
    )


def _has_required(row: pd.Series, prev: pd.Series) -> bool:
    cols = [f"ema_{period}" for period in EMA_PERIODS] + ["atr_14", "close"]
    return not any(pd.isna(row.get(col)) or pd.isna(prev.get(col)) for col in cols)


def _decision_ts(row: pd.Series) -> datetime:
    ts = pd.Timestamp(row["close_time"] if "close_time" in row.index else row["open_time"])
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.to_pydatetime()


def _ema_regime(row: pd.Series) -> str:
    if row["ema_55"] > row["ema_300"]:
        return "ema_uptrend"
    if row["ema_55"] < row["ema_300"]:
        return "ema_downtrend"
    return "ema_flat"


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


def _breakdown(outcomes, context: dict[str, tuple[str, str]], idx: int) -> dict[str, dict]:
    grouped = defaultdict(list)
    for outcome in outcomes:
        grouped[context.get(outcome.outcome_id, ("unknown", "unknown"))[idx]].append(outcome)
    return {
        key: compute_metrics(vals)
        for key, vals in sorted(grouped.items())
    }


def _monthly(outcomes) -> dict[str, dict]:
    grouped = defaultdict(list)
    for outcome in outcomes:
        grouped[outcome.entry_ts.strftime("%Y-%m")].append(outcome)
    return {key: compute_metrics(vals) for key, vals in sorted(grouped.items())}


def _write_markdown(payload: list[dict]) -> None:
    lines = [
        "# Phase 7B - Waqar Strategy 1 EMA Probe",
        "",
        "## Interpretation",
        "",
        "- Timeframe: 15m BTCUSDT Bybit.",
        "- EMA set: 9, 13, 21, 55, 300.",
        "- Literal trend definition: EMA55 crossing above EMA300 marks uptrend; crossing below marks downtrend.",
        "- Validation uses next-candle execution, 0.25% simulated risk, fees/slippage/funding model, and one open position at a time.",
        "- Geometry grid: 0.75-1.5 ATR stop, 1.5-3.0 ATR target, 90-360 minute max hold.",
        "",
        "## Top Variant/Geometry Results",
        "",
        "| Variant | Geometry | Signals | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL | Max DD R | Fee Share |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload[:15]:
        metrics = row["metrics"]
        lines.append(
            f"| {row['variant']} | {row['geometry']} | {row['signals']} | {metrics['trade_count']} | "
            f"{_pct(metrics['win_rate'])} | {_num(metrics['expectancy_r'])} | "
            f"{_num(metrics['profit_factor'])} | ${float(metrics['net_pnl']):+,.2f} | "
            f"{float(metrics['max_drawdown_r']):.2f} | {_pct(metrics['fee_share_of_gross'])} |"
        )
    best = payload[0] if payload else None
    decision = "Rejected."
    if best and best["metrics"]["trade_count"] >= 100 and (best["metrics"]["expectancy_r"] or 0) > 0.20:
        decision = "Research hold only; needs formal event validation and walk-forward before paper consideration."
    lines.extend(
        [
            "",
            "## Decision",
            "",
            decision,
            "",
            "This probe does not alter the Phase 8 recommendation unless a variant clears the same evidence bar as the existing candidate.",
        ]
    )
    (DOCS / "phase7b_waqar_strategy_1_probe.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def _print_summary(payload: list[dict]) -> None:
    for row in payload:
        metrics = row["metrics"]
        print(
            row["variant"],
            row["geometry"],
            "signals", row["signals"],
            "trades", metrics["trade_count"],
            "win", metrics["win_rate"],
            "exp", metrics["expectancy_r"],
            "pf", metrics["profit_factor"],
            "net", metrics["net_pnl"],
            "ddR", metrics["max_drawdown_r"],
        )


def _pct(value) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def _num(value) -> str:
    return "N/A" if value is None else f"{value:.3f}"


if __name__ == "__main__":
    main()
