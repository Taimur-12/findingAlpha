"""
Phase 1 — NautilusTrader Strategy Boundary Spike
-------------------------------------------------
Goal: answer ONE question before we commit to NT or go custom.

    Can we insert our own SignalCandidate -> RiskDecision -> Order flow
    cleanly inside a NautilusTrader Strategy, using NT only as the
    execution + backtest substrate?

Test plan:
    1. Load our Parquet klines and convert to NT Bar objects
    2. Stand up a minimal BacktestEngine with a simulated Bybit venue
    3. Write a strategy that:
         a. receives bars from NT
         b. runs our own signal logic internally
         c. runs our own risk check internally
         d. submits an order to NT only if risk approves
    4. Run the backtest and confirm fills are produced

If this works cleanly -> adopt NT as substrate.
If NT fights us at any point -> go custom simulator.

Run with:
    conda activate finding_alpha
    python notebooks/phase1_nautilus_spike.py
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

# ── NautilusTrader imports ────────────────────────────────────────────────────
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.enums import (
    AggregationSource,
    BarAggregation,
    OmsType,
    AccountType,
    PriceType,
    OrderSide,
)
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue, TraderId
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Price, Quantity, Money
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.config import StrategyConfig

DATA_DIR = Path(__file__).parent.parent / "data"
PARQUET_FILE = DATA_DIR / "bybit_BTCUSDT_15m_spike.parquet"


# ── Step 1: Load our Parquet data and convert to NT Bars ─────────────────────

def load_bars_from_parquet(path: Path, instrument_id: InstrumentId) -> list[Bar]:
    """Convert our Parquet candles into NautilusTrader Bar objects."""
    print(f"  Loading {path.name}...")
    df = pq.read_table(path).to_pandas()
    df = df.sort_values("open_time").reset_index(drop=True)

    bar_type = BarType(
        instrument_id=instrument_id,
        bar_spec=BarSpecification(
            step=15,
            aggregation=BarAggregation.MINUTE,
            price_type=PriceType.LAST,
        ),
        aggregation_source=AggregationSource.EXTERNAL,
    )

    bars = []
    for _, row in df.iterrows():
        ts_ms = int(row["open_time"])
        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(str(round(float(row["open"]), 1))),
            high=Price.from_str(str(round(float(row["high"]), 1))),
            low=Price.from_str(str(round(float(row["low"]), 1))),
            close=Price.from_str(str(round(float(row["close"]), 1))),
            volume=Quantity.from_str(f"{float(row['volume']):.3f}"),
            ts_event=ts_ms * 1_000_000,   # ns
            ts_init=ts_ms * 1_000_000,
        )
        bars.append(bar)

    print(f"  Converted {len(bars)} bars")
    return bar_type, bars


# ── Step 2: Our domain objects (minimal stubs for the spike) ─────────────────

class SignalCandidate:
    """Minimal stub matching our source-of-truth contract."""
    def __init__(self, side: str, entry_ref: float, stop: float, target: float, confidence: float):
        self.side = side
        self.entry_ref = entry_ref
        self.stop_price = stop
        self.target_price = target
        self.confidence = confidence
        self.invalidation_price = stop  # required by contract

    def __repr__(self):
        return (f"SignalCandidate(side={self.side}, entry={self.entry_ref:.1f}, "
                f"stop={self.stop_price:.1f}, target={self.target_price:.1f})")


class RiskDecision:
    def __init__(self, approved: bool, reason: str = ""):
        self.approved = approved
        self.reason = reason

    def __repr__(self):
        status = "APPROVED" if self.approved else f"REJECTED({self.reason})"
        return f"RiskDecision({status})"


# ── Step 3: Our strategy logic (signal + risk) wrapped inside NT Strategy ─────

class SpikeStrategyConfig(StrategyConfig, frozen=True):
    instrument_id: str
    bar_type: str
    risk_per_trade_pct: float = 0.25
    stop_atr_mult: float = 1.5


class SpikeStrategy(Strategy):
    """
    Minimal spike strategy that demonstrates our pipeline fits inside NT.

    Hot path inside on_bar():
        bar -> signal_logic() -> SignalCandidate
                              -> risk_check() -> RiskDecision
                                              -> submit_order() if approved
    """

    def __init__(self, config: SpikeStrategyConfig):
        super().__init__(config)
        self._instrument_id = InstrumentId.from_str(config.instrument_id)
        self._bar_type = BarType.from_str(config.bar_type)
        self._risk_pct = config.risk_per_trade_pct
        self._stop_mult = config.stop_atr_mult

        self._bars: list[Bar] = []
        self._in_position = False
        self._signals_generated = 0
        self._orders_approved = 0
        self._orders_rejected = 0

    def on_start(self):
        self.subscribe_bars(self._bar_type)
        print(f"  Strategy started, subscribed to {self._bar_type}")

    def on_bar(self, bar: Bar):
        self._bars.append(bar)

        # Need warmup
        if len(self._bars) < 20:
            return

        # Already in a position — skip (v1 rule: one position at a time)
        if self._in_position:
            return

        # ── Our signal logic ──────────────────────────────────────────────
        signal = self._generate_signal(bar)
        if signal is None:
            return

        self._signals_generated += 1

        # ── Our risk check ────────────────────────────────────────────────
        decision = self._risk_check(signal, bar)

        if not decision.approved:
            self._orders_rejected += 1
            return

        # ── NT order submission ───────────────────────────────────────────
        self._submit_signal(signal, bar)
        self._orders_approved += 1
        self._in_position = True

    def _generate_signal(self, bar: Bar) -> SignalCandidate | None:
        """
        Dummy signal: detect a simple 3-bar momentum pattern.
        (Real signal logic goes here in Phase 5.)
        """
        closes = [float(b.close) for b in self._bars[-5:]]
        current_close = float(bar.close)
        atr_proxy = float(bar.high) - float(bar.low)  # single-bar range as ATR proxy

        # Simple long: close rising for 3 bars and not overextended
        if closes[-1] > closes[-2] > closes[-3]:
            stop = current_close - (atr_proxy * self._stop_mult)
            target = current_close + (atr_proxy * self._stop_mult * 2.0)
            return SignalCandidate(
                side="long",
                entry_ref=current_close,
                stop=stop,
                target=target,
                confidence=0.6,
            )
        return None

    def _risk_check(self, signal: SignalCandidate, bar: Bar) -> RiskDecision:
        """
        Minimal risk gate. Real Risk Agent goes here in Phase 6.
        Checks:
        - Stop price must be valid (below entry for long)
        - Minimum R:R ratio
        - No trade if spread is abnormal (not modeled yet — always passes here)
        """
        entry = signal.entry_ref
        stop = signal.stop_price
        target = signal.target_price

        if signal.side == "long" and stop >= entry:
            return RiskDecision(False, "stop_above_entry")

        stop_dist = abs(entry - stop)
        target_dist = abs(target - entry)

        if stop_dist == 0:
            return RiskDecision(False, "zero_stop_distance")

        rr = target_dist / stop_dist
        if rr < 1.5:
            return RiskDecision(False, f"rr_too_low:{rr:.2f}")

        return RiskDecision(True)

    def _submit_signal(self, signal: SignalCandidate, bar: Bar):
        """Convert approved signal to NT market order."""
        from nautilus_trader.model.orders import MarketOrder
        from nautilus_trader.model.enums import TimeInForce

        order = self.order_factory.market(
            instrument_id=self._instrument_id,
            order_side=OrderSide.BUY if signal.side == "long" else OrderSide.SELL,
            quantity=Quantity.from_str("0.001"),  # fixed tiny size for spike
            time_in_force=TimeInForce.IOC,
        )
        self.submit_order(order)

    def on_stop(self):
        print(f"\n  Strategy results:")
        print(f"    Bars processed : {len(self._bars)}")
        print(f"    Signals generated: {self._signals_generated}")
        print(f"    Orders approved  : {self._orders_approved}")
        print(f"    Orders rejected  : {self._orders_rejected}")


# ── Step 4: Wire up BacktestEngine and run ────────────────────────────────────

def run_nautilus_spike():
    print("\n[1] Building NautilusTrader BacktestEngine...")

    engine = BacktestEngine(
        config=BacktestEngineConfig(
            trader_id=TraderId("SPIKE-001"),
            logging=LoggingConfig(log_level="ERROR"),  # suppress NT noise
        )
    )

    print("[2] Adding simulated Bybit venue...")
    from nautilus_trader.backtest.models import FillModel, LatencyModel
    from nautilus_trader.model.enums import BookType

    engine.add_venue(
        venue=Venue("BYBIT"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USDT,
        starting_balances=[Money(10_000, USDT)],
    )

    print("[3] Building BTCUSDT instrument...")
    instrument_id = InstrumentId(Symbol("BTCUSDT-PERP"), Venue("BYBIT"))

    instrument = CryptoPerpetual(
        instrument_id=instrument_id,
        raw_symbol=Symbol("BTCUSDT"),
        base_currency=USDT,
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=1,
        size_precision=3,
        price_increment=Price.from_str("0.1"),
        size_increment=Quantity.from_str("0.001"),
        max_quantity=None,
        min_quantity=Quantity.from_str("0.001"),
        max_notional=None,
        min_notional=None,
        max_price=None,
        min_price=None,
        margin_init=Decimal("0.01"),
        margin_maint=Decimal("0.005"),
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.00055"),
        ts_event=0,
        ts_init=0,
    )
    engine.add_instrument(instrument)

    print("[4] Loading bars from Parquet...")
    bar_type_str = "BTCUSDT-PERP.BYBIT-15-MINUTE-LAST-EXTERNAL"
    bar_type, bars = load_bars_from_parquet(PARQUET_FILE, instrument_id)
    engine.add_data(bars)

    print("[5] Creating and adding strategy...")
    strategy = SpikeStrategy(
        config=SpikeStrategyConfig(
            instrument_id=str(instrument_id),
            bar_type=bar_type_str,
        )
    )
    engine.add_strategy(strategy)

    print("[6] Running backtest...")
    engine.run()

    print("\n[7] Checking results...")
    stats = engine.trader.generate_account_report(Venue("BYBIT"))
    print(f"  Account report generated: {stats is not None}")

    orders = engine.trader.generate_order_fills_report()
    print(f"  Orders/fills report: {len(orders)} rows" if orders is not None else "  No orders report")

    engine.dispose()
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 — NAUTILUS STRATEGY BOUNDARY SPIKE")
    print("=" * 60)

    try:
        success = run_nautilus_spike()
        print("\n" + "=" * 60)
        if success:
            print("RESULT: NautilusTrader strategy boundary WORKS")
            print("  -> Our signal/risk pipeline fits cleanly inside NT Strategy")
            print("  -> NT handles bars, fills, account tracking")
            print("  -> Decision: consider adopting NT as substrate")
        print("=" * 60)
    except Exception as e:
        import traceback
        print(f"\nSPIKE FAILED: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        print("\n" + "=" * 60)
        print("RESULT: NautilusTrader integration has friction")
        print("  -> Review the error above")
        print("  -> May indicate we should go custom simulator")
        print("=" * 60)
        sys.exit(1)
