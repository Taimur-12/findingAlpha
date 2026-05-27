"""
Execution contracts.
ExecutionReport: fill confirmation from the exchange.
TradeOutcome: closed trade result with PnL and R multiple.
Local order state changes ONLY through execution reports or reconciliation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _new_id() -> str:
    return str(uuid4())


# All valid states an order can be in — matches source of truth state machine
ORDER_STATES = Literal[
    "planned",
    "submitted",
    "acknowledged",
    "open",
    "partially_filled",
    "filled",
    "cancel_requested",
    "canceled",
    "rejected",
    "expired",
    "reconciliation_required",
]


class ExecutionReport(BaseModel):
    """
    Fill or status update from the exchange.
    Local order state changes ONLY through these reports.
    The exchange is source of truth — this is a projection of that truth.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    report_id: str = Field(default_factory=_new_id)
    order_id: str                           # our internal order ID
    client_order_id: str                    # our deterministic idempotency key
    venue_order_id: str                     # exchange-assigned order ID

    status: ORDER_STATES
    filled_quantity: Decimal
    remaining_quantity: Decimal
    avg_fill_price: Optional[Decimal] = None
    fee: Decimal = Decimal("0")
    fee_currency: str = "USDT"
    liquidity_flag: Literal["maker", "taker", "unknown"] = "unknown"

    exchange_ts: datetime
    received_ts: datetime
    raw_response_ref: Optional[str] = None  # reference to stored raw exchange response

    @model_validator(mode="after")
    def validate_report(self) -> ExecutionReport:
        for field_name in ("exchange_ts", "received_ts"):
            ts = getattr(self, field_name)
            if ts.tzinfo is None:
                raise ValueError(f"{field_name} must be timezone-aware (UTC)")
        if self.filled_quantity < Decimal("0"):
            raise ValueError("filled_quantity must be non-negative")
        if self.remaining_quantity < Decimal("0"):
            raise ValueError("remaining_quantity must be non-negative")
        if self.fee < Decimal("0"):
            raise ValueError("fee must be non-negative")
        return self

    @property
    def is_terminal(self) -> bool:
        return self.status in ("filled", "canceled", "rejected", "expired")


class TradeOutcome(BaseModel):
    """
    The complete record of a closed trade.
    Built from entry and exit ExecutionReports.
    R multiple = net_pnl / initial_risk_amount.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    outcome_id: str = Field(default_factory=_new_id)
    signal_id: str
    intent_id: str
    venue: str
    symbol: str
    timeframe: str
    side: Literal["long", "short"]

    entry_ts: datetime
    exit_ts: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal

    gross_pnl: Decimal
    total_fees: Decimal
    funding_cost: Decimal = Decimal("0")
    net_pnl: Decimal

    initial_risk_amount: Decimal
    r_multiple: Optional[Decimal] = None   # net_pnl / initial_risk_amount

    exit_reason: Literal[
        "take_profit", "stop_loss", "max_hold_time",
        "manual", "circuit_breaker", "emergency",
    ]
    strategy_id: str
    strategy_version: str
    feature_version: str

    @model_validator(mode="after")
    def compute_r_multiple(self) -> TradeOutcome:
        for field_name in ("entry_ts", "exit_ts"):
            ts = getattr(self, field_name)
            if ts.tzinfo is None:
                raise ValueError(f"{field_name} must be timezone-aware (UTC)")
        if self.exit_ts <= self.entry_ts:
            raise ValueError("exit_ts must be after entry_ts")
        if self.initial_risk_amount > Decimal("0") and self.r_multiple is None:
            object.__setattr__(
                self,
                "r_multiple",
                (self.net_pnl / self.initial_risk_amount).quantize(Decimal("0.01")),
            )
        return self
