"""
Risk state — mutable account view passed into the Risk Agent on every evaluation.
Immutable snapshot: build a new RiskState after each trade opens/closes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OpenPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    side: Literal["long", "short"]
    risk_amount: Decimal       # USDT committed as risk for this position


class RiskState(BaseModel):
    model_config = ConfigDict(frozen=True)

    equity: Decimal                                        # current account equity (USDT)
    peak_equity: Decimal                                   # highest equity ever reached
    daily_start_equity: Decimal                            # equity at start of UTC day
    open_positions: list[OpenPosition] = Field(default_factory=list)
    circuit_breaker_active: bool = False

    @property
    def daily_pnl(self) -> Decimal:
        return self.equity - self.daily_start_equity

    @property
    def daily_loss_pct(self) -> Decimal:
        """Negative means a loss. Zero or positive means no daily loss."""
        return self.daily_pnl / self.daily_start_equity

    @property
    def drawdown_pct(self) -> Decimal:
        """Positive means we are below peak (drawdown). Zero means at peak."""
        if self.peak_equity == 0:
            return Decimal("0")
        return (self.peak_equity - self.equity) / self.peak_equity

    @property
    def total_open_risk(self) -> Decimal:
        return sum((p.risk_amount for p in self.open_positions), Decimal("0"))

    @property
    def portfolio_heat_pct(self) -> Decimal:
        """Total open risk as a fraction of equity."""
        if self.equity == 0:
            return Decimal("0")
        return self.total_open_risk / self.equity
