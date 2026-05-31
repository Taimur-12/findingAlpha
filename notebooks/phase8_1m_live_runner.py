"""
1m scalp live runner — ema_scalp_1m_v1.

Polls every 60 seconds (one 1m bar). Run this in a terminal during demos
so trades happen automatically without clicking the dashboard button.

Usage:
    python notebooks/phase8_1m_live_runner.py           # poll every 60s
    python notebooks/phase8_1m_live_runner.py --once    # single pass
    python notebooks/phase8_1m_live_runner.py --status  # show state
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))

from dotenv import load_dotenv
load_dotenv(_root / ".env", override=False)

from finding_alpha.paper.runtime import PaperRuntimeConfig, run_loop, run_once
from finding_alpha.paper.state import load_state

LIVE_DIR = _root / "paper" / "live" / "scalp_1m"

cfg = PaperRuntimeConfig(
    symbol="BTCUSDT",
    timeframe="1m",
    venue="bybit",
    lookback_bars=300,
    funding_days=3,
    oi_days=3,
    strategy_id="ema_scalp_1m_v1",
    initial_equity=10_000,
    risk_pct="0.0025",
    max_hold_minutes=10,
    maker_fee_bps="2.0",
    taker_fee_bps="5.5",
    stop_slippage_bps="10",
    qty_precision=3,
    min_notional=10,
    max_leverage=10,
    daily_loss_limit_pct="0.03",
    max_drawdown_pct="0.10",
    paper_dir=LIVE_DIR,
    execution_mode="live",
)


def print_status() -> None:
    state = load_state(cfg.state_path)
    closed: list[dict] = []
    if cfg.trade_log_path.exists():
        with open(cfg.trade_log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    closed.append(json.loads(line))

    wins = [t for t in closed if float(t["net_pnl"]) > 0]
    win_rate = len(wins) / len(closed) if closed else 0.0
    total_pnl = sum(float(t["net_pnl"]) for t in closed)

    print("=" * 60)
    print("  1M SCALP LIVE STATUS  (ema_scalp_1m_v1)")
    print("=" * 60)
    print(f"  Equity:      {state.equity} USDT")
    print(f"  Trades:      {len(closed)}  Win rate: {win_rate:.1%}  Net PnL: {total_pnl:+.2f}")
    print(f"  Last bar:    {state.last_processed_bar_ts}")
    if state.has_open_position():
        pos = state.open_position
        print(f"  OPEN: {pos.side} entry={pos.entry_price} stop={pos.stop_price}")
    else:
        print("  Position:    flat")
    print("=" * 60)
    if closed:
        print("  RECENT TRADES:")
        for t in closed[-5:]:
            print(f"    {t['exit_ts'][:19]}  {t['exit_reason']:12s}  R={float(t.get('r_multiple',0)):+.2f}  {float(t['net_pnl']):+.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="1m scalp live runner")
    parser.add_argument("--once",   action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--poll",   type=int, default=60)
    args = parser.parse_args()

    if args.status:
        print_status()
        return
    if args.once:
        result = run_once(cfg, now=datetime.now(timezone.utc))
        print(json.dumps(result, indent=2, default=str))
        print()
        print_status()
        return

    print("Running ema_scalp_1m_v1 — polling every 60s. Ctrl+C to stop.")
    run_loop(cfg, poll_seconds=args.poll)


if __name__ == "__main__":
    main()
