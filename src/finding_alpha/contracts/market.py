"""
Market-layer contracts.
These represent raw exchange data coming in from the Data Agent.
All are immutable after creation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


class MarketEvent(BaseModel):
    """
    Raw normalized event from an exchange feed.
    Immutable after creation. Every live event carries both timestamps.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    event_id: str = Field(default_factory=_new_id)
    venue: str
    symbol: str
    event_type: Literal[
        "trade", "book", "kline", "funding",
        "open_interest", "mark_price", "index_price",
    ]
    exchange_ts: datetime
    received_ts: datetime
    payload: dict[str, Any]
    source_sequence: Optional[int] = None

    @model_validator(mode="after")
    def timestamps_must_be_utc(self) -> MarketEvent:
        for field_name in ("exchange_ts", "received_ts"):
            ts = getattr(self, field_name)
            if ts.tzinfo is None:
                raise ValueError(f"{field_name} must be timezone-aware (UTC)")
        return self


class CandleEvent(BaseModel):
    """
    A single OHLCV candle from the exchange.
    Strategy agents may ONLY act on final candles (is_final=True).
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    event_id: str = Field(default_factory=_new_id)
    venue: str
    symbol: str
    timeframe: str                        # e.g. "15m", "1h"
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal
    taker_buy_volume: Optional[Decimal] = None
    is_final: bool = False                # only True on candle close confirmation

    @model_validator(mode="after")
    def validate_ohlcv(self) -> CandleEvent:
        if self.high < self.low:
            raise ValueError("high must be >= low")
        if self.high < self.open or self.high < self.close:
            raise ValueError("high must be >= open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("low must be <= open and close")
        if self.volume < Decimal("0"):
            raise ValueError("volume must be non-negative")
        for field_name in ("open_time", "close_time"):
            ts = getattr(self, field_name)
            if ts.tzinfo is None:
                raise ValueError(f"{field_name} must be timezone-aware (UTC)")
        return self


class DataQualityEvent(BaseModel):
    """
    Emitted by the Data Agent when it detects a data problem.
    The system uses these to block new entries for affected symbols.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    event_id: str = Field(default_factory=_new_id)
    venue: str
    symbol: str
    detected_at: datetime
    reason_code: str                      # from reason_codes module
    detail: str = ""
    affected_timeframes: list[str] = Field(default_factory=list)
    resolved: bool = False

    @model_validator(mode="after")
    def detected_at_must_be_utc(self) -> DataQualityEvent:
        if self.detected_at.tzinfo is None:
            raise ValueError("detected_at must be timezone-aware (UTC)")
        return self
