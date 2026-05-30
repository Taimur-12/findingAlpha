"""
LLM advisory layer: loader, validator, gate helpers.

The advisory is a ResearchState persisted to JSON on disk. A daily LLM run writes
it; the paper runtime reads it on every bar and applies three gates:

    1. is_hard_block(rs)            -> block all new entries
    2. is_strategy_allowed(rs, sid) -> filter by allowlist
    3. effective_risk_scalar(rs)    -> multiplier into Portfolio Agent sizing

If the file is missing, malformed, or expired, the caller substitutes
default_advisory() — permissive defaults that let the system trade normally.
The LLM is upside-only: it can reduce risk or block, never raise risk above 1.0.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from finding_alpha.contracts.signals import ResearchState

DEFAULT_VALIDITY_HOURS = 24
RISK_SCALAR_FLOOR = Decimal("0.25")
RISK_SCALAR_CEILING = Decimal("1.0")


def default_advisory(now: datetime, validity_hours: int = DEFAULT_VALIDITY_HOURS) -> ResearchState:
    """Permissive default used when no advisory file exists, is expired, or malformed."""
    return ResearchState(
        as_of=now,
        expires_at=now + timedelta(hours=validity_hours),
        assets=["BTC"],
        event_type="none",
        severity=Decimal("0"),
        directional_bias=Decimal("0"),
        confidence_multiplier=Decimal("1.0"),
        trade_policy="normal",
        model_id="default-no-llm",
        prompt_version="default",
        one_sentence_summary="No advisory present; permissive defaults applied.",
        allowed_strategies=[],
    )


def load_advisory(path: Path, now: Optional[datetime] = None) -> Optional[ResearchState]:
    """
    Return the advisory at `path` if it parses and has not expired, otherwise None.
    Callers substitute default_advisory(now) on None — the runtime never trades
    blocked because the advisory file is missing.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        rs = ResearchState.model_validate(raw)
    except Exception:
        return None
    if rs.expires_at <= now:
        return None
    return rs


def save_advisory(rs: ResearchState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(rs.model_dump_json(indent=2))


def is_hard_block(rs: ResearchState) -> bool:
    if rs.trade_policy in {"block_new_entries", "close_risk_positions"}:
        return True
    return rs.is_hard_block


def effective_risk_scalar(rs: ResearchState) -> Decimal:
    """
    Clamp the advisory's confidence_multiplier into [0.25, 1.0] for runtime use.
    Contract allows up to 1.15, but LLM is upside-only. Floor 0.25 prevents
    accidental zero-sizing; the only way to fully block is trade_policy.
    """
    return max(RISK_SCALAR_FLOOR, min(RISK_SCALAR_CEILING, rs.confidence_multiplier))


def is_strategy_allowed(rs: ResearchState, strategy_id: str) -> bool:
    """Empty allowed_strategies = no constraint (all allowed)."""
    if not rs.allowed_strategies:
        return True
    return strategy_id in rs.allowed_strategies


def generate_advisory(*, now: Optional[datetime] = None) -> ResearchState:
    """
    Stub generator. Returns a permissive default. Real Claude API call replaces
    this body when the API key is in place.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return default_advisory(now)
