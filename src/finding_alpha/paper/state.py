"""
Paper trading state for Phase 8.

PaperPosition  — one open paper trade. Always carries stop_price.
PendingEntry   — a signal that approved and is waiting for the entry limit to fill
                 on the next bar. Cleared (filled or expired) after one bar.
PaperTrade     — immutable closed-trade record.
PaperState     — mutable container. Enforces one position max (Phase 8 policy).

Invariants:
  - PaperPosition.stop_price is always set — no unprotected paper position.
  - At most one open position AND at most one pending entry at any time.
  - Equity updates only when a trade closes.
  - save() / load_state() round-trip via state.json; trades append to trades.jsonl.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator


class PaperPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str
    strategy_id: str
    intent_id: str
    symbol: str
    side: Literal["long", "short"]
    entry_ts: datetime
    entry_price: Decimal
    stop_price: Decimal          # REQUIRED — no unprotected paper position
    target_price: Decimal
    quantity: Decimal
    notional: Decimal
    risk_amount: Decimal
    max_exit_ts: datetime        # entry_ts + max_hold_minutes
    feature_version: str
    strategy_version: str

    @model_validator(mode="after")
    def _validate(self) -> PaperPosition:
        for f in ("entry_ts", "max_exit_ts"):
            if getattr(self, f).tzinfo is None:
                raise ValueError(f"{f} must be timezone-aware")
        if self.quantity <= Decimal("0"):
            raise ValueError("quantity must be positive")
        if self.side == "short" and self.stop_price <= self.entry_price:
            raise ValueError("short stop_price must be above entry_price")
        if self.side == "long" and self.stop_price >= self.entry_price:
            raise ValueError("long stop_price must be below entry_price")
        return self


class PendingEntry(BaseModel):
    """
    A signal that passed risk and is waiting for the entry limit to fill.
    Checked on the bar immediately following the signal bar.
    If the bar does not touch entry_price, the pending entry is canceled.
    """
    model_config = ConfigDict(frozen=True)

    signal_id: str
    strategy_id: str
    intent_id: str
    symbol: str
    side: Literal["long", "short"]
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    quantity: Decimal
    notional: Decimal
    risk_amount: Decimal
    max_hold_minutes: int
    signal_bar_open_time: datetime   # open_time of the bar on which the signal fired
    feature_version: str
    strategy_version: str

    @model_validator(mode="after")
    def _validate(self) -> PendingEntry:
        if self.signal_bar_open_time.tzinfo is None:
            raise ValueError("signal_bar_open_time must be timezone-aware")
        return self


class PaperTrade(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str
    strategy_id: str
    intent_id: str
    symbol: str
    side: Literal["long", "short"]
    entry_ts: datetime
    exit_ts: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    gross_pnl: Decimal
    total_fees: Decimal
    net_pnl: Decimal
    initial_risk_amount: Decimal
    r_multiple: Decimal
    exit_reason: Literal["take_profit", "stop_loss", "max_hold_time"]


class PaperState:
    """
    Mutable paper account state. Call save_state() after every mutation.

    Phase 8 limits: one pending entry and one open position at a time.
    Equity starts at INITIAL_EQUITY and updates on each trade close.
    Daily tracking resets at UTC midnight automatically.
    """

    INITIAL_EQUITY = Decimal("10000")

    def __init__(
        self,
        equity: Decimal = INITIAL_EQUITY,
        peak_equity: Decimal = INITIAL_EQUITY,
        daily_start_equity: Decimal = INITIAL_EQUITY,
        daily_date: Optional[str] = None,
        open_position: Optional[PaperPosition] = None,
        pending_entry: Optional[PendingEntry] = None,
        last_processed_bar_ts: Optional[datetime] = None,
        circuit_breaker_active: bool = False,
        live_plan_ref: Optional[dict] = None,
    ):
        self.equity = equity
        self.peak_equity = peak_equity
        self.daily_start_equity = daily_start_equity
        self.daily_date = daily_date
        self.open_position = open_position
        self.pending_entry = pending_entry
        self.last_processed_bar_ts = last_processed_bar_ts
        self.circuit_breaker_active = circuit_breaker_active
        # Opaque serialized PlanState for live-mode execution. The live_execution
        # module owns the schema; state.py just round-trips the dict. None when
        # running in sim mode or when no live order is currently in flight.
        self.live_plan_ref = live_plan_ref

    # ── Derived state ──────────────────────────────────────────────────────────

    def has_open_position(self) -> bool:
        return self.open_position is not None

    def has_pending_entry(self) -> bool:
        return self.pending_entry is not None

    def is_slot_free(self) -> bool:
        """True if we can accept a new signal. Blocks on any of: open paper
        position, pending sim entry, or active live plan (live mode)."""
        return (
            self.open_position is None
            and self.pending_entry is None
            and self.live_plan_ref is None
        )

    def total_open_risk(self) -> Decimal:
        if self.open_position:
            return self.open_position.risk_amount
        if self.pending_entry:
            return self.pending_entry.risk_amount
        return Decimal("0")

    # ── Mutations ──────────────────────────────────────────────────────────────

    def reset_daily_if_needed(self, now: datetime) -> None:
        today = _ensure_utc(now).strftime("%Y-%m-%d")
        if self.daily_date != today:
            self.daily_start_equity = self.equity
            self.daily_date = today

    def apply_trade_close(self, trade: PaperTrade) -> None:
        self.equity += trade.net_pnl
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        self.open_position = None

    # ── Persistence ────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "equity": str(self.equity),
            "peak_equity": str(self.peak_equity),
            "daily_start_equity": str(self.daily_start_equity),
            "daily_date": self.daily_date,
            "open_position": (
                self.open_position.model_dump(mode="json")
                if self.open_position else None
            ),
            "pending_entry": (
                self.pending_entry.model_dump(mode="json")
                if self.pending_entry else None
            ),
            "last_processed_bar_ts": (
                self.last_processed_bar_ts.isoformat()
                if self.last_processed_bar_ts else None
            ),
            "circuit_breaker_active": self.circuit_breaker_active,
            "live_plan_ref": self.live_plan_ref,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PaperState:
        pos = PaperPosition.model_validate(d["open_position"]) if d.get("open_position") else None
        pend = PendingEntry.model_validate(d["pending_entry"]) if d.get("pending_entry") else None
        last_bar_ts: Optional[datetime] = None
        if d.get("last_processed_bar_ts"):
            last_bar_ts = datetime.fromisoformat(d["last_processed_bar_ts"])
            if last_bar_ts.tzinfo is None:
                last_bar_ts = last_bar_ts.replace(tzinfo=timezone.utc)
        return cls(
            equity=Decimal(d["equity"]),
            peak_equity=Decimal(d["peak_equity"]),
            daily_start_equity=Decimal(d["daily_start_equity"]),
            daily_date=d.get("daily_date"),
            open_position=pos,
            pending_entry=pend,
            last_processed_bar_ts=last_bar_ts,
            circuit_breaker_active=d.get("circuit_breaker_active", False),
            live_plan_ref=d.get("live_plan_ref"),
        )


def save_state(state: PaperState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2, default=str), encoding="utf-8")


def load_state(path: Path) -> PaperState:
    if not path.exists():
        return PaperState()
    return PaperState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def append_trade_log(trade: PaperTrade, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(trade.model_dump(mode="json"), default=str) + "\n")


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
