"""
Risk Agent.

evaluate(intent, state, snapshot, research, config, now) → RiskDecision

Evaluation order (first failure → reject immediately):
  1. circuit_breaker_active
  2. research hard block
  3. snapshot age > max_snapshot_age_seconds
  4. funding_stale (when config.block_on_funding_stale is True)
  5. daily loss limit exceeded
  6. max drawdown exceeded
  7. max open positions exceeded
  8. portfolio heat exceeded

All checks passed → approve with approved_intent = intent.
Every rejection carries at least one reason_code (enforced by RiskDecision contract).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import ResearchState
from finding_alpha.contracts.trading import PortfolioIntent, RiskDecision
from finding_alpha.contracts import reason_codes as rc

from .state import RiskState

RISK_POLICY_VERSION = "1.0"


class RiskConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    daily_loss_limit_pct: Decimal = Decimal("0.03")    # 3% of daily_start_equity
    max_drawdown_pct: Decimal = Decimal("0.10")         # 10% from peak
    max_open_positions: int = 3
    max_portfolio_heat_pct: Decimal = Decimal("0.06")   # 6% of equity in open risk
    max_snapshot_age_seconds: int = 300                 # 5 min
    block_on_funding_stale: bool = False                # set True for funding-sensitive strategies
    risk_policy_version: str = RISK_POLICY_VERSION


def evaluate(
    intent: PortfolioIntent,
    state: RiskState,
    snapshot: FeatureSnapshot,
    research: Optional[ResearchState],
    config: RiskConfig,
    now: datetime,
) -> RiskDecision:
    def _reject(codes: list[str]) -> RiskDecision:
        return RiskDecision(
            intent_id=intent.intent_id,
            decision="reject",
            reason_codes=codes,
            risk_policy_version=config.risk_policy_version,
            decided_at=now,
            risk_snapshot=_snapshot_dict(state),
        )

    def _approve() -> RiskDecision:
        return RiskDecision(
            intent_id=intent.intent_id,
            decision="approve",
            approved_intent=intent,
            reason_codes=[],
            risk_policy_version=config.risk_policy_version,
            decided_at=now,
            risk_snapshot=_snapshot_dict(state),
        )

    # ── 1. Circuit breaker ────────────────────────────────────────────────────
    if state.circuit_breaker_active:
        return _reject([rc.RISK_CIRCUIT_BREAKER_ACTIVE])

    # ── 2. Research hard block ────────────────────────────────────────────────
    if research is not None and not research.is_expired and research.is_hard_block:
        return _reject([rc.RISK_RESEARCH_HARD_BLOCK])

    # ── 3. Snapshot freshness ─────────────────────────────────────────────────
    age_seconds = (now - snapshot.ts).total_seconds()
    if age_seconds > config.max_snapshot_age_seconds:
        return _reject([rc.DATA_STALE])

    # ── 4. Funding staleness ──────────────────────────────────────────────────
    if config.block_on_funding_stale and snapshot.funding_stale:
        return _reject([rc.RISK_FUNDING_OI_STALE])

    # ── 5. Daily loss stop ────────────────────────────────────────────────────
    if state.daily_loss_pct < -config.daily_loss_limit_pct:
        return _reject([rc.RISK_DAILY_LOSS_STOP])

    # ── 6. Max drawdown ───────────────────────────────────────────────────────
    if state.drawdown_pct > config.max_drawdown_pct:
        return _reject([rc.RISK_DRAWDOWN_LIMIT])

    # ── 7. Max open positions ─────────────────────────────────────────────────
    if len(state.open_positions) >= config.max_open_positions:
        return _reject([rc.RISK_MAX_POSITIONS])

    # ── 8. Portfolio heat ─────────────────────────────────────────────────────
    projected_heat = (state.total_open_risk + intent.risk_amount) / state.equity
    if projected_heat > config.max_portfolio_heat_pct:
        return _reject([rc.RISK_PORTFOLIO_HEAT])

    return _approve()


def _snapshot_dict(state: RiskState) -> dict:
    return {
        "equity": str(state.equity),
        "daily_loss_pct": str(state.daily_loss_pct.quantize(Decimal("0.0001"))),
        "drawdown_pct": str(state.drawdown_pct.quantize(Decimal("0.0001"))),
        "open_positions": str(len(state.open_positions)),
        "portfolio_heat_pct": str(state.portfolio_heat_pct.quantize(Decimal("0.0001"))),
    }
