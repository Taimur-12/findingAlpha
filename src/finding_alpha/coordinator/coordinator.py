"""
Coordinator.

process_signals() takes all signals from a single bar and returns the subset
that passed sizing + risk, de-duplicated by symbol+direction.

Rules:
  - Sort by base_confidence descending (best signal gets first crack at risk budget)
  - One PortfolioIntent per symbol per direction (first winner blocks others)
  - Research hard block kills ALL signals for the bar
  - Each signal independently passes Portfolio Agent and Risk Agent
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import ResearchState, SignalCandidate
from finding_alpha.contracts.trading import PortfolioIntent, RiskDecision
from finding_alpha.portfolio.agent import PortfolioConfig, size_intent
from finding_alpha.risk.agent import RiskConfig, evaluate
from finding_alpha.risk.state import RiskState


def process_signals(
    signals: list[SignalCandidate],
    equity: Decimal,
    risk_state: RiskState,
    snapshot: FeatureSnapshot,
    research: Optional[ResearchState],
    portfolio_config: PortfolioConfig,
    risk_config: RiskConfig,
    now: datetime,
) -> list[tuple[SignalCandidate, PortfolioIntent, RiskDecision]]:
    """
    Returns a list of (signal, intent, decision) tuples for all approved intents.
    Signals that fail sizing or risk are silently dropped from this list;
    callers should log all inputs + the output set for audit.
    """
    if not signals:
        return []

    # Research hard block kills everything
    if research is not None and not research.is_expired and research.is_hard_block:
        return []

    # Sort highest confidence first — best signal gets priority
    ranked = sorted(signals, key=lambda s: s.base_confidence, reverse=True)

    approved: list[tuple[SignalCandidate, PortfolioIntent, RiskDecision]] = []
    seen: set[tuple[str, str]] = set()   # (symbol, side) already approved

    # After each approval, the risk state heat increases; track incrementally
    running_risk = risk_state.total_open_risk

    for signal in ranked:
        key = (signal.symbol, signal.side)
        if key in seen:
            continue

        intent = size_intent(signal, equity, portfolio_config, now)
        if intent is None:
            continue

        # Check projected heat against running total (not just the base state)
        projected_heat = (running_risk + intent.risk_amount) / equity
        if projected_heat > risk_config.max_portfolio_heat_pct:
            continue

        decision = evaluate(intent, risk_state, snapshot, research, risk_config, now)
        if not decision.is_approved:
            continue

        approved.append((signal, intent, decision))
        seen.add(key)
        running_risk += intent.risk_amount

    return approved
