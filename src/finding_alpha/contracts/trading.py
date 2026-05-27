"""
Trading contracts.
PortfolioIntent: a sized trade proposal before risk approval.
RiskDecision: the Risk Agent's verdict.
OrderPlan: what the Execution Agent actually submits.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _new_id() -> str:
    return str(uuid4())


class TargetLevel(BaseModel):
    """A single take-profit level."""
    model_config = ConfigDict(frozen=True)
    price: Decimal
    quantity_fraction: Decimal            # fraction of position to close here (0-1)


class PortfolioIntent(BaseModel):
    """
    Sized trade proposal produced by the Portfolio Agent.
    Total risk is known before this reaches the Risk Agent.
    No DCA in v1: one entry, one stop, defined targets.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    intent_id: str = Field(default_factory=_new_id)
    signal_id: str
    venue: str
    symbol: str
    side: Literal["long", "short"]
    entry_type: Literal["limit", "market", "post_only_limit"]
    entry_price: Optional[Decimal] = None   # None for market orders
    stop_price: Decimal                     # REQUIRED — no intent without a stop
    target_plan: list[TargetLevel] = Field(default_factory=list)

    risk_amount: Decimal                    # in quote currency (e.g. USDT)
    quantity: Decimal                       # in base currency (e.g. BTC)
    notional: Decimal                       # quantity * entry_price
    leverage: Decimal
    max_slippage_bps: Decimal
    time_in_force: str                      # e.g. "GTC", "IOC", "PostOnly"
    max_hold_minutes: int

    created_at: datetime

    @model_validator(mode="after")
    def validate_intent(self) -> PortfolioIntent:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")
        if self.risk_amount <= Decimal("0"):
            raise ValueError("risk_amount must be positive")
        if self.quantity <= Decimal("0"):
            raise ValueError("quantity must be positive")
        if self.notional <= Decimal("0"):
            raise ValueError("notional must be positive")
        if self.leverage <= Decimal("0"):
            raise ValueError("leverage must be positive")
        if self.max_hold_minutes <= 0:
            raise ValueError("max_hold_minutes must be positive")
        return self


class RiskDecision(BaseModel):
    """
    The Risk Agent's verdict on a PortfolioIntent.
    Execution Agent only acts on approved decisions.
    Every rejection must have at least one reason code.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    decision_id: str = Field(default_factory=_new_id)
    intent_id: str
    decision: Literal["approve", "reject", "mutate", "halt"]
    reason_codes: list[str] = Field(default_factory=list)
    approved_intent: Optional[PortfolioIntent] = None
    risk_snapshot: dict[str, Any] = Field(default_factory=dict)
    risk_policy_version: str
    decided_at: datetime

    @model_validator(mode="after")
    def validate_decision(self) -> RiskDecision:
        if self.decided_at.tzinfo is None:
            raise ValueError("decided_at must be timezone-aware (UTC)")
        if self.decision in ("reject", "halt") and not self.reason_codes:
            raise ValueError(
                f"decision={self.decision} requires at least one reason_code"
            )
        if self.decision == "approve" and self.approved_intent is None:
            raise ValueError("approved decision must include approved_intent")
        return self

    @property
    def is_approved(self) -> bool:
        return self.decision == "approve"


class OrderEntry(BaseModel):
    """A single order leg within an OrderPlan."""
    model_config = ConfigDict(frozen=True)
    order_type: Literal["limit", "market", "stop_market", "stop_limit", "post_only_limit"]
    side: Literal["buy", "sell"]
    quantity: Decimal
    price: Optional[Decimal] = None       # None for market orders
    trigger_price: Optional[Decimal] = None
    time_in_force: str = "GTC"
    reduce_only: bool = False
    client_order_id: str = Field(default_factory=_new_id)


class OrderPlan(BaseModel):
    """
    Complete order plan handed to the Execution Agent.
    Live long/short exposure is not allowed without a protective stop
    confirmed or immediately placed.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    order_plan_id: str = Field(default_factory=_new_id)
    approved_intent_id: str
    entry_order: OrderEntry
    stop_order: OrderEntry                 # REQUIRED — no plan without a stop
    take_profit_orders: list[OrderEntry] = Field(default_factory=list)
    cancel_rules: list[str] = Field(default_factory=list)
    emergency_exit_rules: list[str] = Field(default_factory=list)
    created_at: datetime

    @model_validator(mode="after")
    def created_at_must_be_utc(self) -> OrderPlan:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")
        return self
