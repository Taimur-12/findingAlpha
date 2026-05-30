"""
Reconciliation: compare local PlanState against Bybit ground truth.

Run after a restart, after a network blip, or periodically as a safety
sweep. The reconciler is detection-only — it returns a structured report
describing divergences. The caller decides whether to log, alert, halt,
or call back into the ExecutionAgent to fix.

Divergence categories handled:
  STATE_MISMATCH       local leg state != reconciled exchange state
  UNPROTECTED_POSITION position open, stop terminal or missing
  GHOST_POSITION       exchange has size > 0 with no open stop AND local
                       state thinks nothing is filled (we missed a fill)
  MISSING_POSITION     local state says filled, exchange size == 0
                       (position closed outside our control)

The first two are the hot-path safety checks. Ghost / missing detection
relies on a position query, which the per-plan call makes once per call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from finding_alpha.contracts.reason_codes import (
    EXEC_RECONCILIATION_MISMATCH,
    EXEC_UNPROTECTED_POSITION,
)
from finding_alpha.execution.bybit_client import BybitClient
from finding_alpha.execution.execution_agent import (
    LEG_ENTRY,
    LEG_STOP,
    ExecutionAgent,
    PlanState,
)
from finding_alpha.execution.order_state import OrderState, is_terminal

# Divergence kind tags
KIND_STATE_MISMATCH = "state_mismatch"
KIND_UNPROTECTED = "unprotected_position"
KIND_GHOST_POSITION = "ghost_position"
KIND_MISSING_POSITION = "missing_position"

# Recommended actions (caller interprets these strings)
ACTION_REPLACE_STOP = "replace_stop"
ACTION_HALT = "halt"
ACTION_MARK_CLOSED = "mark_closed"


@dataclass(frozen=True)
class Divergence:
    kind: str
    leg: Optional[str]
    detail: str
    reason_code: str
    recommended_action: str


@dataclass
class ReconciliationReport:
    plan_id: str
    symbol: str
    checked_at: datetime
    exchange_position_size: Decimal = Decimal("0")
    exchange_position_side: Optional[str] = None
    divergences: list[Divergence] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.divergences

    @property
    def has_critical(self) -> bool:
        return any(
            d.kind in (KIND_UNPROTECTED, KIND_GHOST_POSITION)
            for d in self.divergences
        )


def find_unprotected(state: PlanState) -> bool:
    """Local-only check: entry filled or partially filled, but no live stop.

    Useful as a cheap pre-check before doing any API work."""
    entry = state.legs.get(LEG_ENTRY)
    if entry is None:
        return False
    if entry.state not in (OrderState.FILLED, OrderState.PARTIALLY_FILLED):
        return False
    stop = state.legs.get(LEG_STOP)
    if stop is None:
        return True
    # Stop is live (not terminal) and not rejected = protected.
    if is_terminal(stop.state) and stop.state != OrderState.FILLED:
        return True
    return False


def _query_position_size(client: BybitClient, symbol: str) -> tuple[Decimal, Optional[str]]:
    """Return (size, side) for the symbol; (0, None) if no position."""
    result = client.query_positions(symbol=symbol)
    rows = result.get("list", []) or []
    for row in rows:
        if row.get("symbol") != symbol:
            continue
        size_str = row.get("size", "0") or "0"
        try:
            size = Decimal(size_str)
        except Exception:
            size = Decimal("0")
        if size > 0:
            return size, row.get("side")
    return Decimal("0"), None


def reconcile_plan(
    agent: ExecutionAgent,
    state: PlanState,
    *,
    now: Optional[datetime] = None,
) -> ReconciliationReport:
    """Reconcile a single PlanState against exchange truth.

    Steps:
      1. For each known leg, call agent.reconcile_leg to refresh local state
         from the exchange's view of that orderLinkId.
      2. Query position size on the symbol.
      3. Compare reconciled local state to position:
           - position > 0 + no live stop                       → UNPROTECTED
           - position > 0 + local entry not filled             → GHOST_POSITION
           - position == 0 + local entry filled                → MISSING_POSITION

    Returns a report. Local state in `state` is mutated by reconcile_leg.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    pre_states: dict[str, OrderState] = {
        name: leg.state for name, leg in state.legs.items()
    }

    for leg_name in list(state.legs.keys()):
        agent.reconcile_leg(state, leg_name)

    size, exch_side = _query_position_size(agent._client, state.symbol)  # noqa: SLF001

    report = ReconciliationReport(
        plan_id=state.plan_id,
        symbol=state.symbol,
        checked_at=now,
        exchange_position_size=size,
        exchange_position_side=exch_side,
    )

    for name, before in pre_states.items():
        after = state.legs[name].state
        if before != after:
            report.divergences.append(Divergence(
                kind=KIND_STATE_MISMATCH,
                leg=name,
                detail=f"{before.value} -> {after.value}",
                reason_code=EXEC_RECONCILIATION_MISMATCH,
                recommended_action="",
            ))

    entry = state.legs.get(LEG_ENTRY)
    stop = state.legs.get(LEG_STOP)
    entry_filled = entry is not None and entry.state in (
        OrderState.FILLED, OrderState.PARTIALLY_FILLED
    )
    stop_live = stop is not None and not is_terminal(stop.state)

    if size > 0 and not stop_live:
        report.divergences.append(Divergence(
            kind=KIND_UNPROTECTED,
            leg=LEG_STOP,
            detail=f"position size={size} but stop is {stop.state.value if stop else 'absent'}",
            reason_code=EXEC_UNPROTECTED_POSITION,
            recommended_action=ACTION_REPLACE_STOP,
        ))

    if size > 0 and not entry_filled:
        report.divergences.append(Divergence(
            kind=KIND_GHOST_POSITION,
            leg=LEG_ENTRY,
            detail=f"exchange size={size} side={exch_side} but local entry={entry.state.value if entry else 'absent'}",
            reason_code=EXEC_RECONCILIATION_MISMATCH,
            recommended_action=ACTION_HALT,
        ))

    if size == 0 and entry_filled:
        report.divergences.append(Divergence(
            kind=KIND_MISSING_POSITION,
            leg=LEG_ENTRY,
            detail=f"local entry={entry.state.value} but exchange size=0",
            reason_code=EXEC_RECONCILIATION_MISMATCH,
            recommended_action=ACTION_MARK_CLOSED,
        ))

    return report
