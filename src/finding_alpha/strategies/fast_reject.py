"""
Shared fast-reject helpers used by all strategy modules.

fast_reject returns (rejected: bool, reason_code: str | None).
When rejected is True, reason_code is always set.
"""

from __future__ import annotations

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts import reason_codes as rc


def check_regime(
    regime: RegimeState,
    blocked: frozenset[str],
) -> tuple[bool, str | None]:
    if regime.regime in blocked:
        return True, rc.SIGNAL_REGIME_BLOCKED
    return False, None


def check_features(
    snapshot: FeatureSnapshot,
    required: tuple[str, ...],
) -> tuple[bool, str | None]:
    for field in required:
        if getattr(snapshot, field) is None:
            return True, rc.DATA_MISSING_FEATURE
    return False, None


def check_rr(
    entry: float,
    stop: float,
    target: float,
    min_rr: float = 1.5,
) -> tuple[bool, str | None]:
    risk = abs(entry - stop)
    if risk == 0:
        return True, rc.RISK_ZERO_STOP_DISTANCE
    reward = abs(target - entry)
    if reward < min_rr * risk:
        return True, rc.SIGNAL_TARGET_INSUFFICIENT_R
    return False, None
