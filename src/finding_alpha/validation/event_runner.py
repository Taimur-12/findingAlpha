"""
Phase 7 authoritative event-driven validation runner.

The runner replays final candles through the real Finding Alpha path:
features -> regime -> strategies -> coordinator/risk/portfolio -> simulator.
Signals are generated from candle N and can only fill from candle N+1 onward.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable, Iterable, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from finding_alpha.analytics.metrics import compute_metrics
from finding_alpha.contracts.execution import TradeOutcome
from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.market import CandleEvent
from finding_alpha.contracts.signals import ResearchState, SignalCandidate
from finding_alpha.contracts.trading import PortfolioIntent, RiskDecision
from finding_alpha.features.snapshot import FEATURE_VERSION, build_feature_df, build_snapshot
from finding_alpha.portfolio.agent import PortfolioConfig, size_intent
from finding_alpha.regime.classifier import classify_regime
from finding_alpha.risk.agent import RiskConfig, evaluate
from finding_alpha.risk.state import OpenPosition, RiskState
from finding_alpha.simulation.executor import SimConfig, simulate_trade
from finding_alpha.strategies.liquidity_sweep_v1 import find_signal as sweep_signal
from finding_alpha.strategies.prev_day_breakdown_v1 import find_signal as breakdown_signal
from finding_alpha.strategies.squeeze_v1 import find_signal as squeeze_signal
from finding_alpha.strategies.trend_pullback_v1 import find_signal as pullback_signal


StrategyFn = Callable[[FeatureSnapshot, RegimeState, pd.Series, datetime], Optional[SignalCandidate]]


def _sweep_adapter(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    row: pd.Series,
    now: datetime,
) -> Optional[SignalCandidate]:
    return sweep_signal(snapshot, regime, float(row["high"]), float(row["low"]), now)


def _squeeze_adapter(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    row: pd.Series,
    now: datetime,
) -> Optional[SignalCandidate]:
    return squeeze_signal(snapshot, regime, now)


def _pullback_adapter(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    row: pd.Series,
    now: datetime,
) -> Optional[SignalCandidate]:
    return pullback_signal(snapshot, regime, now)


def _breakdown_adapter(
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    row: pd.Series,
    now: datetime,
) -> Optional[SignalCandidate]:
    return breakdown_signal(snapshot, regime, now)


STRATEGIES: dict[str, StrategyFn] = {
    "liquidity_sweep_v1": _sweep_adapter,
    "squeeze_v1": _squeeze_adapter,
    "trend_pullback_v1": _pullback_adapter,
    "prev_day_breakdown_v1": _breakdown_adapter,
}


class ValidationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    venue: str = "bybit"
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    initial_equity: Decimal = Decimal("10000")
    warmup_bars: int = 220
    one_position_at_a_time: bool = True
    use_signal_horizon_as_max_hold: bool = True
    feature_version: str = FEATURE_VERSION
    strategy_ids: tuple[str, ...] = tuple(STRATEGIES.keys())
    score_start: datetime | None = None
    score_end: datetime | None = None
    portfolio_config: PortfolioConfig = PortfolioConfig()
    risk_config: RiskConfig = RiskConfig(max_open_positions=1)
    sim_config: SimConfig = SimConfig()


class StrategyStats(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    signals_fired: int = 0
    approved: int = 0
    sized_rejected: int = 0
    risk_rejected: int = 0
    coordinator_rejected: int = 0
    entry_not_filled: int = 0
    outcomes: list[TradeOutcome] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    by_regime: dict[str, dict] = Field(default_factory=dict)
    by_session: dict[str, dict] = Field(default_factory=dict)
    rejection_reasons: dict[str, int] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: ValidationConfig
    start: datetime
    end: datetime
    bars_seen: int
    final_equity: Decimal
    peak_equity: Decimal
    strategy_stats: dict[str, StrategyStats]
    all_metrics: dict
    no_lookahead: dict
    notes: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class _ActiveTrade:
    outcome: TradeOutcome

    @property
    def risk_position(self) -> OpenPosition:
        return OpenPosition(
            symbol=self.outcome.symbol,
            side=self.outcome.side,
            risk_amount=self.outcome.initial_risk_amount,
        )


def run_event_validation(
    candles: pd.DataFrame,
    funding: pd.DataFrame | None = None,
    oi: pd.DataFrame | None = None,
    config: ValidationConfig | None = None,
    research: ResearchState | None = None,
    no_lookahead_indices: Iterable[int] | None = None,
) -> ValidationResult:
    """Run a Phase 7 event-driven validation over a candle DataFrame."""
    cfg = config or ValidationConfig()
    _validate_strategy_ids(cfg.strategy_ids)

    fdf = build_feature_df(candles, funding=funding, oi=oi)
    for col in ("open", "high", "low", "close", "volume", "quote_volume"):
        if col in fdf.columns:
            fdf[col] = pd.to_numeric(fdf[col], errors="coerce")

    if fdf.empty:
        raise ValueError("candles cannot be empty")
    if len(fdf) <= cfg.warmup_bars + 1:
        raise ValueError("not enough candles after warmup for event validation")

    stats = {sid: StrategyStats() for sid in cfg.strategy_ids}
    outcome_context: dict[str, tuple[str, str]] = {}
    all_outcomes: list[TradeOutcome] = []
    active: list[_ActiveTrade] = []

    equity = cfg.initial_equity
    peak_equity = cfg.initial_equity
    daily_start_equity = cfg.initial_equity
    current_day: Optional[datetime.date] = None

    for i in range(cfg.warmup_bars, len(fdf) - 1):
        row = fdf.iloc[i]
        decision_ts = _decision_ts(row, cfg.timeframe)
        if current_day != decision_ts.date():
            current_day = decision_ts.date()
            daily_start_equity = equity

        settled, active = _settle_active(active, decision_ts)
        if settled:
            equity += sum((o.net_pnl for o in settled), Decimal("0"))
            peak_equity = max(peak_equity, equity)

        candle = _candle_event(row, cfg, decision_ts)
        if not candle.is_final:
            continue
        if cfg.score_start is not None and decision_ts < cfg.score_start:
            continue
        if cfg.score_end is not None and decision_ts > cfg.score_end:
            continue

        snapshot = build_snapshot(
            fdf,
            cfg.venue,
            cfg.symbol,
            cfg.timeframe,
            feature_version=cfg.feature_version,
            row_idx=i,
        ).model_copy(update={"ts": decision_ts})
        regime = classify_regime(snapshot).model_copy(update={"classified_at": decision_ts})

        signals = _collect_signals(cfg, snapshot, regime, row, decision_ts, stats)
        if not signals:
            continue

        risk_state = RiskState(
            equity=equity,
            peak_equity=peak_equity,
            daily_start_equity=daily_start_equity,
            open_positions=[trade.risk_position for trade in active],
        )
        approved = _coordinate_with_audit(
            signals=signals,
            equity=equity,
            risk_state=risk_state,
            snapshot=snapshot,
            research=research,
            portfolio_config=cfg.portfolio_config,
            risk_config=cfg.risk_config,
            now=decision_ts,
            stats=stats,
            use_signal_horizon=cfg.use_signal_horizon_as_max_hold,
        )

        future_df = fdf.iloc[i + 1 :].reset_index(drop=True)
        for signal, intent, _decision in approved:
            outcome = simulate_trade(
                intent,
                future_df,
                cfg.sim_config,
                signal.strategy_id,
                signal.strategy_version,
                signal.feature_version,
                cfg.timeframe,
                decision_ts,
            )
            if outcome is None:
                stats[signal.strategy_id].entry_not_filled += 1
                continue

            stats[signal.strategy_id].outcomes.append(outcome)
            all_outcomes.append(outcome)
            outcome_context[outcome.outcome_id] = (regime.regime, _session_name(decision_ts))
            active.append(_ActiveTrade(outcome=outcome))

    # Settle remaining outcomes so final equity reflects every simulated trade.
    remaining = [trade.outcome for trade in active]
    if remaining:
        equity += sum((o.net_pnl for o in remaining), Decimal("0"))
        peak_equity = max(peak_equity, equity)

    _finalize_stats(stats, outcome_context)

    lookahead = verify_no_lookahead(
        candles,
        funding,
        oi,
        cfg,
        indices=no_lookahead_indices,
    )

    start = pd.Timestamp(fdf.iloc[cfg.warmup_bars]["open_time"]).to_pydatetime()
    end = pd.Timestamp(fdf.iloc[-1]["open_time"]).to_pydatetime()
    return ValidationResult(
        config=cfg,
        start=start,
        end=end,
        bars_seen=len(fdf) - cfg.warmup_bars,
        final_equity=equity.quantize(Decimal("0.01")),
        peak_equity=peak_equity.quantize(Decimal("0.01")),
        strategy_stats=stats,
        all_metrics=compute_metrics(all_outcomes),
        no_lookahead=lookahead,
        notes=[
            "Signals generated from candle N are simulated only on candle N+1 or later.",
            "Open simulated positions are kept active until their exit_ts and block new entries under the risk policy.",
        ],
    )


def verify_no_lookahead(
    candles: pd.DataFrame,
    funding: pd.DataFrame | None,
    oi: pd.DataFrame | None,
    config: ValidationConfig | None = None,
    indices: Iterable[int] | None = None,
) -> dict:
    """
    Recompute selected feature rows on truncated prefixes and compare them with
    the full feature DataFrame. Equality proves later candles did not alter the
    decision-row features for the checked rows.
    """
    cfg = config or ValidationConfig()
    full = build_feature_df(candles, funding=funding, oi=oi)
    if indices is None:
        last = len(full) - 2
        mid = cfg.warmup_bars + max(1, (last - cfg.warmup_bars) // 2)
        indices = [cfg.warmup_bars, mid, last]

    checked_fields = [
        "close", "rsi_14", "ema_20", "ema_50", "ema_200", "atr_14",
        "bb_upper", "bb_lower", "adx_14", "volume_z_score", "funding_rate",
        "oi_value",
    ]
    failures: list[dict] = []
    checked = 0
    for idx in indices:
        if idx < 0 or idx >= len(full):
            continue
        prefix = candles.iloc[: idx + 1].copy()
        prefix_features = build_feature_df(prefix, funding=funding, oi=oi)
        full_row = full.iloc[idx]
        prefix_row = prefix_features.iloc[-1]
        checked += 1
        for field_name in checked_fields:
            if field_name not in full_row.index or field_name not in prefix_row.index:
                continue
            if not _values_equal(full_row[field_name], prefix_row[field_name]):
                failures.append(
                    {
                        "row_idx": idx,
                        "field": field_name,
                        "full": str(full_row[field_name]),
                        "prefix": str(prefix_row[field_name]),
                    }
                )

    return {
        "passed": not failures,
        "checked_rows": checked,
        "checked_fields": checked_fields,
        "failures": failures,
    }


def _coordinate_with_audit(
    signals: list[SignalCandidate],
    equity: Decimal,
    risk_state: RiskState,
    snapshot: FeatureSnapshot,
    research: Optional[ResearchState],
    portfolio_config: PortfolioConfig,
    risk_config: RiskConfig,
    now: datetime,
    stats: dict[str, StrategyStats],
    use_signal_horizon: bool,
) -> list[tuple[SignalCandidate, PortfolioIntent, RiskDecision]]:
    if research is not None and not research.is_expired and research.is_hard_block:
        for signal in signals:
            stats[signal.strategy_id].risk_rejected += 1
            _inc_reason(stats[signal.strategy_id], "RISK_RESEARCH_HARD_BLOCK")
        return []

    ranked = sorted(signals, key=lambda s: s.base_confidence, reverse=True)
    approved: list[tuple[SignalCandidate, PortfolioIntent, RiskDecision]] = []
    seen: set[tuple[str, str]] = set()
    running_risk = risk_state.total_open_risk

    for signal in ranked:
        stat = stats[signal.strategy_id]
        key = (signal.symbol, signal.side)
        if key in seen:
            stat.coordinator_rejected += 1
            _inc_reason(stat, "COORDINATOR_DUPLICATE_SYMBOL_SIDE")
            continue

        intent = size_intent(signal, equity, portfolio_config, now)
        if intent is None:
            stat.sized_rejected += 1
            _inc_reason(stat, "PORTFOLIO_SIZING_REJECTED")
            continue
        if use_signal_horizon:
            intent = intent.model_copy(update={"max_hold_minutes": signal.expected_horizon_minutes})

        projected_heat = (running_risk + intent.risk_amount) / equity
        if projected_heat > risk_config.max_portfolio_heat_pct:
            stat.risk_rejected += 1
            _inc_reason(stat, "RISK_PORTFOLIO_HEAT")
            continue

        decision = evaluate(intent, risk_state, snapshot, research, risk_config, now)
        if not decision.is_approved:
            stat.risk_rejected += 1
            for code in decision.reason_codes:
                _inc_reason(stat, code)
            continue

        stat.approved += 1
        approved.append((signal, intent, decision))
        seen.add(key)
        running_risk += intent.risk_amount

    return approved


def _collect_signals(
    cfg: ValidationConfig,
    snapshot: FeatureSnapshot,
    regime: RegimeState,
    row: pd.Series,
    now: datetime,
    stats: dict[str, StrategyStats],
) -> list[SignalCandidate]:
    signals: list[SignalCandidate] = []
    for sid in cfg.strategy_ids:
        signal = STRATEGIES[sid](snapshot, regime, row, now)
        if signal is not None:
            stats[sid].signals_fired += 1
            signals.append(signal)
    return signals


def _finalize_stats(
    stats: dict[str, StrategyStats],
    outcome_context: dict[str, tuple[str, str]],
) -> None:
    for stat in stats.values():
        stat.metrics = compute_metrics(stat.outcomes)
        by_regime: dict[str, list[TradeOutcome]] = defaultdict(list)
        by_session: dict[str, list[TradeOutcome]] = defaultdict(list)
        for outcome in stat.outcomes:
            regime, session = outcome_context.get(outcome.outcome_id, ("unknown", "unknown"))
            by_regime[regime].append(outcome)
            by_session[session].append(outcome)
        stat.by_regime = {
            regime: _compact_metrics(compute_metrics(outcomes))
            for regime, outcomes in sorted(by_regime.items())
        }
        stat.by_session = {
            session: _compact_metrics(compute_metrics(outcomes))
            for session, outcomes in sorted(by_session.items())
        }


def _compact_metrics(metrics: dict) -> dict:
    return {
        "trade_count": metrics["trade_count"],
        "win_rate": metrics["win_rate"],
        "expectancy_r": metrics["expectancy_r"],
        "profit_factor": metrics["profit_factor"],
        "net_pnl": metrics["net_pnl"],
    }


def _settle_active(
    active: list[_ActiveTrade],
    now: datetime,
) -> tuple[list[TradeOutcome], list[_ActiveTrade]]:
    settled: list[TradeOutcome] = []
    still_active: list[_ActiveTrade] = []
    for trade in active:
        if trade.outcome.exit_ts <= now:
            settled.append(trade.outcome)
        else:
            still_active.append(trade)
    return settled, still_active


def _candle_event(row: pd.Series, cfg: ValidationConfig, decision_ts: datetime) -> CandleEvent:
    open_ts = _ensure_utc(pd.Timestamp(row["open_time"]).to_pydatetime())
    close_ts = _ensure_utc(pd.Timestamp(row.get("close_time", decision_ts)).to_pydatetime())
    return CandleEvent(
        venue=cfg.venue,
        symbol=cfg.symbol,
        timeframe=cfg.timeframe,
        open_time=open_ts,
        close_time=close_ts,
        open=Decimal(str(row["open"])),
        high=Decimal(str(row["high"])),
        low=Decimal(str(row["low"])),
        close=Decimal(str(row["close"])),
        volume=Decimal(str(row.get("volume", "0"))),
        quote_volume=Decimal(str(row.get("quote_volume", "0"))),
        is_final=bool(row.get("is_final", True)),
    )


def _decision_ts(row: pd.Series, timeframe: str) -> datetime:
    if "close_time" in row.index and not pd.isna(row["close_time"]):
        return _ensure_utc(pd.Timestamp(row["close_time"]).to_pydatetime())
    open_ts = _ensure_utc(pd.Timestamp(row["open_time"]).to_pydatetime())
    return open_ts + timedelta(minutes=_timeframe_minutes(timeframe))


def _timeframe_minutes(timeframe: str) -> int:
    if timeframe.endswith("m"):
        return int(timeframe[:-1])
    if timeframe.endswith("h"):
        return int(timeframe[:-1]) * 60
    return 60


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


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _values_equal(a, b) -> bool:
    if pd.isna(a) and pd.isna(b):
        return True
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return str(a) == str(b)


def _inc_reason(stat: StrategyStats, reason: str) -> None:
    counts = Counter(stat.rejection_reasons)
    counts[reason] += 1
    stat.rejection_reasons = dict(counts)


def _validate_strategy_ids(strategy_ids: tuple[str, ...]) -> None:
    unknown = set(strategy_ids) - set(STRATEGIES)
    if unknown:
        raise ValueError(f"Unknown strategies: {sorted(unknown)}")
