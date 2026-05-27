"""
Phase 8 paper trading runtime.

Process flow (one final bar):
  1. Emit CandleEvent to Matrix.
  2. Build FeatureSnapshot + RegimeState from rolling buffer; emit to Matrix.
  3. If pending entry: try to fill limit on this bar; create PaperPosition or cancel.
  4. If open position: check for stop / TP / max-hold-time exit; close if hit.
  5. If slot free and not catch-up: run strategy pipeline (signal → size → risk).
     If signal approved: set pending_entry (fills next bar).

Safety checks enforced before any new entry:
  - Bar must be final (is_bar_final guard on every bar processed).
  - Data must not be stale (is_data_stale → emit DataQualityEvent + block).
  - No duplicate position or pending entry (is_slot_free).
  - Risk Agent must approve (circuit_breaker, daily_loss, drawdown, heat).
  - No paper position ever exists without stop_price.

Catch-up: when multiple new final bars have accumulated (runtime was offline),
  all bars are processed for exits and pending-entry fills, but new entry signals
  are only attempted on the latest bar. This prevents stale-signal entries.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict

from finding_alpha.contracts.execution import TradeOutcome
from finding_alpha.contracts.market import CandleEvent, DataQualityEvent
from finding_alpha.contracts import reason_codes as rc
from finding_alpha.features.snapshot import build_feature_df, build_snapshot
from finding_alpha.live.feed import (
    fetch_recent_candles, fetch_recent_funding, fetch_recent_oi,
    is_bar_final, is_data_stale,
)
from finding_alpha.matrix.event_log import MatrixEventLog
from finding_alpha.paper.state import (
    PaperPosition, PaperState, PaperTrade, PendingEntry,
    append_trade_log, load_state, save_state,
)
from finding_alpha.portfolio.agent import PortfolioConfig, size_intent
from finding_alpha.regime.classifier import classify_regime
from finding_alpha.risk.agent import RiskConfig, evaluate as risk_evaluate
from finding_alpha.risk.state import OpenPosition, RiskState
from finding_alpha.strategies.prev_day_breakdown_v1 import (
    find_signal as _breakdown_signal,
    STRATEGY_ID as _BREAKDOWN_ID,
    STRATEGY_VERSION as _BREAKDOWN_VERSION,
)
from finding_alpha.strategies.short_composite_v1 import (
    find_signal as _composite_signal,
    STRATEGY_ID as _COMPOSITE_ID,
    STRATEGY_VERSION as _COMPOSITE_VERSION,
)

# Registry: strategy_id → (find_fn(snapshot, regime, row, now), strategy_version)
_STRATEGY_REGISTRY: dict[str, tuple] = {
    _BREAKDOWN_ID: (
        lambda sn, reg, row, now: _breakdown_signal(sn, reg, now),
        _BREAKDOWN_VERSION,
    ),
    _COMPOSITE_ID: (
        _composite_signal,
        _COMPOSITE_VERSION,
    ),
}

_BPS = Decimal("0.0001")


class PaperRuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    venue: str = "bybit"
    lookback_bars: int = 300      # bars fetched for feature computation
    funding_days: int = 14
    oi_days: int = 14

    # Paper account
    initial_equity: Decimal = Decimal("10000")
    risk_pct: Decimal = Decimal("0.0025")   # 0.25% per trade
    max_hold_minutes: int = 720             # 12h

    # Fees — must match Phase 7B backtest SimConfig
    maker_fee_bps: Decimal = Decimal("2.0")
    taker_fee_bps: Decimal = Decimal("5.5")
    stop_slippage_bps: Decimal = Decimal("10")

    # Portfolio sizing
    qty_precision: int = 3
    min_notional: Decimal = Decimal("10")
    max_leverage: Decimal = Decimal("10")

    # Risk policy
    daily_loss_limit_pct: Decimal = Decimal("0.03")
    max_drawdown_pct: Decimal = Decimal("0.10")

    # Strategy to run (must be a key in _STRATEGY_REGISTRY)
    strategy_id: str = "prev_day_breakdown_v1"

    # Paths (relative to project root or absolute)
    paper_dir: Path = Path("paper")

    @property
    def state_path(self) -> Path:
        return self.paper_dir / "state.json"

    @property
    def trade_log_path(self) -> Path:
        return self.paper_dir / "trades.jsonl"

    @property
    def matrix_log_path(self) -> Path:
        return self.paper_dir / "matrix.jsonl"


# ── Fee helpers ────────────────────────────────────────────────────────────────

def _fee(notional: Decimal, fee_bps: Decimal) -> Decimal:
    return (notional * fee_bps * _BPS).quantize(Decimal("0.01"))


# ── Pending entry fill ─────────────────────────────────────────────────────────

def _try_fill_entry(
    state: PaperState,
    bar: pd.Series,
    matrix: MatrixEventLog,
    cfg: PaperRuntimeConfig,
    now: datetime,
) -> None:
    """
    Attempt to fill the pending entry limit on the current bar.
    For a short: fills if bar high >= entry_price.
    For a long:  fills if bar low  <= entry_price.
    If not touched, the pending entry is canceled (expired).
    One-bar fill window — consistent with Phase 7B backtest assumption.
    """
    pe = state.pending_entry
    assert pe is not None

    bar_high = Decimal(str(bar["high"]))
    bar_low = Decimal(str(bar["low"]))
    bar_open_time = _bar_open_time(bar)

    touched = (
        bar_high >= pe.entry_price if pe.side == "short"
        else bar_low <= pe.entry_price
    )

    if not touched:
        matrix.append(DataQualityEvent(
            venue=cfg.venue,
            symbol=cfg.symbol,
            detected_at=now,
            reason_code=rc.DATA_MISSING_FEATURE,
            detail=f"pending_entry_missed signal_id={pe.signal_id} entry={pe.entry_price}",
            affected_timeframes=[cfg.timeframe],
        ))
        state.pending_entry = None
        return

    entry_notional = (pe.quantity * pe.entry_price).quantize(Decimal("0.01"))
    entry_fee = _fee(entry_notional, cfg.maker_fee_bps)
    max_exit_ts = bar_open_time + timedelta(minutes=pe.max_hold_minutes)

    position = PaperPosition(
        signal_id=pe.signal_id,
        strategy_id=pe.strategy_id,
        intent_id=pe.intent_id,
        symbol=pe.symbol,
        side=pe.side,
        entry_ts=bar_open_time,
        entry_price=pe.entry_price,
        stop_price=pe.stop_price,
        target_price=pe.target_price,
        quantity=pe.quantity,
        notional=entry_notional,
        risk_amount=pe.risk_amount,
        max_exit_ts=max_exit_ts,
        feature_version=pe.feature_version,
        strategy_version=pe.strategy_version,
    )
    state.open_position = position
    state.pending_entry = None

    # Log entry fee as part of a synthetic TradeOutcome-like record is deferred to close.
    # Here just emit a marker event via DataQualityEvent (paper entry confirmation).
    matrix.append(DataQualityEvent(
        venue=cfg.venue,
        symbol=cfg.symbol,
        detected_at=now,
        reason_code="PAPER_ENTRY_FILLED",
        detail=(
            f"signal_id={pe.signal_id} side={pe.side} "
            f"entry={pe.entry_price} stop={pe.stop_price} "
            f"target={pe.target_price} qty={pe.quantity} "
            f"entry_fee={entry_fee}"
        ),
        affected_timeframes=[cfg.timeframe],
        resolved=True,
    ))


# ── Position exit check ────────────────────────────────────────────────────────

def _check_position_exit(
    state: PaperState,
    bar: pd.Series,
    matrix: MatrixEventLog,
    cfg: PaperRuntimeConfig,
    now: datetime,
) -> Optional[PaperTrade]:
    """
    Check if the open position should exit on this bar.
    Returns the closed PaperTrade if an exit occurred, else None.
    Same-candle stop + TP: stop wins (conservative, matches backtest).
    """
    pos = state.open_position
    assert pos is not None

    bar_high = Decimal(str(bar["high"]))
    bar_low = Decimal(str(bar["low"]))
    bar_open_time = _bar_open_time(bar)

    stop_hit: bool
    tp_hit: bool

    if pos.side == "short":
        stop_hit = bar_high >= pos.stop_price
        tp_hit = bar_low <= pos.target_price
    else:
        stop_hit = bar_low <= pos.stop_price
        tp_hit = bar_high >= pos.target_price

    # Timeout check
    timeout_hit = bar_open_time >= pos.max_exit_ts

    # Stop wins over TP on same candle (conservative)
    if stop_hit and tp_hit:
        tp_hit = False

    exit_reason: Optional[str] = None
    exit_price: Optional[Decimal] = None
    exit_fee_bps: Decimal

    if stop_hit:
        slip = cfg.stop_slippage_bps * _BPS
        if pos.side == "short":
            exit_price = (pos.stop_price * (Decimal("1") + slip)).quantize(Decimal("0.01"))
        else:
            exit_price = (pos.stop_price * (Decimal("1") - slip)).quantize(Decimal("0.01"))
        exit_reason = "stop_loss"
        exit_fee_bps = cfg.taker_fee_bps
    elif tp_hit:
        exit_price = pos.target_price
        exit_reason = "take_profit"
        exit_fee_bps = cfg.maker_fee_bps
    elif timeout_hit:
        exit_price = Decimal(str(bar["close"]))
        exit_reason = "max_hold_time"
        exit_fee_bps = cfg.taker_fee_bps

    if exit_reason is None:
        return None

    # Compute PnL
    exit_notional = (pos.quantity * exit_price).quantize(Decimal("0.01"))
    entry_fee = _fee(pos.notional, cfg.maker_fee_bps)
    exit_fee = _fee(exit_notional, exit_fee_bps)
    total_fees = (entry_fee + exit_fee).quantize(Decimal("0.01"))

    side_sign = Decimal("-1") if pos.side == "short" else Decimal("1")
    gross_pnl = ((exit_price - pos.entry_price) * pos.quantity * side_sign).quantize(Decimal("0.01"))
    net_pnl = (gross_pnl - total_fees).quantize(Decimal("0.01"))
    r_multiple = (net_pnl / pos.risk_amount).quantize(Decimal("0.001")) if pos.risk_amount > 0 else Decimal("0")

    exit_ts = bar_open_time + timedelta(minutes=1)  # one minute into the bar (conservative)

    trade = PaperTrade(
        signal_id=pos.signal_id,
        strategy_id=pos.strategy_id,
        intent_id=pos.intent_id,
        symbol=pos.symbol,
        side=pos.side,
        entry_ts=pos.entry_ts,
        exit_ts=exit_ts,
        entry_price=pos.entry_price,
        exit_price=exit_price,
        quantity=pos.quantity,
        gross_pnl=gross_pnl,
        total_fees=total_fees,
        net_pnl=net_pnl,
        initial_risk_amount=pos.risk_amount,
        r_multiple=r_multiple,
        exit_reason=exit_reason,
    )

    # Emit TradeOutcome to Matrix
    matrix.append(TradeOutcome(
        signal_id=pos.signal_id,
        intent_id=pos.intent_id,
        venue=cfg.venue,
        symbol=pos.symbol,
        timeframe=cfg.timeframe,
        side=pos.side,
        entry_ts=pos.entry_ts,
        exit_ts=exit_ts,
        entry_price=pos.entry_price,
        exit_price=exit_price,
        quantity=pos.quantity,
        gross_pnl=gross_pnl,
        total_fees=total_fees,
        net_pnl=net_pnl,
        initial_risk_amount=pos.risk_amount,
        exit_reason=exit_reason,
        strategy_id=pos.strategy_id,
        strategy_version=pos.strategy_version,
        feature_version=pos.feature_version,
    ))

    state.apply_trade_close(trade)
    return trade


# ── Strategy pipeline ──────────────────────────────────────────────────────────

def _run_strategy_pipeline(
    state: PaperState,
    feature_df: pd.DataFrame,
    bar: pd.Series,
    matrix: MatrixEventLog,
    cfg: PaperRuntimeConfig,
    now: datetime,
    bar_open_time: datetime,
) -> None:
    """
    Run snapshot → regime → signal → size → risk for the latest final bar.
    If approved, sets state.pending_entry. All decisions logged to Matrix.
    """
    strategy_fn, strategy_version = _STRATEGY_REGISTRY[cfg.strategy_id]

    snapshot = build_snapshot(feature_df, cfg.venue, cfg.symbol, cfg.timeframe)
    regime = classify_regime(snapshot)
    matrix.append(snapshot)
    matrix.append(regime)

    signal = strategy_fn(snapshot, regime, bar, now)
    if signal is None:
        return

    matrix.append(signal)

    port_cfg = PortfolioConfig(
        risk_pct=cfg.risk_pct,
        max_leverage=cfg.max_leverage,
        min_notional_usdt=cfg.min_notional,
        qty_precision=cfg.qty_precision,
        taker_fee_bps=cfg.taker_fee_bps,
        max_hold_minutes=cfg.max_hold_minutes,
    )
    intent = size_intent(signal, state.equity, port_cfg, now)
    if intent is None:
        return

    risk_cfg = RiskConfig(
        daily_loss_limit_pct=cfg.daily_loss_limit_pct,
        max_drawdown_pct=cfg.max_drawdown_pct,
        max_open_positions=1,
        max_snapshot_age_seconds=7200,  # 2h — covers 1h bar + processing lag
        block_on_funding_stale=False,
    )
    risk_state = RiskState(
        equity=state.equity,
        peak_equity=state.peak_equity,
        daily_start_equity=state.daily_start_equity,
        open_positions=(
            [OpenPosition(symbol=cfg.symbol, side=state.open_position.side,
                          risk_amount=state.open_position.risk_amount)]
            if state.open_position else []
        ),
        circuit_breaker_active=state.circuit_breaker_active,
    )

    decision = risk_evaluate(intent, risk_state, snapshot, None, risk_cfg, now)
    matrix.append(intent)
    matrix.append(decision)

    if not decision.is_approved:
        return

    # Approved — queue for entry fill on the next bar
    target_price = intent.target_plan[0].price if intent.target_plan else signal.target_prices[0]
    state.pending_entry = PendingEntry(
        signal_id=signal.signal_id,
        strategy_id=cfg.strategy_id,
        intent_id=intent.intent_id,
        symbol=cfg.symbol,
        side=signal.side,
        entry_price=intent.entry_price,
        stop_price=intent.stop_price,
        target_price=target_price,
        quantity=intent.quantity,
        notional=intent.notional,
        risk_amount=intent.risk_amount,
        max_hold_minutes=cfg.max_hold_minutes,
        signal_bar_open_time=bar_open_time,
        feature_version=snapshot.feature_version,
        strategy_version=strategy_version,
    )


# ── Main bar processor ─────────────────────────────────────────────────────────

def process_final_bar(
    bar: pd.Series,
    state: PaperState,
    candle_buffer: pd.DataFrame,
    funding_df: pd.DataFrame,
    oi_df: pd.DataFrame,
    matrix: MatrixEventLog,
    cfg: PaperRuntimeConfig,
    now: datetime,
    is_catchup: bool = False,
) -> Optional[PaperTrade]:
    """
    Process one confirmed final candle through the full paper pipeline.

    Args:
        bar:          The final candle row (Series from candle_buffer).
        state:        Mutable paper state; mutated in place.
        candle_buffer: Full rolling DataFrame including this bar (for features).
        funding_df:   Recent funding data for feature computation.
        oi_df:        Recent OI data for feature computation.
        matrix:       Append-only event log.
        cfg:          Immutable runtime config.
        now:          Wall-clock UTC time (injected for testability).
        is_catchup:   True when processing a bar that closed while we were offline.
                      Exits and fill checks run; new entry signals are skipped.

    Returns:
        Closed PaperTrade if a position exited this bar, else None.
    """
    bar_open_time = _bar_open_time(bar)
    state.reset_daily_if_needed(now)

    # Emit the candle to Matrix
    matrix.append(CandleEvent(
        venue=cfg.venue,
        symbol=cfg.symbol,
        timeframe=cfg.timeframe,
        open_time=bar_open_time,
        close_time=pd.Timestamp(bar["close_time"]).to_pydatetime().replace(tzinfo=timezone.utc),
        open=Decimal(str(bar["open"])),
        high=Decimal(str(bar["high"])),
        low=Decimal(str(bar["low"])),
        close=Decimal(str(bar["close"])),
        volume=Decimal(str(bar["volume"])),
        quote_volume=Decimal(str(bar["quote_volume"])),
        is_final=True,
    ))

    # 1. Try to fill any pending entry
    if state.has_pending_entry():
        _try_fill_entry(state, bar, matrix, cfg, now)

    # 2. Check open position for exit
    closed_trade: Optional[PaperTrade] = None
    if state.has_open_position():
        closed_trade = _check_position_exit(state, bar, matrix, cfg, now)

    # 3. Run strategy pipeline only on the latest bar (not catch-up)
    if not is_catchup and state.is_slot_free():
        # Build features on the full buffer (includes this bar)
        feature_df = build_feature_df(candle_buffer, funding_df, oi_df)

        # Stale check: most recent bar's open_time should be this bar
        last_final_ts = feature_df.iloc[-1]["open_time"]
        if hasattr(last_final_ts, "to_pydatetime"):
            last_final_ts = last_final_ts.to_pydatetime()
        if last_final_ts.tzinfo is None:
            last_final_ts = last_final_ts.replace(tzinfo=timezone.utc)

        if is_data_stale(last_final_ts, cfg.timeframe, now):
            matrix.append(DataQualityEvent(
                venue=cfg.venue,
                symbol=cfg.symbol,
                detected_at=now,
                reason_code=rc.DATA_STALE,
                detail=f"last_final_bar={last_final_ts.isoformat()} now={now.isoformat()}",
                affected_timeframes=[cfg.timeframe],
            ))
        else:
            _run_strategy_pipeline(state, feature_df, bar, matrix, cfg, now, bar_open_time)

    state.last_processed_bar_ts = bar_open_time
    return closed_trade


# ── run_once ───────────────────────────────────────────────────────────────────

def run_once(cfg: PaperRuntimeConfig, now: Optional[datetime] = None) -> dict:
    """
    Single execution pass: fetch latest data, process any new final bars, persist.

    Returns a status dict summarising what happened. Safe to call repeatedly.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    cfg.paper_dir.mkdir(parents=True, exist_ok=True)
    state = load_state(cfg.state_path)
    matrix = MatrixEventLog(log_path=cfg.matrix_log_path)

    # Fetch rolling data
    raw_candles = fetch_recent_candles(cfg.symbol, cfg.timeframe, n=cfg.lookback_bars + 5)
    if raw_candles.empty:
        return {"status": "no_data", "ts": now.isoformat()}

    # Filter to truly final bars
    final_mask = raw_candles["open_time"].apply(
        lambda t: is_bar_final(t.to_pydatetime(), cfg.timeframe, now)
    )
    final_candles = raw_candles[final_mask].reset_index(drop=True)
    if final_candles.empty:
        return {"status": "no_final_bars", "ts": now.isoformat()}

    # Determine which bars are new since last run
    if state.last_processed_bar_ts is not None:
        last_ts = _ensure_utc(state.last_processed_bar_ts)
        new_bars = final_candles[
            final_candles["open_time"] > pd.Timestamp(last_ts)
        ].reset_index(drop=True)
    else:
        # First run: process only the last bar to avoid hours of historical catch-up
        new_bars = final_candles.tail(1).reset_index(drop=True)

    if new_bars.empty:
        return {
            "status": "up_to_date",
            "ts": now.isoformat(),
            "last_bar": state.last_processed_bar_ts.isoformat() if state.last_processed_bar_ts else None,
        }

    # Fetch supporting data (one network round-trip, reused for all new bars)
    funding_df = fetch_recent_funding(cfg.symbol, days=cfg.funding_days)
    oi_df = fetch_recent_oi(cfg.symbol, cfg.timeframe, days=cfg.oi_days)

    # Process new bars in chronological order; only the last is "live" (not catch-up)
    trades_closed: list[PaperTrade] = []
    for i, (_, bar) in enumerate(new_bars.iterrows()):
        is_catchup = i < len(new_bars) - 1

        # Build candle buffer: all final candles up to and including this bar
        bar_open_time = bar["open_time"]
        buffer = final_candles[final_candles["open_time"] <= bar_open_time].copy()

        trade = process_final_bar(
            bar=bar,
            state=state,
            candle_buffer=buffer,
            funding_df=funding_df,
            oi_df=oi_df,
            matrix=matrix,
            cfg=cfg,
            now=now,
            is_catchup=is_catchup,
        )
        if trade is not None:
            append_trade_log(trade, cfg.trade_log_path)
            trades_closed.append(trade)

    save_state(state, cfg.state_path)

    return {
        "status": "ok",
        "ts": now.isoformat(),
        "bars_processed": len(new_bars),
        "trades_closed": len(trades_closed),
        "has_open_position": state.has_open_position(),
        "has_pending_entry": state.has_pending_entry(),
        "equity": str(state.equity),
        "last_bar": state.last_processed_bar_ts.isoformat() if state.last_processed_bar_ts else None,
    }


# ── run_loop ───────────────────────────────────────────────────────────────────

def run_loop(cfg: PaperRuntimeConfig, poll_seconds: int = 60) -> None:
    """
    Poll continuously. Checks for new final bars every poll_seconds.
    Ctrl-C to stop. Status is printed to stdout after each pass.
    """
    print(f"[paper-runtime] starting — symbol={cfg.symbol} tf={cfg.timeframe} poll={poll_seconds}s")
    while True:
        now = datetime.now(timezone.utc)
        try:
            result = run_once(cfg, now=now)
            _print_status(result)
        except Exception as exc:
            print(f"[paper-runtime] ERROR {now.isoformat()} — {exc}")
        time.sleep(poll_seconds)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _bar_open_time(bar: pd.Series) -> datetime:
    ts = bar["open_time"]
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _print_status(result: dict) -> None:
    ts = result.get("ts", "?")
    status = result.get("status", "?")
    if status == "ok":
        bars = result.get("bars_processed", 0)
        trades = result.get("trades_closed", 0)
        pos = "OPEN" if result.get("has_open_position") else ("PENDING" if result.get("has_pending_entry") else "flat")
        equity = result.get("equity", "?")
        print(f"[{ts}] bars={bars} trades_closed={trades} position={pos} equity={equity}")
    else:
        print(f"[{ts}] {status}")
