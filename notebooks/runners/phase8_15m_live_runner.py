"""
15m scalp live runner.

Runs one pass of ema_scalp_15m_v1 against Bybit testnet.
Fetches latest 15m candles, checks for fills/exits, runs strategy if slot is free.

Usage:
    # Run once and exit:
    python notebooks/phase8_15m_live_runner.py --once

    # Poll every 15 minutes continuously:
    python notebooks/phase8_15m_live_runner.py

    # Custom poll interval (seconds):
    python notebooks/phase8_15m_live_runner.py --poll 900

    # Print current status without running:
    python notebooks/phase8_15m_live_runner.py --status

State is written to paper/live/scalp_15m/.
Requires .env with BYBIT_TESTNET_API_KEY + BYBIT_TESTNET_API_SECRET.
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

LIVE_DIR = _root / "paper" / "live" / "scalp_15m"

cfg = PaperRuntimeConfig(
    symbol="BTCUSDT",
    timeframe="15m",
    venue="bybit",
    lookback_bars=300,
    funding_days=14,
    oi_days=14,
    strategy_id="ema_scalp_15m_v1",
    initial_equity=10_000,
    risk_pct="0.0025",
    max_hold_minutes=120,
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

    closed_trades: list[dict] = []
    if cfg.trade_log_path.exists():
        with open(cfg.trade_log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    closed_trades.append(json.loads(line))

    wins      = [t for t in closed_trades if float(t["net_pnl"]) > 0]
    win_rate  = len(wins) / len(closed_trades) if closed_trades else 0.0
    total_pnl = sum(float(t["net_pnl"]) for t in closed_trades)

    print("=" * 60)
    print("  15M SCALP LIVE STATUS  (ema_scalp_15m_v1)")
    print("=" * 60)
    print(f"  As of:          {datetime.now(timezone.utc).isoformat()}")
    print(f"  Equity:         {state.equity} USDT")
    drawdown = (state.peak_equity - state.equity) / state.peak_equity * 100 if state.peak_equity > 0 else 0
    print(f"  Drawdown:       {drawdown:.2f}%")
    print(f"  Total trades:   {len(closed_trades)}")
    print(f"  Win rate:       {win_rate:.1%}")
    print(f"  Net PnL:        {total_pnl:+.2f} USDT")
    print()
    if state.has_open_position():
        pos = state.open_position
        print(f"  OPEN: {pos.side} {pos.symbol}  entry={pos.entry_price}  stop={pos.stop_price}  target={pos.target_price}")
    elif state.has_pending_entry():
        pe = state.pending_entry
        print(f"  PENDING: {pe.side} @ {pe.entry_price}  (bar {pe.signal_bar_open_time.isoformat()})")
    else:
        print("  Position: flat")
    print()
    print(f"  Last bar: {state.last_processed_bar_ts}")
    print(f"  Circuit breaker: {state.circuit_breaker_active}")
    print("=" * 60)

    if closed_trades:
        print()
        print("  RECENT TRADES (last 5):")
        for t in closed_trades[-5:]:
            r   = float(t.get("r_multiple", 0))
            pnl = float(t["net_pnl"])
            print(f"    {t['exit_ts'][:19]}  {t['exit_reason']:15s}  R={r:+.2f}  PnL={pnl:+.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="15m scalp live runner")
    parser.add_argument("--once",   action="store_true", help="Run one pass and exit")
    parser.add_argument("--status", action="store_true", help="Print status and exit")
    parser.add_argument("--poll",   type=int, default=900, help="Poll interval in seconds (default 900 = 15min)")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.once:
        now    = datetime.now(timezone.utc)
        result = run_once(cfg, now=now)
        print(json.dumps(result, indent=2, default=str))
        print()
        print_status()
        return

    run_loop(cfg, poll_seconds=args.poll)


if __name__ == "__main__":
    main()
