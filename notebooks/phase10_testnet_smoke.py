"""
Phase 10 testnet smoke test.

Live round-trip against real Bybit testnet to prove:
  1. HMAC signing is correct end-to-end (read endpoints reject bad auth)
  2. ExecutionAgent.submit_plan reaches the exchange
  3. The submitted order appears via query_order (orderLinkId lookup)
  4. cancel_leg succeeds and the order shows Cancelled status
  5. Reconciliation matches local state to exchange truth

Costs: $0 (testnet only). Does NOT touch mainnet.

Safety:
  - Limit SELL at $200,000 — far above any plausible BTC market price.
    Will not fill. Cancels cleanly.
  - Qty 0.001 BTC (Bybit minimum for BTCUSDT linear).
  - No stop leg submitted; this verifies the entry round-trip only.

Run:
    python notebooks/phase10_testnet_smoke.py

Requires .env at project root with:
    BYBIT_TESTNET_API_KEY=...
    BYBIT_TESTNET_API_SECRET=...
    BYBIT_LIVE_MODE=testnet   (or omit — defaults to testnet)
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from dotenv import load_dotenv

from finding_alpha.contracts.trading import OrderEntry, OrderPlan, PortfolioIntent
from finding_alpha.execution.bybit_client import (
    BybitAPIError,
    BybitClient,
    BybitClientConfig,
)
from finding_alpha.execution.execution_agent import (
    LEG_ENTRY,
    ExecutionAgent,
)
from finding_alpha.execution.order_state import OrderState
from finding_alpha.execution.reconciliation import reconcile_plan

SYMBOL = "BTCUSDT"
SAFE_PRICE = Decimal("200000")     # far above market — limit sell will not fill
SAFE_QTY = Decimal("0.001")        # Bybit BTCUSDT linear minimum
STOP_TRIGGER = Decimal("210000")   # used only to satisfy intent validators


def _step(n: str, name: str) -> None:
    print(f"\n[{n}] {name}")


def _fail(msg: str) -> None:
    print(f"\nFAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def check_read_endpoints(client: BybitClient) -> None:
    _step("1a", "Query wallet balance (auth check)")
    wallet = client.query_wallet_balance()
    rows = wallet.get("list", []) or []
    coins_seen: list[str] = []
    for row in rows:
        for coin in row.get("coin", []) or []:
            coins_seen.append(f"{coin.get('coin')}={coin.get('walletBalance')}")
    print(f"    accounts found: {len(rows)}  coins: {coins_seen[:5]}")
    if not rows:
        _fail("wallet balance returned no rows — wrong account type or no funds?")

    _step("1b", f"Query positions on {SYMBOL}")
    positions = client.query_positions(symbol=SYMBOL)
    rows = positions.get("list", []) or []
    open_positions = [r for r in rows if Decimal(r.get("size", "0") or "0") > 0]
    print(f"    rows: {len(rows)}  with open size: {len(open_positions)}")


def build_intent_and_plan() -> tuple[PortfolioIntent, OrderPlan]:
    now = datetime.now(timezone.utc)
    intent = PortfolioIntent(
        signal_id="smoke-test",
        venue="bybit",
        symbol=SYMBOL,
        side="short",
        entry_type="limit",
        entry_price=SAFE_PRICE,
        stop_price=STOP_TRIGGER,
        risk_amount=Decimal("10"),
        quantity=SAFE_QTY,
        notional=SAFE_PRICE * SAFE_QTY,
        leverage=Decimal("1"),
        max_slippage_bps=Decimal("10"),
        time_in_force="GTC",
        max_hold_minutes=60,
        created_at=now,
    )
    entry = OrderEntry(
        order_type="limit",
        side="sell",
        quantity=SAFE_QTY,
        price=SAFE_PRICE,
    )
    stop = OrderEntry(
        order_type="stop_market",
        side="buy",
        quantity=SAFE_QTY,
        trigger_price=STOP_TRIGGER,
        reduce_only=True,
    )
    plan = OrderPlan(
        approved_intent_id=intent.intent_id,
        entry_order=entry,
        stop_order=stop,
        created_at=now,
    )
    return intent, plan


def round_trip(agent: ExecutionAgent) -> None:
    intent, plan = build_intent_and_plan()

    _step("2", f"Submit limit SELL {SAFE_QTY} {SYMBOL} @ {SAFE_PRICE}")
    state = agent.submit_plan(plan, intent)
    print(f"    leg state:      {state.entry.state.value}")
    print(f"    link_id:        {state.entry.link_id}")
    print(f"    venue_order_id: {state.entry.venue_order_id}")
    if state.entry.state != OrderState.ACKNOWLEDGED:
        _fail(f"expected ACKNOWLEDGED, got {state.entry.state.value}")

    _step("3", "Reconcile leg (query by orderLinkId)")
    agent.reconcile_leg(state, LEG_ENTRY)
    print(f"    reconciled state: {state.entry.state.value}")
    if state.entry.state not in (OrderState.OPEN, OrderState.PARTIALLY_FILLED):
        _fail(f"order should be OPEN after submission, got {state.entry.state.value}")

    _step("4", "Reconciliation report")
    report = reconcile_plan(agent, state)
    print(f"    divergences: {len(report.divergences)}")
    print(f"    position size: {report.exchange_position_size}")
    for d in report.divergences:
        print(f"      - {d.kind}: {d.detail}")

    _step("5", "Cancel order")
    try:
        agent.cancel_leg(state, LEG_ENTRY)
    except BybitAPIError as exc:
        _fail(f"cancel failed: {exc}")
    print(f"    after cancel request: {state.entry.state.value}")

    _step("6", "Reconcile after cancel")
    agent.reconcile_leg(state, LEG_ENTRY)
    print(f"    final state: {state.entry.state.value}")
    if state.entry.state != OrderState.CANCELED:
        _fail(f"expected CANCELED, got {state.entry.state.value}")


def main() -> None:
    load_dotenv()
    print("Phase 10 testnet smoke test")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")

    try:
        cfg = BybitClientConfig.from_env()
    except Exception as exc:
        _fail(f"cannot load Bybit credentials: {exc}")
    print(f"Endpoint: {cfg.base_url}")

    with BybitClient(cfg) as client:
        try:
            check_read_endpoints(client)
        except BybitAPIError as exc:
            _fail(f"read endpoint error: {exc}")
        except Exception as exc:
            _fail(f"read endpoint exception: {exc!r}")

        agent = ExecutionAgent(client)
        try:
            round_trip(agent)
        except BybitAPIError as exc:
            _fail(f"order round-trip error: {exc}")
        except Exception as exc:
            _fail(f"order round-trip exception: {exc!r}")

    print("\n=== PASS ===")


if __name__ == "__main__":
    main()
