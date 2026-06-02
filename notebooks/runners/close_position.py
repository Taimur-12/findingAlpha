"""
Emergency position closer for BTCUSDT on Bybit testnet.

Usage:
    python notebooks/close_position.py              # tries market first, falls back to limit+chase
    python notebooks/close_position.py --limit       # skip market, go straight to limit+chase
    python notebooks/close_position.py --dry-run     # print position only, no orders

Limit+chase: places a limit order 0.5% above current ask (for closing a short),
then re-prices it every 5 seconds until filled or 60 seconds pass.
"""

from __future__ import annotations

import argparse
import sys
import time
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

from finding_alpha.execution.bybit_client import BybitAPIError, BybitClient, BybitClientConfig
from finding_alpha.paper.live_execution import query_position_state

SYMBOL = "BTCUSDT"
CHASE_INTERVAL_S = 5
CHASE_TIMEOUT_S  = 60
SLIPPAGE_PCT     = Decimal("0.005")  # 0.5% above ask when closing short


def _get_best_ask(client: BybitClient) -> Decimal:
    result = client._get("/v5/market/orderbook", {"category": "linear", "symbol": SYMBOL, "limit": 1})
    ask = result.get("a", [])
    if ask:
        return Decimal(ask[0][0])
    raise RuntimeError("Could not fetch order book ask price")


def _check_filled(client: BybitClient, order_link_id: str) -> bool:
    result = client.query_order(symbol=SYMBOL, order_link_id=order_link_id)
    rows = result.get("list", [])
    if rows:
        status = rows[0].get("orderStatus", "")
        print(f"  order status: {status}")
        return status == "Filled"
    return False


def close_market(client: BybitClient, size: Decimal, close_side: str) -> bool:
    print(f"\n→ Attempting market close: {close_side} {size} {SYMBOL}")
    try:
        client.create_order(
            symbol=SYMBOL,
            side=close_side,
            order_type="Market",
            qty=str(size),
            reduce_only=True,
        )
        print("  ✓ Market close submitted successfully")
        return True
    except BybitAPIError as e:
        print(f"  ✗ Market order rejected ({e.ret_code}): {e.ret_msg}")
        return False
    except Exception as e:
        print(f"  ✗ Market order error: {e}")
        return False


def close_limit_chase(client: BybitClient, size: Decimal, close_side: str) -> bool:
    print(f"\n→ Limit+chase close: {close_side} {size} {SYMBOL}")
    link_id = f"emergency-close-{int(time.time())}"
    current_order_id = None
    deadline = time.time() + CHASE_TIMEOUT_S

    while time.time() < deadline:
        ask = _get_best_ask(client)
        # For closing a short (Buy side): price slightly above ask to ensure fill
        limit_price = (ask * (1 + SLIPPAGE_PCT)).quantize(Decimal("0.01"))
        print(f"  ask={ask}  limit={limit_price}  link_id={link_id}")

        if current_order_id is not None:
            # Cancel previous limit before repricing
            try:
                client.cancel_order(symbol=SYMBOL, order_link_id=link_id)
                print("  cancelled previous limit")
            except Exception as e:
                print(f"  cancel warning (may already be filled): {e}")
                if _check_filled(client, link_id):
                    print("  ✓ Already filled during cancel — done")
                    return True

        try:
            result = client.create_order(
                symbol=SYMBOL,
                side=close_side,
                order_type="Limit",
                qty=str(size),
                price=str(limit_price),
                order_link_id=link_id,
                reduce_only=True,
            )
            current_order_id = result.get("orderId")
            print(f"  limit order placed (id={current_order_id})")
        except BybitAPIError as e:
            print(f"  ✗ Limit order rejected ({e.ret_code}): {e.ret_msg}")
            return False
        except Exception as e:
            print(f"  ✗ Limit order error: {e}")
            return False

        time.sleep(CHASE_INTERVAL_S)

        if _check_filled(client, link_id):
            print("  ✓ Limit order filled — done")
            return True

        print("  not filled yet, repricing...")
        link_id = f"emergency-close-{int(time.time())}"

    print("  ✗ Chase timeout — position may still be open. Check Bybit manually.")
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",   action="store_true", help="Skip market, go straight to limit+chase")
    parser.add_argument("--dry-run", action="store_true", help="Print position only, no orders")
    args = parser.parse_args()

    client = BybitClient(BybitClientConfig.from_env())

    print(f"Querying {SYMBOL} position on Bybit testnet...")
    size, side, mark = query_position_state(client, SYMBOL)

    if size == 0 or side is None:
        print("No open position. Nothing to do.")
        return

    print(f"Position found: {side} {size} BTC @ mark ${mark}")

    if args.dry_run:
        print("--dry-run: no orders placed.")
        return

    close_side = "Buy" if side == "Sell" else "Sell"

    if not args.limit:
        success = close_market(client, size, close_side)
        if success:
            print("\nDone. Now run:")
            print("  rm paper/live/scalp_15m/state.json")
            print("  Then press RUN LIVE CYCLE NOW in the dashboard.")
            return
        print("\nMarket close failed. Falling back to limit+chase...")

    success = close_limit_chase(client, size, close_side)
    if success:
        print("\nDone. Now run:")
        print("  rm paper/live/scalp_15m/state.json")
        print("  Then press RUN LIVE CYCLE NOW in the dashboard.")
    else:
        print("\nCould not close automatically. Close manually on Bybit testnet.")


if __name__ == "__main__":
    main()
