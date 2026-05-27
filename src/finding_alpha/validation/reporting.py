"""Report writers for Phase 7 validation output."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .event_runner import ValidationResult
from .walk_forward import WalkForwardResult


def write_json_report(result: ValidationResult, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(result), indent=2), encoding="utf-8")
    return path


def write_markdown_report(
    result: ValidationResult,
    path: Path,
    walk_forward: WalkForwardResult | None = None,
    independent_results: dict[str, ValidationResult] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase 7 - Authoritative Event-Driven Validation Report",
        "",
        f"Generated: {datetime.utcnow().date().isoformat()}",
        f"Dataset: {result.config.venue} {result.config.symbol} {result.config.timeframe}",
        f"Period scored: {result.start.date().isoformat()} to {result.end.date().isoformat()}",
        "",
        "## Validation Rules",
        "",
        "- Candle N can generate a signal only after that candle is final.",
        "- Entry simulation starts at candle N+1, never on the signal candle.",
        "- Open simulated positions remain active until their exit timestamp.",
        "- Same-candle stop/target ambiguity is resolved by stop loss first.",
        "- Position sizing uses floored quantity precision and risk checks before simulation.",
        "",
        "## Combined Portfolio Metrics",
        "",
        _metrics_table(result.all_metrics),
        "",
        "## Strategy Metrics",
        "",
        "| Strategy | Signals | Approved | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL | Max DD R | Entry Misses |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    strategy_source = _strategy_source(result, independent_results)
    for sid, stat in strategy_source.items():
        m = stat.metrics
        lines.append(
            "| "
            + " | ".join(
                [
                    sid,
                    str(stat.signals_fired),
                    str(stat.approved),
                    str(m["trade_count"]),
                    _pct(m["win_rate"]),
                    _num(m["expectancy_r"]),
                    _num(m["profit_factor"]),
                    _money(m["net_pnl"]),
                    _num(m["max_drawdown_r"]),
                    str(stat.entry_not_filled),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Rejection Counts", ""])
    for sid, stat in strategy_source.items():
        lines.append(f"### {sid}")
        if not stat.rejection_reasons:
            lines.append("")
            lines.append("No sizing/risk/coordinator rejections after signal creation.")
            lines.append("")
            continue
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|---|---:|")
        for reason, count in sorted(stat.rejection_reasons.items()):
            lines.append(f"| {reason} | {count} |")
        lines.append("")

    lines.extend(["## Regime Breakdown", ""])
    for sid, stat in strategy_source.items():
        lines.append(f"### {sid}")
        lines.append("")
        lines.append("| Regime | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for regime, m in stat.by_regime.items():
            lines.append(
                f"| {regime} | {m['trade_count']} | {_pct(m['win_rate'])} | "
                f"{_num(m['expectancy_r'])} | {_num(m['profit_factor'])} | {_money(m['net_pnl'])} |"
            )
        lines.append("")

    lines.extend(["## Session Breakdown", ""])
    for sid, stat in strategy_source.items():
        lines.append(f"### {sid}")
        lines.append("")
        lines.append("| Session | Trades | Win Rate | Expectancy R | Profit Factor | Net PnL |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for session, m in stat.by_session.items():
            lines.append(
                f"| {session} | {m['trade_count']} | {_pct(m['win_rate'])} | "
                f"{_num(m['expectancy_r'])} | {_num(m['profit_factor'])} | {_money(m['net_pnl'])} |"
            )
        lines.append("")

    lines.extend(
        [
            "## No-Lookahead Proof",
            "",
            f"Passed: `{result.no_lookahead['passed']}`",
            f"Rows checked: {result.no_lookahead['checked_rows']}",
            "",
        ]
    )
    if result.no_lookahead["failures"]:
        lines.append("| Row | Field | Full | Prefix |")
        lines.append("|---:|---|---:|---:|")
        for failure in result.no_lookahead["failures"]:
            lines.append(
                f"| {failure['row_idx']} | {failure['field']} | "
                f"{failure['full']} | {failure['prefix']} |"
            )
        lines.append("")

    if walk_forward is not None:
        lines.extend(
            [
                "## Walk-Forward Summary",
                "",
                f"Windows: {walk_forward.aggregate_metrics['window_count']}",
                f"Trades: {walk_forward.aggregate_metrics['trade_count']}",
                f"Expectancy R: {_num(walk_forward.aggregate_metrics['expectancy_r'])}",
                f"Net PnL: {_money(walk_forward.aggregate_metrics['net_pnl'])}",
                f"Profitable windows: {walk_forward.aggregate_metrics['profitable_windows']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Promotion Decision",
            "",
            _promotion_decision(strategy_source, result.no_lookahead["passed"]),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return to_jsonable(value.model_dump())
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [to_jsonable(v) for v in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _strategy_source(
    result: ValidationResult,
    independent_results: dict[str, ValidationResult] | None,
) -> dict:
    if not independent_results:
        return result.strategy_stats
    stats = {}
    for sid, independent in independent_results.items():
        stats[sid] = independent.strategy_stats[sid]
    return stats


def _promotion_decision(strategy_stats: dict, no_lookahead_passed: bool) -> str:
    promoted: list[str] = []
    for sid, stat in strategy_stats.items():
        metrics = stat.metrics
        if (
            metrics["trade_count"] >= 300
            and metrics["expectancy_r"] is not None
            and metrics["expectancy_r"] > 0
            and metrics["profit_factor"] is not None
            and metrics["profit_factor"] >= 1.25
            and no_lookahead_passed
        ):
            promoted.append(sid)
    if promoted:
        return "PROMOTE TO PHASE 8 PAPER CANDIDATE: " + ", ".join(promoted)
    return "DO NOT PROMOTE. No strategy meets Phase 7 promotion gates."


def _metrics_table(metrics: dict) -> str:
    rows = [
        ("Trades", metrics["trade_count"]),
        ("Win rate", _pct(metrics["win_rate"])),
        ("Expectancy R", _num(metrics["expectancy_r"])),
        ("Profit factor", _num(metrics["profit_factor"])),
        ("Gross PnL", _money(metrics["gross_pnl"])),
        ("Fees", _money(metrics["total_fees"])),
        ("Net PnL", _money(metrics["net_pnl"])),
        ("Max drawdown R", _num(metrics["max_drawdown_r"])),
        ("Fee share of gross", _pct(metrics["fee_share_of_gross"])),
    ]
    lines = ["| Metric | Value |", "|---|---:|"]
    lines.extend(f"| {name} | {value} |" for name, value in rows)
    return "\n".join(lines)


def _pct(value) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1%}"


def _num(value) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.3f}"


def _money(value) -> str:
    if value is None:
        return "N/A"
    return f"${float(value):+,.2f}"
