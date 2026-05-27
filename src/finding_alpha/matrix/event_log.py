"""
Matrix event log.
Append-only. Immutable after write. Deterministic replay.
Replaying the same events always produces the same final state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from ..contracts import (
    MarketEvent, CandleEvent, DataQualityEvent,
    FeatureSnapshot, RegimeState,
    SignalCandidate, ResearchState,
    PortfolioIntent, RiskDecision, OrderPlan,
    ExecutionReport, TradeOutcome,
)

# All event types the log can store
AnyEvent = Union[
    MarketEvent, CandleEvent, DataQualityEvent,
    FeatureSnapshot, RegimeState,
    SignalCandidate, ResearchState,
    PortfolioIntent, RiskDecision, OrderPlan,
    ExecutionReport, TradeOutcome,
]

# Maps type name string back to the correct class for deserialization
_TYPE_REGISTRY: dict[str, type] = {
    "MarketEvent": MarketEvent,
    "CandleEvent": CandleEvent,
    "DataQualityEvent": DataQualityEvent,
    "FeatureSnapshot": FeatureSnapshot,
    "RegimeState": RegimeState,
    "SignalCandidate": SignalCandidate,
    "ResearchState": ResearchState,
    "PortfolioIntent": PortfolioIntent,
    "RiskDecision": RiskDecision,
    "OrderPlan": OrderPlan,
    "ExecutionReport": ExecutionReport,
    "TradeOutcome": TradeOutcome,
}


class MatrixEventLog:
    """
    Append-only event log.

    Rules:
    - Events are appended, never modified or deleted.
    - Each event is serialized immediately on append.
    - Replaying the same log file always produces the same sequence.
    - Latest-state projections are maintained in memory for fast reads.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self._events: list[AnyEvent] = []
        self._log_path = log_path

        # Latest-state projections (fast reads)
        self._latest_candle: dict[str, CandleEvent] = {}         # key: venue:symbol:tf
        self._latest_features: dict[str, FeatureSnapshot] = {}   # key: venue:symbol:tf
        self._latest_regime: dict[str, RegimeState] = {}         # key: venue:symbol:tf
        self._latest_research: Optional[ResearchState] = None
        self._open_signals: dict[str, SignalCandidate] = {}      # key: signal_id
        self._risk_decisions: dict[str, RiskDecision] = {}       # key: intent_id
        self._trade_outcomes: list[TradeOutcome] = []
        self._data_quality_events: list[DataQualityEvent] = []

        if log_path and log_path.exists():
            self._load_from_file(log_path)

    def append(self, event: AnyEvent) -> None:
        """Append an event. Immediately persists if a log path is set."""
        self._events.append(event)
        self._update_projections(event)
        if self._log_path:
            self._write_event(event)

    def _update_projections(self, event: AnyEvent) -> None:
        """Update latest-state cache from the new event."""
        if isinstance(event, CandleEvent):
            key = f"{event.venue}:{event.symbol}:{event.timeframe}"
            self._latest_candle[key] = event

        elif isinstance(event, FeatureSnapshot):
            key = f"{event.venue}:{event.symbol}:{event.timeframe}"
            self._latest_features[key] = event

        elif isinstance(event, RegimeState):
            key = f"{event.venue}:{event.symbol}:{event.timeframe}"
            self._latest_regime[key] = event

        elif isinstance(event, ResearchState):
            self._latest_research = event

        elif isinstance(event, SignalCandidate):
            self._open_signals[event.signal_id] = event

        elif isinstance(event, RiskDecision):
            self._risk_decisions[event.intent_id] = event

        elif isinstance(event, TradeOutcome):
            self._trade_outcomes.append(event)
            # Remove the signal from open signals once trade closes
            self._open_signals.pop(event.signal_id, None)

        elif isinstance(event, DataQualityEvent):
            self._data_quality_events.append(event)

    # ── Serialization ──────────────────────────────────────────────────────────

    def _serialize_event(self, event: AnyEvent) -> str:
        data = event.model_dump(mode="json")
        data["_type"] = type(event).__name__
        return json.dumps(data, default=str)

    def _deserialize_event(self, line: str) -> AnyEvent:
        data = json.loads(line)
        type_name = data.pop("_type")
        cls = _TYPE_REGISTRY[type_name]
        return cls.model_validate(data)

    def _write_event(self, event: AnyEvent) -> None:
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(self._serialize_event(event) + "\n")

    def _load_from_file(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    event = self._deserialize_event(line)
                    self._events.append(event)
                    self._update_projections(event)

    # ── Read access ────────────────────────────────────────────────────────────

    @property
    def events(self) -> list[AnyEvent]:
        return list(self._events)  # copy — caller cannot mutate

    def latest_candle(self, venue: str, symbol: str, timeframe: str) -> Optional[CandleEvent]:
        return self._latest_candle.get(f"{venue}:{symbol}:{timeframe}")

    def latest_features(self, venue: str, symbol: str, timeframe: str) -> Optional[FeatureSnapshot]:
        return self._latest_features.get(f"{venue}:{symbol}:{timeframe}")

    def latest_regime(self, venue: str, symbol: str, timeframe: str) -> Optional[RegimeState]:
        return self._latest_regime.get(f"{venue}:{symbol}:{timeframe}")

    def latest_research(self) -> Optional[ResearchState]:
        return self._latest_research

    def open_signals(self) -> list[SignalCandidate]:
        return list(self._open_signals.values())

    def trade_outcomes(self) -> list[TradeOutcome]:
        return list(self._trade_outcomes)

    def active_data_quality_issues(self) -> list[DataQualityEvent]:
        return [e for e in self._data_quality_events if not e.resolved]

    def event_count(self) -> int:
        return len(self._events)


def replay(log_path: Path) -> MatrixEventLog:
    """
    Load and replay an event log from disk.
    Calling this twice on the same file always produces identical state.
    """
    return MatrixEventLog(log_path=log_path)
