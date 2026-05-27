"""
Phase 6 pipeline tests.

Covers: Portfolio Agent sizing, Risk Agent failure modes,
Coordinator deduplication, Execution Simulator fill/stop/TP/timeout,
Analytics metrics.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from finding_alpha.contracts.features import FeatureSnapshot, RegimeState
from finding_alpha.contracts.signals import SignalCandidate
from finding_alpha.contracts.trading import PortfolioIntent
from finding_alpha.contracts.execution import TradeOutcome

from finding_alpha.portfolio.agent import PortfolioConfig, size_intent, build_order_plan
from finding_alpha.risk.state import RiskState, OpenPosition
from finding_alpha.risk.agent import RiskConfig, evaluate
from finding_alpha.coordinator.coordinator import process_signals
from finding_alpha.simulation.executor import SimConfig, simulate_trade
from finding_alpha.analytics.metrics import compute_metrics


# ── Shared fixtures ────────────────────────────────────────────────────────────

_NOW = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
_EQUITY = Decimal("10000")
_DEFAULT_CFG = PortfolioConfig()
_DEFAULT_RISK_CFG = RiskConfig()
_DEFAULT_SIM_CFG = SimConfig()
_CLEAN_STATE = RiskState(
    equity=_EQUITY,
    peak_equity=_EQUITY,
    daily_start_equity=_EQUITY,
)


def _signal(
    side="long",
    entry=50000.0,
    stop=49500.0,
    target=51000.0,
    confidence="0.70",
    strategy_id="test_v1",
) -> SignalCandidate:
    now = _NOW
    return SignalCandidate(
        strategy_id=strategy_id,
        venue="bybit", symbol="BTCUSDT", timeframe="1h",
        side=side,
        created_at=now,
        expires_at=now + timedelta(hours=4),
        base_confidence=Decimal(confidence),
        expected_horizon_minutes=240,
        entry_reference=Decimal(f"{entry:.2f}"),
        invalidation_price=Decimal(f"{stop:.2f}"),
        target_prices=[Decimal(f"{target:.2f}")],
        feature_version="1.0",
        strategy_version="1.0",
    )


def _snap(age_seconds: int = 60) -> FeatureSnapshot:
    ts = _NOW - timedelta(seconds=age_seconds)
    return FeatureSnapshot(
        venue="bybit", symbol="BTCUSDT", timeframe="1h",
        ts=ts, feature_version="1.0",
        funding_stale=False, oi_stale=False, reference_venue_missing=False,
    )


def _regime() -> RegimeState:
    return RegimeState(
        venue="bybit", symbol="BTCUSDT", timeframe="1h",
        classified_at=_NOW, regime_version="1.0",
        regime="range", confidence=Decimal("0.70"),
        evidence={}, blocked_strategies=[],
    )


def _candles(
    n: int = 20,
    open_: float = 50000.0,
    high: float = 50500.0,
    low: float = 49800.0,
    close: float = 50200.0,
    start: datetime = _NOW,
) -> pd.DataFrame:
    rows = []
    for i in range(n):
        ts = start + timedelta(hours=i)
        rows.append({"open_time": ts, "open": open_, "high": high, "low": low, "close": close})
    return pd.DataFrame(rows)


def _outcome(r: float, strategy_id: str = "test_v1") -> TradeOutcome:
    risk = Decimal("100")
    net  = Decimal(f"{r * 100:.2f}")
    return TradeOutcome(
        signal_id="s1", intent_id="i1",
        venue="bybit", symbol="BTCUSDT", timeframe="1h",
        side="long",
        entry_ts=_NOW,
        exit_ts=_NOW + timedelta(hours=1),
        entry_price=Decimal("50000"),
        exit_price=Decimal("50100"),
        quantity=Decimal("0.01"),
        gross_pnl=net + Decimal("10"),
        total_fees=Decimal("10"),
        funding_cost=Decimal("0"),
        net_pnl=net,
        initial_risk_amount=risk,
        exit_reason="take_profit" if r > 0 else "stop_loss",
        strategy_id=strategy_id,
        strategy_version="1.0",
        feature_version="1.0",
    )


# ── Portfolio Agent ────────────────────────────────────────────────────────────

class TestPortfolioAgent:
    def test_basic_sizing_produces_intent(self):
        sig = _signal(entry=50000.0, stop=49500.0)
        intent = size_intent(sig, _EQUITY, _DEFAULT_CFG, _NOW)
        assert intent is not None
        assert isinstance(intent, PortfolioIntent)

    def test_risk_amount_respects_risk_pct(self):
        sig = _signal(entry=50000.0, stop=49500.0)
        intent = size_intent(sig, _EQUITY, _DEFAULT_CFG, _NOW)
        # risk_amount ≤ equity * risk_pct (flooring keeps it at or below)
        assert intent.risk_amount <= _EQUITY * _DEFAULT_CFG.risk_pct

    def test_rounded_qty_does_not_exceed_risk(self):
        sig = _signal(entry=50000.0, stop=49500.0)
        intent = size_intent(sig, _EQUITY, _DEFAULT_CFG, _NOW)
        stop_dist = abs(float(sig.entry_reference) - float(sig.invalidation_price))
        actual_risk = float(intent.quantity) * stop_dist
        budget = float(_EQUITY * _DEFAULT_CFG.risk_pct)
        # After flooring, actual_risk must not exceed the original budget
        assert actual_risk <= budget + 1e-6

    def test_rejects_if_min_notional_not_met(self):
        """Tiny equity + tight stop → quantity so small notional < minimum."""
        tiny_equity = Decimal("10")
        sig = _signal(entry=50000.0, stop=49999.0)  # very tight stop → tiny qty
        cfg = PortfolioConfig(min_notional_usdt=Decimal("100"))
        intent = size_intent(sig, tiny_equity, cfg, _NOW)
        assert intent is None

    def test_rejects_if_leverage_exceeded(self):
        """Huge trade → leverage cap → qty scaled down below min_notional."""
        sig = _signal(entry=50000.0, stop=49999.0)  # 1 USDT stop → qty = 100 BTC
        cfg = PortfolioConfig(max_leverage=Decimal("2"), min_notional_usdt=Decimal("1000000"))
        intent = size_intent(sig, _EQUITY, cfg, _NOW)
        assert intent is None

    def test_short_signal_sized_correctly(self):
        sig = _signal(side="short", entry=50000.0, stop=50500.0, target=49000.0)
        intent = size_intent(sig, _EQUITY, _DEFAULT_CFG, _NOW)
        assert intent is not None
        assert intent.side == "short"
        assert intent.stop_price > intent.entry_price

    def test_build_order_plan_has_stop(self):
        sig = _signal()
        intent = size_intent(sig, _EQUITY, _DEFAULT_CFG, _NOW)
        plan = build_order_plan(intent, _NOW)
        assert plan.stop_order is not None
        assert plan.stop_order.reduce_only is True


# ── Risk Agent ─────────────────────────────────────────────────────────────────

class TestRiskAgent:
    def _intent(self):
        sig = _signal()
        return size_intent(sig, _EQUITY, _DEFAULT_CFG, _NOW)

    def test_approves_clean_state(self):
        decision = evaluate(self._intent(), _CLEAN_STATE, _snap(), None, _DEFAULT_RISK_CFG, _NOW)
        assert decision.is_approved

    def test_rejects_circuit_breaker(self):
        state = RiskState(
            equity=_EQUITY, peak_equity=_EQUITY,
            daily_start_equity=_EQUITY, circuit_breaker_active=True,
        )
        decision = evaluate(self._intent(), state, _snap(), None, _DEFAULT_RISK_CFG, _NOW)
        assert not decision.is_approved
        assert "RISK_CIRCUIT_BREAKER_ACTIVE" in decision.reason_codes

    def test_rejects_data_stale(self):
        old_snap = _snap(age_seconds=400)  # > default 300s limit
        decision = evaluate(self._intent(), _CLEAN_STATE, old_snap, None, _DEFAULT_RISK_CFG, _NOW)
        assert not decision.is_approved
        assert "DATA_STALE" in decision.reason_codes

    def test_rejects_daily_loss_stop(self):
        state = RiskState(
            equity=Decimal("9600"),          # 4% loss
            peak_equity=_EQUITY,
            daily_start_equity=_EQUITY,      # 3% limit → 4% loss triggers
        )
        decision = evaluate(self._intent(), state, _snap(), None, _DEFAULT_RISK_CFG, _NOW)
        assert not decision.is_approved
        assert "RISK_DAILY_LOSS_STOP" in decision.reason_codes

    def test_rejects_max_drawdown(self):
        state = RiskState(
            equity=Decimal("8900"),          # 11% down from peak
            peak_equity=_EQUITY,
            daily_start_equity=Decimal("8900"),  # no daily loss, but drawdown exceeds 10%
        )
        decision = evaluate(self._intent(), state, _snap(), None, _DEFAULT_RISK_CFG, _NOW)
        assert not decision.is_approved
        assert "RISK_DRAWDOWN_LIMIT" in decision.reason_codes

    def test_rejects_max_positions(self):
        positions = [
            OpenPosition(symbol="BTCUSDT", side="long", risk_amount=Decimal("100"))
            for _ in range(3)
        ]
        state = RiskState(equity=_EQUITY, peak_equity=_EQUITY, daily_start_equity=_EQUITY, open_positions=positions)
        cfg = RiskConfig(max_open_positions=3)
        decision = evaluate(self._intent(), state, _snap(), None, cfg, _NOW)
        assert not decision.is_approved
        assert "RISK_MAX_POSITIONS" in decision.reason_codes

    def test_rejects_portfolio_heat(self):
        # 5.8% already committed + new 1% would exceed 6%
        state = RiskState(
            equity=_EQUITY,
            peak_equity=_EQUITY,
            daily_start_equity=_EQUITY,
            open_positions=[
                OpenPosition(symbol="BTCUSDT", side="long", risk_amount=Decimal("580"))
            ],
        )
        decision = evaluate(self._intent(), state, _snap(), None, _DEFAULT_RISK_CFG, _NOW)
        assert not decision.is_approved
        assert "RISK_PORTFOLIO_HEAT" in decision.reason_codes

    def test_rejects_funding_stale_when_configured(self):
        stale_snap = FeatureSnapshot(
            venue="bybit", symbol="BTCUSDT", timeframe="1h",
            ts=_NOW, feature_version="1.0",
            funding_stale=True, oi_stale=False, reference_venue_missing=False,
        )
        cfg = RiskConfig(block_on_funding_stale=True)
        decision = evaluate(self._intent(), _CLEAN_STATE, stale_snap, None, cfg, _NOW)
        assert not decision.is_approved
        assert "RISK_FUNDING_OI_STALE" in decision.reason_codes

    def test_rejection_always_has_reason_code(self):
        """Every non-approve decision must have at least one reason code."""
        state = RiskState(
            equity=Decimal("9600"), peak_equity=_EQUITY, daily_start_equity=_EQUITY,
        )
        decision = evaluate(self._intent(), state, _snap(), None, _DEFAULT_RISK_CFG, _NOW)
        if not decision.is_approved:
            assert len(decision.reason_codes) >= 1


# ── Coordinator ────────────────────────────────────────────────────────────────

class TestCoordinator:
    def test_deduplicates_same_symbol_direction(self):
        """Two long signals for BTCUSDT → only one approved."""
        sig_a = _signal(confidence="0.80", strategy_id="strat_a")
        sig_b = _signal(confidence="0.65", strategy_id="strat_b")
        results = process_signals(
            [sig_a, sig_b], _EQUITY, _CLEAN_STATE, _snap(), None,
            _DEFAULT_CFG, _DEFAULT_RISK_CFG, _NOW,
        )
        assert len(results) == 1
        assert results[0][0].strategy_id == "strat_a"  # higher confidence wins

    def test_approves_opposing_directions(self):
        """Long and short on same symbol → both can pass (different keys)."""
        sig_long  = _signal(side="long",  entry=50000.0, stop=49500.0, target=51000.0)
        sig_short = _signal(side="short", entry=50000.0, stop=50500.0, target=49000.0)
        results = process_signals(
            [sig_long, sig_short], _EQUITY, _CLEAN_STATE, _snap(), None,
            _DEFAULT_CFG, _DEFAULT_RISK_CFG, _NOW,
        )
        sides = {r[0].side for r in results}
        assert "long" in sides and "short" in sides

    def test_empty_signals_returns_empty(self):
        results = process_signals(
            [], _EQUITY, _CLEAN_STATE, _snap(), None,
            _DEFAULT_CFG, _DEFAULT_RISK_CFG, _NOW,
        )
        assert results == []


# ── Execution Simulator ────────────────────────────────────────────────────────

class TestExecutionSimulator:
    def _intent_from_signal(self, sig):
        return size_intent(sig, _EQUITY, _DEFAULT_CFG, _NOW)

    def test_limit_entry_fills_when_price_touched(self):
        """Entry limit at 50000; candles dip to low=49800 → fills."""
        sig    = _signal(entry=50000.0, stop=49500.0, target=51000.0)
        intent = self._intent_from_signal(sig)
        candles = _candles(n=10, open_=50100, high=50200, low=49800, close=50050)
        outcome = simulate_trade(intent, candles, _DEFAULT_SIM_CFG, "test_v1", "1.0", "1.0", "1h", _NOW)
        assert outcome is not None
        assert outcome.entry_price == Decimal("50000.00")

    def test_limit_entry_not_filled_returns_none(self):
        """Entry limit at 50000; candles stay above 50100 → never fills."""
        sig    = _signal(entry=50000.0, stop=49500.0, target=51000.0)
        intent = self._intent_from_signal(sig)
        candles = _candles(n=10, open_=50200, high=50400, low=50100, close=50250)
        outcome = simulate_trade(intent, candles, _DEFAULT_SIM_CFG, "test_v1", "1.0", "1.0", "1h", _NOW)
        assert outcome is None

    def test_stop_triggers_correctly(self):
        """After entry, price drops below stop → stop_loss exit."""
        sig    = _signal(entry=50000.0, stop=49500.0, target=51000.0)
        intent = self._intent_from_signal(sig)
        # First few candles: entry fills (low=49800 touches 50000? No — entry is 50000, low=49800 ≤ 50000)
        # Then candles with low=49400 → stop at 49500 triggered
        entry_candles = pd.DataFrame([
            {"open_time": _NOW + timedelta(hours=i), "open": 50100, "high": 50200, "low": 49800, "close": 50050}
            for i in range(3)
        ] + [
            {"open_time": _NOW + timedelta(hours=i + 3), "open": 50000, "high": 50100, "low": 49400, "close": 49600}
            for i in range(5)
        ])
        outcome = simulate_trade(intent, entry_candles, _DEFAULT_SIM_CFG, "test_v1", "1.0", "1.0", "1h", _NOW)
        assert outcome is not None
        assert outcome.exit_reason == "stop_loss"
        assert outcome.net_pnl < Decimal("0")

    def test_target_triggers_correctly(self):
        """After entry, price rises above target → take_profit exit."""
        sig    = _signal(entry=50000.0, stop=49500.0, target=51000.0)
        intent = self._intent_from_signal(sig)
        candles = pd.DataFrame([
            {"open_time": _NOW + timedelta(hours=i), "open": 50100, "high": 51200, "low": 49800, "close": 51100}
            for i in range(10)
        ])
        outcome = simulate_trade(intent, candles, _DEFAULT_SIM_CFG, "test_v1", "1.0", "1.0", "1h", _NOW)
        assert outcome is not None
        assert outcome.exit_reason == "take_profit"
        assert outcome.gross_pnl > Decimal("0")

    def test_stop_wins_over_tp_same_candle(self):
        """Same candle triggers both stop and TP → stop wins (conservative)."""
        sig    = _signal(entry=50000.0, stop=49500.0, target=51000.0)
        intent = self._intent_from_signal(sig)
        # Entry fills on first candle (low ≤ 50000)
        candles = pd.DataFrame([
            {"open_time": _NOW + timedelta(hours=i), "open": 50050, "high": 51100, "low": 49400, "close": 50100}
            for i in range(5)
        ])
        outcome = simulate_trade(intent, candles, _DEFAULT_SIM_CFG, "test_v1", "1.0", "1.0", "1h", _NOW)
        assert outcome is not None
        assert outcome.exit_reason == "stop_loss"

    def test_max_hold_timeout_exits_at_close(self):
        """Price never hits stop or TP within max_hold → exit at close."""
        cfg = PortfolioConfig(max_hold_minutes=120)  # 2 h → 2 bars for 1h candles
        sig    = _signal(entry=50000.0, stop=49500.0, target=52000.0)
        intent = size_intent(sig, _EQUITY, cfg, _NOW)
        # Candles stay in a safe range (never hit stop or target)
        candles = _candles(n=20, open_=50100, high=50300, low=49600, close=50200)
        outcome = simulate_trade(intent, candles, _DEFAULT_SIM_CFG, "test_v1", "1.0", "1.0", "1h", _NOW)
        assert outcome is not None
        assert outcome.exit_reason == "max_hold_time"

    def test_no_unprotected_position(self):
        """OrderPlan built from intent always has a stop order."""
        sig    = _signal()
        intent = size_intent(sig, _EQUITY, _DEFAULT_CFG, _NOW)
        plan   = build_order_plan(intent, _NOW)
        assert plan.stop_order is not None
        assert plan.stop_order.trigger_price is not None


# ── Analytics ──────────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_empty_outcomes(self):
        m = compute_metrics([])
        assert m["trade_count"] == 0
        assert m["win_rate"] is None

    def test_all_wins(self):
        outcomes = [_outcome(2.0) for _ in range(5)]
        m = compute_metrics(outcomes)
        assert m["win_count"] == 5
        assert m["win_rate"] == 1.0
        assert m["expectancy_r"] == pytest.approx(2.0)
        assert m["net_pnl"] > Decimal("0")

    def test_all_losses(self):
        outcomes = [_outcome(-1.0) for _ in range(5)]
        m = compute_metrics(outcomes)
        assert m["win_count"] == 0
        assert m["win_rate"] == 0.0
        assert m["net_pnl"] < Decimal("0")

    def test_mixed_profit_factor(self):
        """3 wins at +2R, 2 losses at -1R → profit factor = 6/2 = 3.0"""
        outcomes = [_outcome(2.0)] * 3 + [_outcome(-1.0)] * 2
        m = compute_metrics(outcomes)
        assert m["profit_factor"] == pytest.approx(3.0)

    def test_fee_share_positive_when_profitable(self):
        outcomes = [_outcome(2.0) for _ in range(4)]
        m = compute_metrics(outcomes)
        assert m["fee_share_of_gross"] is not None
        assert m["fee_share_of_gross"] > 0

    def test_by_strategy_breakdown(self):
        outcomes = [_outcome(2.0, "strat_a")] * 3 + [_outcome(-1.0, "strat_b")] * 2
        m = compute_metrics(outcomes)
        assert "strat_a" in m["by_strategy"]
        assert "strat_b" in m["by_strategy"]
        assert m["by_strategy"]["strat_a"]["win_rate"] == 1.0
        assert m["by_strategy"]["strat_b"]["win_rate"] == 0.0
