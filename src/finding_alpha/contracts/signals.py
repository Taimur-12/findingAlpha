"""
Signal contracts.
SignalCandidate: a trade proposal from a strategy agent.
ResearchState: structured output from the LLM Research Agent.
Both are immutable. Neither places orders.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _new_id() -> str:
    return str(uuid4())


class SignalCandidate(BaseModel):
    """
    A trade proposal emitted by a strategy agent.
    A signal without an invalidation_price is invalid and will be rejected.
    Signals do not size trades, do not call APIs, do not place orders.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    signal_id: str = Field(default_factory=_new_id)
    strategy_id: str
    venue: str
    symbol: str
    timeframe: str
    side: Literal["long", "short"]
    created_at: datetime
    expires_at: datetime

    base_confidence: Decimal              # 0.0 to 1.0
    expected_horizon_minutes: int
    entry_reference: Decimal              # reference price at signal creation
    invalidation_price: Decimal           # REQUIRED — signal is invalid without this
    target_prices: list[Decimal] = Field(default_factory=list)
    evidence: dict[str, str] = Field(default_factory=dict)

    feature_version: str
    strategy_version: str

    @model_validator(mode="after")
    def validate_signal(self) -> SignalCandidate:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware (UTC)")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        if not (Decimal("0") <= self.base_confidence <= Decimal("1")):
            raise ValueError("base_confidence must be between 0 and 1")
        if self.expected_horizon_minutes <= 0:
            raise ValueError("expected_horizon_minutes must be positive")

        # Core invariant from source of truth: no stop = invalid signal
        if self.side == "long" and self.invalidation_price >= self.entry_reference:
            raise ValueError(
                "long signal: invalidation_price must be below entry_reference"
            )
        if self.side == "short" and self.invalidation_price <= self.entry_reference:
            raise ValueError(
                "short signal: invalidation_price must be above entry_reference"
            )
        return self


class ResearchState(BaseModel):
    """
    Structured output from the LLM Research Agent.
    This is optional context, never a trade command.
    Expired research state is ignored, never silently reused.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    state_id: str = Field(default_factory=_new_id)
    as_of: datetime
    expires_at: datetime
    assets: list[str]                     # e.g. ["BTC", "ETH"]

    event_type: Literal[
        "none", "macro", "geopolitical", "regulatory",
        "exchange_risk", "stablecoin_risk", "protocol_risk",
        "market_structure", "unknown",
    ]
    severity: Decimal                     # 0.0 to 1.0
    directional_bias: Decimal             # -1.0 to 1.0
    confidence_multiplier: Decimal        # 0.0 to 1.15 — clamped on creation
    trade_policy: Literal[
        "normal", "raise_thresholds", "reduce_size",
        "block_new_entries", "close_risk_positions",
    ]
    reason_codes: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    one_sentence_summary: str = ""
    model_id: str
    prompt_version: str

    # Strategy allowlist gate (Phase 9 LLM Advisory layer).
    # Empty list = no constraint; runtime treats all known strategies as allowed.
    # Non-empty list = only the listed strategy_ids may take entries while this state is valid.
    allowed_strategies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_research(self) -> ResearchState:
        for field_name in ("as_of", "expires_at"):
            ts = getattr(self, field_name)
            if ts.tzinfo is None:
                raise ValueError(f"{field_name} must be timezone-aware (UTC)")
        if self.expires_at <= self.as_of:
            raise ValueError("expires_at must be after as_of")
        if not (Decimal("0") <= self.severity <= Decimal("1")):
            raise ValueError("severity must be between 0 and 1")
        if not (Decimal("-1") <= self.directional_bias <= Decimal("1")):
            raise ValueError("directional_bias must be between -1 and 1")
        # Clamp multiplier to allowed range
        object.__setattr__(
            self,
            "confidence_multiplier",
            max(Decimal("0"), min(Decimal("1.15"), self.confidence_multiplier)),
        )
        return self

    @property
    def is_expired(self) -> bool:
        from datetime import timezone
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_hard_block(self) -> bool:
        from . import reason_codes as rc
        hard_block_codes = {
            rc.RESEARCH_EXCHANGE_INSOLVENCY,
            rc.RESEARCH_WITHDRAWALS_FROZEN,
            rc.RESEARCH_STABLECOIN_DEPEG,
            rc.RESEARCH_EXCHANGE_HACK,
        }
        return bool(hard_block_codes.intersection(self.reason_codes))
