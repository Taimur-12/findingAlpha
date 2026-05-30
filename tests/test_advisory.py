"""
Tests for the Phase 9 LLM advisory layer (loader, validator, gate helpers).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from finding_alpha.contracts import reason_codes
from finding_alpha.contracts.signals import ResearchState
from finding_alpha.research.advisory import (
    default_advisory,
    effective_risk_scalar,
    generate_advisory,
    is_hard_block,
    is_strategy_allowed,
    load_advisory,
    save_advisory,
)

_UTC = timezone.utc


def _now() -> datetime:
    return datetime(2026, 5, 30, 12, 0, 0, tzinfo=_UTC)


def _build_advisory(
    *,
    confidence_multiplier: Decimal = Decimal("1.0"),
    trade_policy: str = "normal",
    allowed_strategies: list[str] | None = None,
    reason_codes_list: list[str] | None = None,
    valid_hours: int = 24,
) -> ResearchState:
    now = _now()
    return ResearchState(
        as_of=now,
        expires_at=now + timedelta(hours=valid_hours),
        assets=["BTC"],
        event_type="none",
        severity=Decimal("0"),
        directional_bias=Decimal("0"),
        confidence_multiplier=confidence_multiplier,
        trade_policy=trade_policy,
        reason_codes=reason_codes_list or [],
        model_id="claude-sonnet-4-6",
        prompt_version="1.0",
        allowed_strategies=allowed_strategies or [],
    )


# ── default behavior ──────────────────────────────────────────────────────────

def test_default_advisory_is_permissive():
    rs = default_advisory(_now())
    assert is_hard_block(rs) is False
    assert effective_risk_scalar(rs) == Decimal("1.0")
    assert is_strategy_allowed(rs, "prev_day_breakdown_v1") is True
    assert is_strategy_allowed(rs, "short_composite_v1") is True
    assert is_strategy_allowed(rs, "anything_else") is True


def test_generate_advisory_stub_returns_default(tmp_path):
    rs = generate_advisory(now=_now())
    assert rs.model_id == "default-no-llm"
    assert effective_risk_scalar(rs) == Decimal("1.0")


# ── file load/save ────────────────────────────────────────────────────────────

def test_load_returns_none_when_file_missing(tmp_path):
    assert load_advisory(tmp_path / "advisory.json", now=_now()) is None


def test_load_returns_none_when_expired(tmp_path):
    rs = _build_advisory(valid_hours=1)
    path = tmp_path / "advisory.json"
    save_advisory(rs, path)
    later = _now() + timedelta(hours=2)
    assert load_advisory(path, now=later) is None


def test_load_returns_none_when_malformed(tmp_path):
    path = tmp_path / "advisory.json"
    path.write_text("{not valid json")
    assert load_advisory(path, now=_now()) is None


def test_save_then_load_round_trip(tmp_path):
    rs = _build_advisory(
        confidence_multiplier=Decimal("0.5"),
        allowed_strategies=["prev_day_breakdown_v1"],
    )
    path = tmp_path / "advisory.json"
    save_advisory(rs, path)
    loaded = load_advisory(path, now=_now())
    assert loaded is not None
    assert loaded.confidence_multiplier == Decimal("0.5")
    assert loaded.allowed_strategies == ["prev_day_breakdown_v1"]


# ── gate: hard_block ──────────────────────────────────────────────────────────

def test_is_hard_block_on_block_new_entries():
    rs = _build_advisory(trade_policy="block_new_entries")
    assert is_hard_block(rs) is True


def test_is_hard_block_on_close_risk_positions():
    rs = _build_advisory(trade_policy="close_risk_positions")
    assert is_hard_block(rs) is True


def test_is_hard_block_on_reason_code():
    rs = _build_advisory(
        trade_policy="normal",
        reason_codes_list=[reason_codes.RESEARCH_EXCHANGE_INSOLVENCY],
    )
    assert is_hard_block(rs) is True


# ── gate: risk_scalar ─────────────────────────────────────────────────────────

def test_effective_risk_scalar_clamps_ceiling():
    rs = _build_advisory(confidence_multiplier=Decimal("1.15"))
    assert effective_risk_scalar(rs) == Decimal("1.0")


def test_effective_risk_scalar_floors_to_0_25():
    rs = _build_advisory(confidence_multiplier=Decimal("0"))
    assert effective_risk_scalar(rs) == Decimal("0.25")


def test_effective_risk_scalar_passthrough():
    rs = _build_advisory(confidence_multiplier=Decimal("0.5"))
    assert effective_risk_scalar(rs) == Decimal("0.5")


# ── gate: strategy allowlist ──────────────────────────────────────────────────

def test_is_strategy_allowed_empty_list_means_all():
    rs = _build_advisory(allowed_strategies=[])
    assert is_strategy_allowed(rs, "prev_day_breakdown_v1") is True
    assert is_strategy_allowed(rs, "short_composite_v1") is True


def test_is_strategy_allowed_filters_by_list():
    rs = _build_advisory(allowed_strategies=["prev_day_breakdown_v1"])
    assert is_strategy_allowed(rs, "prev_day_breakdown_v1") is True
    assert is_strategy_allowed(rs, "short_composite_v1") is False
